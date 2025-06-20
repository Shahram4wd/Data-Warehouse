# LeadConduit CSV Import Implementation Summary

## Completed Tasks

### 1. Created CSV Import Command
- **File**: `ingestion/management/commands/csv_leadconduit_leads.py`
- **Purpose**: Import leads from LeadConduit-exported CSV files
- **Features**:
  - Automatic CSV header mapping to database fields
  - Data validation and cleaning (phone numbers, emails, timestamps)
  - Dry-run mode for previewing imports
  - Force-refresh option for updating existing leads
  - Batch processing for large files
  - Comprehensive error handling
  - Progress tracking with tqdm

### 2. Enhanced LeadConduit_Lead Model
- **File**: `ingestion/models/leadconduit.py`
- **Changes**:
  - Added marketing/campaign fields (campaign, ad_group, keyword, UTM parameters)
  - Added lead scoring fields (quality_score, lead_score, is_duplicate)
  - Added technical fields (ip_address, user_agent, referring_url, landing_page)
  - Added status tracking (status, disposition)
  - Added import_source field to track data origin (api, csv, events)
  - Increased field lengths for compatibility with various ID formats
  - Added comprehensive database indexes for performance

### 3. Database Migration
- **File**: `ingestion/migrations/0045_update_leadconduit_lead_for_csv_import.py`
- **Status**: Successfully applied
- **Changes**: Added all new fields to the LeadConduit_Lead table

### 4. Updated Existing API Import
- **File**: `ingestion/management/commands/sync_leadconduit_leads.py`
- **Changes**:
  - Added import_source='events' for leads extracted from events
  - Added import_source='api' for leads from search API
  - Maintains backward compatibility

### 5. Documentation
- **File**: `docs/csv_leadconduit_leads.md`
- **Content**: Comprehensive documentation including:
  - Usage examples
  - CSV format specifications
  - Field mapping reference
  - Data processing rules
  - Error handling information
  - Docker usage instructions

## Field Mapping Capabilities

### Automatic CSV Header Recognition
The command recognizes various common CSV header formats:

**Contact Information**:
- Names: first_name, firstName, fname → first_name
- Email: email, email_address → email
- Phone: phone, phone_1, primary_phone → phone_1

**Address Information**:
- Address: address, address_1, street_address → address_1
- Location: city, state, zip, postal_code → respective fields

**Marketing Data**:
- Campaign: campaign, campaign_name → campaign
- UTM parameters: utm_source, utmSource → utm_source
- Keywords: keyword, kw, search_term → keyword

**Lead Quality**:
- Scoring: quality_score, score → quality_score
- Status: status, lead_status → status
- Duplicates: is_duplicate, duplicate → is_duplicate

## Testing Results

### Sample Data Import
- ✅ Successfully imported 3 test leads from CSV
- ✅ Dry-run mode working correctly
- ✅ Force-refresh option updating existing records
- ✅ Custom file path support
- ✅ Database tracking with import_source='csv'

### Validation
- ✅ Phone number cleaning (digits only, 10+ digits required)
- ✅ Email validation (basic @ and . checks, lowercase conversion)
- ✅ Timestamp parsing (multiple format support)
- ✅ Boolean conversion for is_duplicate field
- ✅ Numeric conversion for scoring fields

## Usage Examples

### Basic Import
```bash
python manage.py csv_leadconduit_leads
```

### With Options
```bash
# Preview without saving
python manage.py csv_leadconduit_leads --dry-run

# Force update existing leads
python manage.py csv_leadconduit_leads --force-refresh

# Custom file path
python manage.py csv_leadconduit_leads /path/to/file.csv
```

### Docker Usage
```bash
# Default file
docker-compose run --rm web python manage.py csv_leadconduit_leads

# With options
docker-compose run --rm web python manage.py csv_leadconduit_leads --dry-run --force-refresh
```

## File Locations

### Implementation Files
- `ingestion/management/commands/csv_leadconduit_leads.py` - Main CSV import command
- `ingestion/models/leadconduit.py` - Enhanced model definition
- `ingestion/migrations/0045_update_leadconduit_lead_for_csv_import.py` - Database migration

### Data Files
- `ingestion/csv/leadconduit_leads.csv` - Default CSV location
- Any custom path can be specified as command argument

### Documentation
- `docs/csv_leadconduit_leads.md` - Complete usage documentation

## Performance Features

- **Batch Processing**: Configurable batch size (default: 500 records)
- **Bulk Operations**: Uses Django's bulk_create and bulk_update for efficiency
- **Database Indexes**: Added indexes on frequently queried fields
- **Memory Management**: Processes large files in batches to prevent memory issues
- **Transaction Safety**: Each batch processed in atomic transactions

## Error Handling

- **Data Validation**: Invalid data logged and skipped, processing continues
- **Missing Fields**: Handles missing required fields gracefully
- **Type Conversion**: Automatic conversion with fallback for invalid data
- **Database Errors**: Transaction rollback on database errors
- **File Errors**: Clear error messages for missing or invalid files

## Integration

The CSV import command integrates seamlessly with the existing LeadConduit infrastructure:
- Uses same model as API imports
- Compatible with existing sync history tracking
- Maintains data consistency with import_source tracking
- Works with existing database indexes and constraints

This implementation provides a robust, production-ready solution for importing LeadConduit leads from CSV exports while maintaining data integrity and providing excellent user experience.
