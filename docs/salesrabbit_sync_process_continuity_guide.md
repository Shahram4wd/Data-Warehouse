# SalesRabbit Sync Process Continuity Guide

## 📋 Overview
This guide provides comprehensive instructions for handling SalesRabbit sync process interruptions, continuing from where you left off, and maintaining system continuity without starting over. This implementation follows the HubSpot sync patterns and includes enhanced error logging for easier debugging.

## 🚨 Critical Issues Addressed

### 1. **Enhanced Error Logging (July 2025)**
- **Problem**: Missing record IDs in error logs made it impossible to find records in SalesRabbit
- **Solution**: Enhanced logging with SalesRabbit URLs and record context
- **Files Modified**: 
  - `ingestion/sync/salesrabbit/processors/base.py`
  - `ingestion/sync/salesrabbit/processors/leads.py`
  - `ingestion/management/commands/base_salesrabbit_sync.py`
  - `ingestion/management/commands/sync_salesrabbit_leads.py`

### 2. **Batch Failure Prevention**
- **Problem**: When one record failed, entire batch (500 records) would fail
- **Solution**: Individual record error handling with detailed field information
- **Impact**: Prevents loss of 499 good records when 1 record has issues

### 3. **Database Field Length Validation**
- **Problem**: "value too long for type character varying" errors without field identification
- **Solution**: Pre-validation and truncation with detailed logging
- **Benefit**: Prevents database constraint violations

### 4. **Global Sync History Integration**
- **Problem**: SalesRabbit was using custom `SalesRabbit_SyncHistory` instead of framework standard
- **Solution**: Migrated to global `SyncHistory` model in `ingestion.models.common`
- **Benefit**: Unified reporting and monitoring across all CRM integrations

## 🔄 Process Recovery Procedures

### When Sync Process Freezes/Crashes

#### 1. **Identify Current State**
```bash
# Check recent logs to see last processed batch
tail -n 100 logs/sync_engines.log | grep "Batch.*completed"

# Find last successful sync timestamp
grep "completed successfully" logs/sync_engines.log | tail -1

# Check for error patterns
grep -E "(ERROR|Failed|value too long)" logs/sync_engines.log | tail -20
```

#### 2. **Determine Resume Point**
```bash
# For leads - find last processed lead ID
grep "leads.*Fetched" logs/sync_engines.log | tail -1

# Check database for latest records
docker-compose exec web python manage.py shell
```

In Django shell:
```python
from ingestion.models.salesrabbit import SalesRabbit_Lead
from ingestion.models.common import SyncHistory

# Find latest synced records
latest_lead = SalesRabbit_Lead.objects.order_by('-date_modified').first()
print(f"Latest lead: {latest_lead.id} - {latest_lead.date_modified}")

# Check sync history
latest_sync = SyncHistory.objects.filter(crm_source='salesrabbit', sync_type='leads').order_by('-end_time').first()
print(f"Last sync: {latest_sync.end_time if latest_sync else 'None'}")
```

#### 3. **Resume Sync from Specific Point**

**Option A: Resume with Date Filter**
```bash
# Resume leads from specific date
docker-compose exec web python manage.py sync_salesrabbit_leads --since=2025-07-16 --force-overwrite --debug

# Resume with enhanced error logging
docker-compose exec web python manage.py sync_salesrabbit_leads --since=2025-07-16 --debug
```

**Option B: Resume with Record Limits**
```bash
# Process smaller batches to avoid timeouts
docker-compose exec web python manage.py sync_salesrabbit_leads --max-records=1000 --batch-size=100 --debug

# Incremental sync (default behavior)
docker-compose exec web python manage.py sync_salesrabbit_leads --debug
```

**Option C: Force Complete Refresh (Last Resort)**
```bash
# Full sync - use only if necessary
docker-compose exec web python manage.py sync_salesrabbit_leads --full --force-overwrite --debug
```

## 📊 Monitoring Progress During Sync

