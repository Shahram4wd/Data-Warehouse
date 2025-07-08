# Data Warehouse CRM Integration Standards & Architecture Guide
**Version**: 3.0  
**Last Updated**: July 7, 2025  
**Purpose**: Unified architecture and implementation standards for all CRM integrations

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Base Class Patterns](#base-class-patterns)
3. [Sync History Management](#sync-history-management)
4. [Error Handling Standards](#error-handling-standards)
5. [Configuration Management](#configuration-management)
6. [Data Validation Framework](#data-validation-framework)
7. [Performance Optimization](#performance-optimization)
8. [Testing Standards](#testing-standards)
9. [Implementation Guidelines](#implementation-guidelines)
10. [CRM-Specific Recommendations](#crm-specific-recommendations)

## Architecture Overview

### Core Principles
1. **Unified Base Classes**: All CRM integrations inherit from common base classes
2. **Common Sync History**: Single model tracks all sync operations across CRMs
3. **Standardized Error Handling**: Consistent error patterns and recovery strategies
4. **Configuration-Driven**: Dynamic field mappings and sync configurations
5. **Async-First**: All operations use async patterns for better performance
6. **Comprehensive Testing**: Unit and integration tests for all components

### Directory Structure
```
ingestion/
├── base/
│   ├── __init__.py
│   ├── sync_engine.py          # Base sync engine
│   ├── client.py               # Base API client
│   ├── processor.py            # Base data processor
│   └── exceptions.py           # Custom exceptions
├── models/
│   ├── common.py               # Common models (SyncHistory, etc.)
│   ├── genius.py               # Genius-specific models
│   ├── hubspot.py              # HubSpot-specific models
│   └── ...
├── sync/
│   ├── genius/
│   │   ├── __init__.py
│   │   ├── sync_engine.py      # Genius sync implementation
│   │   ├── client.py           # Genius API client
│   │   └── processors.py       # Genius data processors
│   ├── hubspot/
│   │   ├── __init__.py
│   │   ├── sync_engine.py      # HubSpot sync implementation
│   │   ├── client.py           # HubSpot API client
│   │   └── processors.py       # HubSpot data processors
│   └── ...
├── management/
│   └── commands/
│       ├── sync_genius_*.py    # Genius sync commands
│       ├── sync_hubspot_*.py   # HubSpot sync commands
│       └── ...
└── tests/
    ├── unit/
    │   ├── test_base/
    │   ├── test_genius/
    │   ├── test_hubspot/
    │   └── ...
    └── integration/
        ├── test_genius_sync/
        ├── test_hubspot_sync/
        └── ...
```

## Base Class Patterns

### 1. Universal Sync Engine Base Class
```python
# filepath: ingestion/base/sync_engine.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
from django.db import transaction
from django.utils import timezone
from ingestion.models.common import SyncHistory
from ingestion.base.exceptions import SyncException, ValidationException

class BaseSyncEngine(ABC):
    """Universal base class for all CRM sync operations"""
    
    def __init__(self, crm_source: str, sync_type: str, **kwargs):
        self.crm_source = crm_source
        self.sync_type = sync_type
        self.batch_size = kwargs.get('batch_size', self.get_default_batch_size())
        self.dry_run = kwargs.get('dry_run', False)
        self.sync_history = None
        self.client = None
        self.processor = None
        
    @abstractmethod
    def get_default_batch_size(self) -> int:
        """Return default batch size for this sync type"""
        pass
        
    @abstractmethod
    async def initialize_client(self) -> None:
        """Initialize the API client or database connection"""
        pass
        
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch data from source system in batches"""
        pass
        
    @abstractmethod
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw data to target format"""
        pass
        
    @abstractmethod
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        pass
        
    @abstractmethod
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data to database"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        pass
    
    # Common sync workflow methods
    async def start_sync(self, **kwargs) -> SyncHistory:
        """Start sync operation and create history record"""
        self.sync_history = SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.sync_type,
            endpoint=kwargs.get('endpoint'),
            start_time=timezone.now(),
            status='running',
            configuration=kwargs
        )
        return self.sync_history
    
    async def complete_sync(self, results: Dict[str, int], error: Optional[str] = None):
        """Complete sync operation and update history"""
        if self.sync_history:
            self.sync_history.end_time = timezone.now()
            self.sync_history.status = 'failed' if error else 'success'
            self.sync_history.records_processed = results.get('processed', 0)
            self.sync_history.records_created = results.get('created', 0)
            self.sync_history.records_updated = results.get('updated', 0)
            self.sync_history.records_failed = results.get('failed', 0)
            self.sync_history.error_message = error
            self.sync_history.performance_metrics = {
                'duration_seconds': (self.sync_history.end_time - self.sync_history.start_time).total_seconds(),
                'records_per_second': results.get('processed', 0) / max(1, (self.sync_history.end_time - self.sync_history.start_time).total_seconds())
            }
            await self.sync_history.asave()
    
    async def run_sync(self, **kwargs) -> SyncHistory:
        """Main sync execution method"""
        history = await self.start_sync(**kwargs)
        results = {'processed': 0, 'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            await self.initialize_client()
            
            async for batch in self.fetch_data(**kwargs):
                try:
                    # Transform data
                    transformed_batch = await self.transform_data(batch)
                    
                    # Validate data
                    validated_batch = await self.validate_data(transformed_batch)
                    
                    # Save data
                    if not self.dry_run:
                        batch_results = await self.save_data(validated_batch)
                        for key, value in batch_results.items():
                            results[key] += value
                    
                    results['processed'] += len(batch)
                    
                except Exception as e:
                    results['failed'] += len(batch)
                    await self.handle_batch_error(batch, e)
            
            await self.complete_sync(results)
            
        except Exception as e:
            await self.complete_sync(results, str(e))
            raise
        finally:
            await self.cleanup()
        
        return history
    
    async def handle_batch_error(self, batch: List[Dict], error: Exception):
        """Handle batch processing errors with fallback to individual processing"""
        for record in batch:
            try:
                transformed = await self.transform_data([record])
                validated = await self.validate_data(transformed)
                if not self.dry_run:
                    await self.save_data(validated)
            except Exception as individual_error:
                # Log individual record error
                pass
```

### 2. Base API Client
```python
# filepath: ingestion/base/client.py
from abc import ABC, abstractmethod
import aiohttp
import asyncio
from typing import Dict, Any, Optional, List
from ingestion.base.exceptions import APIException, RateLimitException

class BaseAPIClient(ABC):
    """Base class for all API clients"""
    
    def __init__(self, base_url: str, timeout: int = 30):
        self.base_url = base_url
        self.timeout = timeout
        self.session = None
        self.headers = {}
        
    @abstractmethod
    async def authenticate(self) -> None:
        """Authenticate with the API"""
        pass
        
    @abstractmethod
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return rate limit headers for this API"""
        pass
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=self.timeout),
            headers=self.headers
        )
        await self.authenticate()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    async def make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """Make HTTP request with retry logic"""
        url = f"{self.base_url.rstrip('/')}/{endpoint.lstrip('/')}"
        
        for attempt in range(3):
            try:
                async with self.session.request(method, url, **kwargs) as response:
                    if response.status == 429:
                        await self.handle_rate_limit(response)
                        continue
                    
                    if response.status >= 400:
                        raise APIException(f"HTTP {response.status}: {await response.text()}")
                    
                    return await response.json()
                    
            except aiohttp.ClientError as e:
                if attempt == 2:
                    raise APIException(f"Request failed after 3 attempts: {e}")
                await asyncio.sleep(2 ** attempt)
    
    async def handle_rate_limit(self, response: aiohttp.ClientResponse):
        """Handle rate limiting"""
        retry_after = int(response.headers.get('Retry-After', 60))
        await asyncio.sleep(retry_after)
```

### 3. Base Data Processor
```python
# filepath: ingestion/base/processor.py
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from django.db import transaction
from ingestion.base.exceptions import ValidationException

class BaseDataProcessor(ABC):
    """Base class for data processing operations"""
    
    def __init__(self, model_class, **kwargs):
        self.model_class = model_class
        self.batch_size = kwargs.get('batch_size', 500)
        self.field_mappings = self.get_field_mappings()
        
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from source to target"""
        pass
        
    @abstractmethod
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single record"""
        pass
        
    @abstractmethod
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single record"""
        pass
    
    async def process_batch(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process a batch of records"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Transform records
        transformed_records = []
        for record in records:
            try:
                transformed = self.transform_record(record)
                validated = self.validate_record(transformed)
                transformed_records.append(validated)
            except Exception as e:
                results['failed'] += 1
                continue
        
        # Save records
        if transformed_records:
            batch_results = await self.save_records(transformed_records)
            results['created'] += batch_results.get('created', 0)
            results['updated'] += batch_results.get('updated', 0)
            results['failed'] += batch_results.get('failed', 0)
        
        return results
    
    async def save_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save records to database with bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # Bulk create/update logic
            existing_ids = set()
            if hasattr(self.model_class, 'id'):
                existing_ids = set(
                    self.model_class.objects.filter(
                        id__in=[r.get('id') for r in records if r.get('id')]
                    ).values_list('id', flat=True)
                )
            
            to_create = []
            to_update = []
            
            for record in records:
                if record.get('id') in existing_ids:
                    to_update.append(record)
                else:
                    to_create.append(record)
            
            # Bulk create
            if to_create:
                created_objects = await self.bulk_create(to_create)
                results['created'] = len(created_objects)
            
            # Bulk update
            if to_update:
                updated_count = await self.bulk_update(to_update)
                results['updated'] = updated_count
                
        except Exception as e:
            # Fallback to individual saves
            individual_results = await self.save_individual_records(records)
            results.update(individual_results)
        
        return results
    
    async def bulk_create(self, records: List[Dict[str, Any]]) -> List:
        """Bulk create records"""
        objects = [self.model_class(**record) for record in records]
        return await self.model_class.objects.abulk_create(objects, batch_size=self.batch_size)
    
    async def bulk_update(self, records: List[Dict[str, Any]]) -> int:
        """Bulk update records"""
        # Implementation depends on specific update logic
        pass
    
    async def save_individual_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Fallback to individual record saves"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in records:
            try:
                obj, created = await self.model_class.objects.aget_or_create(
                    id=record.get('id'),
                    defaults=record
                )
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
            except Exception:
                results['failed'] += 1
        
        return results
```

## Sync History Management

### Common Sync History Model
```python
# filepath: ingestion/models/common.py
from django.db import models
from django.utils import timezone

class SyncHistory(models.Model):
    """Universal sync history for all CRM operations"""
    
    # Sync identification
    crm_source = models.CharField(max_length=50)  # 'genius', 'hubspot', etc.
    sync_type = models.CharField(max_length=100)  # 'appointments', 'contacts', etc.
    endpoint = models.CharField(max_length=200, null=True, blank=True)
    
    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ])
    
    # Metrics
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(null=True, blank=True)
    
    # Configuration and performance
    configuration = models.JSONField(default=dict)
    performance_metrics = models.JSONField(default=dict)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sync_history'
        indexes = [
            models.Index(fields=['crm_source', 'sync_type']),
            models.Index(fields=['start_time']),
            models.Index(fields=['status']),
        ]
        
    def __str__(self):
        return f"{self.crm_source} {self.sync_type} - {self.status}"
    
    @property
    def duration_seconds(self):
        """Calculate sync duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def records_per_second(self):
        """Calculate processing rate"""
        duration = self.duration_seconds
        if duration and duration > 0:
            return self.records_processed / duration
        return 0
```

## Error Handling Standards

### Custom Exceptions
```python
# filepath: ingestion/base/exceptions.py
class SyncException(Exception):
    """Base exception for sync operations"""
    pass

class ValidationException(SyncException):
    """Exception raised during data validation"""
    pass

class APIException(SyncException):
    """Exception raised during API operations"""
    pass

class RateLimitException(APIException):
    """Exception raised when rate limit is exceeded"""
    pass

class DatabaseException(SyncException):
    """Exception raised during database operations"""
    pass

class ConfigurationException(SyncException):
    """Exception raised for configuration issues"""
    pass
```

### Error Handling Patterns
```python
# Retry with exponential backoff
async def retry_with_backoff(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return await func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

# Bulk operation with individual fallback
async def save_with_fallback(self, records):
    try:
        return await self.bulk_save(records)
    except Exception as bulk_error:
        # Log bulk error
        individual_results = {'created': 0, 'updated': 0, 'failed': 0}
        for record in records:
            try:
                result = await self.save_individual(record)
                individual_results[result] += 1
            except Exception as individual_error:
                individual_results['failed'] += 1
                # Log individual error
        return individual_results
```

## Configuration Management

### Dynamic Configuration System
```python
# filepath: ingestion/models/common.py
class SyncConfiguration(models.Model):
    """Dynamic sync configuration"""
    
    crm_source = models.CharField(max_length=50)
    sync_type = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    # Sync settings
    batch_size = models.IntegerField(default=500)
    retry_count = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=1)  # seconds
    
    # Field mappings
    field_mappings = models.JSONField(default=dict)
    
    # API settings
    api_settings = models.JSONField(default=dict)
    
    # Scheduling
    schedule_enabled = models.BooleanField(default=False)
    schedule_cron = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['crm_source', 'sync_type']
        
    def __str__(self):
        return f"{self.crm_source} {self.sync_type} Config"

class APICredential(models.Model):
    """Encrypted API credentials"""
    
    crm_source = models.CharField(max_length=50, unique=True)
    credentials = models.JSONField()  # Encrypted
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.crm_source} Credentials"
```

## Data Validation Framework

### Validation Rules
```python
# filepath: ingestion/base/validators.py
from abc import ABC, abstractmethod
import re
from typing import Any, Dict, List, Optional

class BaseValidator(ABC):
    """Base validator class"""
    
    @abstractmethod
    def validate(self, value: Any) -> Any:
        """Validate and return cleaned value"""
        pass
        
    @abstractmethod
    def get_error_message(self) -> str:
        """Return validation error message"""
        pass

class PhoneValidator(BaseValidator):
    """Phone number validator"""
    
    def validate(self, value: Any) -> Optional[str]:
        if not value:
            return None
        
        # Remove all non-digit characters
        phone = re.sub(r'[^\d]', '', str(value))
        
        # Validate length
        if len(phone) < 10 or len(phone) > 15:
            raise ValidationException(f"Invalid phone number length: {value}")
        
        return phone
    
    def get_error_message(self) -> str:
        return "Phone number must be 10-15 digits"

class EmailValidator(BaseValidator):
    """Email validator"""
    
    def validate(self, value: Any) -> Optional[str]:
        if not value:
            return None
        
        email = str(value).strip().lower()
        
        # Basic email validation
        if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
            raise ValidationException(f"Invalid email format: {value}")
        
        return email
    
    def get_error_message(self) -> str:
        return "Invalid email format"

class DateValidator(BaseValidator):
    """Date validator"""
    
    def __init__(self, formats: List[str] = None):
        self.formats = formats or [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%fZ',
        ]
    
    def validate(self, value: Any) -> Optional[str]:
        if not value:
            return None
        
        from datetime import datetime
        
        for fmt in self.formats:
            try:
                parsed = datetime.strptime(str(value), fmt)
                return parsed.isoformat()
            except ValueError:
                continue
        
        raise ValidationException(f"Invalid date format: {value}")
    
    def get_error_message(self) -> str:
        return f"Date must be in one of these formats: {', '.join(self.formats)}"
```

## Performance Optimization

### Performance Standards
```python
# Batch processing settings
DEFAULT_BATCH_SIZES = {
    'genius': 500,
    'hubspot': 100,
    'marketsharp': 200,
    'activeprospect': 100,
    'salespro': 500,
    'arrivy': 1000,
}

# Connection pooling
ASYNC_CONNECTION_SETTINGS = {
    'pool_size': 10,
    'max_overflow': 20,
    'pool_timeout': 30,
    'pool_recycle': 3600,
}

# Memory management
MEMORY_MANAGEMENT = {
    'max_batch_memory_mb': 100,
    'streaming_threshold': 10000,
    'chunk_size': 1000,
}
```

### Async Processing Patterns
```python
# Concurrent batch processing
async def process_batches_concurrently(self, batches: List[List[Dict]], max_concurrent: int = 5):
    semaphore = asyncio.Semaphore(max_concurrent)
    
    async def process_single_batch(batch):
        async with semaphore:
            return await self.process_batch(batch)
    
    tasks = [process_single_batch(batch) for batch in batches]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    return results
```

## Testing Standards

### Unit Test Structure
```python
# filepath: ingestion/tests/unit/test_base/test_sync_engine.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory

class TestBaseSyncEngine:
    """Test suite for BaseSyncEngine"""
    
    @pytest.fixture
    def sync_engine(self):
        class TestSyncEngine(BaseSyncEngine):
            def get_default_batch_size(self):
                return 100
            
            async def initialize_client(self):
                pass
            
            async def fetch_data(self, **kwargs):
                yield [{'id': 1, 'name': 'Test'}]
            
            async def transform_data(self, raw_data):
                return raw_data
            
            async def validate_data(self, data):
                return data
            
            async def save_data(self, validated_data):
                return {'created': len(validated_data), 'updated': 0, 'failed': 0}
            
            async def cleanup(self):
                pass
        
        return TestSyncEngine('test_crm', 'test_sync')
    
    @pytest.mark.asyncio
    async def test_sync_workflow(self, sync_engine):
        """Test complete sync workflow"""
        history = await sync_engine.run_sync()
        
        assert history.crm_source == 'test_crm'
        assert history.sync_type == 'test_sync'
        assert history.status == 'success'
        assert history.records_processed == 1
        assert history.records_created == 1
    
    @pytest.mark.asyncio
    async def test_error_handling(self, sync_engine):
        """Test error handling in sync process"""
        sync_engine.fetch_data = AsyncMock(side_effect=Exception("Test error"))
        
        with pytest.raises(Exception):
            await sync_engine.run_sync()
        
        # Verify error was recorded
        history = await SyncHistory.objects.aget(
            crm_source='test_crm',
            sync_type='test_sync'
        )
        assert history.status == 'failed'
        assert 'Test error' in history.error_message
```

### Integration Test Structure
```python
# filepath: ingestion/tests/integration/test_genius_sync/test_appointments.py
import pytest
from unittest.mock import patch, AsyncMock
from ingestion.sync.genius.sync_engine import GeniusAppointmentSyncEngine
from ingestion.models.genius import Genius_Appointment

class TestGeniusAppointmentSync:
    """Integration tests for Genius appointment sync"""
    
    @pytest.fixture
    def mock_genius_client(self):
        with patch('ingestion.sync.genius.client.GeniusClient') as mock:
            mock_instance = AsyncMock()
            mock.return_value = mock_instance
            yield mock_instance
    
    @pytest.fixture
    def sample_appointment_data(self):
        return [
            {
                'id': 1,
                'prospect_id': 100,
                'type_id': 1,
                'date': '2025-07-07',
                'time': '10:00:00',
                'status': 'scheduled'
            }
        ]
    
    @pytest.mark.asyncio
    async def test_appointment_sync_end_to_end(self, mock_genius_client, sample_appointment_data):
        """Test complete appointment sync process"""
        # Setup mock client
        mock_genius_client.fetch_appointments.return_value = sample_appointment_data
        
        # Run sync
        sync_engine = GeniusAppointmentSyncEngine()
        history = await sync_engine.run_sync()
        
        # Verify results
        assert history.status == 'success'
        assert history.records_processed == 1
        assert history.records_created == 1
        
        # Verify data was saved
        appointment = await Genius_Appointment.objects.aget(id=1)
        assert appointment.prospect_id == 100
        assert appointment.status == 'scheduled'
    
    @pytest.mark.asyncio
    async def test_appointment_sync_with_validation_errors(self, mock_genius_client):
        """Test sync with validation errors"""
        invalid_data = [
            {
                'id': 1,
                'prospect_id': None,  # Invalid - required field
                'type_id': 1,
                'date': 'invalid-date',  # Invalid date format
            }
        ]
        
        mock_genius_client.fetch_appointments.return_value = invalid_data
        
        sync_engine = GeniusAppointmentSyncEngine()
        history = await sync_engine.run_sync()
        
        # Should handle validation errors gracefully
        assert history.status == 'partial'
        assert history.records_failed == 1
        assert history.records_created == 0
```

## Implementation Guidelines

### Command Structure Template
```python
# filepath: ingestion/management/commands/sync_[crm]_[entity].py
import asyncio
from django.core.management.base import BaseCommand
from ingestion.sync.[crm].sync_engine import [CRM][Entity]SyncEngine

class Command(BaseCommand):
    help = "Sync [entity] from [CRM]"
    
    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, help='Batch size for processing')
        parser.add_argument('--dry-run', action='store_true', help='Run without saving data')
        parser.add_argument('--incremental', action='store_true', help='Incremental sync only')
        parser.add_argument('--since', type=str, help='Sync data since this date (YYYY-MM-DD)')
        parser.add_argument('--limit', type=int, help='Limit number of records to process')
    
    def handle(self, *args, **options):
        """Execute the sync command"""
        # Run async sync in sync context
        asyncio.run(self.async_handle(**options))
    
    async def async_handle(self, **options):
        """Async handler for sync operation"""
        sync_engine = [CRM][Entity]SyncEngine(**options)
        
        try:
            history = await sync_engine.run_sync(**options)
            
            self.stdout.write(
                self.style.SUCCESS(
                    f"Sync completed: {history.records_processed} processed, "
                    f"{history.records_created} created, {history.records_updated} updated"
                )
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"Sync failed: {str(e)}")
            )
            raise
```

### Sync Engine Implementation Template
```python
# filepath: ingestion/sync/[crm]/sync_engine.py
from typing import Dict, Any, List, AsyncGenerator
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.sync.[crm].client import [CRM]Client
from ingestion.sync.[crm].processors import [CRM][Entity]Processor

class [CRM][Entity]SyncEngine(BaseSyncEngine):
    """Sync engine for [CRM] [entity]"""
    
    def __init__(self, **kwargs):
        super().__init__('[crm]', '[entity]', **kwargs)
        self.processor = [CRM][Entity]Processor(batch_size=self.batch_size)
    
    def get_default_batch_size(self) -> int:
        return 500  # Adjust based on CRM
    
    async def initialize_client(self) -> None:
        """Initialize [CRM] client"""
        self.client = [CRM]Client()
        await self.client.authenticate()
    
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch [entity] data from [CRM]"""
        async for batch in self.client.fetch_[entity](
            batch_size=self.batch_size,
            since=kwargs.get('since'),
            limit=kwargs.get('limit')
        ):
            yield batch
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw [entity] data"""
        return await self.processor.transform_batch(raw_data)
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate [entity] data"""
        return await self.processor.validate_batch(data)
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save [entity] data"""
        return await self.processor.save_batch(validated_data)
    
    async def cleanup(self) -> None:
        """Cleanup resources"""
        if self.client:
            await self.client.close()
```

## CRM-Specific Recommendations

### Genius CRM
- **Batch Size**: 500 (database direct access allows larger batches)
- **Key Features**: Direct database sync, API sync, foreign key resolution
- **Error Handling**: Exponential backoff for API, connection retry for database
- **Special Considerations**: Handle both MySQL direct and API endpoints

### HubSpot
- **Batch Size**: 100 (API rate limits require smaller batches)
- **Key Features**: Complex associations, webhook support, OAuth2
- **Error Handling**: Adaptive retry based on rate limit headers
- **Special Considerations**: Handle nested object relationships, respect rate limits

### MarketSharp
- **Batch Size**: 200 (XML processing overhead)
- **Key Features**: XML/OData API, field mapping configuration
- **Error Handling**: XML parsing error recovery, connection retry
- **Special Considerations**: Complex XML structure transformation

### ActiveProspect
- **Batch Size**: 100 (event-based processing)
- **Key Features**: Event streaming, webhook support, real-time processing
- **Error Handling**: Event-level error handling, retry with backoff
- **Special Considerations**: Event deduplication, real-time processing

### SalesPro
- **Batch Size**: 500 (CSV processing)
- **Key Features**: CSV import only, batch processing
- **Error Handling**: Individual record fallback, CSV parsing errors
- **Special Considerations**: File processing, header mapping

### Arrivy
- **Batch Size**: 1000 (large file processing)
- **Key Features**: Large CSV files, bulk operations
- **Error Handling**: Memory-efficient processing, bulk error handling
- **Special Considerations**: Memory management for large files

## Migration Strategy

### Phase 1: Infrastructure Setup
1. Create base classes and common models
2. Implement sync history system
3. Set up testing framework
4. Create configuration management

### Phase 2: CRM Migration
1. Migrate each CRM to new architecture (one at a time)
2. Implement comprehensive tests
3. Performance optimization
4. Error handling improvements

### Phase 3: Advanced Features
1. Real-time sync capabilities
2. Advanced monitoring
3. Data quality improvements
4. Scalability enhancements

## Success Metrics

### Performance Targets
- **Sync Success Rate**: 99.9%
- **Processing Speed**: 1000+ records/minute
- **Error Recovery**: 95% of failed records recovered
- **Memory Usage**: <500MB per sync process

### Quality Metrics
- **Test Coverage**: 90%+ for all sync engines
- **Code Consistency**: 100% adherence to patterns
- **Documentation**: Complete API documentation
- **Error Handling**: Comprehensive error categorization

This architecture guide provides the foundation for implementing consistent, reliable, and scalable CRM integrations across the entire data