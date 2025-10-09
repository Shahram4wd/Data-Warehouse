# Monitoring Dashboard Overhaul - Requirements

**Date**: October 9, 2025  
**Priority**: High  
**Requestor**: System Administrator  
**Status**: Planning

---

## Problem Statement

The current monitoring page at `http://localhost:8000/ingestion/monitoring/` displays random, non-functional diagrams and does not provide useful operational insights. The page uses mock data and doesn't integrate with the actual Data Warehouse system.

### Current Issues
1. Uses mock/fake data instead of real system metrics
2. References non-existent models (`Hubspot_SyncHistory` instead of `SyncHistory`)
3. Displays random diagrams with no meaningful information
4. No integration with actual CRM sync operations
5. Missing critical operational metrics
6. Template is overly complex (1000+ lines) with unused features

---

## User Story

**As a** Data Warehouse Administrator,  
**I want** a functional monitoring dashboard that shows real-time system health and sync status,  
**So that** I can quickly identify issues, track performance, and ensure all CRM integrations are operating correctly.

---

## Acceptance Criteria

### AC1: Real Data Integration
Given the monitoring dashboard is accessed,  
When the page loads,  
Then it displays real data from the `orchestration.sync_history` table and actual system metrics.

### AC2: CRM Sync Status
Given CRM syncs are running,  
When I view the dashboard,  
Then I see the current status of all CRM sync operations with accurate record counts.

### AC3: Performance Metrics
Given sync operations have completed,  
When I view the performance section,  
Then I see actual sync duration, records per second, and success rates.

### AC4: Error Tracking
Given sync failures have occurred,  
When I view the error section,  
Then I see real error messages, affected CRMs, and failure timestamps from SyncHistory.

### AC5: System Health
Given the system is operational,  
When I view the health section,  
Then I see database connection status, Celery worker status, and Redis availability.

### AC6: Real-Time Updates
Given the dashboard is open,  
When new sync operations complete,  
Then the dashboard updates automatically (every 30 seconds) without manual refresh.

---

## Key Metrics to Display

### 1. Overview Cards (Top of Page)
- **Active Syncs**: Count of running syncs (status='running')
- **Completed Today**: Successful syncs in last 24 hours
- **Failed Syncs**: Failed syncs in last 24 hours
- **Success Rate**: (Successful / Total) × 100% for last 24 hours

### 2. CRM Sync Status Table
For each CRM (HubSpot, Genius, CallRail, SalesRabbit, etc.):
- CRM Name
- Last Sync Time (from SyncHistory.end_time)
- Status (Success/Failed/Running)
- Records Processed (from SyncHistory.records_processed)
- Records Created/Updated
- Duration (end_time - start_time)
- Next Scheduled Sync (from SyncSchedule if available)

### 3. Recent Sync Activity (Timeline)
Last 20 sync operations:
- Timestamp
- CRM Source
- Sync Type (entity)
- Status
- Record counts
- Duration
- Error message (if failed)

### 4. Performance Charts
- **Sync Duration Over Time**: Line chart showing sync duration trends
- **Records Processed**: Bar chart by CRM
- **Success Rate Trend**: Line chart over last 7 days
- **Sync Frequency**: Bar chart showing sync counts per CRM

### 5. Error Analysis
- **Recent Errors**: Last 10 failed syncs with error messages
- **Error Distribution**: Pie chart of error types
- **Most Problematic CRMs**: CRMs with highest failure rate

### 6. System Health Indicators
- **Database**: PostgreSQL connection status (green/red)
- **Celery Workers**: Worker count and status
- **Redis**: Message broker availability
- **API Endpoints**: HubSpot, CallRail, etc. (optional - can ping)

---

## Technical Requirements

### Backend Changes

#### 1. Update `ingestion/views/monitoring.py`
- Remove all mock data
- Query `orchestration.sync_history` table (SyncHistory model from `ingestion.models.common`)
- Query `orchestration.sync_schedule` table (SyncSchedule model)
- Calculate real metrics from database
- Add system health checks (DB, Celery, Redis)

#### 2. API Endpoints Needed

**GET `/ingestion/monitoring/api/stats/`**
```json
{
  "overview": {
    "active_syncs": 2,
    "completed_today": 45,
    "failed_today": 3,
    "success_rate": 93.75
  },
  "timestamp": "2025-10-09T10:30:00Z"
}
```

