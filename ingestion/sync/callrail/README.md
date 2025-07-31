# CallRail CRM Integration

This module provides comprehensive integration with CallRail API v3 for synchronizing call tracking data into the Data Warehouse.

## Architecture

The CallRail integration follows the standard CRM sync guide architecture with four main layers:

### 1. Models (`ingestion/models/callrail.py`)
Django models for storing CallRail data:
- `CallRail_Account` - CallRail account information
- `CallRail_Company` - Company/business units within accounts
- `CallRail_Call` - Individual call records (primary entity)
- `CallRail_Tracker` - Phone number trackers
- `CallRail_FormSubmission` - Web form submissions
- `CallRail_TextMessage` - SMS/text message records
- `CallRail_Tag` - Tags for categorizing calls
- `CallRail_User` - User accounts within CallRail

### 2. Clients (`ingestion/sync/callrail/clients/`)
API clients for fetching data from CallRail:
- `CallRailBaseClient` - Base client with authentication and pagination
- `CallsClient` - Fetch call records
- `CompaniesClient` - Fetch company information
- `TrackersClient` - Fetch tracker configurations

### 3. Sync Engines (`ingestion/sync/CallRail/engines/`)
Orchestration layer for data synchronization:
- `CallRailBaseSyncEngine` - Base engine with common sync logic
- `CallsSyncEngine` - Sync call records with delta support
- `CompaniesSyncEngine` - Sync company information
- `TrackersSyncEngine` - Sync tracker configurations

### 4. Processors (`ingestion/sync/callrail/processors/`)
Data transformation and validation:
- `CallRailBaseProcessor` - Base processor with common transformations
- `CallsProcessor` - Transform and validate call data
- `CompaniesProcessor` - Transform and validate company data
- `TrackersProcessor` - Transform and validate tracker data

### 5. Validators (`ingestion/sync/CallRail/validators.py`)
Business rule validation and data quality checks.

## Configuration

### Environment Variables
Add to your `.env` file:
```bash
CALLRAIL_API_KEY=your_callrail_api_key_here
```

### Django Settings
The integration will automatically use the `CALLRAIL_API_KEY` from Django settings.

## Usage

### Management Commands

#### Sync All Data
```bash
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID
```

#### Sync Specific Entities
```bash
# Sync only calls
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID --entities calls

# Sync companies and trackers
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID --entities companies trackers
```

#### Full Sync vs Delta Sync
```bash
# Delta sync (default) - only new/updated records
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID

# Full sync - all records
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID --full-sync
```

#### Individual Entity Commands
```bash
# Sync calls with date range
python manage.py CallRail_calls_sync --account-id YOUR_ACCOUNT_ID \
    --start-date 2024-01-01 --end-date 2024-01-31

# Sync companies
python manage.py CallRail_companies_sync --account-id YOUR_ACCOUNT_ID

# Sync trackers for specific company
python manage.py CallRail_trackers_sync --account-id YOUR_ACCOUNT_ID \
    --company-id COMPANY_ID
```

### Advanced Options
```bash
# Dry run mode
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID --dry-run

# Parallel sync (experimental)
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID --parallel

# Filter by company
python manage.py CallRail_sync --account-id YOUR_ACCOUNT_ID \
    --company-id COMPANY_ID
```

## Features

### Delta Synchronization
- Automatically detects new/updated records using timestamp comparison
- Reduces API calls and processing time
- Fallback to full sync when no previous sync data exists

### Rate Limiting
- Respects CallRail's 200 requests/minute limit
- Automatic backoff and retry on rate limit errors
- Configurable request delays

### Bulk Operations
- Uses Django's `bulk_create` and `bulk_update` for performance
- Fallback to individual saves when bulk operations fail
- Comprehensive error handling and logging

### Data Validation
- Phone number format validation
- Email format validation
- Business rule validation (call duration, status, etc.)
- Data quality warnings and alerts

### Error Handling
- Comprehensive logging at all levels
- Graceful handling of API errors
- Detailed error reporting in sync results
- Continuation on individual record failures

## API Rate Limits

CallRail API v3 limits:
- **Rate Limit**: 200 requests per minute
- **Pagination**: Maximum 100 records per page
- **Authentication**: Token-based authentication

The integration automatically handles these limits with:
- Request rate limiting
- Exponential backoff on errors
- Optimal pagination sizes

## Data Relationships

```
Account (1) → (*) Company → (*) Tracker
                       ↘    ↗
                         Call
                       ↗    ↘
                  User       Tag
```

## Monitoring and Logging

All sync operations are logged with:
- Sync statistics (created, updated, errors)
- Performance metrics (duration, throughput)
- Error details and warnings
- Data quality alerts

Logs are written to:
- `logs/ingestion.log` - General sync logs
- Django console output - Real-time progress

## Error Recovery

The integration includes several error recovery mechanisms:
- Individual record error isolation
- Bulk operation fallbacks
- API retry logic
- Partial sync continuation

## Performance Considerations

### Batch Sizes
- Calls: 100 records per API request
- Companies: 100 records per API request  
- Trackers: 100 records per API request

### Optimization Tips
1. Use delta sync for regular updates
2. Filter by company for large accounts
3. Use date ranges for call syncs
4. Monitor rate limits during large syncs

## Development

### Adding New Entities
1. Create model in `CallRail.py`
2. Add client in `clients/`
3. Add sync engine in `engines/`
4. Add processor in `processors/`
5. Update validators
6. Create management command

### Testing
```bash
# Test with dry run
python manage.py CallRail_sync --account-id TEST_ACCOUNT --dry-run

# Test individual entities
python manage.py CallRail_calls_sync --account-id TEST_ACCOUNT --full-sync
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify `CALLRAIL_API_KEY` is set correctly
   - Check API key has proper permissions

2. **Rate Limit Errors**
   - Reduce batch sizes
   - Increase delays between requests
   - Use delta sync instead of full sync

3. **Data Validation Errors**
   - Check log files for specific validation failures
   - Verify data formats match expectations

4. **Import Errors**
   - Django development environment may show import warnings
   - These are typically resolved when running in proper Django context

### Support
For integration issues, check:
1. Django logs in `logs/ingestion.log`
2. Sync command output for detailed statistics
3. CallRail API documentation for API changes
