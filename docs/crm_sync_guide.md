# CRM Sync Architecture Guide

## Overview

This document outlines the enterprise-grade sync architecture for CRM systems (HubSpot, Salesforce, etc.). The architecture supports delta sync, bulk operations, error handling, and enterprise monitoring.

## Architecture Components

### 1. **Layered Architecture**

```
┌─────────────────┐
│ Management      │  ← Command-line interface & scheduling
│ Commands        │
├─────────────────┤
│ Sync Engines    │  ← Orchestration & workflow management
├─────────────────┤
│ API Clients     │  ← External API communication
├─────────────────┤
│ Processors      │  ← Data transformation & validation
├─────────────────┤
│ Models          │  ← Database persistence layer
└─────────────────┘
```

### 2. **Core Classes**

- **BaseSyncEngine**: Universal sync workflow orchestration
- **BaseAPIClient**: HTTP client with rate limiting & error handling
- **BaseProcessor**: Data transformation & validation framework
- **BaseCommand**: Management command with common flags & options

### 3. **Standardized Module Structure**

All CRM sync modules follow a consistent file and folder organization pattern to ensure maintainability and architectural coherence:

```
ingestion/sync/{crm_name}/
├── clients/              # API and data source clients
│   ├── __init__.py
│   ├── base.py          # Base client implementations
│   └── {entity}.py      # Specific entity clients (contacts, deals, etc.)
├── engines/             # Sync orchestration engines
│   ├── __init__.py
│   ├── base.py          # Base sync engine with common functionality
│   └── {entity}.py      # Entity-specific sync engines
├── processors/          # Data transformation and validation
│   ├── __init__.py
│   ├── base.py          # Base processor with common transforms
│   └── {entity}.py      # Entity-specific processors
├── validators.py        # CRM-specific validation rules
└── __init__.py         # Module initialization
```

**Examples:**
- `ingestion/sync/hubspot/` - HubSpot sync module
- `ingestion/sync/salesrabbit/` - SalesRabbit sync module  
- `ingestion/sync/salespro/` - SalesPro sync module

This structure ensures:
- **Separation of Concerns**: Each layer has a clear responsibility
- **Consistency**: All CRM modules follow the same pattern
- **Scalability**: Easy to add new entities or CRM sources
- **Maintainability**: Clear location for each type of functionality


## Delta Sync Implementation

### Key Concepts

1. **Incremental Sync (Default)**: Only fetch records modified since last successful sync
2. **Full Sync**: Fetch all records but respect local timestamps for updates
3. **Force Overwrite**: Fetch all records and completely replace local data

### Delta Sync Flow

```python
def get_last_sync_time():
    """Priority order:
    1. --since parameter (manual override)
    2. --force-overwrite flag (None = fetch all)
    3. --full flag (None = fetch all)
    4. Database last sync timestamp
    5. Default: None (full sync)
    """
```

### Critical: Data Type Consistency for --since Parameter

The `--since` parameter requires careful handling to ensure consistent data types throughout the sync pipeline:

**Key Architecture Requirements:**

1. **Input Standardization**: Accept `--since` as string (YYYY-MM-DD format) but immediately convert to `datetime` object
2. **Internal Consistency**: All internal methods should work with `datetime` objects, not strings
3. **Database Query Safety**: Format datetime to string only when building SQL queries
4. **Field Name Mapping**: Handle different timestamp field names across tables

