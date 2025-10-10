# Codebase Navigation Map

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Quick reference for finding components in the codebase

---

## Directory Structure Overview

```
Data-Warehouse/
├── data_warehouse/          # Django project settings
│   ├── settings.py          # Main configuration
│   ├── celery.py            # Celery task queue setup
│   ├── urls.py              # Root URL configuration
│   └── wsgi.py              # WSGI application
│
├── ingestion/               # Main Django app
│   ├── models/              # Database models
│   │   ├── common.py        # SyncHistory, SyncSchedule
│   │   ├── hubspot.py       # HubSpot models
│   │   ├── genius.py        # Genius models
│   │   ├── callrail.py      # CallRail models
│   │   └── [other CRMs]     # Additional CRM models
│   │
│   ├── sync/                # CRM sync implementations
│   │   ├── {crm}/           # Per-CRM directory
│   │   │   ├── clients/     # API clients
│   │   │   ├── processors/  # Data transformation
│   │   │   ├── engines/     # Sync engines
│   │   │   └── README.md    # Integration docs
│   │   └── ...
│   │
│   ├── base/                # Base classes
│   │   ├── sync_engine.py   # BaseSyncEngine
│   │   ├── processor.py     # BaseDataProcessor
│   │   └── client.py        # BaseClient
│   │
│   ├── management/          # Django management commands
│   │   └── commands/
│   │       ├── sync_hubspot_contacts.py
│   │       ├── sync_callrail_calls.py
│   │       └── [all sync commands]
│   │
│   ├── services/            # Business logic layer
│   │   ├── crm_discovery.py        # Auto-discover CRMs
│   │   ├── sync_management.py      # Sync orchestration
│   │   └── data_access.py          # Data access layer
│   │
│   ├── views/               # Web views
│   │   ├── crm_dashboard/   # Dashboard views
│   │   │   ├── views.py     # HTML views
│   │   │   └── api_views.py # REST API views
│   │   └── ...
│   │
│   ├── tests/               # Test suite
│   │   ├── test_crm_hubspot.py
│   │   ├── test_callrail.py
│   │   ├── test_interface.py
│   │   ├── base/            # Test infrastructure
│   │   └── ...
│   │
│   ├── migrations/          # Database migrations
│   ├── static/              # Static files (CSS, JS, images)
│   ├── templates/           # Django templates
│   └── urls.py              # App URL configuration
│
├── docs/                    # Documentation
│   ├── AI/                  # AI agent documentation
│   │   ├── reference/       # Reference docs
│   │   │   ├── ARCHITECTURE.md
│   │   │   ├── DATABASE_SCHEMA.md
│   │   │   ├── API_INTEGRATIONS.md
│   │   │   ├── EXISTING_TESTS.md
│   │   │   ├── PM_GUIDE.md
│   │   │   ├── CRM_SYNC_GUIDE.md
│   │   │   ├── WORKER_POOL_SYSTEM.md
│   │   │   └── CODEBASE_MAP.md (this file)
│   │   ├── SETUP_GUIDE.md
│   │   ├── QUICK_REFERENCE.md
│   │   └── INTEGRATION_SUMMARY.md
│   ├── crm_sync_guide.md
│   ├── CRM_DASHBOARD_REQUIREMENTS.md
│   └── [other documentation]
│
├── scripts/                 # Utility scripts
│   ├── setup_adk.bat        # Google ADK setup (Windows)
│   ├── setup_adk.sh         # Google ADK setup (Linux/Mac)
│   └── [other scripts]
│
├── logs/                    # Application logs
├── templates/               # Global templates
├── staticfiles/             # Collected static files
├── agents/                  # Google ADK agents
│   ├── tools.py             # Agent tools
│   └── team.py              # Agent workflow
│
├── docker-compose.yml       # Docker orchestration
├── Dockerfile               # Docker image definition
├── requirements.txt         # Python dependencies
├── manage.py                # Django management script
└── .env                     # Environment variables (gitignored)
```

---

## Quick Find Guide

### "I need to..."

#### 🚨 **CRITICAL REFERENCE**: Before Adding Any New Feature

**MANDATORY READING for AI agents and developers:**

1. **[CRM_SYNC_GUIDE.md](CRM_SYNC_GUIDE.md)** - **READ FIRST** before any CRM integration work
   - SyncHistory framework (MANDATORY for all CRMs)
   - Universal command flags and patterns
   - Async-compatible sync engine requirements
   - Performance optimization patterns
   - Production-ready architecture standards

