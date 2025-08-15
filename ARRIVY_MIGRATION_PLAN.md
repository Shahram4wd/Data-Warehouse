# Arrivy CRM Sync Migration Plan

## Overview

This document outlines the complete migration of Arrivy from legacy sync patterns to the enterprise CRM sync architecture as defined in `docs/crm_sync_guide.md`.

## Current State (Legacy Implementation)

### Problems with Current Arrivy Sync:
1. **❌ Custom Sync Tracking**: Uses `Arrivy_SyncHistory` instead of standardized `SyncHistory`
2. **❌ Fragmented Commands**: Multiple individual command files (`sync_arrivy_entities.py`, `sync_arrivy_tasks.py`, etc.)
3. **❌ No Modular Architecture**: Code not following `ingestion/sync/{crm_name}/` structure
4. **❌ Inconsistent Delta Sync**: Custom timestamp tracking instead of `SyncHistory.end_time`
5. **❌ Missing Enterprise Patterns**: No bulk operations, error handling, or monitoring compliance

### Legacy Files to Remove:
```
ingestion/management/commands/
├── sync_arrivy_entities.py
├── sync_arrivy_tasks.py
├── sync_arrivy_groups.py
├── sync_arrivy_location_reports.py
├── sync_arrivy_task_status.py
└── sync_arrivy_all.py

ingestion/models/arrivy.py
└── Arrivy_SyncHistory model (lines 282-297)

ingestion/arrivy/
└── arrivy_client.py (to be refactored and moved)
```

## Target State (Enterprise Architecture)

### New Modular Structure:
```
ingestion/sync/arrivy/
├── __init__.py
├── validators.py                # Arrivy-specific validation rules
├── clients/
│   ├── __init__.py
│   ├── base.py                 # Refactored ArrivyClient
│   ├── entities.py             # Entity-specific API operations
│   ├── tasks.py                # Task-specific API operations
│   └── groups.py               # Group-specific API operations
├── engines/
│   ├── __init__.py
│   ├── base.py                 # ArrivyBaseSyncEngine
│   ├── entities.py             # Entity sync orchestration
│   ├── tasks.py                # Task sync orchestration
│   └── groups.py               # Group sync orchestration
└── processors/
    ├── __init__.py
    ├── base.py                 # Base data transformation
    ├── entities.py             # Entity data processing
    ├── tasks.py                # Task data processing
    └── groups.py               # Group data processing
```

### New Unified Command:
```
ingestion/management/commands/
└── sync_arrivy.py              # Single unified command
```

## Migration Tasks

### 1. Data Migration (CRITICAL)
```python
# Create Django migration to move Arrivy_SyncHistory -> SyncHistory
# Data mapping:
Arrivy_SyncHistory.sync_type -> SyncHistory.sync_type
Arrivy_SyncHistory.last_synced_at -> SyncHistory.end_time
# New fields:
SyncHistory.crm_source = 'arrivy'
SyncHistory.status = 'success'  # Default for historical records
SyncHistory.start_time = SyncHistory.end_time  # Estimate
```

### 2. Architecture Implementation

#### A. Create Base Sync Engine
```python
# ingestion/sync/arrivy/engines/base.py
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory

class ArrivyBaseSyncEngine(BaseSyncEngine):
    def __init__(self, entity_type: str, **kwargs):
        super().__init__('arrivy', entity_type, **kwargs)
        # Initialize Arrivy-specific settings
```

#### B. Create Entity-Specific Engines
```python
# ingestion/sync/arrivy/engines/entities.py
from .base import ArrivyBaseSyncEngine
from ..clients.entities import ArrivyEntitiesClient
from ..processors.entities import ArrivyEntitiesProcessor

class ArrivyEntitiesSyncEngine(ArrivyBaseSyncEngine):
    def __init__(self, **kwargs):
        super().__init__('entities', **kwargs)
        self.client = ArrivyEntitiesClient()
        self.processor = ArrivyEntitiesProcessor()
```