```python
class BaseSyncEngine:
    """Standardized --since parameter handling"""
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Always return datetime object, never string"""
        # Query database for last successful sync
        # Return datetime object or None
        pass
    
    def determine_sync_strategy(self, force_full: bool = False, since_param: str = None) -> Dict[str, Any]:
        """Process --since parameter with proper data type conversion"""
        
        # 1. Handle --since parameter (string input)
        since_date = None
        if since_param:
            # Convert string to datetime object immediately
            since_date = datetime.strptime(since_param, '%Y-%m-%d')
        
        # 2. Fall back to database timestamp (already datetime)
        if not since_date and not force_full:
            since_date = await self.get_last_sync_timestamp()
        
        # 3. Return strategy with datetime object
        return {
            'type': 'full' if not since_date or force_full else 'incremental',
            'since_date': since_date,  # Always datetime or None
            'force_full': force_full
        }
    
    def build_incremental_query(self, since_date: datetime, table_name: str) -> str:
        """Build query with proper field name mapping"""
        
        # Convert datetime to SQL-safe string format
        since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
        
        # Map table names to their timestamp fields
        timestamp_field_map = {
            'contacts': 'updated_at',
            'deals': 'updated_at', 
            'activities': 'created_at',  # Activities don't get updated
            'user_logs': 'created_at',   # Log entries don't get updated
        }
        
        # Get appropriate timestamp field for this table
        timestamp_field = timestamp_field_map.get(table_name, 'updated_at')
        
        # Build query with proper field
        query = f"""
        SELECT * FROM {table_name} 
        WHERE {timestamp_field} > timestamp '{since_str}'
        ORDER BY {timestamp_field}
        """
        
        return query
```

**Common Pitfalls and Solutions:**

| Problem | Cause | Solution |
|---------|-------|----------|
| `TypeError: strftime()` | Passing string to datetime method | Convert string to datetime early in pipeline |
| Inconsistent date filtering | Using wrong timestamp field | Maintain table → field mapping |
| SQL injection risk | String concatenation | Use parameterized queries or safe formatting |
| Timezone issues | Missing timezone awareness | Use UTC consistently or timezone-aware objects |

**Implementation Checklist:**

- [ ] Convert `--since` string input to `datetime` object immediately
- [ ] Ensure `get_last_sync_timestamp()` returns `datetime` or `None`
- [ ] Map table names to correct timestamp fields (`created_at` vs `updated_at`)
- [ ] Use consistent datetime formatting for SQL queries (`%Y-%m-%d %H:%M:%S`)
- [ ] Handle timezone considerations (recommend UTC)
- [ ] Validate date input format and provide clear error messages

### API Implementation

```python
async def fetch_data(self, last_sync: Optional[datetime] = None):
    """
    if last_sync:
        # Use search endpoint with date filter
        # Example: hs_lastmodifieddate >= last_sync_timestamp
    else:
        # Use regular endpoint for full fetch
    """
```

### Table-Specific Timestamp Field Strategy

Different entity types require different timestamp fields for accurate incremental sync:

**Field Selection Logic:**

```python
def get_timestamp_field(entity_type: str) -> str:
    """Map entity types to appropriate timestamp fields"""
    
    # Entities that get updated (use updated_at)
    updatable_entities = {
        'contacts', 'companies', 'deals', 'tickets', 
        'customers', 'estimates', 'credit_applications',
        'payments', 'lead_results'
    }
    
    # Log/activity entities (use created_at - they don't get updated)
    activity_entities = {
        'activities', 'user_activities', 'call_logs',
        'email_events', 'meeting_events', 'task_logs'
    }
    
    if entity_type in updatable_entities:
        return 'updated_at'  # Track modifications
    elif entity_type in activity_entities:
        return 'created_at'  # Track when logged
    else:
        # Default fallback (prefer updated_at if available)
        return 'updated_at'
```

**Implementation Pattern:**

```python
async def build_incremental_filter(self, entity_type: str, since_date: datetime) -> str:
    """Build incremental sync filter based on entity type"""
    
    timestamp_field = self.get_timestamp_field(entity_type)
    since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
    
    # API-based sources (REST/GraphQL)
    if self.source_type == 'api':
        # Different CRMs use different field names
        api_field_map = {
            'updated_at': 'hs_lastmodifieddate',  # Example for one CRM
            'created_at': 'hs_createdate'
        }
        api_field = api_field_map.get(timestamp_field, timestamp_field)
        return f"{api_field} >= {since_str}"
    
    # Database sources (SQL)
    elif self.source_type == 'database':
        return f"{timestamp_field} > timestamp '{since_str}'"
    
    # CSV sources (filter after loading)
    elif self.source_type == 'csv':
        # Handle in post-processing since CSV doesn't support filtering
        return None
```

## Command-Line Flags & Options

### Standard Flags (All CRM Syncs)

