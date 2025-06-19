# Arrivy Integration

This package provides comprehensive integration with the Arrivy API using official endpoints for syncing customers, entities (crew members), groups (locations), and bookings data.

## Configuration

Add the following environment variables to your `.env` file:

```env
ARRIVY_API_KEY=your_api_key_here
ARRIVY_AUTH_KEY=your_auth_key_here
ARRIVY_API_URL=https://api.arrivy.com/v1/
```

## Models

### Arrivy_Customer
- Stores customer information including contact details, addresses, and metadata
- Primary key: `id` (Arrivy customer ID)
- Includes fields for company name, personal details, address, timezone, and custom fields
- Table: `ingestion_arrivy_customer`

### Arrivy_Entity
- Stores individual crew member information from the official `/entities` endpoint
- Primary key: `id` (Arrivy entity ID)
- Includes fields for name, contact details, permissions, skills, and group assignments
- Table: `ingestion_arrivy_entity`

### Arrivy_Group
- Stores group/location information from the official `/groups` endpoint
- Primary key: `id` (Arrivy group ID)
- Includes fields for name, address, contact information, and organizational data
- Table: `ingestion_arrivy_group`

### Arrivy_Booking
- Stores booking/appointment information (called "tasks" in Arrivy API)
- Primary key: `id` (Arrivy booking ID)
- References customers via `customer_id` field (string, not foreign key to allow importing all bookings)
- Includes scheduling, location, team assignments, and status information
- Table: `ingestion_arrivy_booking`

### Arrivy_SyncHistory
- Tracks sync operations for each endpoint
- Stores last sync timestamps and statistics
- Table: `ingestion_arrivy_sync_history`

## Management Commands

### Test Connection
```bash
python manage.py test_arrivy --endpoint customers --limit 5
```

Test the API connection and fetch sample data.

**Options:**
- `--endpoint`: Which endpoint to test (customers, entities, groups, bookings)
- `--limit`: Number of records to fetch (default: 5)
- `--output`: Save data to file

### Sync Customers
```bash
python manage.py sync_arrivy_customers
```

Sync customer data from Arrivy using the official `/customers` endpoint.

**Options:**
- `--full`: Perform full sync instead of incremental
- `--pages`: Maximum pages to process (0 = unlimited)
- `--lastmodifieddate`: Filter by modification date (YYYY-MM-DD)
- `--debug`: Show debug output

### Sync Entities (Crew Members)
```bash
python manage.py sync_arrivy_entities
```

Sync individual crew member data from Arrivy using the official `/entities` endpoint.

**Options:** Same as customers sync

### Sync Groups (Locations)
```bash
python manage.py sync_arrivy_groups
```

Sync group/location data from Arrivy using the official `/groups` endpoint.

**Options:** Same as customers sync

### Sync Bookings
```bash
python manage.py sync_arrivy_bookings
```

Sync booking data from Arrivy using the official `/tasks` endpoint.

**Options:** Same as customers sync, plus:
- `--start-date`: Filter bookings starting after date (YYYY-MM-DD)
- `--end-date`: Filter bookings ending before date (YYYY-MM-DD)

### Sync All Data
```bash
python manage.py sync_arrivy_all
```

Sync all Arrivy data using official endpoints in the correct order (customers → entities → groups → bookings).

**Options:** All options from individual commands, plus:
- `--skip-customers`: Skip customer sync
- `--skip-entities`: Skip entities (crew members) sync
- `--skip-groups`: Skip groups (locations) sync
- `--skip-bookings`: Skip booking sync

## Usage Examples

### Full Initial Sync
```bash
# Sync all data for the first time
python manage.py sync_arrivy_all --full

# Test connection first
python manage.py test_arrivy --endpoint customers --limit 1
```

### Incremental Daily Sync
```bash
# Sync only data modified in the last day
python manage.py sync_arrivy_all --lastmodifieddate $(date -d "1 day ago" +%Y-%m-%d)
```

### Sync Specific Date Range for Bookings
```bash
# Sync bookings for a specific month
python manage.py sync_arrivy_bookings --start-date 2025-06-01 --end-date 2025-06-30
```

### Limited Sync for Testing
```bash
# Sync only first 2 pages of each endpoint
python manage.py sync_arrivy_all --pages 2
```

## Database Migrations

After setting up the models, run migrations:

```bash
python manage.py makemigrations
python manage.py migrate
```

## API Client

The `ArrivyClient` class provides asynchronous methods for interacting with the official Arrivy API endpoints:

```python
from ingestion.arrivy.arrivy_client import ArrivyClient
import asyncio

client = ArrivyClient()

# Test connection
success, message = await client.test_connection()

# Get customers (official /customers endpoint)
result = await client.get_customers(page_size=100, page=1)

# Get entities/crew members (official /entities endpoint)
result = await client.get_entities(page_size=100, page=1)

# Get groups/locations (official /groups endpoint)
result = await client.get_groups(page_size=100, page=1)

# Get bookings (official /tasks endpoint)
result = await client.get_bookings(
    page_size=100, 
    page=1,
    start_date=datetime(2025, 6, 1),
    end_date=datetime(2025, 6, 30)
)
```

## Error Handling

All sync commands include comprehensive error handling:
- Individual record processing errors are logged but don't stop the sync
- Database transaction errors are caught and reported
- API connection errors are retried with backoff
- Detailed logging for troubleshooting

## Performance Considerations

- Uses bulk database operations for better performance
- Processes data in configurable batches (default: 100 records)
- Implements checkpointing to save progress during long syncs
- Supports pagination for large datasets
- Uses async HTTP client for better API performance

## Monitoring

Check sync history:
```python
from ingestion.models import Arrivy_SyncHistory

# Get last sync times
history = Arrivy_SyncHistory.objects.all()
for h in history:
    print(f"{h.endpoint}: {h.last_synced_at}")
```

## Troubleshooting

1. **Connection Issues**: Use `test_arrivy` command to verify API credentials
2. **Rate Limits**: The client handles rate limiting automatically
3. **Data Issues**: Check logs for individual record processing errors
4. **Performance**: Adjust batch sizes and use `--pages` limit for testing
