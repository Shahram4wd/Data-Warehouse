# LeadConduit CSV Import Command

## Overview
The `csv_leadconduit_leads` command allows you to import leads from a LeadConduit-exported CSV file into the data warehouse.

## Usage

### Basic Import
```bash
python manage.py csv_leadconduit_leads
```
This will import leads from the default CSV file: `ingestion/csv/leadconduit_leads.csv`

### Custom CSV File
```bash
python manage.py csv_leadconduit_leads /path/to/your/leadconduit_export.csv
```

### Available Options

- `--dry-run`: Preview what would be imported without saving to database
- `--force-refresh`: Update existing leads with new data from CSV
- `--help`: Show all available options

### Examples

```bash
# Preview import without saving
python manage.py csv_leadconduit_leads --dry-run

# Import with force refresh of existing leads
python manage.py csv_leadconduit_leads --force-refresh

# Import specific file with preview
python manage.py csv_leadconduit_leads /app/data/leads_export.csv --dry-run
```

## CSV Format

The command automatically maps CSV headers to database fields. Supported field mappings include:

### Lead Identification
- `lead_id`, `id`, `leadId` → `lead_id` (required)
- `flow_id`, `flowId` → `flow_id`
- `flow_name`, `flowName` → `flow_name`
- `source_id`, `sourceId` → `source_id`
- `source_name`, `sourceName`, `source` → `source_name`

### Contact Information
- `first_name`, `firstName`, `fname` → `first_name`
- `last_name`, `lastName`, `lname` → `last_name`
- `email`, `email_address` → `email`
- `phone_1`, `phone1`, `phone`, `primary_phone` → `phone_1`
- `phone_2`, `phone2`, `secondary_phone` → `phone_2`

### Address Information
- `address_1`, `address1`, `address` → `address_1`
- `address_2`, `address2` → `address_2`
- `city` → `city`
- `state`, `state_province` → `state`
- `postal_code`, `zip`, `zip_code` → `postal_code`
- `country` → `country`

### Marketing Data
- `campaign`, `campaign_name` → `campaign`
- `ad_group`, `adGroup`, `ad_group_name` → `ad_group`
- `keyword`, `kw`, `search_term` → `keyword`
- `utm_source`, `utmSource` → `utm_source`
- `utm_medium`, `utmMedium` → `utm_medium`
- `utm_campaign`, `utmCampaign` → `utm_campaign`
- `utm_content`, `utmContent` → `utm_content`
- `utm_term`, `utmTerm` → `utm_term`

### Lead Scoring & Quality
- `quality_score`, `qualityScore`, `score` → `quality_score`
- `lead_score`, `leadScore` → `lead_score`
- `is_duplicate`, `duplicate`, `dup` → `is_duplicate`

### Technical Data
- `ip_address`, `ip` → `ip_address`
- `user_agent`, `userAgent`, `ua` → `user_agent`
- `referring_url`, `referrer`, `ref_url` → `referring_url`
- `landing_page`, `landingPage`, `lp` → `landing_page`

### HubSpot Integration Data
- `createdate`, `hs_createdate` → `hs_createdate`
- `lastmodifieddate`, `hs_lastmodifieddate` → `hs_lastmodifieddate`
- `hs_object_id`, `hubspot_object_id` → `hs_object_id`
- `hs_lead_status`, `lead_status` → `hs_lead_status`
- `hs_lifecyclestage`, `lifecyclestage` → `hs_lifecyclestage`
- `hs_analytics_source`, `analytics_source` → `hs_analytics_source`
- `hs_analytics_source_data_1`, `analytics_source_data_1` → `hs_analytics_source_data_1`
- `hs_analytics_source_data_2`, `analytics_source_data_2` → `hs_analytics_source_data_2`

### SalesRabbit Integration Data
- `salesrabbit_lead_id`, `lead_salesrabbit_lead_id`, `sr_lead_id` → `salesrabbit_lead_id`
- `salesrabbit_rep_id`, `sr_rep_id`, `rep_id` → `salesrabbit_rep_id`
- `salesrabbit_rep_name`, `sr_rep_name`, `rep_name` → `salesrabbit_rep_name`
- `salesrabbit_area_id`, `sr_area_id`, `area_id` → `salesrabbit_area_id`
- `salesrabbit_area_name`, `sr_area_name`, `area_name` → `salesrabbit_area_name`
- `salesrabbit_status`, `sr_status` → `salesrabbit_status`
- `salesrabbit_disposition`, `sr_disposition` → `salesrabbit_disposition`
- `salesrabbit_notes`, `sr_notes` → `salesrabbit_notes`
- `salesrabbit_created_at`, `sr_created_at` → `salesrabbit_created_at`
- `salesrabbit_updated_at`, `sr_updated_at` → `salesrabbit_updated_at`
- `salesrabbit_appointment_date`, `sr_appointment_date`, `appointment_date` → `salesrabbit_appointment_date`
- `salesrabbit_sale_amount`, `sr_sale_amount`, `sale_amount` → `salesrabbit_sale_amount`
- `salesrabbit_commission`, `sr_commission`, `commission` → `salesrabbit_commission`

### Status & Timing
- `status`, `lead_status` → `status`
- `disposition`, `outcome` → `disposition`
- `submission_timestamp`, `submission_time`, `created_at`, `timestamp` → `submission_timestamp`
- `status`, `lead_status` → `status`
- `disposition`, `outcome` → `disposition`
- `submission_timestamp`, `submission_time`, `created_at`, `timestamp` → `submission_timestamp`

### Example CSV Format
```csv
lead_id,first_name,last_name,email,phone_1,address_1,city,state,postal_code,campaign,utm_source,utm_medium,submission_timestamp,source_name,flow_name,status
LC001,John,Doe,john.doe@example.com,5551234567,123 Main St,Anytown,CA,90210,Google Ads,google,cpc,2025-06-20 10:00:00,Google Lead Form,Home Insurance Flow,new
LC002,Jane,Smith,jane.smith@example.com,5552345678,456 Oak Ave,Springfield,TX,75001,Facebook Ads,facebook,social,2025-06-20 11:00:00,Facebook Form,Auto Insurance Flow,contacted
```

## Data Processing

- **Phone numbers**: Automatically cleaned to digits only, must be at least 10 digits
- **Emails**: Converted to lowercase, basic validation (@. present)
- **Timestamps**: Parsed using Django's `parse_datetime_obj` function
- **Duplicates**: Identified by `lead_id`, existing leads are skipped unless `--force-refresh` is used
- **Booleans**: `is_duplicate` field accepts: true, 1, yes, y, duplicate (case insensitive)
- **Numeric**: `quality_score` (float) and `lead_score` (integer) are automatically converted

## Import Tracking

- All CSV imports are marked with `import_source = 'csv'`
- Original CSV data is stored in the `full_data` JSON field
- Import statistics are displayed after each run
- Existing leads are only updated when `--force-refresh` is used

## Error Handling

- Invalid data types are logged and skipped (row continues processing)
- Missing required fields (lead_id) cause the row to be skipped
- Parsing errors for timestamps/numbers are logged but don't stop import
- Database errors are handled gracefully with transaction rollback

## Docker Usage

When using Docker, make sure your CSV file is accessible in the container:

```bash
# Copy file to container volume
docker cp myfile.csv data-warehouse-web-1:/app/ingestion/csv/

# Or mount a volume and run
docker-compose run --rm -v /host/path:/app/data web python manage.py csv_leadconduit_leads /app/data/leads.csv
```