| Flag | Type | Default | Description |
|------|------|---------|-------------|
| `--full` | bool | False | Perform full sync (ignore last sync timestamp) |
| `--force-overwrite` | bool | False | Completely replace existing records |
| `--since` | date | None | Manual sync start date (YYYY-MM-DD) |
| `--dry-run` | bool | False | Test run without database writes |
| `--batch-size` | int | 100 | Records per API batch |
| `--max-records` | int | 0 | Limit total records (0 = unlimited) |
| `--debug` | bool | False | Enable verbose logging |

### Usage Examples

```bash
# Standard incremental sync (delta)
python manage.py sync_crm_contacts

# Full sync with local timestamp respect
python manage.py sync_crm_contacts --full

# Complete data replacement
python manage.py sync_crm_contacts --full --force-overwrite

# Sync recent data only
python manage.py sync_crm_contacts --since=2025-01-01

# Force overwrite recent data
python manage.py sync_crm_contacts --since=2025-01-01 --force-overwrite

# Testing with limited records
python manage.py sync_crm_contacts --max-records=50 --dry-run
```

## Data Source Abstraction

### 1. **Multi-Source Support**

The architecture supports various data source types:

#### API-Based Sources (HubSpot, Salesforce, Pipedrive)
```python
class APIDataSource:
    """For CRMs with REST APIs"""
    
    async def fetch_paginated_data(self, endpoint: str, **kwargs):
        """Handle API pagination patterns"""
        # Offset-based pagination
        # Cursor-based pagination  
        # Token-based pagination
        pass
    
    async def handle_rate_limiting(self, response):
        """Implement rate limit handling"""
        if response.status == 429:
            retry_after = int(response.headers.get('Retry-After', 60))
            await asyncio.sleep(retry_after)
```

#### Database-Based Sources (SalesPro, MarketSharp)
```python
class DatabaseDataSource:
    """For direct database access"""
    
    async def execute_query(self, query: str, params: Dict = None):
        """Execute database queries safely"""
        # Connection pooling
        # Query parameterization
        # Transaction management
        pass
    
    def build_incremental_query(self, last_sync: datetime, table: str):
        """Build queries for incremental sync"""
        return f"""
        SELECT * FROM {table} 
        WHERE last_modified >= %s 
        ORDER BY last_modified
        """
```

#### File-Based Sources (CSV, GitHub)
```python
class FileDataSource:
    """For CSV and file-based sources"""
    
    async def fetch_from_github(self, repo: str, file_path: str):
        """Fetch CSV from GitHub repository"""
        # GitHub API integration
        # Version control awareness
        # Automatic updates
        pass
    
    async def process_csv_stream(self, file_stream):
        """Process CSV with memory optimization"""
        # Streaming processing
        # Memory-efficient parsing
        # Error recovery
        pass
```

### 2. **Data Source Factory Pattern**

```python
class DataSourceFactory:
    """Factory for creating appropriate data source clients"""
    
    @staticmethod
    def create_client(crm_source: str, source_type: str, **kwargs):
        """Create appropriate client based on source type"""
        source_map = {
            'api': APIDataSource,
            'database': DatabaseDataSource,
            'csv': FileDataSource,
            'webhook': WebhookDataSource
        }
        
        client_class = source_map.get(source_type)
        if not client_class:
            raise ValueError(f"Unsupported source type: {source_type}")
        
        return client_class(crm_source, **kwargs)
```

### 1. **Fetch Phase**
```python
async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict], None]:
    last_sync = kwargs.get('last_sync')
    
    # Implement pagination with delta filtering
    async for batch in client.fetch_records(last_sync=last_sync):
        yield batch
```

### 2. **Transform Phase**
```python
def transform_record(self, record: Dict) -> Dict:
    # 1. Apply field mappings (API → Model)
    transformed = self.apply_field_mappings(record)
    
    # 2. Parse data types (datetime, decimal, boolean)
    transformed = self.parse_data_types(transformed)
    
    # 3. Clean and normalize data
    transformed = self.clean_data(transformed)
    
    return transformed
```

