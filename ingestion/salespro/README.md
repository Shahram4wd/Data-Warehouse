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

### csv_salespro_appointments
Import appointment/sales data from a SalesPro CSV export file.

```bash
# Import appointments from CSV
python manage.py csv_salespro_appointments /path/to/SalesPro2025-06-18.csv

# Dry run to see what would be imported
python manage.py csv_salespro_appointments /path/to/SalesPro2025-06-18.csv --dry-run
```

**Features:**
- Bulk create/update operations for performance
- Duplicate detection and handling
- Progress tracking with tqdm
- Comprehensive error handling
- Dry run mode for testing
- Automatic sync history tracking

## CSV Data Format

The expected CSV format includes these columns:
- `_id`: Unique appointment identifier
- `_created_at`: Creation timestamp (ISO format)
- `_updated_at`: Last update timestamp (ISO format)
- `isSale`: Boolean indicating if appointment resulted in sale
- `resultFullString`: Detailed appointment result information
- `customer.nameLast`: Customer last name
- `customer.nameFirst`: Customer first name
- `customer.estimateName`: Customer estimate name/identifier
- `salesrep.email`: Sales representative email
- `salesrep.nameFirst`: Sales rep first name
- `salesrep.nameLast`: Sales rep last name
- `saleAmount`: Sale amount (if applicable)

## Configuration

No special environment variables needed for CSV imports. The system uses standard Django database settings.

## Usage Examples

### Basic Import
```bash
python manage.py csv_salespro_appointments /path/to/export.csv
```

### Dry Run First
```bash
# Test the import first
python manage.py csv_salespro_appointments /path/to/export.csv --dry-run

# If successful, run the actual import
python manage.py csv_salespro_appointments /path/to/export.csv
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