#### C. Create Unified Command
```python
# ingestion/management/commands/sync_arrivy.py
from ingestion.base.commands import BaseSyncCommand
from ingestion.sync.arrivy.engines import (
    ArrivyEntitiesSyncEngine,
    ArrivyTasksSyncEngine, 
    ArrivyGroupsSyncEngine
)

class Command(BaseSyncCommand):
    def add_arguments(self, parser):
        super().add_arguments(parser)
        parser.add_argument(
            '--entity-type',
            choices=['entities', 'tasks', 'groups', 'all'],
            default='all',
            help='Type of Arrivy entities to sync'
        )
```

### 3. SyncHistory Compliance

#### Required Field Standards:
- `crm_source`: `'arrivy'` (lowercase, no underscores)
- `sync_type`: `'entities'`, `'tasks'`, `'groups'` (no '_sync' suffix)
- `status`: `'running'`, `'success'`, `'failed'`, `'partial'` (exact values)

#### Delta Sync Implementation:
```python
async def get_last_sync_timestamp(self) -> Optional[datetime]:
    """Get last successful sync from SyncHistory table"""
    last_sync = await sync_to_async(SyncHistory.objects.filter)(
        crm_source='arrivy',
        sync_type=self.entity_type,
        status='success'
    ).order_by('-end_time').first()
    
    return last_sync.end_time if last_sync else None
```

### 4. Command-Line Interface

#### Standard Flags Implementation:
```bash
# New unified command usage:
python manage.py sync_arrivy --entity-type=entities
python manage.py sync_arrivy --entity-type=all --full
python manage.py sync_arrivy --entity-type=tasks --since=2025-01-01
python manage.py sync_arrivy --entity-type=groups --dry-run --batch-size=50
```

## Validation Checklist

### ✅ SyncHistory Compliance:
- [ ] Uses standardized `SyncHistory` model only
- [ ] No custom sync tracking (`Arrivy_SyncHistory` removed)
- [ ] Proper field formats (`crm_source='arrivy'`, `sync_type='entities'`)
- [ ] Delta sync uses `SyncHistory.end_time`
- [ ] Status updates on sync completion

### ✅ Architecture Compliance:
- [ ] Follows `ingestion/sync/arrivy/` structure
- [ ] Separation of clients, engines, processors
- [ ] Async orchestration with proper error handling
- [ ] Bulk operations with conflict resolution
- [ ] Enterprise monitoring and performance metrics

### ✅ Command Interface:
- [ ] Single unified command (`sync_arrivy.py`)
- [ ] Standard flags (`--full`, `--force-overwrite`, `--since`, `--dry-run`)
- [ ] Entity type parameter (`--entity-type`)
- [ ] Proper help documentation

### ✅ Legacy Cleanup:
- [ ] All `sync_arrivy_*.py` commands removed
- [ ] `Arrivy_SyncHistory` model deleted
- [ ] Data successfully migrated to `SyncHistory`
- [ ] Import references updated
- [ ] No broken dependencies

## Deployment Strategy

### 1. Pre-Migration (Staging)
1. Create data backup of `ingestion_arrivy_sync_history` table
2. Test data migration scripts
3. Validate new sync engines with sample data
4. Verify SyncHistory integration works correctly

### 2. Migration (Production)
1. Run data migration during maintenance window
2. Deploy new sync architecture
3. Test unified command with `--dry-run`
4. Monitor first real sync operations
5. Verify delta sync uses correct timestamps

### 3. Post-Migration
1. Monitor sync performance and error rates
2. Validate SyncHistory data quality
3. Remove old migration files after successful deployment
4. Update documentation and runbooks

## Rollback Plan

### If Migration Fails:
1. **Restore Code**: Revert to previous deployment
2. **Restore Data**: Use backup to recreate `Arrivy_SyncHistory` table
3. **Restore Commands**: Re-enable individual sync command files
4. **Validate State**: Ensure sync operations continue normally

### Emergency Procedures:
- Keep backup of all removed files until migration is proven stable
- Maintain data migration scripts for quick rollback
- Document exact revert steps for production team

---

This migration plan ensures a safe, comprehensive transition from legacy Arrivy sync patterns to enterprise CRM sync architecture while maintaining data integrity and operational continuity.