### 3. **Validate Phase**
```python
def validate_record(self, record: Dict) -> Dict:
    # 1. Required field validation
    # 2. Data type validation
    # 3. Business rule validation
    # 4. Field-specific validation (email, phone, URLs)
    
    return validated_record
```

### 4. **Save Phase**
```python
async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
    if self.force_overwrite:
        return await self._force_overwrite_records(validated_data)
    else:
        return await self._bulk_upsert_records(validated_data)
```

## Validation & Processing Framework

### 1. **Multi-Level Validation Strategy**

```python
class ValidationFramework:
    """Enhanced validation framework with context-aware logging"""
    
    def __init__(self, crm_source: str):
        self.crm_source = crm_source
        self.validators = self.load_validators()
        self.strict_mode = self.get_validation_config()
    
    def validate_field(self, field_name: str, value: Any, 
                      field_type: str, context: Dict = None) -> Any:
        """Core validation method with enhanced logging"""
        try:
            validator = self.get_validator(field_type)
            return validator.validate(value)
            
        except ValidationException as e:
            context_info = self.build_context_string(context)
            
            if self.strict_mode:
                logger.error(
                    f"Strict validation failed for field '{field_name}' "
                    f"with value '{value}'{context_info}: {e}"
                )
                raise ValidationException(f"Field '{field_name}': {e}")
            else:
                logger.warning(
                    f"Validation warning for field '{field_name}' "
                    f"with value '{value}'{context_info}: {e}"
                )
                return value  # Return original value in non-strict mode
```

### 2. **Field Type Validators**

```python
FIELD_TYPE_VALIDATORS = {
    'email': EmailValidator,
    'phone': PhoneValidator,
    'url': URLValidator,
    'date': DateValidator,
    'datetime': DateTimeValidator,
    'decimal': DecimalValidator,
    'integer': IntegerValidator,
    'boolean': BooleanValidator,
    'zip_code': ZipCodeValidator,
    'state': StateValidator,
    'object_id': ObjectIdValidator
}

class BaseValidator:
    """Base validator with common functionality"""
    
    def validate(self, value: Any) -> Any:
        """Main validation method"""
        if value is None or value == '':
            return None
        
        return self._validate_value(value)
    
    @abstractmethod
    def _validate_value(self, value: Any) -> Any:
        """Implement specific validation logic"""
        pass
```

### 3. **Standardized Logging Format**

All log messages follow these patterns:

**Validation Warnings:**
```
WARNING: Validation warning for field '{field_name}' with value '{value}' (Record: id={record_id}): {error_message}
```

**Processing Errors:**
```
WARNING: Failed to parse {data_type} value: '{value}' in field '{field_name}' for {crm_source} {record_id}
```

**Sync Operation Logs:**
```
INFO: Starting {crm_source} {entity_type} sync with {record_count} records
INFO: Completed {crm_source} {entity_type} sync: {created} created, {updated} updated, {failed} failed
```

### 4. **Data Transformation Patterns**

```python
class FieldMapper:
    """Generic field mapping for any CRM source"""
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Load field mappings from configuration"""
        return {
            # API-based sources (dot notation for nested fields)
            'properties.email': 'email',
            'properties.phone': 'phone',
            'properties.first_name': 'first_name',
            
            # Database sources (direct field names)
            'email_address': 'email',
            'phone_number': 'phone',
            'fname': 'first_name',
            
            # CSV sources (column headers)
            'Email': 'email',
            'Phone': 'phone',
            'FirstName': 'first_name'
        }
    
    def extract_nested_value(self, record: Dict, field_path: str) -> Any:
        """Extract values using dot notation for nested fields"""
        keys = field_path.split('.')
        value = record
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
```

### 5. **Business Rule Validation**

```python
class BusinessRuleValidator:
    """Custom business logic validation"""
    
    def validate_contact_completeness(self, record: Dict) -> List[str]:
        """Ensure contacts have minimum required information"""
        warnings = []
        
        if not record.get('email') and not record.get('phone'):
            warnings.append("Contact missing both email and phone")
        
        if not record.get('first_name') and not record.get('last_name'):
            warnings.append("Contact missing both first and last name")
        
        return warnings
    
    def validate_deal_consistency(self, record: Dict) -> List[str]:
        """Ensure deal data is logically consistent"""
        warnings = []
        
        if record.get('close_date') and record.get('create_date'):
            if record['close_date'] < record['create_date']:
                warnings.append("Deal close date is before create date")
        
        return warnings
```

