# Monitoring Dashboard Overhaul - ADK Agent Execution Guide

## Overview
This guide explains how to use the Google ADK agent team to overhaul the monitoring dashboard.

## Problem Summary
The current monitoring page (`http://localhost:8000/ingestion/monitoring/`) has critical issues:
- Uses mock data (MockConnectionManager, fake statistics)
- References non-existent `Hubspot_SyncHistory` model
- Shows random non-functional diagrams
- 1035-line template with no real data integration

## Solution Approach
Use the Google ADK multi-agent system to collaboratively design and implement a functional monitoring dashboard.

## Method 1: ADK Web Interface (RECOMMENDED)

### Step 1: Access the ADK Web Interface
```bash
# The ADK service is already running on port 7860
# Open in your browser:
http://localhost:7860
```

### Step 2: Submit the Requirement
Copy and paste the following requirement into the ADK web interface:

```
REQUIREMENT: Monitoring Dashboard Overhaul

Read the complete requirements from: docs/MONITORING_OVERHAUL_REQUIREMENTS.md

CRITICAL: All agents must read their reference documentation:
- Architecture: docs/AI/reference/ARCHITECTURE.md
- Database Schema: docs/AI/reference/DATABASE_SCHEMA.md
- API Integrations: docs/AI/reference/API_INTEGRATIONS.md
- Existing Tests: docs/AI/reference/EXISTING_TESTS.md
- Codebase Map: docs/AI/reference/CODEBASE_MAP.md

=== AGENT RESPONSIBILITIES ===

PM Agent (ProjectManager):
- Read docs/MONITORING_OVERHAUL_REQUIREMENTS.md
- Analyze the 6 acceptance criteria
- Create detailed user stories for each component
- Break down implementation into measurable tasks
- Output pm_spec.yaml with task breakdown

Architect Agent (SoftwareArchitect):
- Read docs/AI/reference/ARCHITECTURE.md to understand existing patterns
- Read docs/AI/reference/DATABASE_SCHEMA.md to understand SyncHistory model
- Design the monitoring system architecture
- Specify exact database queries needed (SELECT from orchestration.sync_history)
- Design API endpoint structure (5 endpoints specified in requirements)
- Plan template simplification (1035 lines → ~300 lines)
- Output dev_plan with file edits and technical decisions

Developer Agent (Developer):
- Implement backend: ingestion/views/monitoring.py
  * Remove all mock data (MockConnectionManager)
  * Remove references to non-existent Hubspot_SyncHistory
  * Use correct model: from ingestion.models.common import SyncHistory
  * Implement 5 API endpoints:
    1. GET /api/overview/ - Overview metrics
    2. GET /api/crm-status/ - Per-CRM sync status
    3. GET /api/recent-syncs/ - Last 50 syncs
    4. GET /api/performance/ - Hourly performance data
    5. GET /api/system-health/ - System checks
  
- Implement frontend: templates/monitoring/dashboard.html
  * Simplify from 1035 lines to ~300 lines
  * Add Chart.js for performance graphs
  * Add auto-refresh every 30 seconds
  * Show real-time metrics from API endpoints

Tester Agent (Tester):
- Create tests in ingestion/tests/test_monitoring.py
- Test API endpoints return correct JSON
- Verify no mock data is used
- Run RunTests() tool

Documenter Agent (Documenter):
- Update docs/AI/changelog/ with implementation details
- Document new API endpoints
- Include test_report results

=== SUCCESS CRITERIA ===

✓ Dashboard shows real data from orchestration.sync_history
✓ No mock data anywhere in the code
✓ All metrics are accurate and meaningful
✓ Auto-refresh works (30 second interval)
✓ Charts display correctly with real data
✓ System health checks functional
✓ All tests pass
```

### Step 3: Monitor Agent Execution
The agents will execute in this order:
1. **PM (ProjectManager)** - Analyzes requirements → Creates pm_spec.yaml
2. **Architect (SoftwareArchitect)** - Reads reference docs → Designs solution → Creates dev_plan
3. **FixUntilGreen Loop** (up to 5 iterations):
   - **Developer** - Implements code using WriteText tool
   - **Tester** - Runs tests using RunTests tool
4. **Documenter** - Updates documentation

### Step 4: Review Generated Files
After completion, check:
- `ingestion/views/monitoring.py` - Backend with real queries
- `templates/monitoring/dashboard.html` - Simplified frontend
- `ingestion/tests/test_monitoring.py` - Test suite
- `docs/AI/changelog/` - Implementation documentation