2. **[WORKER_POOL_SYSTEM.md](WORKER_POOL_SYSTEM.md)** - **READ FIRST** before task/sync management work
   - Task lifecycle management
   - Celery integration patterns
   - Error handling and recovery
   - Performance monitoring
   - Production deployment considerations

#### Add a New CRM Integration

**⚠️ MANDATORY**: Read `CRM_SYNC_GUIDE.md` completely before starting!

**Start Here**:
1. `docs/AI/reference/CRM_SYNC_GUIDE.md` - **MANDATORY** CRM integration framework
2. `docs/AI/reference/ARCHITECTURE.md` - System architecture overview
3. `ingestion/models/{crm}.py` - Create new model file
4. `ingestion/sync/{crm}/` - Create sync directory structure
5. `ingestion/management/commands/sync_{crm}_{entity}.py` - Create command

**Follow Patterns From**:
- `ingestion/models/hubspot.py` - Model structure
- `ingestion/sync/hubspot/` - Complete integration example
- `ingestion/management/commands/sync_hubspot_contacts.py` - Command example

**Critical Requirements** (from CRM_SYNC_GUIDE.md):
- ✅ MUST use SyncHistory table for tracking
- ✅ MUST support universal command flags (--debug, --full, --dry-run, etc.)
- ✅ MUST follow layered architecture (clients/processors/engines)
- ✅ MUST implement async-compatible methods
- ✅ MUST include comprehensive testing

#### Work with Task/Sync Management

**⚠️ MANDATORY**: Read `WORKER_POOL_SYSTEM.md` before modifying sync/task systems!

**Key Components**:
1. `ingestion/services/worker_pool.py` - Worker pool orchestration
2. `ingestion/tasks_enhanced.py` - Enhanced Celery tasks
3. `ingestion/services/ingestion_adapter.py` - Centralized command routing
4. `ingestion/management/commands/manage_worker_pool.py` - CLI management

**Critical Patterns** (from WORKER_POOL_SYSTEM.md):
- ✅ Dual architecture: Legacy periodic tasks + Worker pool system
- ✅ Individual model command mapping (61 commands vs 9 generic)
- ✅ Proper Celery task registration and discovery
- ✅ Redis-backed state persistence
- ✅ Comprehensive error handling and recovery

#### Fix a Sync Issue

**Files to Check**:
1. `ingestion/sync/{crm}/engines/{entity}.py` - Sync engine logic
2. `ingestion/models/common.py` - SyncHistory model
3. `ingestion/base/sync_engine.py` - BaseSyncEngine base class
4. `logs/ingestion.log` - Application logs
5. Database: Query `orchestration.sync_history` table

**Common Issues**:
- **Records showing 0**: Check `save_data()` or `save_data_bulk()` method
- **Sync not starting**: Check management command and engine initialization
- **Dashboard wrong data**: Check `services/crm_discovery.py` mappings

#### Add a Dashboard Feature

**Files to Modify**:
1. `ingestion/views/crm_dashboard/views.py` - HTML views
2. `ingestion/views/crm_dashboard/api_views.py` - API endpoints
3. `templates/crm_dashboard/` - Template files
4. `ingestion/static/` - CSS/JS files
5. `ingestion/urls.py` - URL routing

**Service Layer**:
- `ingestion/services/crm_discovery.py` - CRM data access
- `ingestion/services/sync_management.py` - Sync operations
- `ingestion/services/data_access.py` - Model queries

#### Write Tests

**Test Files**:
- `ingestion/tests/test_crm_{crm}.py` - CRM-specific tests
- `ingestion/tests/test_interface.py` - Test configurations
- `ingestion/tests/command_test_base.py` - Test utilities

**Test Infrastructure**:
- `ingestion/tests/base/` - Base classes
- `ingestion/tests/utils/test_data_controller.py` - Data mode control
- `ingestion/tests/mock_responses.py` - Mock API data

#### Update Documentation

**Documentation Files**:
- `docs/AI/reference/` - Reference documentation
- `docs/crm_sync_guide.md` - Sync implementation guide
- `ingestion/sync/{crm}/README.md` - CRM-specific docs
- `README.md` - Project overview

---

## Component Location Guide