### 6. **Record Processing Context**

```python
class ProcessingContext:
    """Context manager for record processing with detailed logging"""
    
    def __init__(self, crm_source: str, entity_type: str, record_id: str):
        self.crm_source = crm_source
        self.entity_type = entity_type
        self.record_id = record_id
        self.start_time = None
        self.warnings = []
        self.errors = []
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = time.time() - self.start_time
        
        if exc_type:
            logger.error(
                f"Failed to process {self.crm_source} {self.entity_type} "
                f"{self.record_id} after {duration:.2f}s: {exc_val}"
            )
        elif self.errors:
            logger.error(
                f"Errors processing {self.crm_source} {self.entity_type} "
                f"{self.record_id}: {'; '.join(self.errors)}"
            )
        elif self.warnings:
            logger.warning(
                f"Warnings processing {self.crm_source} {self.entity_type} "
                f"{self.record_id}: {'; '.join(self.warnings)}"
            )
```

## Error Handling & Resilience

### 1. **Hierarchical Error Handling**

```python
# Level 1: Batch-level errors (fallback to individual processing)
try:
    results = await self.bulk_save(batch)
except BulkOperationError:
    results = await self.individual_save(batch)

# Level 2: Individual record errors (log and continue)
for record in batch:
    try:
        await self.save_record(record)
    except RecordError as e:
        logger.error(f"Record {record['id']} failed: {e}")
        continue
```

### 2. **Error Categories**

- **Transient Errors**: Rate limits, network timeouts (retry)
- **Data Errors**: Invalid formats, missing required fields (log & skip)
- **System Errors**: Database connection, disk space (fail fast)

### 3. **Error Context Logging**

```python
logger.error(
    f"Error processing {entity_type} {record_id}: {error} - "
    f"CRM URL: {crm_record_url} - "
    f"Context: {error_context}"
)
```

## Performance Optimization

### 1. **Bulk Operations**

```python
# Preferred: Bulk upsert with conflict resolution
Model.objects.bulk_create(
    objects,
    update_conflicts=True,
    update_fields=['field1', 'field2', ...],
    unique_fields=['id'],
    batch_size=batch_size
)

# Fallback: Individual upsert
for record in records:
    Model.objects.update_or_create(
        id=record['id'],
        defaults=record
    )
```

### 2. **Connection Pooling**

```python
# Implement connection pools for:
# - CRM API connections
# - Database connections
# - External service connections
```

### 3. **Progress Tracking**

```python
# Use progress bars for long-running syncs
with tqdm(total=estimated_total, desc="Syncing records") as pbar:
    async for batch in fetch_data():
        # Process batch
        pbar.update(len(batch))
```

## Monitoring & Observability

### 1. **Mandatory Sync History Tracking with SyncHistory Table**

**CRITICAL REQUIREMENT**: All CRM integrations must use the standardized `SyncHistory` model for sync tracking. This is the single source of truth for all sync operations.

```python
from ingestion.models.common import SyncHistory

class SyncHistory(models.Model):
    """Centralized sync tracking for all CRM sources"""
    crm_source = models.CharField(max_length=50)      # 'hubspot', 'salesforce', 'callrail', 'salesrabbit'
    sync_type = models.CharField(max_length=50)       # 'contacts', 'deals', 'calls', 'leads'
    status = models.CharField(max_length=20)          # 'running', 'success', 'failed', 'partial'
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    error_message = models.TextField(null=True, blank=True)
    performance_metrics = models.JSONField(default=dict)
    configuration = models.JSONField(default=dict)    # Store sync parameters
    
    class Meta:
        db_table = 'ingestion_sync_history'
        indexes = [
            models.Index(fields=['crm_source', 'sync_type', '-start_time']),
            models.Index(fields=['status', '-start_time']),
            models.Index(fields=['-end_time']),
        ]
```

### **MANDATORY: Standard SyncHistory Implementation Pattern**

