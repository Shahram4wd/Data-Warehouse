# Google Sheets Integration Setup Guide

This guide explains how to set up and use the Google Sheets integration for the Data Warehouse project.

## Overview

The Google Sheets integration follows the same architectural patterns as other CRM integrations in this project:

- **Clients**: Handle API connections and data retrieval
- **Engines**: Orchestrate the sync process and manage state
- **Processors**: Transform and validate data before storage
- **Models**: Django models for storing sheet data

## Features

- ✅ OAuth2 authentication with Google
- ✅ Delta sync based on sheet modification time
- ✅ Full sync history tracking using SyncHistory model
- ✅ Comprehensive error handling and validation
- ✅ Support for multiple sheets/tabs
- ✅ Auto-detection of column headers
- ✅ Raw data preservation in JSON format

## Authentication Setup

### 1. Create Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable the following APIs:
   - Google Sheets API
   - Google Drive API

### 2. Create OAuth2 Credentials

1. Go to "Credentials" in the Google Cloud Console
2. Click "Create Credentials" > "OAuth 2.0 Client IDs"
3. Choose "Desktop application"
4. Download the JSON credentials file
5. Save it as `credentials.json` in your project root

### 3. Environment Variables

Add these to your `.env` file:

```bash
# Google Sheets OAuth2 Authentication
GOOGLE_CREDENTIALS_FILE=credentials.json
GOOGLE_TOKEN_FILE=token.json

# Optional: Google account for OAuth flow
GOOGLE_USERNAME=your-email@gmail.com
GOOGLE_PASSWORD=your-password  # Note: OAuth will still require browser authentication
```

## Database Setup

Run migrations to create the required database tables:

```bash
python manage.py makemigrations ingestion
python manage.py migrate
```

This will create:
- `ingestion_gsheet_marketing_lead` - Marketing leads data
- `ingestion_gsheet_config` - Sheet configuration
- SyncHistory entries for tracking sync operations

## Configuration

### Marketing Leads Sheet

The system is pre-configured for the Marketing Source Leads sheet:

- **Sheet ID**: `1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo`
- **Tab**: "Marketing Source Leads"
- **Headers**: Auto-detected from row 1
- **Data**: Starting from row 2

### Adding New Sheets

To add support for new sheets:

1. Create a new model in `ingestion/models/gsheet.py`
2. Create a new client in `ingestion/sync/gsheet/clients/`
3. Create a new processor in `ingestion/sync/gsheet/processors/`
4. Create a new engine in `ingestion/sync/gsheet/engines/`
5. Create a new management command in `ingestion/management/commands/`

## Usage

### Test Connection

```bash
python manage.py sync_gsheet_marketing_leads --test-connection
```

### Show Sync Summary

```bash
python manage.py sync_gsheet_marketing_leads --show-summary
```

### Dry Run (Test Without Saving)

```bash
python manage.py sync_gsheet_marketing_leads --dry-run
```

### Full Sync

```bash
python manage.py sync_gsheet_marketing_leads
```

### Force Sync (Ignore Modification Time)

```bash
python manage.py sync_gsheet_marketing_leads --force
```

### Sync All Sheets

```bash
python manage.py sync_gsheet_all
```

## Advanced Options

### Batch Size

```bash
python manage.py sync_gsheet_marketing_leads --batch-size 1000
```

### Debug Mode

```bash
python manage.py sync_gsheet_marketing_leads --debug
```

### Quiet Mode

```bash
python manage.py sync_gsheet_marketing_leads --quiet
```

## Delta Sync Logic

The system uses Google Drive API to check the sheet's last modification time:

1. **First Sync**: Always performs full sync
2. **Subsequent Syncs**: Compares sheet modification time with last known time
3. **If Modified**: Performs full sync (Google Sheets doesn't support row-level change tracking)
4. **If Not Modified**: Skips sync unless `--force` is used

## Data Model

### GoogleSheetMarketingLead

The marketing leads are stored with these fields:

- `id`: Auto-generated primary key
- `created_at`/`updated_at`: Timestamps
- `sheet_row_number`: Original row in the sheet
- `sheet_last_modified`: Sheet modification time
- `date`, `source`, `medium`, `campaign`, `leads`, `cost`: Mapped from sheet columns
- `raw_data`: Complete row data as JSON

### Field Mapping

The system automatically maps sheet columns to model fields:

```python
# Common mappings
'Date' -> 'date'
'Source' -> 'source'  
'Medium' -> 'medium'
'Campaign' -> 'campaign'
'Leads' -> 'leads'
'Cost' -> 'cost'

# Alternative column names are also supported
'Marketing Source' -> 'source'
'Lead Count' -> 'leads'
'Ad Spend' -> 'cost'
```

## Error Handling

The system includes comprehensive error handling:

- **Connection Errors**: Retries with exponential backoff
- **Authentication Errors**: Clear error messages with setup guidance
- **Data Validation**: Warnings for invalid data, but continues processing
- **Sheet Structure**: Validates headers and suggests missing columns

## Monitoring

### Sync History

All sync operations are tracked in the `SyncHistory` model:

```python
from ingestion.models.common import SyncHistory

# Get latest sync
latest = SyncHistory.objects.filter(
    crm_source='gsheet',
    sync_type='marketing_leads'
).order_by('-start_time').first()
```

### Performance Metrics

Each sync records:
- Duration
- Records processed/created/updated/failed
- Error messages
- Performance metrics (records per second)

## Troubleshooting

### Authentication Issues

1. **Invalid Credentials**: Ensure `credentials.json` is valid and in the project root
2. **Token Expired**: Delete `token.json` to force re-authentication
3. **Scope Issues**: Make sure you have read access to the sheet

### Sheet Access Issues

1. **Permission Denied**: Ensure the Google account has access to the sheet
2. **Sheet Not Found**: Check the sheet ID in the URL
3. **Tab Not Found**: Verify the tab name "Marketing Source Leads"

### Data Issues

1. **No Data**: Check if the sheet has data starting from row 2
2. **Invalid Headers**: Ensure row 1 contains column headers
3. **Empty Rows**: The system automatically skips empty rows

### Performance Issues

1. **Large Sheets**: Use `--batch-size` to adjust processing batch size
2. **Slow API**: Google Sheets API has rate limits; the system includes automatic retries

## API Limits

Google Sheets API has these limits:
- 100 requests per 100 seconds per user
- 300 requests per minute per user

The system includes:
- Automatic retry with exponential backoff
- Connection pooling
- Batch processing to minimize API calls

## Security

- OAuth2 tokens are stored securely in `token.json`
- All data is retrieved read-only
- No sensitive data is logged (except in debug mode)
- SSL/TLS encryption for all API communications

## Contributing

When adding new sheet integrations:

1. Follow the established patterns in the marketing leads implementation
2. Include comprehensive tests
3. Update this documentation
4. Add appropriate validation rules
5. Consider data privacy and security implications
