# Delta Sync Implementation for db_genius_* Commands

## Summary
Successfully implemented delta sync functionality for `db_genius_appointments.py` following the CRM sync guide patterns. This serves as the template for updating all other `db_genius_*` commands.

## Completed Implementation (db_genius_appointments.py)

### ✅ New Command Arguments Added:
1. `--full` - Perform full sync (ignore last sync timestamp)
2. `--force-overwrite` - Completely replace existing records  
3. `--since YYYY-MM-DD` - Manual sync start date (manual override)
4. `--dry-run` - Test run without database writes
5. `--max-records N` - Limit total records (0 = unlimited)
6. `--debug` - Enable verbose logging
7. `--start-date` - (DEPRECATED) Use --since instead
8. `--end-date` - End date for sync

### ✅ SyncHistory Integration:
- Added `SyncHistory` model import for centralized sync tracking
- Implemented `_create_sync_record()` for sync state management
- Added `_complete_sync_record()` for success/failure tracking
- Using 'genius' as crm_source and entity name as sync_type

### ✅ Delta Sync Logic:
Priority order implemented following CRM sync guide:
1. `--since` parameter (manual override)
2. `--force-overwrite` flag (None = fetch all)
3. `--full` flag (None = fetch all)  
4. `SyncHistory` table last successful sync timestamp
5. Default: None (full sync)

### ✅ Helper Methods Added:
- `_parse_since_parameter()` - Parse command line date arguments
- `_parse_date_parameter()` - Convert YYYY-MM-DD to datetime object
- `_get_last_sync_timestamp()` - Query SyncHistory for last successful sync
- `_determine_sync_strategy()` - Implement sync priority logic
- `_build_where_clause()` - Generate SQL WHERE clause for timestamp filtering
- `_create_sync_record()` - Initialize SyncHistory tracking record
- `_complete_sync_record()` - Finalize sync with status and metrics

### ✅ Database Query Updates:
- Modified SQL queries to include timestamp-based WHERE clauses
- Added support for `updated_at` field filtering (appointments can be modified)
- Integrated max_records limit within processing loop

## Remaining Commands to Update

### Pattern to Apply to Each Command:

1. **Import Updates:**
```python
from ingestion.models.common import SyncHistory
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional
```

2. **Arguments Template:**
```python
def add_arguments(self, parser):
    # Standard CRM sync flags
    parser.add_argument('--full', action='store_true', help='Perform full sync (ignore last sync timestamp)')
    parser.add_argument('--force-overwrite', action='store_true', help='Completely replace existing records')
    parser.add_argument('--since', type=str, help='Manual sync start date (YYYY-MM-DD format)')
    parser.add_argument('--dry-run', action='store_true', help='Test run without database writes')
    parser.add_argument('--max-records', type=int, default=0, help='Limit total records (0 = unlimited)')
    parser.add_argument('--debug', action='store_true', help='Enable verbose logging')
    
    # Backward compatibility
    parser.add_argument('--start-date', type=str, help='(DEPRECATED) Use --since instead')
    parser.add_argument('--end-date', type=str, help='End date for sync')
    
    # Keep existing command-specific arguments...
```

3. **Sync Strategy Logic:**
- Copy all helper methods from `db_genius_appointments.py`
- Update `sync_type` parameter in helper methods to match entity name
- Update timestamp field in `_build_where_clause()` method:
  - Use `updated_at` for updatable entities (contacts, divisions, users, prospects)
  - Use `created_at` for activity/log entities (leads, appointments might use add_date)

4. **Handle Method Updates:**
- Add sync record creation at start
- Add sync strategy determination
- Modify queries to include WHERE clause
- Add sync record completion on success/failure
- Add max_records limiting

## Entity-Specific Timestamp Field Mapping:

| Command | Entity | Timestamp Field | Rationale |
|---------|--------|----------------|-----------|
| appointments | appointment | updated_at | Appointments can be modified |
| divisions | division | updated_at | Divisions can be updated |
| users | user | updated_at | User information changes |
| prospects | prospect | updated_at | Prospect data gets updated |
| leads | lead | added_on | Leads are typically immutable once created |
| quotes | quote | updated_at | Quotes can be modified |
| services | service | updated_at | Service definitions can change |

## Command Files Needing Updates:

1. ✅ `db_genius_appointments.py` - **COMPLETED**
2. ⏳ `db_genius_divisions.py` - **IN PROGRESS**  
3. ⭕ `db_genius_users.py`
4. ⭕ `db_genius_prospects.py` 
5. ⭕ `db_genius_leads.py`
6. ⭕ `db_genius_quotes.py`
7. ⭕ `db_genius_services.py`
8. ⭕ `db_genius_prospect_sources.py`
9. ⭕ `db_genius_appointment_types.py`
10. ⭕ `db_genius_appointment_outcomes.py`
11. ⭕ `db_genius_appointment_services.py`
12. ⭕ `db_genius_appointment_outcome_types.py`
13. ⭕ `db_genius_division_groups.py`
14. ⭕ `db_genius_marketing_sources.py`
15. ⭕ `db_genius_marketing_source_types.py`
16. ⭕ `db_genius_marketsharp_sources.py`
17. ⭕ `db_genius_marketsharp_marketing_source_maps.py`
18. ⭕ `db_genius_user_titles.py`

## Testing the Implementation:

```bash
# Test delta sync with manual date
docker-compose exec web python manage.py db_genius_appointments --since=2025-01-01 --dry-run

# Test full sync
docker-compose exec web python manage.py db_genius_appointments --full --dry-run

# Test with max records limit  
docker-compose exec web python manage.py db_genius_appointments --max-records=100 --dry-run

# Test incremental sync (uses SyncHistory)
docker-compose exec web python manage.py db_genius_appointments --dry-run
```

## Key Implementation Notes:

1. **SyncHistory Integration:** Every command must use the standardized SyncHistory table with:
   - `crm_source='genius'`
   - `sync_type=entity_name` (e.g., 'appointments', 'divisions', 'users')
   - Proper status tracking ('running', 'success', 'failed')

2. **Backward Compatibility:** Keep existing arguments but add deprecation warnings for `--start-date`

3. **Error Handling:** Ensure SyncHistory record is updated on both success and failure

4. **Performance Metrics:** Track duration, records per second, and failure counts in SyncHistory

5. **SQL Query Modification:** Add WHERE clauses for timestamp filtering while maintaining existing LIMIT/OFFSET logic

This pattern ensures all `db_genius_*` commands follow the same delta sync architecture as other CRM integrations in the system.