### Real-time Progress Tracking
```bash
# Monitor sync progress in real-time
tail -f logs/sync_engines.log | grep -E "(Batch.*completed|Success Rate|records/s)"

# Track error patterns
tail -f logs/sync_engines.log | grep -E "(ERROR|WARNING|Failed)"

# Monitor specific record processing
tail -f logs/sync_engines.log | grep "Record.*id="
```

### Progress Indicators to Watch
1. **Batch Completion**: `Batch X completed: Y processed`
2. **Success Rate**: `Success Rate: X.XX%`
3. **Processing Rate**: `XX.XX records/s`
4. **Error Patterns**: `value too long`, `Invalid email format`, etc.

## 🔧 Troubleshooting Common Issues

### Issue 1: "Value Too Long" Database Errors
**Symptoms**:
```
ERROR: value too long for type character varying(10)
Batch metrics - Success Rate: 0.00%
```

**Solution**:
1. Check the enhanced logs for field details:
```bash
grep "too long.*Record:" logs/sync_engines.log | tail -10
```

2. The logs now show which fields are problematic with SalesRabbit URLs:
```
WARNING: Field 'state' too long (15 chars), truncating to 10 for record 12345: 'NEWTON FALLS...' - SalesRabbit URL: https://app.salesrabbit.com/leads/12345
```

3. Fix the data in SalesRabbit or update field length in database schema

### Issue 2: Validation Warnings
**Symptoms**:
```
WARNING: Validation warning for field 'email' (Record: id=12345): Invalid email format: 'notanemail@domain'
```

**Solution**:
1. Enhanced logs now include SalesRabbit URLs for direct access
2. Clean data in SalesRabbit using the provided URL
3. Validation warnings don't stop the sync - records are still processed

### Issue 3: Batch Failures
**Symptoms**:
```
Force bulk overwrite failed: value too long for type character varying(50)
Batch metrics - Success Rate: 0.00%
```

**Recovery Steps**:
1. Identify the problematic record using enhanced logging
2. Fix the specific field in SalesRabbit
3. Resume sync from that batch:
```bash
# Use smaller batch size to isolate problem
docker-compose exec web python manage.py sync_salesrabbit_leads --batch-size=50 --max-records=500 --debug
```

## 📈 Performance Optimization

### Optimal Sync Parameters
```bash
# Balanced performance (recommended)
--batch-size=500 --max-records=10000

# Conservative (for problematic data)
--batch-size=100 --max-records=5000

# Aggressive (for clean data)
--batch-size=1000 --max-records=20000
```

### Memory Management
```bash
# Monitor Docker memory usage
docker stats

# Restart containers if memory issues
docker-compose restart web worker
```

## 📝 Error Log Analysis

### New Enhanced Log Format (July 2025)
**Old Format** (Hard to debug):
```
Failed to parse email value: invalid@email
Validation warning for field 'state': value too long
```

**New Format** (Easy to debug):
```
Validation warning for field 'email' with value 'invalid@email' (Record: id=12345): Invalid email format - SalesRabbit URL: https://app.salesrabbit.com/leads/12345
Field 'state' too long (15 chars), truncating to 10 for record 12345: 'NEWTON FALLS...' - SalesRabbit URL: https://app.salesrabbit.com/leads/12345
```

### Log Analysis Commands
```bash
# Find records with specific errors
grep "SalesRabbit URL.*12345" logs/sync_engines.log

# Count error types
grep "Failed to parse" logs/sync_engines.log | wc -l
grep "Invalid email format" logs/sync_engines.log | wc -l
grep "value too long" logs/sync_engines.log | wc -l

# Extract SalesRabbit URLs for batch fixing
grep -o "https://app.salesrabbit.com[^[:space:]]*" logs/sync_engines.log | sort | uniq
```

## 🔄 Sync Strategy Recommendations

### 1. **Incremental Sync (Daily)**
```bash
# Run daily incremental sync
docker-compose exec web python manage.py sync_salesrabbit_leads --debug
```