### Step 5: Test the New Dashboard
```bash
# Access the monitoring dashboard
http://localhost:8000/ingestion/monitoring/

# Verify:
# ✓ Shows real data from SyncHistory table
# ✓ No mock data or errors
# ✓ Metrics update every 30 seconds
# ✓ Charts display correctly
# ✓ CRM status cards show actual sync states
```

## Method 2: Direct Script Execution (Alternative)

If the web interface is not accessible, you can create a direct execution script:

```python
# create_monitoring_task.py
from google.adk.agents import run

# Execute ShipFlow with the requirement
result = run(
    agent=ShipFlow,
    input_text="<requirement text here>",
    output_dir="./adk_output"
)

print(result)
```

Run with:
```bash
docker exec -it data-warehouse-adk-1 python /app/create_monitoring_task.py
```

## Files That Will Be Modified

### Backend Changes
- **ingestion/views/monitoring.py**
  - Remove MockConnectionManager
  - Add real SyncHistory queries
  - Implement 5 API endpoints
  - Add system health checks

### Frontend Changes
- **templates/monitoring/dashboard.html**
  - Simplify from 1035 → ~300 lines
  - Add Chart.js integration
  - Add auto-refresh functionality
  - Remove non-functional diagrams

### New Files
- **ingestion/tests/test_monitoring.py** - Test suite
- **docs/AI/changelog/monitoring_overhaul.md** - Implementation log

## Database Queries (For Reference)

The agents will implement queries like:

```python
from ingestion.models.common import SyncHistory
from django.db.models import Count, Avg, Q
from django.utils import timezone
from datetime import timedelta

# Overview metrics
total_syncs_today = SyncHistory.objects.filter(
    started_at__date=timezone.now().date()
).count()

success_rate = SyncHistory.objects.filter(
    started_at__date=timezone.now().date()
).aggregate(
    success_rate=Avg(
        Case(When(status='completed', then=1), default=0)
    )
)

# Per-CRM status
crm_status = SyncHistory.objects.values('crm_source').annotate(
    total=Count('id'),
    successful=Count('id', filter=Q(status='completed')),
    failed=Count('id', filter=Q(status='failed')),
    last_sync=Max('started_at')
).order_by('crm_source')

# Recent syncs
recent_syncs = SyncHistory.objects.select_related().order_by('-started_at')[:50]
```

## Troubleshooting

### ADK Web Interface Not Accessible
```bash
# Check if ADK container is running
docker ps | grep adk

# Check ADK logs
docker logs data-warehouse-adk-1

# Restart ADK service
docker-compose restart adk
```

### Google Cloud Authentication Issues
```bash
# Verify credentials are mounted
docker exec data-warehouse-adk-1 ls -la /app/credentials.json

# Check environment variables
docker exec data-warehouse-adk-1 env | grep GOOGLE
```

### Agent Execution Fails
1. Check that all reference documentation exists:
   - `docs/AI/reference/ARCHITECTURE.md`
   - `docs/AI/reference/DATABASE_SCHEMA.md`
   - `docs/AI/reference/API_INTEGRATIONS.md`
   - `docs/AI/reference/EXISTING_TESTS.md`
   - `docs/AI/reference/CODEBASE_MAP.md`

2. Verify requirements document exists:
   - `docs/MONITORING_OVERHAUL_REQUIREMENTS.md`

3. Check file permissions in Docker container

## Expected Timeline

- **PM Analysis**: ~2 minutes
- **Architecture Design**: ~5 minutes
- **Development**: ~10-15 minutes
- **Testing Iterations**: ~5-10 minutes
- **Documentation**: ~2 minutes

**Total**: ~25-35 minutes

## Next Steps After Completion

1. **Code Review**: Review the generated code for quality and adherence to patterns
2. **Manual Testing**: Test the dashboard with real data
3. **Integration**: Ensure it works with existing authentication and permissions
4. **Deployment**: Merge changes and deploy to production

## Support

If you encounter issues:
1. Check the ADK logs: `docker logs data-warehouse-adk-1`
2. Review the detailed requirements: `docs/MONITORING_OVERHAUL_REQUIREMENTS.md`
3. Verify Google Cloud credentials are configured
4. Ensure all reference documentation is complete