**GET `/ingestion/monitoring/api/crm-status/`**
```json
{
  "crms": [
    {
      "name": "HubSpot",
      "last_sync": "2025-10-09T10:15:00Z",
      "status": "success",
      "records_processed": 1523,
      "records_created": 15,
      "records_updated": 1508,
      "duration_seconds": 125,
      "next_sync": "2025-10-09T11:00:00Z"
    },
    ...
  ]
}
```

**GET `/ingestion/monitoring/api/recent-syncs/`**
```json
{
  "syncs": [
    {
      "id": 12345,
      "crm_source": "hubspot",
      "sync_type": "contacts",
      "status": "success",
      "start_time": "2025-10-09T10:10:00Z",
      "end_time": "2025-10-09T10:12:15Z",
      "duration_seconds": 135,
      "records_processed": 1523,
      "records_created": 15,
      "records_updated": 1508,
      "records_failed": 0
    },
    ...
  ],
  "total": 20
}
```

**GET `/ingestion/monitoring/api/system-health/`**
```json
{
  "database": {
    "status": "healthy",
    "connection_count": 5,
    "response_time_ms": 12
  },
  "celery": {
    "status": "healthy",
    "active_workers": 2,
    "pending_tasks": 5
  },
  "redis": {
    "status": "healthy",
    "memory_used_mb": 45,
    "connected_clients": 8
  }
}
```

**GET `/ingestion/monitoring/api/performance-charts/`**
```json
{
  "sync_duration_trend": {
    "labels": ["Oct 2", "Oct 3", ..., "Oct 9"],
    "data": [120, 135, 128, ...]
  },
  "records_by_crm": {
    "labels": ["HubSpot", "CallRail", "Genius", ...],
    "data": [15234, 8923, 12456, ...]
  },
  "success_rate_trend": {
    "labels": ["Oct 2", "Oct 3", ..., "Oct 9"],
    "data": [95.2, 94.8, 96.1, ...]
  }
}
```

### Frontend Changes

#### 1. Simplify `templates/monitoring/dashboard.html`
- Remove unused sections (automation, security, approvals)
- Focus on core monitoring: syncs, performance, errors, health
- Use Bootstrap 5 for clean, responsive design
- Implement Chart.js for visualizations
- Add auto-refresh every 30 seconds

#### 2. Dashboard Layout
```
+----------------------------------------------------------+
| MONITORING DASHBOARD                    [Auto-refresh: 30s] |
+----------------------------------------------------------+
|  [Active: 2]  [Completed: 45]  [Failed: 3]  [Rate: 93.75%] |
+----------------------------------------------------------+
|                    CRM SYNC STATUS                         |
| +--------------------------------------------------------+ |
| | CRM      | Last Sync | Status  | Records | Duration   | |
| | HubSpot  | 2 min ago | Success | 1,523   | 2m 15s    | |
| | CallRail | 5 min ago | Success | 892     | 1m 30s    | |
| | ...                                                      | |
| +--------------------------------------------------------+ |
+----------------------------------------------------------+
|        RECENT SYNC ACTIVITY     |    PERFORMANCE CHARTS  |
| +-----------------------------+ | +--------------------+ |
| | [Timeline of last 20 syncs] | | | [Charts]           | |
| +-----------------------------+ | +--------------------+ |
+----------------------------------------------------------+
|           ERRORS & SYSTEM HEALTH                          |
| [Recent errors]         [System health indicators]        |
+----------------------------------------------------------+
```

---

## Implementation Plan

### Phase 1: Backend Updates (Priority 1)
1. Update `DashboardStatsView` to query real SyncHistory data
2. Create `CRMStatusView` for per-CRM status
3. Create `RecentSyncsView` for sync timeline
4. Create `SystemHealthView` for health checks
5. Create `PerformanceChartsView` for chart data
6. Remove all mock data and unused code

### Phase 2: Frontend Updates (Priority 1)
1. Simplify dashboard.html template (reduce to ~300 lines)
2. Implement overview cards with real data
3. Implement CRM status table
4. Implement recent syncs timeline
5. Implement performance charts (Chart.js)
6. Implement error tracking section
7. Implement system health indicators
8. Add auto-refresh with JavaScript