### Models (Database Tables)

| What | Where |
|------|-------|
| Common models (SyncHistory, SyncSchedule) | `ingestion/models/common.py` |
| HubSpot models | `ingestion/models/hubspot.py` |
| Genius models | `ingestion/models/genius.py` |
| CallRail models | `ingestion/models/callrail.py` |
| SalesRabbit models | `ingestion/models/salesrabbit.py` |
| Arrivy models | `ingestion/models/arrivy.py` |
| Five9 models | `ingestion/models/five9.py` |
| MarketSharp models | `ingestion/models/marketsharp.py` |
| LeadConduit models | `ingestion/models/leadconduit.py` |
| SalesPro models | `ingestion/models/salespro.py` |
| Google Sheets models | `ingestion/models/gsheet.py` |
| Alert models | `ingestion/models/alerts.py` |

### Sync Engines

| CRM | Engine Location |
|-----|-----------------|
| HubSpot | `ingestion/sync/hubspot/engines/` |
| Genius | `ingestion/sync/genius/engines/` |
| CallRail | `ingestion/sync/callrail/engines/` |
| SalesRabbit | `ingestion/sync/salesrabbit/engines/` |
| Arrivy | `ingestion/sync/arrivy/engines/` |
| Five9 | `ingestion/sync/five9/engines/` |
| MarketSharp | `ingestion/sync/marketsharp/engines/` |
| LeadConduit | `ingestion/sync/leadconduit/engines/` |
| SalesPro | `ingestion/sync/salespro/engines/` |
| Google Sheets | `ingestion/sync/gsheet/engines/` |

### Management Commands

**Location**: `ingestion/management/commands/`

**Naming Convention**: `sync_{crm}_{entity}.py`

**Examples**:
- `sync_hubspot_contacts.py`
- `sync_callrail_calls.py`
- `sync_genius_leads.py`
- `sync_salesrabbit_leads.py`

**Orchestration Commands**:
- `sync_hubspot_all.py` - All HubSpot syncs
- `sync_callrail_all.py` - All CallRail syncs
- `sync_arrivy_all.py` - All Arrivy syncs

### Services

| Service | File | Purpose |
|---------|------|---------|
| CRM Discovery | `ingestion/services/crm_discovery.py` | Auto-discover CRMs and models |
| Sync Management | `ingestion/services/sync_management.py` | Execute and monitor syncs |
| Data Access | `ingestion/services/data_access.py` | Query model data |

### Views

| View Type | Location | Purpose |
|-----------|----------|---------|
| Dashboard HTML | `ingestion/views/crm_dashboard/views.py` | Main dashboard pages |
| Dashboard API | `ingestion/views/crm_dashboard/api_views.py` | REST API endpoints |
| Test Interface | `ingestion/tests/views.py` | Test execution UI |

### Templates

| Template | Location |
|----------|----------|
| Dashboard home | `templates/crm_dashboard/dashboard.html` |
| CRM models list | `templates/crm_dashboard/crm_models.html` |
| Model detail | `templates/crm_dashboard/model_detail.html` |
| Sync history | `templates/crm_dashboard/sync_history.html` |
| Test list | `templates/testing/test_list.html` |
| Test detail | `templates/testing/test_detail.html` |

### Base Classes

| Base Class | File | Purpose |
|------------|------|---------|
| BaseSyncEngine | `ingestion/base/sync_engine.py` | Base for all sync engines |
| BaseDataProcessor | `ingestion/base/processor.py` | Base for data processors |
| BaseClient | `ingestion/base/client.py` | Base for API clients |

### Tests

| Test Type | Location |
|-----------|----------|
| HubSpot tests | `ingestion/tests/test_crm_hubspot.py` |
| CallRail tests | `ingestion/tests/test_callrail.py` |
| Arrivy tests | `ingestion/tests/test_crm_arrivy.py` |
| SalesRabbit tests | `ingestion/tests/crm_commands/test_salesrabbit.py` |
| Common tests | `ingestion/tests/test_crm_sync_commands_common.py` |
| Test interface | `ingestion/tests/test_interface.py` |
| Test infrastructure | `ingestion/tests/command_test_base.py` |

---

## URL Patterns

### Dashboard URLs

