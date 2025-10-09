# API & Integration Reference

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Complete reference for all CRM API integrations, sync engines, clients, and processors

---

## Quick Reference

| CRM | API Type | Auth Method | Endpoints | Sync Engines | Rate Limits |
|-----|----------|-------------|-----------|--------------|-------------|
| **HubSpot** | REST v3 | API Key | 10+ | 10 engines | 100 req/10s |
| **Genius** | Direct DB | PostgreSQL | N/A | 8 engines | No limit |
| **CallRail** | REST v3 | API Key | 9+ | 9 engines | 60 req/min |
| **SalesRabbit** | GraphQL | API Token | 2 | 2 engines | 50 req/min |
| **Arrivy** | REST | API Token | 6 | 6 engines | 120 req/min |
| **Five9** | REST | API Key | 1 | 1 engine | 30 req/min |
| **MarketSharp** | Direct DB | MSSQL | N/A | 1 engine | No limit |
| **LeadConduit** | REST | API Key | 1 | 1 engine | 60 req/min |
| **SalesPro** | AWS Athena | IAM | SQL Queries | 4 engines | AWS limits |
| **Google Sheets** | Google API | OAuth2 | Sheets API | 3 engines | 60 req/min |

---

## HubSpot Integration

### Overview
- **API Version**: v3 (REST)
- **Base URL**: `https://api.hubapi.com`
- **Authentication**: API Key (Bearer token)
- **Rate Limit**: 100 requests per 10 seconds
- **Pagination**: Cursor-based

### API Endpoints

#### 1. Contacts API
- **GET** `/crm/v3/objects/contacts`
- **Purpose**: Fetch contact records
- **Pagination**: `after` parameter for cursor
- **Filters**: `properties`, `associations`
- **Response**: Contact objects with properties

#### 2. Deals API
- **GET** `/crm/v3/objects/deals`
- **Purpose**: Fetch deal/opportunity records
- **Features**: Pipeline stages, amount, close date

#### 3. Companies API
- **GET** `/crm/v3/objects/companies`
- **Purpose**: Fetch company/account records

#### 4. Associations API
- **GET** `/crm/v4/associations/{fromObjectType}/{toObjectType}/batch/read`
- **Purpose**: Fetch object relationships
- **Types**: contact-to-deal, contact-to-company, etc.

#### 5. Custom Objects API
- **GET** `/crm/v3/objects/{objectType}`
- **Custom Objects**: 
  - `genius_users`: Genius CRM users
  - `divisions`: Business divisions
  - `zipcodes`: Service area zipcodes

### Sync Engines

**Location**: `ingestion/sync/hubspot/engines/`

1. **HubSpotContactsSyncEngine** (`contacts.py`)
   - Syncs contacts with full property mapping
   - Handles SalesRabbit lead field integration (60+ fields)
   
2. **HubSpotDealsSyncEngine** (`deals.py`)
   - Syncs deal records with pipeline data
   
3. **HubSpotGeniusUsersSyncEngine** (`genius_users.py`)
   - Syncs custom genius_users objects
   - Recently fixed to properly track sync statistics
   
4. **HubSpotDivisionsSyncEngine** (`divisions.py`)
   - Syncs custom division objects
   
5. **HubSpotZipcodesSyncEngine** (`zipcodes.py`)
   - Syncs custom zipcode objects
   
6. **HubSpotAssociationsSyncEngine** (`associations.py`)
   - Syncs contact-deal and contact-company associations
   
7. **HubSpotAppointmentsSyncEngine** (`appointments.py`)
   - Syncs meeting/appointment records

### Management Commands

```bash
# Individual entity syncs
python manage.py sync_hubspot_contacts [--full] [--dry-run]
python manage.py sync_hubspot_deals [--full] [--dry-run]
python manage.py sync_hubspot_genius_users [--full] [--dry-run]
python manage.py sync_hubspot_divisions [--full] [--dry-run]
python manage.py sync_hubspot_zipcodes [--full] [--dry-run]
python manage.py sync_hubspot_associations [--full] [--dry-run]
python manage.py sync_hubspot_appointments [--full] [--dry-run]

# Orchestration command (runs all HubSpot syncs)
python manage.py sync_hubspot_all [--full] [--dry-run]
```

### Example Usage

```python
from ingestion.sync.hubspot.engines.contacts import HubSpotContactsSyncEngine

# Initialize engine
engine = HubSpotContactsSyncEngine(
    crm_source='hubspot',
    sync_type='contacts',
    batch_size=100,
    dry_run=False
)

# Run sync
results = await engine.run_sync(force_full=False)
# Returns: {'processed': N, 'created': X, 'updated': Y, 'failed': Z}
```

