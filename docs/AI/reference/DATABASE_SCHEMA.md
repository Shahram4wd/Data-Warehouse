# Database Schema Reference

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Comprehensive database schema documentation for all CRM models

---

## Table of Contents
1. [Overview](#overview)
2. [Common Models](#common-models)
3. [CRM-Specific Models](#crm-specific-models)
4. [Relationships](#relationships)
5. [Indexes and Performance](#indexes-and-performance)
6. [Database Conventions](#database-conventions)

---

## Overview

### Database Configuration
- **DBMS**: PostgreSQL 13+
- **Main Schema**: `public`
- **Orchestration Schema**: `orchestration` (sync metadata)
- **Connection Pooling**: Yes (django-db-connection-pool)
- **Migrations**: Django migrations system

### Table Naming Conventions
- Common models: `orchestration.sync_history`, `orchestration.sync_schedule`
- CRM models: `{crm}_{{entity}}` (e.g., `hubspot_contact`, `callrail_call`)
- Some legacy tables use `ingestion_` prefix

### Total Tables
- **Common**: 2 (SyncHistory, SyncSchedule)
- **HubSpot**: 10+ models
- **Genius**: 8 models
- **CallRail**: 8 models
- **SalesRabbit**: 2 models
- **Arrivy**: 6 models
- **Five9**: 1 model
- **MarketSharp**: 1 model
- **LeadConduit**: 1 model
- **SalesPro**: 4 models
- **Google Sheets**: 2 models
- **Alerts**: 2 models
- **Total**: 47+ models

---

## Common Models

### 1. SyncHistory
**Table**: `orchestration.sync_history`  
**Purpose**: Universal tracking for all sync operations across all CRMs

**Schema**:
```sql
CREATE TABLE "orchestration"."sync_history" (
    id BIGSERIAL PRIMARY KEY,
    crm_source VARCHAR(50) NOT NULL,         -- 'genius', 'hubspot', 'callrail', etc.
    sync_type VARCHAR(100) NOT NULL,         -- 'appointments', 'contacts', 'prospects', etc.
    endpoint VARCHAR(200),                   -- API endpoint or data source
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP,
    status VARCHAR(20) DEFAULT 'running',    -- 'running', 'success', 'failed', 'partial'
    records_processed INTEGER DEFAULT 0,
    records_created INTEGER DEFAULT 0,
    records_updated INTEGER DEFAULT 0,
    records_failed INTEGER DEFAULT 0,
    error_message TEXT,
    configuration JSONB DEFAULT '{}',        -- Sync parameters
    performance_metrics JSONB DEFAULT '{}',  -- Duration, rate, etc.
    created_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_history_crm_type ON sync_history(crm_source, sync_type);
CREATE INDEX idx_sync_history_start_time ON sync_history(start_time);
CREATE INDEX idx_sync_history_status ON sync_history(status);
```

**Key Fields**:
- `crm_source`: Identifies which CRM system (genius, hubspot, callrail, etc.)
- `sync_type`: Entity type being synced (contacts, leads, appointments, etc.)
- `status`: Current sync state (running → success/failed/partial)
- `records_*`: Counts for created, updated, failed records
- `configuration`: Stores sync parameters (batch_size, full_sync, etc.)
- `performance_metrics`: Timing data, rate metrics

**Relationships**:
- Referenced by all sync engines
- No foreign keys (design choice for flexibility)
- Used for dashboard analytics

**Indexes**:
- Composite index on (crm_source, sync_type) for dashboard queries
- Index on start_time for chronological queries
- Index on status for filtering running/failed syncs

**Usage Example**:
```python
# Create sync record
sync = SyncHistory.objects.create(
    crm_source='hubspot',
    sync_type='contacts',
    start_time=timezone.now(),
    status='running'
)

# Update on completion
sync.end_time = timezone.now()
sync.status = 'success'
sync.records_processed = 1000
sync.records_created = 50
sync.records_updated = 950
sync.save()
```

### 2. SyncSchedule
**Table**: `orchestration.sync_schedule`  
**Purpose**: Defines scheduled sync operations (replaces IngestionSchedule)

**Schema**:
```sql
CREATE TABLE "orchestration"."sync_schedule" (
    id BIGSERIAL PRIMARY KEY,
    name VARCHAR(128) NOT NULL,
    crm_source VARCHAR(64) NOT NULL,
    model_name VARCHAR(128) NOT NULL,        -- Entity to sync
    mode VARCHAR(16) NOT NULL,               -- 'delta', 'full', 'force7'
    recurrence_type VARCHAR(16) NOT NULL,    -- 'interval', 'crontab'
    every INTEGER,                           -- For interval: run every N units
    period VARCHAR(24),                      -- 'minutes', 'hours', 'days', 'weeks'
    crontab_minute VARCHAR(64) DEFAULT '*',
    crontab_hour VARCHAR(64) DEFAULT '*',
    crontab_day_of_week VARCHAR(64) DEFAULT '*',
    crontab_day_of_month VARCHAR(64) DEFAULT '*',
    crontab_month_of_year VARCHAR(64) DEFAULT '*',
    enabled BOOLEAN DEFAULT TRUE,
    last_run TIMESTAMP,
    next_run TIMESTAMP,
    periodic_task_id INTEGER REFERENCES django_celery_beat_periodictask(id),
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_sync_schedule_source ON sync_schedule(crm_source);
CREATE INDEX idx_sync_schedule_enabled ON sync_schedule(enabled);
```

**Modes**:
- `delta`: Incremental sync since last successful sync
- `full`: Full sync (delete and reimport)
- `force7`: Force sync last 7 days of data

**Recurrence**:
- `interval`: Run every N minutes/hours/days/weeks
- `crontab`: Cron-like scheduling (minute, hour, day, etc.)

**Integration**: Links to django-celery-beat's PeriodicTask for execution

---

## CRM-Specific Models

### HubSpot Models
**Location**: `ingestion/models/hubspot.py`

#### 1. Hubspot_Contact
**Table**: `hubspot_contact`  
**Purpose**: HubSpot contact records (leads, customers)

**Key Fields**:
- `id` (PK): HubSpot contact ID (string)
- `email`: Contact email address
- `firstname`, `lastname`: Contact name
- `phone`: Phone number
- `address`, `city`, `state`, `zip`: Location
- `division`: Business division
- `createdate`, `lastmodifieddate`: HubSpot timestamps
- `lead_*`: SalesRabbit lead integration fields (60+ fields)
- `marketsharp_id`: MarketSharp integration
- `archived`: Soft delete flag
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**Special Features**:
- Extensive lead tracking (lead_id, lead_agent_id, lead_status, etc.)
- Marketing attribution (campaign_name, adgroupid, search_terms)
- Custom properties support
- SalesRabbit integration fields

**Relationships**:
- Associated with HubSpot_Deal via associations
- Linked to external CRMs (MarketSharp, SalesRabbit)

#### 2. Hubspot_Deal
**Table**: `hubspot_deal`  
**Purpose**: HubSpot deal/opportunity records

**Key Fields**:
- `id` (PK): Deal ID
- `dealname`: Deal name
- `amount`: Deal value
- `dealstage`: Pipeline stage
- `closedate`: Expected/actual close date
- `pipeline`: Pipeline ID
- `createdate`, `hs_lastmodifieddate`: Timestamps
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**Relationships**:
- Associated with Hubspot_Contact
- Associated with Hubspot_Company

#### 3. Hubspot_GeniusUser
**Table**: `hubspot_geniususer`  
**Purpose**: Custom HubSpot object for Genius CRM users

**Key Fields**:
- `id` (PK): HubSpot object ID
- `email`: User email
- `division_name`: Division assignment
- `firstname`, `lastname`: User name
- `is_active`: Active status
- `hs_object_id`: HubSpot internal ID
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**Purpose**: Syncs Genius CRM users to HubSpot as custom objects

#### 4. Hubspot_Division
**Table**: `hubspot_division`  
**Purpose**: Custom HubSpot object for business divisions

**Key Fields**:
- `id` (PK): Division ID
- `name`: Division name
- `code`: Division code
- `manager_email`: Division manager
- `hs_object_id`: HubSpot internal ID

#### 5. Hubspot_Zipcode
**Table**: `hubspot_zipcode`  
**Purpose**: Custom HubSpot object for service area zipcodes

**Key Fields**:
- `id` (PK): Zipcode ID
- `zipcode`: Zipcode value
- `city`, `state`: Location
- `division`: Assigned division
- `hs_object_id`: HubSpot internal ID

#### 6. Hubspot_Appointment
**Table**: `hubspot_appointment`  
**Purpose**: HubSpot appointments/meetings

**Key Fields**:
- `id` (PK): Appointment ID
- `subject`: Appointment subject
- `start_time`, `end_time`: Appointment schedule
- `attendees`: JSON field with attendee list
- `meeting_outcome`: Outcome/notes
- `createdate`: Creation timestamp

**Additional HubSpot Models**:
- `Hubspot_Company`: Company/account records
- `Hubspot_ContactToDealAssociation`: Contact-Deal relationships
- `Hubspot_ContactToCompanyAssociation`: Contact-Company relationships
- `Hubspot_LineItem`: Deal line items

### Genius Models
**Location**: `ingestion/models/genius.py`

#### 1. Genius_Lead
**Table**: `genius_lead`  
**Purpose**: Genius CRM lead records

**Key Fields**:
- `lead_id` (PK): Genius lead ID
- `contact_id`: Associated contact
- `division_id`: Division assignment
- `agent_id`: Assigned agent
- `status`: Lead status
- `address1`, `city`, `state`, `zipcode`: Location
- `firstname`, `lastname`, `email`, `phone`: Contact info
- `source`: Lead source
- `created`, `modified`: Timestamps
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**Relationships**:
- Foreign key to Genius_Contact
- Foreign key to Genius_Division
- Foreign key to Genius_User (agent)

#### 2. Genius_Prospect
**Table**: `genius_prospect`  
**Purpose**: Genius prospect records (earlier stage than leads)

**Key Fields**:
- `prospect_id` (PK): Prospect ID
- `division_id`: Division
- `address`, `city`, `state`, `zip`: Location
- `firstname`, `lastname`, `email`, `phone`: Contact
- `status`: Prospect status
- `source`: Lead source

#### 3. Genius_Appointment
**Table**: `genius_appointment`  
**Purpose**: Genius appointment scheduling

**Key Fields**:
- `appointment_id` (PK): Appointment ID
- `lead_id`: Associated lead
- `user_id`: Assigned user
- `appointment_date`: Scheduled date
- `appointment_time`: Scheduled time
- `status`: Appointment status
- `notes`: Appointment notes

#### 4. Genius_User
**Table**: `genius_user`  
**Purpose**: Genius CRM users/agents

**Key Fields**:
- `user_id` (PK): User ID
- `email`: User email
- `firstname`, `lastname`: User name
- `division_id`: Division assignment
- `is_active`: Active status
- `role`: User role

**Additional Genius Models**:
- `Genius_Division`: Business divisions
- `Genius_Contact`: Contact records
- `Genius_DivisionGroup`: Division groupings
- `Genius_Appointment`: Scheduling data

### CallRail Models
**Location**: `ingestion/models/callrail.py`

#### 1. CallRail_Call
**Table**: `callrail_call`  
**Purpose**: Individual call records from CallRail

**Key Fields**:
- `id` (PK): CallRail call ID
- `customer_phone_number`: Caller's phone
- `tracking_phone_number`: Tracked number dialed
- `duration`: Call duration (seconds)
- `start_time`: Call start timestamp
- `answered`: Boolean if answered
- `company_id`: Associated company
- `direction`: 'inbound' or 'outbound'
- `recording_url`: Call recording URL
- `transcription`: Call transcription (if available)
- `tags`: JSON array of tags
- `value`: Call value/revenue
- `lead_status`: Lead qualification status
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**JSON Fields**:
- `tags`: Array of call tags
- `custom_fields`: Additional metadata

#### 2. CallRail_Company
**Table**: `callrail_company`  
**Purpose**: CallRail company/account records

**Key Fields**:
- `id` (PK): Company ID
- `name`: Company name
- `status`: Account status
- `created_at`: Account creation date
- `time_zone`: Company timezone

#### 3. CallRail_Tracker
**Table**: `callrail_tracker`  
**Purpose**: Phone number tracking configurations

**Key Fields**:
- `id` (PK): Tracker ID
- `name`: Tracker name
- `company_id`: Associated company
- `tracking_number`: Tracked phone number
- `destination_number`: Forward-to number
- `status`: 'active' or 'inactive'
- `source`: Tracking source (website, ad, etc.)

**Additional CallRail Models**:
- `CallRail_Account`: Account information
- `CallRail_FormSubmission`: Web form submissions
- `CallRail_TextMessage`: SMS/text messages
- `CallRail_User`: CallRail users
- `CallRail_Tag`: Call tags

### SalesRabbit Models
**Location**: `ingestion/models/salesrabbit.py`

#### 1. SalesRabbit_Lead
**Table**: `salesrabbit_lead`  
**Purpose**: SalesRabbit door-to-door lead records

**Key Fields**:
- `id` (PK): SalesRabbit lead ID
- `leadHash`: Unique lead hash
- `dispositionId`: Lead disposition
- `prospectName`: Prospect name
- `prospectPhone`: Contact phone
- `prospectEmail`: Contact email
- `prospectAddress`: Full address
- `latitude`, `longitude`: GPS coordinates
- `createdBy`: Agent who created lead
- `createdAt`: Creation timestamp
- `lastModified`: Last modification timestamp
- `appointmentType`: Appointment category
- `appointment`: JSON appointment data
- `customFields`: JSON custom field data
- `files`: JSON array of file attachments
- `created_at`, `updated_at`: Sync timestamps

**Special Features**:
- GPS location tracking
- Custom field support (JSON)
- File attachment tracking
- Appointment scheduling integration

#### 2. SalesRabbit_User
**Table**: `salesrabbit_user`  
**Purpose**: SalesRabbit users/reps

**Key Fields**:
- `id` (PK): User ID
- `email`: User email
- `firstName`, `lastName`: User name
- `phone`: Contact phone
- `active`: Active status
- `teamId`: Team assignment
- `created_at`, `updated_at`: Sync timestamps

### Arrivy Models
**Location**: `ingestion/models/arrivy.py`

#### 1. Arrivy_Booking
**Table**: `arrivy_booking`  
**Purpose**: Arrivy job/service bookings

**Key Fields**:
- `id` (PK): Booking ID
- `title`: Booking title
- `customer_name`: Customer name
- `customer_email`: Customer email
- `customer_phone`: Customer phone
- `customer_address`: Service address
- `start_datetime`: Scheduled start
- `end_datetime`: Scheduled end
- `status`: Booking status
- `entity_ids`: JSON array of assigned entities
- `group_id`: Group assignment
- `sync_created_at`, `sync_updated_at`: Sync timestamps

**JSON Fields**:
- `entity_ids`: Assigned team members
- `extra_fields`: Custom booking data

#### 2. Arrivy_Task
**Table**: `arrivy_task`  
**Purpose**: Tasks within bookings

**Key Fields**:
- `id` (PK): Task ID
- `template_id`: Task template
- `title`: Task title
- `status`: Task status
- `booking_id`: Associated booking
- `entity_ids`: Assigned entities
- `start_datetime`, `end_datetime`: Schedule

**Additional Arrivy Models**:
- `Arrivy_Entity`: Team members/resources
- `Arrivy_Group`: Organization groups
- `Arrivy_Status`: Custom status definitions
- `Arrivy_Template`: Task templates

### Five9 Models
**Location**: `ingestion/models/five9.py`

#### 1. Five9_Contact
**Table**: `five9_contact`  
**Purpose**: Five9 call center contact records

**Key Fields**:
- `id` (PK): Contact ID
- `first_name`, `last_name`: Contact name
- `email`: Email address
- `phone`: Phone number
- `division`: Division assignment
- `status`: Contact status
- `created_date`: Creation timestamp
- `sync_created_at`, `sync_updated_at`: Sync timestamps

### MarketSharp Models
**Location**: `ingestion/models/marketsharp.py`

#### 1. MarketSharp_Data
**Table**: `marketsharp_data`  
**Purpose**: MarketSharp CRM data

**Key Fields**:
- `id` (PK): Record ID
- `lead_id`: Lead identifier
- `customer_name`: Customer name
- `address`, `city`, `state`, `zip`: Location
- `phone`, `email`: Contact info
- `status`: Lead status
- `created_date`: Creation date
- `sync_created_at`, `sync_updated_at`: Sync timestamps

### LeadConduit Models
**Location**: `ingestion/models/leadconduit.py`

#### 1. LeadConduit_Lead
**Table**: `leadconduit_lead`  
**Purpose**: LeadConduit lead aggregation platform leads

**Key Fields**:
- `id` (PK): Lead ID
- `lead_id`: External lead ID
- `email`: Lead email
- `phone`: Lead phone
- `first_name`, `last_name`: Contact name
- `address`, `city`, `state`, `zip`: Location
- `source`: Lead source
- `campaign`: Campaign identifier
- `created_at`: Lead creation time
- `accepted`: Boolean if accepted
- `sync_created_at`, `sync_updated_at`: Sync timestamps

### SalesPro Models
**Location**: `ingestion/models/salespro.py`

#### 1. SalesPro_CreditApplication
**Table**: `salespro_credit_application`  
**Purpose**: Credit application records from SalesPro (via AWS Athena)

**Key Fields**:
- `id` (PK): Application ID
- `customer_id`: Customer reference
- `estimate_id`: Estimate reference
- `credit_app_vendor`: Vendor name
- `credit_app_status`: Application status
- `credit_limit`: Approved limit
- `created_at`, `updated_at`: Timestamps

#### 2. SalesPro_Customer
**Table**: `salespro_customer`  
**Purpose**: Customer records

**Key Fields**:
- `customer_id` (PK): Customer ID
- `estimate_id`: Associated estimate
- `company_id`: Company reference
- `customer_first_name`, `customer_last_name`: Customer name
- `crm_source`: Source CRM system
- `crm_source_id`: External ID
- `created_at`, `updated_at`: Timestamps

#### 3. SalesPro_Estimate
**Table**: `salespro_estimate`  
**Purpose**: Estimate/quote records

**Key Fields**:
- `estimate_id` (PK): Estimate ID
- `customer_id`: Customer reference
- `total_amount`: Estimate total
- `status`: Estimate status
- `created_at`, `updated_at`: Timestamps

#### 4. SalesPro_LeadResult
**Table**: `salespro_lead_result`  
**Purpose**: Lead outcome tracking

**Key Fields**:
- `id` (PK): Result ID
- `lead_id`: Lead reference
- `result_type`: Outcome type
- `result_date`: Result timestamp
- `notes`: Result notes
- `created_at`, `updated_at`: Timestamps

### Google Sheets Models
**Location**: `ingestion/models/gsheet.py`

#### 1. GSheet_MarketingLead
**Table**: `gsheet_marketing_lead`  
**Purpose**: Marketing leads from Google Sheets

**Key Fields**:
- `id` (PK): Auto-generated ID
- `row_number`: Sheet row number
- `date`: Lead date
- `source`: Lead source
- `campaign`: Campaign name
- `first_name`, `last_name`: Contact name
- `email`, `phone`: Contact info
- `notes`: Additional notes
- `sync_created_at`, `sync_updated_at`: Sync timestamps

#### 2. GSheet_MarketingSpend
**Table**: `gsheet_marketing_spend`  
**Purpose**: Marketing spend tracking

**Key Fields**:
- `id` (PK): Auto-generated ID
- `row_number`: Sheet row number
- `date`: Spend date
- `channel`: Marketing channel
- `campaign`: Campaign name
- `amount`: Spend amount
- `impressions`: Ad impressions
- `clicks`: Ad clicks
- `conversions`: Conversions
- `sync_created_at`, `sync_updated_at`: Sync timestamps

---

## Relationships

### Cross-CRM Relationships

**HubSpot ↔ Genius**:
- `Hubspot_Contact.marketsharp_id` → External reference
- `Hubspot_GeniusUser` syncs from `Genius_User`
- `Hubspot_Division` syncs from `Genius_Division`

**HubSpot ↔ SalesRabbit**:
- `Hubspot_Contact.lead_*` fields (60+ fields) contain SalesRabbit lead data
- `Hubspot_Contact.lead_salesrabbit_lead_id` → `SalesRabbit_Lead.id`

**CallRail ↔ HubSpot**:
- CallRail calls track phone numbers that may exist in HubSpot contacts
- No direct foreign key, linked via phone number matching

**SalesPro ↔ Multiple CRMs**:
- `SalesPro_Customer.crm_source` and `crm_source_id` reference external CRMs
- Integrates with MarketSharp, Genius, HubSpot

### Internal Relationships

**HubSpot Associations**:
```
Hubspot_Contact ←→ Hubspot_Deal (via Hubspot_ContactToDealAssociation)
Hubspot_Contact ←→ Hubspot_Company (via Hubspot_ContactToCompanyAssociation)
```

**Genius Relationships**:
```
Genius_Lead → Genius_Contact (contact_id)
Genius_Lead → Genius_Division (division_id)
Genius_Lead → Genius_User (agent_id)
Genius_Appointment → Genius_Lead (lead_id)
Genius_User → Genius_Division (division_id)
```

**CallRail Relationships**:
```
CallRail_Call → CallRail_Company (company_id)
CallRail_Tracker → CallRail_Company (company_id)
```

**Arrivy Relationships**:
```
Arrivy_Task → Arrivy_Booking (booking_id)
Arrivy_Booking → Arrivy_Group (group_id)
Arrivy_Task → Arrivy_Template (template_id)
```

---

## Indexes and Performance

### Critical Indexes

**SyncHistory**:
```sql
CREATE INDEX idx_sync_history_crm_type ON sync_history(crm_source, sync_type);
CREATE INDEX idx_sync_history_start_time ON sync_history(start_time);
CREATE INDEX idx_sync_history_status ON sync_history(status);
```

**HubSpot Contacts**:
```sql
CREATE INDEX idx_hubspot_contact_email ON hubspot_contact(email);
CREATE INDEX idx_hubspot_contact_phone ON hubspot_contact(phone);
CREATE INDEX idx_hubspot_contact_lead_id ON hubspot_contact(lead_id);
CREATE INDEX idx_hubspot_contact_division ON hubspot_contact(division);
CREATE INDEX idx_hubspot_contact_createdate ON hubspot_contact(createdate);
```

**CallRail Calls**:
```sql
CREATE INDEX idx_callrail_call_start_time ON callrail_call(start_time);
CREATE INDEX idx_callrail_call_company ON callrail_call(company_id);
CREATE INDEX idx_callrail_call_customer_phone ON callrail_call(customer_phone_number);
```

**Genius Leads**:
```sql
CREATE INDEX idx_genius_lead_division ON genius_lead(division_id);
CREATE INDEX idx_genius_lead_agent ON genius_lead(agent_id);
CREATE INDEX idx_genius_lead_created ON genius_lead(created);
CREATE INDEX idx_genius_lead_status ON genius_lead(status);
```

### Performance Considerations

1. **Bulk Operations**: All syncs use `bulk_create()` and `bulk_update()`
2. **Batch Size**: Default 100-1000 records per batch
3. **Connection Pooling**: Reuse database connections
4. **Async Operations**: All I/O uses async/await
5. **Index Maintenance**: Regular VACUUM and ANALYZE on PostgreSQL

---

## Database Conventions

### Field Naming
- **Snake_case**: All field names use snake_case
- **Timestamps**: `created_at`, `updated_at` for sync timestamps
- **CRM Timestamps**: Original field names from CRM (e.g., `createdate`, `lastmodifieddate`)
- **IDs**: Usually `{entity}_id` (e.g., `lead_id`, `user_id`)

### Common Patterns
- **Soft Deletes**: Many models use `archived` boolean instead of hard deletes
- **JSON Fields**: Used for flexible/dynamic data (`custom_fields`, `extra_fields`, `tags`)
- **Sync Metadata**: Most models have `sync_created_at` and `sync_updated_at`
- **Raw Data**: Some models store `raw_data` JSON for complete API response

### NULL vs Blank
- **NULL=True**: Field can be NULL in database
- **Blank=True**: Field can be empty in Django forms
- Most fields allow both for flexibility

### Primary Keys
- **Auto-generated**: Django's BigAutoField (most new models)
- **CRM ID**: String fields for HubSpot, CallRail (some models)
- **Composite**: Some models use CRM's composite key pattern

---

## Migration Strategy

### Adding New Models
1. Create model in `ingestion/models/{crm}.py`
2. Run `python manage.py makemigrations`
3. Review migration file
4. Run `python manage.py migrate`
5. Add model to CRM discovery service
6. Create sync engine, client, processor

### Modifying Existing Models
1. Update model definition
2. Create migration: `python manage.py makemigrations`
3. Review generated migration
4. Test migration on copy of production DB
5. Apply to production: `python manage.py migrate`
6. Update sync engines if field mapping changed

### Handling Large Tables
- Use `RunPython` for data migrations
- Batch operations for large updates
- Consider downtime window for schema changes
- Test on database snapshot first

---

## Related Documents

- [Architecture Overview](ARCHITECTURE.md)
- [API & Integration Reference](API_INTEGRATIONS.md)
- [Existing Tests Documentation](EXISTING_TESTS.md)
- [Codebase Navigation Map](CODEBASE_MAP.md)

---

**Document Maintained By**: Development Team  
**Last Review**: 2025  
**Next Review**: Quarterly