### Phase 3: Testing (Priority 1)
1. Manual testing with browser
2. Verify all metrics display correctly
3. Test auto-refresh functionality
4. Test with different sync states (running, success, failed)
5. Test performance with large datasets

### Phase 4: Documentation (Priority 2)
1. Update monitoring documentation
2. Add screenshots of new dashboard
3. Document API endpoints
4. Update README

---

## Database Queries Needed

### Get Overview Statistics
```python
from ingestion.models.common import SyncHistory
from django.utils import timezone
from datetime import timedelta

now = timezone.now()
yesterday = now - timedelta(days=1)

active_syncs = SyncHistory.objects.filter(status='running').count()
completed_today = SyncHistory.objects.filter(
    status='success',
    end_time__gte=yesterday
).count()
failed_today = SyncHistory.objects.filter(
    status='failed',
    end_time__gte=yesterday
).count()
total_today = completed_today + failed_today
success_rate = (completed_today / total_today * 100) if total_today > 0 else 0
```

### Get Last Sync Per CRM
```python
from django.db.models import Max

crm_sources = ['hubspot', 'callrail', 'genius', 'salesrabbit', 'arrivy', 
               'five9', 'marketsharp', 'leadconduit', 'salespro', 'gsheet']

for crm in crm_sources:
    last_sync = SyncHistory.objects.filter(
        crm_source=crm
    ).order_by('-end_time').first()
```

### Get Recent Syncs
```python
recent_syncs = SyncHistory.objects.order_by('-start_time')[:20]
```

---

## Design Mockup (Text)

```
╔══════════════════════════════════════════════════════════════╗
║            DATA WAREHOUSE MONITORING DASHBOARD               ║
║                                                              ║
║  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   ║
║  │ ACTIVE   │  │COMPLETED │  │ FAILED   │  │ SUCCESS  │   ║
║  │    2     │  │   45     │  │    3     │  │  93.75%  │   ║
║  └──────────┘  └──────────┘  └──────────┘  └──────────┘   ║
║                                                              ║
║  CRM SYNC STATUS                                            ║
║  ┌────────────────────────────────────────────────────────┐ ║
║  │ CRM        Last Sync   Status    Records    Duration   │ ║
║  │ HubSpot    2 min ago   ✓ Success  1,523     2m 15s    │ ║
║  │ CallRail   5 min ago   ✓ Success    892     1m 30s    │ ║
║  │ Genius    10 min ago   ✓ Success  2,341     3m 45s    │ ║
║  │ SalesRabbit Running... ⟳ Running    523     ...        │ ║
║  └────────────────────────────────────────────────────────┘ ║
║                                                              ║
║  RECENT ACTIVITY          │  PERFORMANCE                    ║
║  [Timeline view]          │  [Charts: Duration, Records]    ║
║                                                              ║
║  ERRORS & HEALTH                                            ║
║  Recent Errors: [List]    System: ✓ DB  ✓ Celery  ✓ Redis ║
╚══════════════════════════════════════════════════════════════╝
```

---

## Files to Modify

1. **`ingestion/views/monitoring.py`** - Complete rewrite with real data
2. **`templates/monitoring/dashboard.html`** - Simplify and update
3. **`ingestion/urls.py`** - Update monitoring URL patterns if needed
4. **`docs/AI/reference/`** - Update documentation (optional)

---

## Success Metrics

- ✅ Dashboard loads without errors
- ✅ All metrics display real data from database
- ✅ Auto-refresh works correctly
- ✅ Charts render properly with Chart.js
- ✅ System health checks return accurate status
- ✅ No more mock data anywhere
- ✅ Performance is acceptable (page loads < 2 seconds)
- ✅ Mobile responsive design

---

## Non-Goals (Out of Scope)

- ❌ Historical data archival beyond what's in SyncHistory
- ❌ Custom alerting system (use existing logging)
- ❌ User authentication/authorization changes
- ❌ Advanced analytics or ML-based predictions
- ❌ Integration with external monitoring tools
- ❌ Real-time WebSocket updates (polling is sufficient)

---

## Related Documents

- [Architecture Overview](../docs/AI/reference/ARCHITECTURE.md)
- [Database Schema](../docs/AI/reference/DATABASE_SCHEMA.md)
- [Existing Tests](../docs/AI/reference/EXISTING_TESTS.md)

---

**This requirement should be implemented by the Google ADK agent team working collaboratively.**