---

## Genius Integration

### Overview
- **Type**: Direct PostgreSQL Database Connection
- **Connection**: SQLAlchemy engine to Genius production DB
- **Authentication**: Database credentials
- **Rate Limit**: None (direct DB access)
- **Query Type**: Raw SQL queries

### Database Tables

1. **leads**: Lead records
2. **prospects**: Prospect records  
3. **appointments**: Appointment scheduling
4. **users**: CRM users/agents
5. **divisions**: Business divisions
6. **contacts**: Contact information
7. **division_groups**: Division groupings

### Sync Engines

**Location**: `ingestion/sync/genius/engines/`

1. **GeniusLeadsSyncEngine** (`leads.py`)
   - Direct SQL queries to leads table
   - Chunked processing for large datasets
   
2. **GeniusProspectsSyncEngine** (`prospects.py`)
   - Syncs prospect records
   
3. **GeniusAppointmentsSyncEngine** (`appointments.py`)
   - Syncs appointment data
   
4. **GeniusUsersSyncEngine** (`users.py`)
   - Syncs user/agent records
   
5. **GeniusDivisionsSyncEngine** (`divisions.py`)
   - Syncs division records

### Management Commands

```bash
python manage.py sync_genius_leads [--full] [--dry-run] [--max-records N]
python manage.py sync_genius_prospects [--full] [--dry-run]
python manage.py sync_genius_appointments [--full] [--dry-run]
python manage.py sync_genius_users [--full] [--dry-run]
python manage.py sync_genius_divisions [--full] [--dry-run]
```

### Example SQL Query

```python
query = """
SELECT 
    lead_id,
    contact_id,
    division_id,
    agent_id,
    status,
    address1,
    city,
    state,
    zipcode,
    created,
    modified
FROM leads
WHERE modified >= %s
ORDER BY modified
LIMIT %s OFFSET %s
"""
```

---

## CallRail Integration

### Overview
- **API Version**: v3 (REST)
- **Base URL**: `https://api.callrail.com/v3`
- **Authentication**: API Key (Bearer token)
- **Rate Limit**: 60 requests per minute (120 burst)
- **Pagination**: Page-based

### API Endpoints

1. **GET** `/a/{account_id}/calls.json`
   - Fetch call records
   - Filters: `start_date`, `end_date`, `company_id`
   
2. **GET** `/a/{account_id}/companies.json`
   - Fetch company records
   
3. **GET** `/a/{account_id}/trackers.json`
   - Fetch tracker configurations
   
4. **GET** `/a/{account_id}/form_submissions.json`
   - Fetch web form submissions
   
5. **GET** `/a/{account_id}/text_messages.json`
   - Fetch SMS/text messages
   
6. **GET** `/a/{account_id}/accounts.json`
   - Fetch account information
   
7. **GET** `/a/{account_id}/users.json`
   - Fetch CallRail users
   
8. **GET** `/a/{account_id}/tags.json`
   - Fetch call tags

### Sync Engines

**Location**: `ingestion/sync/callrail/engines/`

All engines inherit from `CallRailBaseSyncEngine`

1. **CallRailCallsSyncEngine**
2. **CallRailCompaniesSyncEngine**
3. **CallRailTrackersSyncEngine**
4. **CallRailFormSubmissionsSyncEngine**
5. **CallRailTextMessagesSyncEngine**
6. **CallRailAccountsSyncEngine**
7. **CallRailUsersSyncEngine**
8. **CallRailTagsSyncEngine**
9. **CallRailAllSyncEngine** (orchestration)

### Management Commands

```bash
python manage.py sync_callrail_calls [--since YYYY-MM-DD] [--dry-run]
python manage.py sync_callrail_companies [--dry-run]
python manage.py sync_callrail_trackers [--dry-run]
python manage.py sync_callrail_form_submissions [--since YYYY-MM-DD]
python manage.py sync_callrail_text_messages [--since YYYY-MM-DD]
python manage.py sync_callrail_accounts [--dry-run]
python manage.py sync_callrail_users [--dry-run]
python manage.py sync_callrail_tags [--dry-run]

# Orchestration (all CallRail syncs)
python manage.py sync_callrail_all [--dry-run]
```

---

## SalesRabbit Integration

### Overview
- **API Type**: GraphQL
- **Base URL**: `https://cloud.salesrabbit.com/graphql`
- **Authentication**: API Token (Bearer)
- **Rate Limit**: ~50 requests per minute
- **Pagination**: Cursor-based

### GraphQL Queries

