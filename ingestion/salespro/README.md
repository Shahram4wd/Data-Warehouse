# SalesPro Integration

This module handles importing data from SalesPro CSV exports into the data warehouse.

## Overview

SalesPro is a sales management system that tracks appointments, customer interactions, and sales results. This integration focuses on importing appointment/sales data from CSV exports.

## Models

### SalesPro_Users
- Existing model for SalesPro user data
- Contains user profile information, office assignments, and permissions

### SalesPro_Appointment
- New model for appointment/sales data from CSV exports
- Tracks individual appointments, customer information, sales rep details, and results
- Includes sale amounts and detailed result strings

### SalesPro_SyncHistory
- Tracks import history and sync status
- Records processed counts, errors, and file paths

## Management Commands

SalesPro data synchronization is now handled through AWS Athena database sync commands:

```bash
# Sync all SalesPro entities from AWS Athena
python manage.py db_salespro_all

# Sync specific entities
python manage.py db_salespro_customers
python manage.py db_salespro_leadresults
python manage.py db_salespro_estimates
python manage.py db_salespro_payments
python manage.py db_salespro_creditapplications
python manage.py db_salespro_useractivities
```

**Features:**
- Incremental sync support
- Bulk operations for performance
- Enterprise monitoring and error handling
- Progress tracking
- Dry run mode for testing
- Automatic sync history tracking

## Configuration

The system uses AWS Athena for data synchronization. Ensure proper AWS credentials and database configuration are set up.

## Usage Examples

### Sync All Entities
```bash
python manage.py db_salespro_all
```

### Incremental Sync
```bash
# The system automatically performs incremental syncs based on last sync timestamp
python manage.py db_salespro_customers
```

### Full Sync
```bash
# Force a full sync ignoring last sync timestamp
python manage.py db_salespro_customers --full
```

### Check Import History
```python
from ingestion.models import SalesPro_SyncHistory

# View recent imports
recent_syncs = SalesPro_SyncHistory.objects.filter(
    sync_type='csv_appointments'
).order_by('-started_at')[:5]

for sync in recent_syncs:
    print(f"{sync.started_at}: {sync.status} - {sync.records_processed} processed")
```

## Data Processing

### Batch Processing
- Uses configurable batch sizes (default 500 records)
- Processes updates and creates separately for optimal performance
- Transaction-based processing for data integrity

### Data Validation
- Parses ISO datetime formats
- Handles boolean values from string representations
- Validates decimal/numeric values
- Graceful handling of missing or invalid data

### Duplicate Handling
- Uses `ignore_conflicts=True` for bulk creates
- Updates existing records based on appointment ID
- Maintains data integrity with unique constraints

## Error Handling

The system includes comprehensive error handling:
- File validation before processing
- Data parsing error recovery
- Transaction rollback on failures
- Detailed error logging and reporting
- Sync history tracking for failed imports

## Performance Considerations

- Bulk operations for large datasets
- Configurable batch sizes via `BATCH_SIZE` environment variable
- Progress bars for long-running imports
- Memory-efficient processing for large CSV files

## Troubleshooting

### Common Issues

1. **File Not Found**
   ```
   File not found: /path/to/file.csv
   ```
   - Verify the file path exists and is accessible
   - Check file permissions

2. **CSV Format Issues**
   ```
   KeyError: '_id'
   ```
   - Verify CSV has correct column headers
   - Check for BOM or encoding issues
   - Ensure CSV is properly formatted

3. **Date Parsing Errors**
   ```
   Could not parse datetime: invalid_date
   ```
   - Check date format in CSV (should be ISO format)
   - Verify timezone information

4. **Memory Issues with Large Files**
   - Reduce `BATCH_SIZE` environment variable
   - Process files in smaller chunks
   - Monitor system memory usage

### Checking Sync Status

```python
# Check latest sync status
latest_sync = SalesPro_SyncHistory.objects.filter(
    sync_type='csv_appointments'
).order_by('-started_at').first()

if latest_sync:
    print(f"Status: {latest_sync.status}")
    print(f"Records: {latest_sync.records_processed}")
    if latest_sync.error_message:
        print(f"Error: {latest_sync.error_message}")
```

## Database Tables

- `salespro_users`: User profile data
- `salespro_appointment`: Appointment/sales data from CSV imports  
- `salespro_sync_history`: Import tracking and history

All tables use appropriate indexes for optimal query performance.