**Every CRM sync engine MUST implement this exact pattern:**

```python
from asgiref.sync import sync_to_async
from ingestion.models.common import SyncHistory
from django.utils import timezone

class StandardSyncEngine:
    """MANDATORY pattern for all CRM sync engines"""
    
    def __init__(self, crm_source: str, entity_type: str):
        self.crm_source = crm_source    # e.g., 'callrail', 'salesrabbit', 'hubspot'
        self.entity_type = entity_type  # e.g., 'calls', 'leads', 'contacts'
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """STANDARD PATTERN: Get last successful sync timestamp from SyncHistory"""
        try:
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source=self.crm_source,        # EXACT: CRM source name
                    sync_type=self.entity_type,        # EXACT: Entity type (NO '_sync' suffix)
                    status__in=['success', 'completed'], # Include successful syncs
                    end_time__isnull=False             # Only completed syncs
                ).order_by('-end_time').first()
                
                return last_sync.end_time if last_sync else None
            
            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """STANDARD PATTERN: Execute sync with mandatory SyncHistory tracking"""
        
        # Step 1: Create SyncHistory record at start
        sync_record = SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type=self.entity_type,    # IMPORTANT: Use entity_type directly
            status='running',
            start_time=timezone.now(),
            configuration=kwargs
        )
        
        stats = {
            'sync_history_id': sync_record.id,
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        try:
            # Step 2: Execute sync logic
            async for batch in self.fetch_data(**kwargs):
                batch_results = await self.process_batch(batch)
                stats['total_processed'] += batch_results['processed']
                stats['created'] += batch_results['created']
                stats['updated'] += batch_results['updated']
                stats['errors'] += batch_results['errors']
            
            # Step 3: Update SyncHistory with success
            sync_record.status = 'success' if stats['errors'] == 0 else 'partial'
            sync_record.end_time = timezone.now()
            sync_record.records_processed = stats['total_processed']
            sync_record.records_created = stats['created']
            sync_record.records_updated = stats['updated']
            sync_record.records_failed = stats['errors']
            sync_record.performance_metrics = {
                'duration_seconds': (sync_record.end_time - sync_record.start_time).total_seconds(),
                'records_per_second': stats['total_processed'] / (sync_record.end_time - sync_record.start_time).total_seconds() if stats['total_processed'] > 0 else 0,
                'success_rate': (stats['total_processed'] - stats['errors']) / stats['total_processed'] if stats['total_processed'] > 0 else 0
            }
            sync_record.save()
            
            return stats
            
        except Exception as e:
            # Step 4: Update SyncHistory with failure
            sync_record.status = 'failed'
            sync_record.end_time = timezone.now()
            sync_record.error_message = str(e)
            sync_record.records_failed = stats.get('errors', 0)
            sync_record.save()
            
            logger.error(f"{self.crm_source} {self.entity_type} sync failed: {e}")
            raise
```

### **Critical Field Standards**

| Field | Format | Examples | Notes |
|-------|--------|----------|-------|
| `crm_source` | Lowercase CRM name | `'callrail'`, `'salesrabbit'`, `'hubspot'` | **NO underscores or spaces** |
| `sync_type` | Entity name only | `'calls'`, `'leads'`, `'contacts'` | **NO '_sync' suffix** |
| `status` | Standard values | `'running'`, `'success'`, `'failed'`, `'partial'` | **Use exact values** |

### **🚫 FORBIDDEN Patterns**

**DO NOT use these incorrect patterns:**

```python
# ❌ WRONG: Adding '_sync' suffix to entity type
sync_type='leads_sync'     # Should be 'leads'
sync_type='calls_sync'     # Should be 'calls'

# ❌ WRONG: Using different status values
status='completed'         # Should be 'success'
status='error'            # Should be 'failed'

# ❌ WRONG: Different field names
crm_type='salesrabbit'    # Should be 'crm_source'
entity_name='calls'       # Should be 'sync_type'
```

### **SyncHistory Compliance Validation**

**Use this checklist to verify SyncHistory compliance for any CRM integration:**