| URL | View | Purpose |
|-----|------|---------|
| `/dashboard/` | `CRMDashboardView` | Dashboard home |
| `/dashboard/{crm}/models/` | `CRMModelsView` | CRM models list |
| `/dashboard/{crm}/models/{model}/` | `ModelDetailView` | Model data table |
| `/dashboard/sync-history/` | `SyncHistoryView` | All sync history |
| `/dashboard/schedules/` | `AllSchedulesView` | Schedule management |

### API URLs

| URL | View | Purpose |
|-----|------|---------|
| `/api/crms/` | `CRMListAPIView` | List all CRMs |
| `/api/crms/{crm}/models/` | `CRMModelsAPIView` | CRM models |
| `/api/crms/{crm}/models/{model}/data/` | `ModelDataAPIView` | Paginated data |
| `/api/sync/execute/` | `SyncExecuteAPIView` | Trigger sync |
| `/api/sync/status/` | `SyncStatusAPIView` | Check sync status |
| `/api/sync/history/` | `SyncHistoryAPIView` | Sync history |

### Test URLs

| URL | View | Purpose |
|-----|------|---------|
| `/testing/` | `test_list` | Test list |
| `/testing/{test_name}/` | `test_detail` | Test detail |
| `/testing/run/` | `run_test_form` | Execute test |
| `/testing/results/` | `test_results` | Test results |

---

## Configuration Files

### Application Settings

| File | Purpose |
|------|---------|
| `data_warehouse/settings.py` | Django settings |
| `.env` | Environment variables (API keys, DB credentials) |
| `data_warehouse/celery.py` | Celery configuration |
| `docker-compose.yml` | Docker services |
| `Dockerfile` | Docker image build |
| `requirements.txt` | Python dependencies |
| `gunicorn.conf.py` | Gunicorn web server config |

### Environment Variables (.env)

```bash
# Database
DATABASE_URL=postgresql://user:pass@host:5432/dbname

# HubSpot
HUBSPOT_API_KEY=your-api-key

# CallRail
CALLRAIL_API_KEY=your-api-key
CALLRAIL_ACCOUNT_ID=your-account-id

# SalesRabbit
SALESRABBIT_API_TOKEN=your-token

# Arrivy
ARRIVY_API_TOKEN=your-token

# AWS (SalesPro)
AWS_ACCESS_KEY_ID=your-key
AWS_SECRET_ACCESS_KEY=your-secret
AWS_REGION=us-east-1

# Google (Sheets, ADK)
GOOGLE_APPLICATION_CREDENTIALS=/path/to/credentials.json
GOOGLE_CLOUD_PROJECT=your-project-id
GOOGLE_CLOUD_LOCATION=us-west1

# Celery
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

---

## Common File Patterns

### Sync Engine Pattern

**File**: `ingestion/sync/{crm}/engines/{entity}.py`

```python
from ingestion.base.sync_engine import BaseSyncEngine

class {CRM}{Entity}SyncEngine(BaseSyncEngine):
    def __init__(self, **kwargs):
        super().__init__(crm_source='{crm}', sync_type='{entity}', **kwargs)
    
    async def initialize_client(self):
        # Initialize API client
        
    async def fetch_data(self, **kwargs):
        # Fetch data from API
        
    async def transform_data(self, raw_data):
        # Transform data
        
    async def validate_data(self, data):
        # Validate data
        
    async def save_data(self, validated_data):
        # Save to database
        
    async def cleanup(self):
        # Cleanup resources
```

### Management Command Pattern

**File**: `ingestion/management/commands/sync_{crm}_{entity}.py`

```python
from django.core.management.base import BaseCommand
from ingestion.sync.{crm}.engines.{entity} import {CRM}{Entity}SyncEngine
import asyncio

class Command(BaseCommand):
    help = 'Sync {CRM} {entity}'
    
    def add_arguments(self, parser):
        parser.add_argument('--full', action='store_true')
        parser.add_argument('--dry-run', action='store_true')
        parser.add_argument('--debug', action='store_true')
        
    def handle(self, *args, **options):
        engine = {CRM}{Entity}SyncEngine(
            dry_run=options['dry_run'],
            **options
        )
        results = asyncio.run(engine.run_sync(force_full=options['full']))
        self.stdout.write(self.style.SUCCESS(f"Sync complete: {results}"))
```

### Test Pattern

**File**: `ingestion/tests/test_crm_{crm}.py`

```python
from django.test import TestCase
from ingestion.tests.command_test_base import CRMCommandTestBase

