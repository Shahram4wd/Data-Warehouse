# Data Warehouse CRM Integration Standards & Architecture Guide
**Version**: 4.0  
**Last Updated**: July 7, 2025  
**Purpose**: Unified architecture and implementation standards for all CRM integrations
**Status**: Enhanced with Enterprise Features Based on HubSpot Implementation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Enterprise Features (NEW)](#enterprise-features-new)
3. [Advanced Validation Framework](#advanced-validation-framework)
4. [Performance Monitoring & Resource Management](#performance-monitoring--resource-management)
5. [Dynamic Configuration System](#dynamic-configuration-system)
6. [Base Class Patterns](#base-class-patterns)
7. [Sync History Management](#sync-history-management)
8. [Error Handling Standards](#error-handling-standards)
9. [Testing Standards](#testing-standards)
10. [Implementation Guidelines](#implementation-guidelines)
11. [CRM-Specific Recommendations](#crm-specific-recommendations)
12. [Enterprise Deployment](#enterprise-deployment)

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
│   ├── validators.py           # Advanced validation framework ✨
│   ├── performance.py          # Real-time performance monitoring ✨
│   ├── config.py               # Dynamic configuration system ✨
│   ├── retry.py                # Enterprise retry logic ✨
│   └── exceptions.py           # Custom exceptions
├── models/
│   ├── common.py               # Common models (SyncHistory, SyncConfiguration, APICredential)
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
│   │   ├── clients/            # Modular client architecture ✨
│   │   │   ├── contact_client.py
│   │   │   ├── deal_client.py
│   │   │   └── ...
│   │   ├── engines/            # Entity-specific sync engines ✨
│   │   │   ├── contact_engine.py
│   │   │   ├── deal_engine.py
│   │   │   └── ...
│   │   ├── processors/         # Advanced data processors ✨
│   │   │   ├── contact_processor.py
│   │   │   ├── deal_processor.py
│   │   │   └── ...
│   │   └── validators.py       # HubSpot-specific validators ✨
│   └── ...
├── tests/
│   ├── integration/            # Comprehensive test suite ✨
│   ├── unit/                   # Unit tests with mocking ✨
│   └── performance/            # Performance benchmarks ✨
└── monitoring/                 # Enterprise monitoring (TO BE IMPLEMENTED)
    ├── dashboard.py            # Real-time monitoring dashboard
    ├── alerts.py               # Automated alerting system
    └── reports.py              # Advanced reporting
```

✨ **NEW**: Enhanced enterprise features that exceed standard requirements

## Enterprise Features (NEW)

### 1. Advanced Validation Framework
Our implementation exceeds the standard validation requirements with:

#### Multi-Level Validation
```python
# filepath: ingestion/base/validators.py
class ValidationPipeline:
    """Multi-stage validation pipeline"""
    
    def __init__(self):
        self.validators = []
        self.transformers = []
        self.post_processors = []
    
    async def validate_batch(self, records: List[Dict]) -> List[Dict]:
        """Validate entire batch with pipeline approach"""
        results = []
        for record in records:
            try:
                # Stage 1: Basic validation
                validated = await self.basic_validation(record)
                # Stage 2: Business logic validation
                validated = await self.business_validation(validated)
                # Stage 3: Cross-field validation
                validated = await self.cross_field_validation(validated)
                results.append(validated)
            except ValidationException as e:
                # Collect validation errors for reporting
                self.collect_validation_error(record, e)
        return results
```

#### Domain-Specific Validators
```python
# filepath: ingestion/sync/hubspot/validators.py
class HubSpotEmailValidator(BaseValidator):
    """HubSpot-specific email validation with additional checks"""
    
    def validate(self, value: Any) -> Optional[str]:
        # Enhanced email validation with HubSpot-specific rules
        # - Supports HubSpot's email format requirements
        # - Validates against HubSpot's blocked domains
        # - Checks email deliverability scores
        pass

class HubSpotPhoneValidator(BaseValidator):
    """International phone validation with HubSpot formatting"""
    
    def validate(self, value: Any) -> Optional[str]:
        # Advanced phone validation
        # - International format support
        # - HubSpot-specific formatting
        # - Validation against HubSpot's phone standards
        pass
```

### 2. Real-Time Performance Monitoring
Enterprise-grade monitoring that exceeds standard requirements:

#### Resource Monitoring
```python
# filepath: ingestion/base/performance.py
class PerformanceMonitor:
    """Real-time performance monitoring with resource tracking"""
    
    def __init__(self):
        self.metrics = PerformanceMetrics()
        self.resource_tracker = ResourceTracker()
        self.alert_thresholds = self.load_alert_thresholds()
    
    @contextmanager
    def monitor_operation(self, operation_name: str):
        """Context manager for monitoring operations"""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        try:
            yield self.metrics
        finally:
            self.metrics.record_operation(
                operation_name,
                duration=time.time() - start_time,
                memory_delta=psutil.Process().memory_info().rss - start_memory
            )
    
    async def check_resource_thresholds(self):
        """Check if resource usage exceeds thresholds"""
        current_usage = await self.get_current_usage()
        
        if current_usage.memory_percent > self.alert_thresholds['memory']:
            await self.trigger_memory_alert(current_usage)
        
        if current_usage.cpu_percent > self.alert_thresholds['cpu']:
            await self.trigger_cpu_alert(current_usage)
```

#### Advanced Metrics Collection
```python
@dataclass
class EnhancedMetrics:
    """Extended metrics beyond standard requirements"""
    
    # Standard metrics
    duration: float
    records_processed: int
    success_rate: float
    
    # Enhanced metrics
    memory_usage_mb: float
    cpu_percent: float
    disk_io_bytes: int
    network_io_bytes: int
    cache_hit_rate: float
    database_queries: int
    api_calls: int
    validation_errors: int
    retry_attempts: int
    
    # Business metrics
    data_quality_score: float
    processing_efficiency: float
    cost_per_record: float
```

### 3. Dynamic Configuration System
Enterprise configuration management that exceeds standard requirements:

#### Runtime Configuration Updates
```python
# filepath: ingestion/base/config.py
class DynamicConfigManager:
    """Dynamic configuration with hot-reload capabilities"""
    
    def __init__(self):
        self.config_cache = {}
        self.watchers = {}
        self.change_listeners = []
    
    async def get_config(self, key: str, default=None):
        """Get configuration with automatic refresh"""
        if key not in self.config_cache or self.is_stale(key):
            await self.refresh_config(key)
        return self.config_cache.get(key, default)
    
    async def update_config(self, key: str, value: Any):
        """Update configuration at runtime"""
        await self.save_config(key, value)
        await self.notify_change_listeners(key, value)
        self.config_cache[key] = value
    
    def watch_config(self, key: str, callback: Callable):
        """Watch for configuration changes"""
        if key not in self.watchers:
            self.watchers[key] = []
        self.watchers[key].append(callback)
```

#### Environment-Specific Configurations
```python
class EnvironmentConfig:
    """Environment-aware configuration management"""
    
    ENVIRONMENTS = {
        'development': {
            'batch_size': 50,
            'rate_limit': 10,
            'debug_mode': True,
            'validation_strict': False
        },
        'staging': {
            'batch_size': 100,
            'rate_limit': 50,
            'debug_mode': False,
            'validation_strict': True
        },
        'production': {
            'batch_size': 500,
            'rate_limit': 100,
            'debug_mode': False,
            'validation_strict': True,
            'monitoring_enabled': True
        }
    }
```

### 4. Modular Architecture
Enterprise-grade modular design that exceeds standard requirements:

#### Entity-Specific Modules
```python
# filepath: ingestion/sync/hubspot/clients/contact_client.py
class HubSpotContactClient(BaseAPIClient):
    """Specialized client for HubSpot contacts"""
    
    def __init__(self):
        super().__init__()
        self.endpoint = '/contacts/v1/contact'
        self.batch_endpoint = '/contacts/v1/contact/batch'
        self.search_endpoint = '/contacts/v1/search'
    
    async def get_contacts(self, **kwargs):
        """Get contacts with advanced filtering"""
        # Enhanced contact retrieval with:
        # - Property-based filtering
        # - Custom field support
        # - Pagination optimization
        # - Incremental sync support
        pass
    
    async def batch_create_contacts(self, contacts: List[Dict]):
        """Batch create with intelligent error handling"""
        # Advanced batch processing with:
        # - Partial failure handling
        # - Automatic retry for failed items
        # - Duplicate detection
        # - Validation before submission
        pass
```

#### Specialized Processors
```python
# filepath: ingestion/sync/hubspot/processors/contact_processor.py
class HubSpotContactProcessor(BaseProcessor):
    """Advanced contact data processor"""
    
    def __init__(self):
        super().__init__()
        self.field_mappings = self.load_field_mappings()
        self.transformation_rules = self.load_transformation_rules()
        self.validation_pipeline = self.create_validation_pipeline()
    
    async def process_contact(self, raw_contact: Dict) -> Dict:
        """Process contact with advanced transformations"""
        # Enhanced processing with:
        # - Smart field mapping
        # - Data enrichment
        # - Deduplication logic
        # - Quality scoring
        pass
    
    async def enrich_contact_data(self, contact: Dict) -> Dict:
        """Enrich contact data with additional information"""
        # Data enrichment features:
        # - Geocoding for addresses
        # - Company information lookup
        # - Social media profile matching
        # - Email validation and scoring
        pass
```

### 5. Comprehensive Testing Framework
Enterprise testing that exceeds standard requirements:

#### Multi-Level Testing
```python
# filepath: ingestion/tests/integration/test_hubspot_integration.py
class TestHubSpotIntegration:
    """Comprehensive integration tests"""
    
    @pytest.mark.asyncio
    async def test_full_sync_workflow(self):
        """Test complete sync workflow end-to-end"""
        # Tests include:
        # - API connectivity
        # - Data transformation
        # - Validation pipeline
        # - Database operations
        # - Performance benchmarks
        pass
    
    @pytest.mark.performance
    async def test_performance_benchmarks(self):
        """Performance testing with benchmarks"""
        # Performance tests:
        # - Memory usage tracking
        # - Processing speed benchmarks
        # - Scalability testing
        # - Resource utilization
        pass
    
    @pytest.mark.docker
    async def test_containerized_environment(self):
        """Test in containerized environment"""
        # Docker-based testing:
        # - Container resource limits
        # - Network isolation testing
        # - Volume mounting verification
        # - Service communication
        pass
```

#### Performance Benchmarking
```python
# filepath: ingestion/tests/performance/benchmark_suite.py
class PerformanceBenchmarkSuite:
    """Automated performance benchmarking"""
    
    def __init__(self):
        self.benchmarks = []
        self.thresholds = self.load_performance_thresholds()
    
    async def run_benchmark(self, test_name: str, test_func: Callable):
        """Run performance benchmark with detailed metrics"""
        with self.performance_monitor.monitor_operation(test_name):
            result = await test_func()
            
        # Validate against thresholds
        if not self.meets_performance_criteria(result):
            raise PerformanceRegressionError(
                f"Performance regression detected in {test_name}"
            )
```
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

## Advanced Validation Framework

### Validation Architecture
Our enhanced validation framework provides enterprise-grade data quality assurance:

#### Base Validation Classes
```python
# filepath: ingestion/base/validators.py
class BaseValidator(ABC):
    """Enhanced base validator with comprehensive error handling"""
    
    def __init__(self, required: bool = False, allow_empty: bool = True):
        self.required = required
        self.allow_empty = allow_empty
        self.error_context = {}
    
    @abstractmethod
    def validate(self, value: Any) -> Any:
        """Validate and return cleaned value"""
        pass
    
    def _check_required(self, value: Any) -> None:
        """Enhanced required field validation"""
        if self.required and (value is None or (not self.allow_empty and str(value).strip() == '')):
            raise ValidationException(f"Required field cannot be empty")
    
    def add_context(self, **kwargs):
        """Add validation context for better error reporting"""
        self.error_context.update(kwargs)

class ValidationPipeline:
    """Multi-stage validation pipeline"""
    
    def __init__(self):
        self.stages = []
        self.error_collector = ValidationErrorCollector()
    
    def add_stage(self, stage_name: str, validators: List[BaseValidator]):
        """Add validation stage"""
        self.stages.append({
            'name': stage_name,
            'validators': validators
        })
    
    async def validate_record(self, record: Dict) -> Dict:
        """Validate record through all stages"""
        validated_record = record.copy()
        
        for stage in self.stages:
            try:
                validated_record = await self.run_stage(stage, validated_record)
            except ValidationException as e:
                self.error_collector.add_error(stage['name'], e)
                if stage.get('critical', False):
                    raise
        
        return validated_record
```

#### Specialized Validators
```python
class EmailValidator(BaseValidator):
    """Enhanced email validator with deliverability checking"""
    
    def __init__(self, check_deliverability: bool = False, **kwargs):
        super().__init__(**kwargs)
        self.check_deliverability = check_deliverability
        self.email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate email with enhanced checks"""
        self._check_required(value)
        
        if not value:
            return None
        
        email = str(value).strip().lower()
        
        # Basic format validation
        if not self.email_pattern.match(email):
            raise ValidationException(f"Invalid email format: {email}")
        
        # Check against blocked domains
        if self.is_blocked_domain(email):
            raise ValidationException(f"Email domain is blocked: {email}")
        
        # Optional deliverability check
        if self.check_deliverability:
            if not self.check_email_deliverability(email):
                raise ValidationException(f"Email appears to be undeliverable: {email}")
        
        return email

class PhoneValidator(BaseValidator):
    """International phone validator with formatting"""
    
    def __init__(self, format_output: bool = True, country_code: str = None, **kwargs):
        super().__init__(**kwargs)
        self.format_output = format_output
        self.country_code = country_code
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate and format phone number"""
        self._check_required(value)
        
        if not value:
            return None
        
        # Remove all non-digit characters
        phone = re.sub(r'[^\d]', '', str(value))
        
        # Validate length
        if len(phone) < 10 or len(phone) > 15:
            raise ValidationException(f"Invalid phone number length: {value}")
        
        # Format output if requested
        if self.format_output:
            return self.format_phone(phone)
        
        return phone
```

## Performance Monitoring & Resource Management

### Real-Time Monitoring
Our performance monitoring system provides enterprise-grade observability:

#### Performance Metrics Collection
```python
# filepath: ingestion/base/performance.py
@dataclass
class PerformanceMetrics:
    """Comprehensive performance metrics"""
    
    # Basic metrics
    operation_name: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration: Optional[float] = None
    
    # Processing metrics
    records_processed: int = 0
    records_per_second: float = 0
    errors_count: int = 0
    success_rate: float = 0
    
    # Resource metrics
    memory_usage_mb: float = 0
    cpu_percent: float = 0
    disk_io_bytes: int = 0
    network_io_bytes: int = 0
    
    # Business metrics
    data_quality_score: float = 0
    validation_errors: int = 0
    retry_attempts: int = 0
    
    # Additional metrics
    additional_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def calculate_efficiency_score(self) -> float:
        """Calculate overall efficiency score"""
        factors = [
            self.success_rate,
            min(self.records_per_second / 100, 1.0),  # Normalize to 100 rps
            max(0, 1 - self.memory_usage_mb / 1000),  # Normalize to 1GB
            self.data_quality_score
        ]
        return sum(factors) / len(factors)

class PerformanceMonitor:
    """Real-time performance monitoring"""
    
    def __init__(self):
        self.active_operations = {}
        self.metrics_history = []
        self.alert_thresholds = self.load_thresholds()
    
    @contextmanager
    def monitor_operation(self, operation_name: str):
        """Monitor operation with automatic metrics collection"""
        metrics = PerformanceMetrics(
            operation_name=operation_name,
            start_time=datetime.now()
        )
        
        start_memory = psutil.Process().memory_info().rss
        start_cpu = psutil.cpu_percent()
        
        try:
            yield metrics
        finally:
            metrics.end_time = datetime.now()
            metrics.duration = (metrics.end_time - metrics.start_time).total_seconds()
            metrics.memory_usage_mb = (psutil.Process().memory_info().rss - start_memory) / 1024 / 1024
            metrics.cpu_percent = psutil.cpu_percent() - start_cpu
            
            self.record_metrics(metrics)
            self.check_alerts(metrics)
    
    async def check_alerts(self, metrics: PerformanceMetrics):
        """Check performance metrics against alert thresholds"""
        if metrics.memory_usage_mb > self.alert_thresholds['memory_mb']:
            await self.send_alert(f"High memory usage: {metrics.memory_usage_mb}MB")
        
        if metrics.duration > self.alert_thresholds['duration_seconds']:
            await self.send_alert(f"Long-running operation: {metrics.duration}s")
        
        if metrics.success_rate < self.alert_thresholds['success_rate']:
            await self.send_alert(f"Low success rate: {metrics.success_rate:.2%}")
```

#### Resource Management
```python
class ResourceManager:
    """Advanced resource management and optimization"""
    
    def __init__(self):
        self.resource_limits = self.load_resource_limits()
        self.optimization_strategies = self.load_optimization_strategies()
    
    async def optimize_batch_size(self, current_metrics: PerformanceMetrics) -> int:
        """Dynamically adjust batch size based on performance"""
        current_batch_size = current_metrics.additional_metrics.get('batch_size', 100)
        
        # Increase batch size if performance is good
        if (current_metrics.success_rate > 0.95 and 
            current_metrics.memory_usage_mb < 200):
            return min(current_batch_size * 1.2, 1000)
        
        # Decrease batch size if performance is poor
        if (current_metrics.success_rate < 0.8 or 
            current_metrics.memory_usage_mb > 500):
            return max(current_batch_size * 0.8, 10)
        
        return current_batch_size
    
    async def manage_memory_usage(self):
        """Proactive memory management"""
        current_usage = psutil.Process().memory_info().rss / 1024 / 1024
        
        if current_usage > self.resource_limits['memory_warning_mb']:
            await self.cleanup_memory()
        
        if current_usage > self.resource_limits['memory_critical_mb']:
            await self.emergency_memory_cleanup()
    
    async def cleanup_memory(self):
        """Cleanup memory resources"""
        # Clear caches
        cache.clear()
        
        # Force garbage collection
        import gc
        gc.collect()
        
        # Clear temporary data
        self.clear_temporary_data()
```

## Dynamic Configuration System

### Configuration Management
Our configuration system provides enterprise-grade flexibility:

#### Dynamic Configuration Manager
```python
# filepath: ingestion/base/config.py
class ConfigurationManager:
    """Enterprise configuration management"""
    
    def __init__(self):
        self.config_store = {}
        self.change_listeners = defaultdict(list)
        self.validation_rules = {}
        self.environment = self.detect_environment()
    
    async def get_config(self, key: str, default=None):
        """Get configuration value with hierarchy support"""
        # Try environment-specific config first
        env_key = f"{self.environment}.{key}"
        if env_key in self.config_store:
            return self.config_store[env_key]
        
        # Fall back to general config
        return self.config_store.get(key, default)
    
    async def update_config(self, key: str, value: Any, validate: bool = True):
        """Update configuration with validation"""
        if validate and key in self.validation_rules:
            await self.validate_config_value(key, value)
        
        old_value = self.config_store.get(key)
        self.config_store[key] = value
        
        # Notify listeners
        await self.notify_config_change(key, old_value, value)
    
    def watch_config(self, key: str, callback: Callable):
        """Watch for configuration changes"""
        self.change_listeners[key].append(callback)
    
    async def validate_config_value(self, key: str, value: Any):
        """Validate configuration value"""
        validator = self.validation_rules.get(key)
        if validator:
            await validator.validate(value)

class EnvironmentAwareConfig:
    """Environment-aware configuration"""
    
    ENVIRONMENT_CONFIGS = {
        'development': {
            'hubspot.batch_size': 10,
            'hubspot.rate_limit': 5,
            'hubspot.timeout': 30,
            'validation.strict_mode': False,
            'monitoring.enabled': False,
            'logging.level': 'DEBUG'
        },
        'staging': {
            'hubspot.batch_size': 50,
            'hubspot.rate_limit': 25,
            'hubspot.timeout': 60,
            'validation.strict_mode': True,
            'monitoring.enabled': True,
            'logging.level': 'INFO'
        },
        'production': {
            'hubspot.batch_size': 500,
            'hubspot.rate_limit': 100,
            'hubspot.timeout': 120,
            'validation.strict_mode': True,
            'monitoring.enabled': True,
            'logging.level': 'WARNING',
            'performance.profiling': True
        }
    }
    
    def get_environment_config(self, environment: str) -> Dict:
        """Get environment-specific configuration"""
        return self.ENVIRONMENT_CONFIGS.get(environment, {})
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


## Generic CRM Sync/Removal Command Architecture (Unified Pattern)

### 1. Modular Entity Structure
For every CRM and entity (e.g., contacts, appointments, deals, zipcodes), implement the following modules:

```
ingestion/sync/<crm>/clients/<entity>_client.py      # API client for entity
ingestion/sync/<crm>/processors/<entity>_processor.py # Data processor for entity
ingestion/sync/<crm>/engines/<entity>_engine.py      # Sync engine for entity
ingestion/management/commands/sync_<crm>_<entity>.py # Management command for entity sync
ingestion/management/commands/sync_<crm>_<entity>_removal.py # Management command for entity removal (if applicable)
```

### 2. Inheritance and Base Classes
- All engines inherit from `BaseSyncEngine` (or a CRM-specific base, e.g., `HubSpotBaseSyncEngine`).
- All clients inherit from `BaseAPIClient` (or CRM-specific base).
- All processors inherit from `BaseDataProcessor` (or CRM-specific base).
- Removal engines/clients/processors should inherit from the same base classes, and may override only the methods needed for removal logic.

### 3. Command Structure
**Sync Command:**
```python
# ingestion/management/commands/sync_<crm>_<entity>.py
import asyncio
from django.core.management.base import BaseCommand
from ingestion.sync.<crm>.engines.<entity>_engine import <CRM><Entity>SyncEngine

class Command(BaseCommand):
    help = "Sync <entity> from <CRM>"

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, help='Batch size for processing')
        parser.add_argument('--limit', type=int, help='Limit number of records to process')

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(**options))

    async def async_handle(self, **options):
        engine = <CRM><Entity>SyncEngine(**options)
        await engine.run_sync(**options)
```

**Removal Command:**
```python
# ingestion/management/commands/sync_<crm>_<entity>_removal.py
import asyncio
from django.core.management.base import BaseCommand
from ingestion.sync.<crm>.engines.<entity>_removal_engine import <CRM><Entity>RemovalSyncEngine

class Command(BaseCommand):
    help = "Remove <entity> records locally that no longer exist in <CRM>"

    def add_arguments(self, parser):
        parser.add_argument('--batch-size', type=int, help='Batch size for processing')
        parser.add_argument('--limit', type=int, help='Limit number of records to check')
        parser.add_argument('--dry-run', action='store_true', help='Show what would be removed')

    def handle(self, *args, **options):
        asyncio.run(self.async_handle(**options))

    async def async_handle(self, **options):
        engine = <CRM><Entity>RemovalSyncEngine(**options)
        await engine.run_removal(**options)
```

### 4. Engine/Client/Processor Patterns
**Sync Engine:**
```python
# ingestion/sync/<crm>/engines/<entity>_engine.py
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.sync.<crm>.clients.<entity>_client import <CRM><Entity>Client
from ingestion.sync.<crm>.processors.<entity>_processor import <CRM><Entity>Processor

class <CRM><Entity>SyncEngine(BaseSyncEngine):
    def __init__(self, **kwargs):
        super().__init__('<crm>', '<entity>', **kwargs)
        self.client = <CRM><Entity>Client()
        self.processor = <CRM><Entity>Processor()
    # Implement required abstract methods
```

**Removal Engine:**
```python
# ingestion/sync/<crm>/engines/<entity>_removal_engine.py
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.sync.<crm>.clients.<entity>_removal_client import <CRM><Entity>RemovalClient

class <CRM><Entity>RemovalSyncEngine(BaseSyncEngine):
    def __init__(self, **kwargs):
        super().__init__('<crm>', '<entity>_removal', **kwargs)
        self.client = <CRM><Entity>RemovalClient()
    # Implement required abstract methods for removal
```

**Client:**
```python
# ingestion/sync/<crm>/clients/<entity>_client.py
from ingestion.base.client import BaseAPIClient

class <CRM><Entity>Client(BaseAPIClient):
    # Implement entity-specific API logic
    pass
```

**Processor:**
```python
# ingestion/sync/<crm>/processors/<entity>_processor.py
from ingestion.base.processor import BaseDataProcessor

class <CRM><Entity>Processor(BaseDataProcessor):
    # Implement entity-specific transformation/validation
    pass
```

### 5. Best Practices
- **No business logic in management commands:** All business logic must reside in engine/client/processor modules.
- **Batch operations:** Use batch APIs and bulk DB operations for performance.
- **Progress reporting:** Engines should handle progress bars and logging.
- **Async everywhere:** All network and DB operations should be async.
- **Extensible for new CRMs:** Follow the same pattern for any new CRM (e.g., Genius, MarketSharp, etc.).

### 6. Example: HubSpot Contacts Sync/Removal
See `ingestion/sync/hubspot/engines/contacts_engine.py`, `contacts_removal_engine.py`, `clients/contacts_client.py`, `clients/contacts_removal_client.py`, and their management commands for a reference implementation.

---
This generic modular pattern ensures all CRM sync/removal commands are:
- Consistent
- Extensible
- Testable
- Easy to maintain and onboard for new CRMs/entities

### Arrivy
- **Batch Size**: 1000 (API allows larger batches for better performance)
- **Key Features**: API-only integration (CSV processing deprecated), bulk operations
- **Error Handling**: Enterprise-grade error handling with retry logic
- **Special Considerations**: Large data volumes, multiple entity types (tasks, groups, entities)
- **Architecture**: Full enterprise implementation following HubSpot patterns
  - Multiple specialized clients (tasks, groups, entities, location_reports, task_statuses)
  - Enterprise validation framework
  - Individual commands per entity + unified sync_arrivy_all command
  - Unified SyncHistory model usage

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

### Enhanced Performance Targets (Enterprise Standards)
- **Sync Success Rate**: 99.95% (enhanced from 99.9%)
- **Processing Speed**: 2000+ records/minute (enhanced from 1000+)
- **Error Recovery**: 98% of failed records recovered (enhanced from 95%)
- **Memory Usage**: <300MB per sync process (optimized from 500MB)
- **Data Quality Score**: 95%+ (new metric)
- **API Efficiency**: <2 API calls per record (new metric)

### Enterprise Quality Metrics
- **Test Coverage**: 95%+ for all sync engines (enhanced from 90%)
- **Code Consistency**: 100% adherence to patterns
- **Documentation**: Complete API documentation with examples
- **Error Handling**: Comprehensive error categorization with automated recovery
- **Performance Monitoring**: Real-time metrics with alerting
- **Security**: Encrypted credentials with rotation capabilities

### Operational Excellence
- **Deployment Success Rate**: 99.9%
- **Mean Time to Recovery (MTTR)**: <15 minutes
- **Change Failure Rate**: <2%
- **Lead Time for Changes**: <2 hours
- **Monitoring Coverage**: 100% of critical operations

## Future Enhancements (Roadmap)

### Phase 1: Enterprise Monitoring Dashboard (In Progress)
- Real-time performance visualization
- Automated alerting system
- Historical trend analysis
- Resource utilization tracking

### Phase 2: Advanced Connection Management
- Connection pooling optimization
- Circuit breaker patterns
- Intelligent retry strategies
- Load balancing capabilities

### Phase 3: Enhanced Security
- Advanced credential encryption
- Role-based access control
- Audit logging
- Compliance reporting

### Phase 4: Advanced Automation
- Self-healing capabilities
- Intelligent error resolution
- Predictive maintenance
- Auto-scaling based on load

This architecture guide provides the foundation for implementing consistent, reliable, and scalable CRM integrations that exceed enterprise standards across the entire data warehouse platform.