```python
class SyncHistoryValidator:
    """Validate that CRM sync engines properly use SyncHistory"""
    
    @staticmethod
    def validate_sync_compliance(crm_source: str, entity_type: str) -> Dict[str, bool]:
        """Check if sync engine follows SyncHistory standards"""
        checks = {}
        
        # Check 1: Recent sync records exist with correct field values
        recent_syncs = SyncHistory.objects.filter(
            crm_source=crm_source,
            sync_type=entity_type  # MUST match exactly - no suffixes
        ).order_by('-start_time')[:5]
        checks['has_sync_records'] = recent_syncs.exists()
        
        # Check 2: Status values are standard
        if recent_syncs.exists():
            latest_sync = recent_syncs.first()
            checks['proper_status'] = latest_sync.status in ['running', 'success', 'failed', 'partial']
            checks['has_end_time'] = latest_sync.end_time is not None if latest_sync.status != 'running' else True
            checks['has_performance_metrics'] = bool(latest_sync.performance_metrics) if latest_sync.status == 'success' else True
        
        # Check 3: Field naming compliance
        valid_pattern = f"{crm_source}_{entity_type}"
        checks['correct_field_pattern'] = True  # This should be verified during code review
        
        return checks
    
    @staticmethod
    def validate_sync_engine_implementation(engine_class) -> List[str]:
        """Validate that sync engine follows mandatory patterns"""
        issues = []
        
        # Check method existence
        if not hasattr(engine_class, 'get_last_sync_timestamp'):
            issues.append("Missing required method: get_last_sync_timestamp()")
        
        # Check SyncHistory import
        source_code = inspect.getsource(engine_class)
        if 'from ingestion.models.common import SyncHistory' not in source_code:
            issues.append("Missing required import: SyncHistory")
        
        return issues
```

### 2. **Key Metrics**

- **Throughput**: Records per second
- **Success Rate**: Successful records / Total records
- **Error Rate**: Failed records / Total records
- **Delta Efficiency**: New records / Total API calls
- **Resource Usage**: Memory, CPU, API rate limits

### 3. **Alerting Triggers**

- Sync failure rate > 5%
- Sync duration > expected baseline
- Zero records processed (potential API issues)
- Rate limit violations

## Security & Authentication

### 1. **API Token Management**

```python
# Environment-based token storage
HUBSPOT_API_TOKEN = os.getenv('HUBSPOT_API_TOKEN')

# Token rotation support
def refresh_token_if_needed(self):
    if self.token_expires_soon():
        self.token = self.refresh_access_token()
```

### 2. **Data Encryption**

```python
# Encrypt sensitive fields in transit and at rest
class EncryptedFieldMixin:
    def encrypt_field(self, value):
        return fernet.encrypt(value.encode())
    
    def decrypt_field(self, encrypted_value):
        return fernet.decrypt(encrypted_value).decode()
```

## Configuration Management

### 1. **Sync Configuration**

```python
SYNC_CONFIG = {
    'hubspot': {
        'contacts': {
            'batch_size': 100,
            'rate_limit': 100,  # requests per 10 seconds
            'retry_attempts': 3,
            'timeout': 30,
            'delta_sync': True,
            'object_type': '0-1',  # HubSpot object type
        }
    }
}
```

### 2. **Field Mappings**

```python
FIELD_MAPPINGS = {
    'hubspot_contacts': {
        'properties.email': 'email',
        'properties.firstname': 'first_name',
        'properties.lastname': 'last_name',
        'properties.phone': 'phone',
        # Add all field mappings
    }
}
```

## Testing Strategy

### 1. **Unit Tests**

- Field mapping validation
- Data transformation logic
- Error handling scenarios
- Delta sync timestamp calculation

### 2. **Integration Tests**

- API client connectivity
- Database operations
- End-to-end sync workflows

### 3. **Performance Tests**

- Large dataset handling
- Memory usage under load
- API rate limit compliance

### 4. **Test Patterns**