class Test{CRM}{Entity}Command(CRMCommandTestBase):
    def setUp(self):
        self.command_name = 'sync_{crm}_{entity}'
    
    def test_unit_flag_validation(self):
        # Test command flags
        
    def test_integration_dry_run(self):
        # Test dry-run execution
```

---

## Search Strategies

### Find by Functionality

**"Where is the code that...?"**

| Functionality | Look In |
|--------------|---------|
| ...syncs HubSpot contacts | `ingestion/sync/hubspot/engines/contacts.py` |
| ...displays the dashboard | `ingestion/views/crm_dashboard/views.py` |
| ...fetches CallRail calls | `ingestion/sync/callrail/clients/calls_client.py` |
| ...saves sync history | `ingestion/base/sync_engine.py` (start_sync, complete_sync) |
| ...discovers CRM models | `ingestion/services/crm_discovery.py` |
| ...executes management commands | `ingestion/management/commands/sync_*.py` |
| ...handles errors | Each engine's `save_data()` method |
| ...controls test data | `ingestion/tests/utils/test_data_controller.py` |

### Find by Model

**"Where is the {Model} used?"**

1. **Model Definition**: `ingestion/models/{crm}.py`
2. **Sync Engine**: `ingestion/sync/{crm}/engines/{entity}.py`
3. **Migrations**: `ingestion/migrations/`
4. **Tests**: `ingestion/tests/test_crm_{crm}.py`

### Find by CRM

**"Where is all the {CRM} code?"**

```
ingestion/
├── models/{crm}.py           # Models
├── sync/{crm}/               # Sync implementation
│   ├── clients/              # API clients
│   ├── processors/           # Data processors
│   ├── engines/              # Sync engines
│   └── README.md             # Documentation
├── management/commands/
│   └── sync_{crm}_*.py       # Management commands
└── tests/
    └── test_crm_{crm}.py     # Tests
```

---

## Getting Started Checklist

### New Developer Onboarding

- [ ] Clone repository
- [ ] Read `README.md`
- [ ] **📖 CRITICAL**: Read `docs/AI/reference/CRM_SYNC_GUIDE.md` - Learn CRM integration patterns
- [ ] **📖 CRITICAL**: Read `docs/AI/reference/WORKER_POOL_SYSTEM.md` - Learn task management
- [ ] Read `docs/AI/reference/ARCHITECTURE.md` - Understand system architecture
- [ ] Set up `.env` file with credentials
- [ ] Run `docker-compose up -d` to start services
- [ ] Run `python manage.py migrate` to set up database
- [ ] Access dashboard at `http://localhost:8000/dashboard/`
- [ ] Run a test sync: `python manage.py sync_hubspot_contacts --dry-run`
- [ ] Explore test interface: `http://localhost:8000/testing/`

### Adding a New Feature

- [ ] **📖 MANDATORY**: Read `docs/AI/reference/CRM_SYNC_GUIDE.md` if CRM-related
- [ ] **📖 MANDATORY**: Read `docs/AI/reference/WORKER_POOL_SYSTEM.md` if task/sync-related
- [ ] Read relevant documentation in `docs/AI/reference/`
- [ ] Identify similar existing feature to use as template
- [ ] Create models if needed (follow SyncHistory patterns)
- [ ] Implement sync engine/service (follow layered architecture)
- [ ] Write tests (follow testing patterns)
- [ ] Update documentation
- [ ] Test manually
- [ ] Create pull request

---

## Related Documents

- [Architecture Overview](ARCHITECTURE.md) - System architecture and design patterns
- [Database Schema Reference](DATABASE_SCHEMA.md) - All models and relationships
- [API & Integration Reference](API_INTEGRATIONS.md) - API endpoints and integrations
- [Existing Tests Documentation](EXISTING_TESTS.md) - Test suite catalog
- [PM Reference Guide](PM_GUIDE.md) - Requirements and user stories
- [CRM Sync Architecture Guide](CRM_SYNC_GUIDE.md) - **CRITICAL**: Enterprise CRM sync patterns, SyncHistory framework, and implementation standards
- [Worker Pool System Documentation](WORKER_POOL_SYSTEM.md) - **CRITICAL**: Task management, Celery integration, and sync orchestration

---

**Document Maintained By**: Development Team  
**Last Review**: 2025  
**Next Review**: Quarterly
