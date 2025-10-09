# Data Warehouse System Architecture

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Comprehensive architecture reference for AI agents and team members

---

## Table of Contents
1. [System Overview](#system-overview)
2. [Architecture Layers](#architecture-layers)
3. [Design Patterns](#design-patterns)
4. [CRM Integration Framework](#crm-integration-framework)
5. [Component Relationships](#component-relationships)
6. [Data Flow](#data-flow)
7. [Technology Stack](#technology-stack)

---

## System Overview

The Data Warehouse is a **Django-based enterprise data integration platform** that consolidates data from multiple CRM systems into a centralized PostgreSQL database. The system supports:

- **11+ CRM Integrations**: HubSpot, Genius, CallRail, SalesRabbit, Arrivy, Five9, MarketSharp, LeadConduit, SalesPro, Google Sheets
- **Async Sync Operations**: Batch processing with Celery distributed task queue
- **Unified Dashboard**: Real-time monitoring of all CRM sync operations
- **Scheduled Automation**: Cron-based sync scheduling with django-celery-beat
- **API-First Design**: RESTful API with Django REST Framework
- **Docker Containerization**: Full production deployment with Docker Compose

### Core Principles
1. **Unified Sync Framework**: All CRM integrations follow `BaseSyncEngine` pattern
2. **SyncHistory Tracking**: Every sync operation tracked with metrics
3. **Async-First**: All I/O operations use async/await
4. **Bulk Operations**: Optimized database operations with Django ORM
5. **Error Resilience**: Comprehensive error handling with fallback strategies

---

## Architecture Layers

### Layer 1: Presentation Layer
**Location**: `ingestion/views/`, `templates/`

**Components**:
- **CRM Dashboard** (`crm_dashboard/views.py`): Main management UI
  - `CRMDashboardView`: Overview of all CRM sources
  - `CRMModelsView`: Model listing per CRM
  - `ModelDetailView`: Individual model data browser
  - `SyncHistoryView`: Sync execution history
  - `AllSchedulesView`: Schedule management
  
- **API Views** (`crm_dashboard/api_views.py`): RESTful endpoints
  - `CRMListAPIView`: List all CRM sources
  - `CRMModelsAPIView`: Get models for CRM
  - `SyncExecuteAPIView`: Trigger sync operations
  - `SyncStatusAPIView`: Real-time sync status
  - `ModelDataAPIView`: Paginated model data
  
- **Test Interface** (`tests/views.py`): Test execution UI
  - Test discovery and execution
  - Safety controls (MOCKED, MINIMAL, SAMPLE, RECENT, FULL_SYNC)
  - Test result tracking

**Technologies**: Django Templates, Bootstrap 5, JavaScript, HTMX

### Layer 2: Service Layer
**Location**: `ingestion/services/`

**Components**:
- **CRMDiscoveryService** (`crm_discovery.py`): Auto-discovers CRM models and metadata
  - Introspects `ingestion/models/` for CRM sources
  - Provides model metadata, record counts, sync status
  - Maps model names to sync_type for dashboard queries
  
- **SyncManagementService** (`sync_management.py`): Orchestrates sync execution
  - Discovers available management commands
  - Executes syncs via subprocess
  - Tracks running processes
  - Handles sync cancellation
  
- **DataAccessService** (`data_access.py`): Model data access layer
  - Paginated model queries
  - Field introspection and metadata
  - Search capabilities
  - Statistics calculation

**Design Pattern**: Service Layer (Domain-Driven Design)

### Layer 3: Sync Engine Layer
**Location**: `ingestion/sync/{crm}/engines/`

**Base Class**: `BaseSyncEngine` (`ingestion/base/sync_engine.py`)

**Abstract Methods**:
```python
async def initialize_client() -> None
async def fetch_data(**kwargs) -> AsyncGenerator[List[Dict], None]
async def transform_data(raw_data: List[Dict]) -> List[Dict]
async def validate_data(data: List[Dict]) -> List[Dict]
async def save_data(validated_data: List[Dict]) -> Dict[str, int]
async def cleanup() -> None
```

**Workflow Methods** (provided by base):
- `start_sync()`: Creates SyncHistory record
- `run_sync()`: Main orchestration loop
- `complete_sync()`: Updates SyncHistory with results
- `save_data_bulk()`: Bulk save operations

**CRM-Specific Engines**:
- `HubSpotBaseSyncEngine`: Contact, deals, appointments, associations, custom objects
- `GeniusBaseSyncEngine`: Leads, appointments, prospects, divisions
- `CallRailBaseSyncEngine`: Calls, companies, trackers, form submissions
- `SalesRabbitBaseSyncEngine`: Leads, users
- `ArrivyBaseSyncEngine`: Bookings, tasks, entities, groups, statuses
- `Five9SyncEngine`: Contact sync
- `MarketSharpSyncEngine`: Data sync
- `LeadConduitSyncEngine`: Lead sync
- `SalesProBaseSyncEngine`: Athena query-based sync (credit apps, customers, estimates)
- `GoogleSheetsSyncEngine`: Marketing leads, spends

**Design Pattern**: Template Method Pattern + Strategy Pattern

### Layer 4: Client Layer
**Location**: `ingestion/sync/{crm}/clients/`

**Responsibility**: API communication and data fetching

**Base Pattern**:
```python
class BaseClient:
    async def fetch_data(self, **params) -> List[Dict]
    async def fetch_paginated(self, endpoint: str, **params) -> AsyncGenerator
    def _handle_rate_limiting(self)
    def _handle_authentication(self)
```

**Examples**:
- `HubSpotContactsClient`: Fetches contacts via HubSpot API
- `CallRailCallsClient`: Fetches calls with pagination
- `SalesRabbitLeadsClient`: GraphQL API client
- `GeniusProspectClient`: Raw SQL queries to Genius DB
- `ArrivyBookingsClient`: REST API with token auth

**Design Pattern**: Repository Pattern + Adapter Pattern

### Layer 5: Processor Layer
**Location**: `ingestion/sync/{crm}/processors/`

**Responsibility**: Data transformation and business logic

**Base Class**: `BaseDataProcessor` (`ingestion/base/processor.py`)

**Methods**:
```python
def transform_data(raw_data: List[Dict]) -> List[Dict]
def validate_record(record: Dict) -> bool
def save_data(records: List[Dict]) -> Dict[str, int]
def _bulk_upsert(records: List[Dict]) -> Dict[str, int]
```

**Examples**:
- `HubSpotContactsProcessor`: Normalizes HubSpot contact properties
- `CallRailCallsProcessor`: Processes call records, extracts metadata
- `GeniusLeadProcessor`: Validates lead data, handles custom fields
- `SalesRabbitLeadProcessor`: Transforms GraphQL response

**Design Pattern**: Strategy Pattern + Chain of Responsibility

### Layer 6: Model Layer
**Location**: `ingestion/models/`

**Structure**:
```
ingestion/models/
├── common.py           # SyncHistory, SyncSchedule, shared models
├── hubspot.py          # HubSpot_Contact, HubSpot_Deal, etc.
├── genius.py           # Genius_Lead, Genius_Appointment, etc.
├── callrail.py         # CallRail_Call, CallRail_Company, etc.
├── salesrabbit.py      # SalesRabbit_Lead, SalesRabbit_User
├── arrivy.py           # Arrivy_Booking, Arrivy_Task, etc.
├── five9.py            # Five9_Contact
├── marketsharp.py      # MarketSharp_Data
├── leadconduit.py      # LeadConduit_Lead
├── salespro.py         # SalesPro_CreditApplication, etc.
├── gsheet.py           # GSheet_MarketingLead, GSheet_MarketingSpend
└── alerts.py           # Alert models
```

**Common Fields Pattern**:
- Most models include: `created_at`, `updated_at`, `raw_data` (JSONField)
- Primary keys vary: some use CRM's ID, others use Django auto-generated
- All tables use `ingestion_` or `{crm}_` prefix

**Design Pattern**: Active Record Pattern (Django ORM)

### Layer 7: Management Commands
**Location**: `ingestion/management/commands/`

**Naming Convention**: `sync_{crm}_{entity}.py`

**Base Class**: Django's `BaseCommand`

**Standard Arguments**:
```python
--dry-run        # Run without saving data
--full           # Full sync (vs delta)
--debug          # Enable debug logging
--batch-size     # Records per batch
--since          # Date filter for delta syncs
--force          # Force overwrite existing records
```

**Examples**:
- `sync_hubspot_contacts.py`: Syncs HubSpot contacts
- `sync_hubspot_all.py`: Orchestrates all HubSpot syncs
- `sync_callrail_calls.py`: Syncs CallRail calls
- `sync_salesrabbit_leads.py`: Syncs SalesRabbit leads
- `sync_genius_prospects.py`: Syncs Genius prospects

**Execution**: 
```bash
python manage.py sync_hubspot_contacts --dry-run --batch-size 100
```

**Design Pattern**: Command Pattern

### Layer 8: Task Queue Layer
**Location**: `ingestion/tasks.py`, `data_warehouse/celery.py`

**Components**:
- **Celery Workers**: Async task execution
- **Celery Beat**: Cron scheduler
- **Redis**: Message broker and result backend

**Task Types**:
- **Scheduled Syncs**: Periodic data synchronization
- **On-Demand Syncs**: Manual sync triggers
- **Report Generation**: Automated report creation

**Example Task**:
```python
@shared_task
def sync_hubspot_contacts_task():
    call_command('sync_hubspot_contacts', '--full')
```

**Design Pattern**: Producer-Consumer Pattern

---

## Design Patterns

### 1. Template Method Pattern
**Used In**: `BaseSyncEngine`

The base sync engine defines the sync workflow skeleton:
```python
async def run_sync(self, **kwargs):
    await self.start_sync()          # Create SyncHistory
    await self.initialize_client()    # Setup
    async for batch in self.fetch_data():
        transformed = await self.transform_data(batch)
        validated = await self.validate_data(transformed)
        results = await self.save_data(validated)
    await self.complete_sync(results)  # Update SyncHistory
    await self.cleanup()
```

Subclasses implement specific steps while framework handles orchestration.

### 2. Strategy Pattern
**Used In**: Sync strategy determination

```python
def determine_sync_strategy(self, force_full: bool = False):
    if force_full:
        return {'mode': 'full', 'since': None}
    else:
        last_sync = self.get_last_successful_sync()
        return {'mode': 'delta', 'since': last_sync.end_time}
```

### 3. Repository Pattern
**Used In**: Client classes

Clients abstract data access from sync engines:
```python
class HubSpotContactsClient:
    async def fetch_contacts(self, since: datetime = None):
        # Abstracts API details from sync engine
```

### 4. Adapter Pattern
**Used In**: CRM-specific integrations

Each CRM adapter conforms to `BaseSyncEngine` interface despite different APIs.

### 5. Observer Pattern
**Used In**: SyncHistory tracking

`SyncHistory` records observe sync lifecycle events and update accordingly.

### 6. Bulk Operations Pattern
**Used Throughout**: Django ORM bulk operations

```python
# Instead of:
for record in records:
    Model.objects.create(**record)

# Use:
Model.objects.bulk_create([Model(**r) for r in records])
Model.objects.bulk_update(objs, fields)
```

### 7. Async/Await Pattern
**Used Throughout**: All I/O operations

```python
from asgiref.sync import sync_to_async

@sync_to_async
def _query_database():
    return list(Model.objects.all())

async def process():
    data = await _query_database()
```

---

## CRM Integration Framework

### Standard Integration Structure

```
ingestion/sync/{crm}/
├── __init__.py
├── README.md                 # Integration documentation
├── clients/
│   ├── __init__.py
│   ├── base.py              # Base client for this CRM
│   └── {entity}_client.py   # Entity-specific clients
├── processors/
│   ├── __init__.py
│   └── {entity}_processor.py
├── engines/
│   ├── __init__.py
│   ├── base.py              # Base engine for this CRM
│   └── {entity}_engine.py   # Entity sync engines
└── config/
    └── settings.py          # CRM-specific settings
```

### Integration Checklist

When adding a new CRM:
1. ✅ Create models in `ingestion/models/{crm}.py`
2. ✅ Run migrations to create tables
3. ✅ Create client class(es) in `sync/{crm}/clients/`
4. ✅ Create processor class(es) in `sync/{crm}/processors/`
5. ✅ Create engine class(es) inheriting from `BaseSyncEngine`
6. ✅ Create management command(s) in `management/commands/`
7. ✅ Add CRM to `CRMDiscoveryService.crm_systems` dict
8. ✅ Create tests in `tests/test_crm_{crm}.py`
9. ✅ Add API credentials to `.env`
10. ✅ Document in `sync/{crm}/README.md`

### SyncHistory Integration

**Every sync operation must**:
1. Call `start_sync()` to create `SyncHistory` record
2. Update `records_processed`, `records_created`, `records_updated`
3. Call `complete_sync()` with final results
4. Set status: `'running'`, `'success'`, `'failed'`, `'partial'`

**Example**:
```python
async def run_sync(self):
    await self.start_sync()  # Creates SyncHistory with status='running'
    
    try:
        # ... sync operations ...
        results = {'processed': 100, 'created': 20, 'updated': 80}
        await self.complete_sync(results)  # Updates SyncHistory with status='success'
    except Exception as e:
        await self.complete_sync({}, error=str(e))  # status='failed'
```

---

## Component Relationships

### Data Flow Diagram
```
┌─────────────────────────────────────────────────────────────────┐
│                      PRESENTATION LAYER                         │
│  Dashboard UI  │  API Endpoints  │  Test Interface              │
└────────────┬───────────────────────────────────────┬────────────┘
             │                                       │
             ▼                                       ▼
┌─────────────────────────────────────────────────────────────────┐
│                       SERVICE LAYER                             │
│  CRMDiscovery  │  SyncManagement  │  DataAccess                 │
└────────────┬─────────────┬──────────────────────────┬───────────┘
             │             │                          │
             ▼             ▼                          ▼
┌─────────────────────────────────────────────────────────────────┐
│                    MANAGEMENT COMMANDS                          │
│  sync_hubspot_contacts  │  sync_callrail_calls  │ ...          │
└────────────┬────────────────────────────────────────────────────┘
             │
             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      SYNC ENGINE LAYER                          │
│  BaseSyncEngine → HubSpotContactsSyncEngine                     │
│                → CallRailCallsSyncEngine                         │
│                → GeniusLeadsSyncEngine                           │
└────────┬───────────────────────────────────┬────────────────────┘
         │                                   │
         ▼                                   ▼
┌──────────────────────┐           ┌─────────────────────┐
│   CLIENT LAYER       │           │  PROCESSOR LAYER    │
│  - API clients       │           │  - Transform data   │
│  - Pagination        │           │  - Validate data    │
│  - Authentication    │◄──────────┤  - Business logic   │
└──────────┬───────────┘           └──────────┬──────────┘
           │                                  │
           └──────────────┬───────────────────┘
                          ▼
                ┌──────────────────────┐
                │    MODEL LAYER       │
                │  Django ORM Models   │
                └──────────┬───────────┘
                           ▼
                ┌──────────────────────┐
                │   PostgreSQL DB      │
                └──────────────────────┘
```

### Key Relationships

1. **Dashboard → Services**: Dashboard calls services for data
2. **Services → Models**: Services query Django ORM
3. **Commands → Engines**: Commands instantiate and execute engines
4. **Engines → Clients**: Engines use clients to fetch data
5. **Engines → Processors**: Engines use processors to transform data
6. **Engines → Models**: Engines save to database via Django ORM
7. **Engines → SyncHistory**: All engines track execution in SyncHistory

---

## Data Flow

### Typical Sync Flow

1. **Trigger**: User clicks "Sync Now" in dashboard OR scheduled Celery task fires
2. **Command Execution**: `SyncExecuteAPIView` calls management command via subprocess
3. **Engine Initialization**: Command creates engine instance
4. **SyncHistory Start**: Engine calls `start_sync()` → creates record with status='running'
5. **Client Setup**: Engine calls `initialize_client()` → creates API client
6. **Strategy**: Engine determines sync strategy (full vs delta)
7. **Fetch Loop**: 
   - Engine calls `client.fetch_data()` → yields batches
   - For each batch:
     - `transform_data()` → normalize format
     - `validate_data()` → check data quality
     - `save_data()` → bulk upsert to DB
8. **Completion**: Engine calls `complete_sync(results)` → updates SyncHistory
9. **Cleanup**: Engine calls `cleanup()` → closes connections
10. **Response**: Dashboard polls sync status, shows results

### Error Handling Flow

```
┌─────────────────┐
│  Bulk Operation │
└────────┬────────┘
         │
         ▼
    ┌─────────┐
    │ Success?│
    └────┬────┘
         │
    ┌────┴─────┐
    │ Yes      │ No
    ▼          ▼
┌────────┐  ┌────────────────────┐
│ Return │  │ Individual Fallback│
│ Results│  └───────┬────────────┘
└────────┘          │
                    ▼
              ┌─────────────┐
              │ Log Failures│
              └─────────────┘
```

---

## Technology Stack

### Backend
- **Framework**: Django 4.2+
- **Database**: PostgreSQL 13+
- **ORM**: Django ORM
- **API**: Django REST Framework
- **Task Queue**: Celery 5.x
- **Message Broker**: Redis 6.x
- **Scheduler**: django-celery-beat
- **Async**: asyncio, asgiref

### Frontend
- **UI Framework**: Bootstrap 5
- **JavaScript**: Vanilla JS + HTMX
- **Charts**: Chart.js
- **Templates**: Django Templates

### Infrastructure
- **Containerization**: Docker, Docker Compose
- **Web Server**: Gunicorn
- **Reverse Proxy**: Nginx (production)
- **Monitoring**: Django Debug Toolbar (dev)

### External APIs
- **HubSpot API**: REST API v3
- **CallRail API**: REST API v3
- **SalesRabbit API**: GraphQL API
- **Arrivy API**: REST API
- **Five9 API**: REST API
- **Google Sheets API**: Google API Client
- **AWS Athena**: boto3 client (SalesPro)

### Development Tools
- **Testing**: pytest, Django TestCase
- **Linting**: flake8, black
- **Version Control**: Git
- **CI/CD**: (to be implemented)

---

## Security Considerations

### API Credentials
- Stored in `.env` file (gitignored)
- Loaded via `django-environ`
- Never hardcoded in source

### Database Access
- Connection pooling via `django-db-connection-pool`
- Separate read replicas for reporting (planned)
- Row-level security (future enhancement)

### Authentication
- Django admin for internal users
- Token-based auth for API access (planned)
- Service account credentials for external APIs

---

## Performance Optimization

### Database Optimization
1. **Bulk Operations**: Always use `bulk_create()`, `bulk_update()`
2. **Indexing**: Index foreign keys and frequently queried fields
3. **Select Related**: Use `select_related()` and `prefetch_related()`
4. **Raw SQL**: Use raw SQL for complex queries (e.g., Genius sync)

### Async Optimization
1. **Batch Processing**: Process records in batches (default 100-1000)
2. **Async I/O**: All API calls use `aiohttp` or async wrappers
3. **Database Connection Pooling**: Reuse connections across requests

### Caching Strategy
1. **Dashboard Cache**: Cache CRM discovery results (5 min TTL)
2. **API Response Cache**: Cache frequently accessed endpoints
3. **Query Result Cache**: Cache expensive aggregate queries

---

## Monitoring and Observability

### Logging
- **Location**: `logs/` directory
- **Files**: `ingestion.log`, `sync_engines.log`, `general.log`
- **Format**: Structured JSON logs
- **Levels**: DEBUG, INFO, WARNING, ERROR, CRITICAL

### Metrics Tracked
- **Sync Duration**: Time per sync operation
- **Record Counts**: Processed, created, updated, failed
- **Error Rates**: Failures per CRM per time period
- **API Call Rates**: Requests per second to external APIs

### SyncHistory Analytics
- All sync operations stored in `SyncHistory` table
- Dashboard provides charts and summaries
- Retention: 90 days (configurable)

---

## Future Enhancements

### Planned Improvements
1. **Real-time Webhooks**: Receive push notifications from CRMs
2. **Data Validation Layer**: Comprehensive data quality checks
3. **Audit Trail**: Track all data modifications
4. **Multi-tenancy**: Support multiple customer organizations
5. **API Rate Limiting**: Intelligent rate limit handling
6. **Data Retention Policies**: Automated archival and cleanup
7. **Advanced Scheduling**: More flexible sync schedules
8. **Error Recovery**: Automatic retry with exponential backoff
9. **Data Lineage**: Track data provenance across systems
10. **Machine Learning**: Predictive sync scheduling, anomaly detection

---

## Related Documents

- [Database Schema Reference](DATABASE_SCHEMA.md)
- [API & Integration Reference](API_INTEGRATIONS.md)
- [Existing Tests Documentation](EXISTING_TESTS.md)
- [PM Reference Guide](PM_GUIDE.md)
- [Codebase Navigation Map](CODEBASE_MAP.md)
- [CRM Sync Guide](../crm_sync_guide.md)
- [Current CRM Implementation](../current_crm_implementation.md)

---

**Document Maintained By**: Development Team  
**Last Review**: 2025  
**Next Review**: Quarterly