```python
class TestCRMProcessor(TestCase):
    """Unit tests for CRM processor implementations"""
    
    def setUp(self):
        self.processor = MockCRMProcessor(MockModel)
        self.sample_data = self.load_test_fixtures()
    
    def test_transform_record_with_valid_data(self):
        """Test record transformation with valid data"""
        input_record = self.sample_data['valid_record']
        result = self.processor.transform_record(input_record)
        
        self.assertIsNotNone(result)
        self.assertEqual(result['email'], input_record['properties']['email'])
        self.assertIsInstance(result['created_date'], datetime)
    
    def test_validate_record_with_invalid_email(self):
        """Test validation with invalid email"""
        record = self.sample_data['invalid_email_record']
        
        with self.assertLogs(level='WARNING') as log:
            result = self.processor.validate_record(record)
            
            # Check that warning was logged with proper format
            self.assertIn('Validation warning for field \'email\'', log.output[0])
            self.assertIn('(Record: id=', log.output[0])

class TestCRMSyncIntegration(AsyncTestCase):
    """Integration tests for complete sync operations"""
    
    async def test_full_sync_operation(self):
        """Test complete sync operation end-to-end"""
        # Setup test data
        mock_data = self.load_mock_api_response()
        self.mock_client.set_response_data(mock_data)
        
        # Execute sync
        result = await self.test_engine.run_sync(max_records=10)
        
        # Verify results
        self.assertEqual(result['status'], 'success')
        self.assertEqual(result['records_processed'], 10)
        self.assertGreater(result['records_created'], 0)
```

### 5. **Test Data Fixtures**

```python
class CRMTestFixtures:
    """Centralized test data fixtures for CRM testing"""
    
    @staticmethod
    def get_valid_contact_record():
        """Return valid contact record for testing"""
        return {
            'id': '12345',
            'properties': {
                'email': 'test@example.com',
                'phone': '+1-555-123-4567',
                'first_name': 'John',
                'last_name': 'Doe',
                'created_date': '2025-01-01T00:00:00Z'
            }
        }
```

## CRM-Specific Considerations

### HubSpot
- Uses custom object types (e.g., '0-1' for contacts)
- Rate limits: 100 requests per 10 seconds
- Delta sync via search API with `hs_lastmodifieddate`
- Pagination with `after` tokens

### Salesforce
- Uses SOQL queries for data retrieval
- Rate limits: API call quotas per org
- Delta sync via `LastModifiedDate` field
- Bulk API for large datasets

### Pipedrive
- REST API with standard pagination
- Rate limits: 1000 requests per hour
- Delta sync via `update_time` parameter

## Deployment Checklist

### Pre-Deployment
- [ ] API credentials configured
- [ ] Database migrations applied
- [ ] Rate limit configurations set
- [ ] Monitoring dashboards created
- [ ] Error alerting configured

### Post-Deployment
- [ ] Initial full sync completed
- [ ] Delta sync verified working
- [ ] Performance metrics baseline established
- [ ] Error handling tested
- [ ] Monitoring alerts functioning

### Maintenance
- [ ] Regular sync performance review
- [ ] API token rotation schedule
- [ ] Data quality monitoring
- [ ] Sync history cleanup
- [ ] Capacity planning updates

## Best Practices Summary

1. **Always implement delta sync** for performance
2. **Use bulk operations** wherever possible
3. **Handle errors gracefully** with fallback strategies
4. **Log comprehensive context** for debugging
5. **Monitor sync health** continuously
6. **Validate data quality** at multiple stages
7. **Plan for API rate limits** and failures
8. **Test with production-like data volumes**
9. **Document field mappings** thoroughly
10. **Implement proper security** for API credentials

## Common Pitfalls to Avoid

1. **No delta sync**: Always fetching all records
2. **Poor error handling**: Failing entire sync for single record errors
3. **No rate limiting**: Exceeding API quotas
4. **Inadequate logging**: Insufficient context for debugging
5. **No monitoring**: Silent failures going unnoticed
6. **Hardcoded configurations**: Environment-specific settings in code
7. **No data validation**: Accepting malformed data
8. **Memory leaks**: Not cleaning up large datasets
9. **No rollback strategy**: No way to recover from bad syncs
10. **Ignoring API changes**: Not handling API version updates

---

*This guide provides a foundation for implementing robust, scalable CRM sync systems. Adapt the patterns and practices to your specific CRM requirements and organizational needs.*