#### Leads Query
```graphql
query GetLeads($cursor: String, $limit: Int) {
  leads(after: $cursor, first: $limit) {
    edges {
      node {
        id
        leadHash
        dispositionId
        prospectName
        prospectPhone
        prospectEmail
        prospectAddress
        latitude
        longitude
        createdBy
        createdAt
        lastModified
        customFields
      }
      cursor
    }
    pageInfo {
      hasNextPage
      endCursor
    }
  }
}
```

#### Users Query
```graphql
query GetUsers {
  users {
    id
    email
    firstName
    lastName
    phone
    active
    teamId
  }
}
```

### Sync Engines

**Location**: `ingestion/sync/salesrabbit/engines/`

1. **SalesRabbitLeadSyncEngine** (`leads.py`)
   - GraphQL query execution
   - Cursor-based pagination
   
2. **SalesRabbitUserSyncEngine** (`users.py`)
   - User/rep sync
   
3. **SalesRabbitAllSyncEngine** (orchestration)

### Management Commands

```bash
python manage.py sync_salesrabbit_leads [--full] [--dry-run]
python manage.py sync_salesrabbit_users [--dry-run]
python manage.py sync_salesrabbit_all [--dry-run]
```

---

## Arrivy Integration

### Overview
- **API Type**: REST
- **Base URL**: `https://www.arrivy.com/api`
- **Authentication**: Token-based
- **Rate Limit**: ~120 requests per minute

### API Endpoints

1. **GET** `/tasks`
   - Fetch task records
   
2. **GET** `/entities`
   - Fetch team members/resources
   
3. **GET** `/groups`
   - Fetch organization groups
   
4. **GET** `/statuses`
   - Fetch custom status definitions

### Sync Engines

**Location**: `ingestion/sync/arrivy/engines/`

1. **ArrivyBookingsSyncEngine**
2. **ArrivyTasksSyncEngine**
3. **ArrivyEntitiesSyncEngine**
4. **ArrivyGroupsSyncEngine**
5. **ArrivyStatusesSyncEngine**
6. **ArrivyAllSyncEngine**

---

## Additional CRM Integrations

### Five9
- REST API for contact sync
- Management command: `sync_five9_contacts`

### MarketSharp
- Direct MSSQL database connection
- Management command: `sync_marketsharp_data`

### LeadConduit
- REST API for lead aggregation
- Management command: `sync_leadconduit_leads`

### SalesPro
- AWS Athena SQL queries
- 4 entities: credit_applications, customers, estimates, lead_results
- Management commands: `sync_salespro_{entity}`

### Google Sheets
- Google Sheets API (OAuth2)
- Marketing leads and spend tracking
- Management commands: `sync_gsheet_marketing_leads`, `sync_gsheet_marketing_spends`

---

## Common Patterns

### Sync Engine Workflow

1. **Initialize**: `await engine.initialize_client()`
2. **Start Tracking**: `await engine.start_sync()`
3. **Determine Strategy**: Full vs delta sync
4. **Fetch Data**: `async for batch in engine.fetch_data()`
5. **Transform**: `await engine.transform_data(batch)`
6. **Validate**: `await engine.validate_data(transformed)`
7. **Save**: `await engine.save_data(validated)`
8. **Complete**: `await engine.complete_sync(results)`
9. **Cleanup**: `await engine.cleanup()`

### Error Handling

All engines follow this pattern:
```python
try:
    results = await self._bulk_save(records)
except Exception as e:
    logger.warning(f"Bulk save failed: {e}")
    results = await self._individual_save_fallback(records)
```

### Rate Limiting

Implemented in clients:
```python
async def _handle_rate_limit(self):
    if self.requests_this_window >= self.rate_limit:
        wait_time = self.window_end - time.time()
        await asyncio.sleep(wait_time)
```

---

## Testing API Integrations

### Unit Tests (Mocked)
```python
@patch('ingestion.sync.hubspot.clients.HubSpotContactsClient')
def test_hubspot_contacts(self, mock_client):
    mock_client.return_value.fetch_contacts.return_value = mock_data
    # Test logic
```

### Integration Tests (Real API, Limited Data)
```python
def test_hubspot_integration():
    engine = HubSpotContactsSyncEngine(batch_size=10)
    results = await engine.run_sync()
    assert results['processed'] <= 10
```

---

## Related Documents

- [Architecture Overview](ARCHITECTURE.md)
- [Database Schema Reference](DATABASE_SCHEMA.md)
- [Existing Tests Documentation](EXISTING_TESTS.md)
- [CRM Sync Guide](../crm_sync_guide.md)

---

**Document Maintained By**: Development Team  
**Last Review**: 2025  
**Next Review**: Quarterly