### 2. **Weekly Full Refresh**
```bash
# Weekly full sync with recent data
docker-compose exec web python manage.py sync_salesrabbit_leads --since=2025-07-01 --force-overwrite --debug
```

### 3. **Monthly Complete Refresh**
```bash
# Monthly full sync (plan for several hours)
docker-compose exec web python manage.py sync_salesrabbit_leads --full --force-overwrite --debug
```

## 🚨 Emergency Recovery Procedures

### Complete Process Freeze
1. **Stop the sync process**: `Ctrl+C`
2. **Check system resources**: `docker stats`, `free -h`
3. **Restart containers**: `docker-compose restart`
4. **Resume from last known good point**:
```bash
# Find last successful timestamp
grep "completed successfully" logs/sync_engines.log | tail -1

# Resume from that point
docker-compose exec web python manage.py sync_salesrabbit_leads --since=YYYY-MM-DD --force-overwrite --debug
```

### Database Connection Issues
```bash
# Restart database
docker-compose restart db

# Check database connectivity
docker-compose exec web python manage.py dbshell

# Verify tables
docker-compose exec web python manage.py shell -c "from ingestion.models.salesrabbit import *; print('DB OK')"
```

### Memory/Performance Issues
```bash
# Monitor resources
docker stats --no-stream

# Reduce batch size
docker-compose exec web python manage.py sync_salesrabbit_leads --batch-size=50 --max-records=1000

# Clean Docker system
docker system prune -f
```

## 📋 Maintenance Checklist

### Daily
- [ ] Check sync completion status
- [ ] Review error logs for patterns
- [ ] Monitor success rates
- [ ] Verify latest record timestamps

### Weekly  
- [ ] Analyze error trends
- [ ] Clean up old log files
- [ ] Run data quality checks
- [ ] Update documentation if needed

### Monthly
- [ ] Full system health check
- [ ] Database optimization
- [ ] Review and clean SalesRabbit data
- [ ] Update sync parameters based on performance

## 📞 Quick Reference Commands

```bash
# Resume leads sync from specific date
docker-compose exec web python manage.py sync_salesrabbit_leads --since=2025-07-16 --force-overwrite --debug

# Resume leads sync with small batches
docker-compose exec web python manage.py sync_salesrabbit_leads --batch-size=100 --max-records=1000 --debug

# Check latest records in database
docker-compose exec web python manage.py shell -c "
from ingestion.models.salesrabbit import SalesRabbit_Lead;
print(f'Latest: {SalesRabbit_Lead.objects.order_by(\"-date_modified\").first().id}')
"

# Monitor real-time progress
tail -f logs/sync_engines.log | grep -E "(Batch.*completed|Success Rate)"

# Find problematic records with SalesRabbit URLs
grep "SalesRabbit URL" logs/sync_engines.log | tail -10

# Check sync history with new global model
docker-compose exec web python manage.py shell -c "
from ingestion.models.common import SyncHistory;
latest = SyncHistory.objects.filter(crm_source='salesrabbit').order_by('-end_time').first();
print(f'Last sync: {latest.end_time if latest else \"None\"} - Status: {latest.status if latest else \"None\"}')
"
```

## 🔧 Configuration Settings

### SalesRabbit API Settings
Ensure these environment variables are set:
```bash
SALESRABBIT_API_KEY=your_api_key_here
SALESRABBIT_API_URL=https://api.salesrabbit.com
```

### Sync Engine Settings
Default settings in `settings.py`:
```python
SALESRABBIT_SYNC_SETTINGS = {
    'default_batch_size': 500,
    'max_retries': 3,
    'retry_delay': 5,  # seconds
    'enable_enhanced_logging': True,
    'strict_validation': False,  # Allow data through with warnings
}
```

---

**Last Updated**: July 20, 2025
**Version**: 1.0 (Initial Implementation)
**Based on**: HubSpot Sync Process Continuity Guide v2.1
**Maintainer**: Development Team
