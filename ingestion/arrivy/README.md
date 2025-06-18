# Arrivy Integration

This package provides comprehensive integration with the Arrivy API for syncing customers, team members, and bookings data.

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

### Arrivy_TeamMember
- Stores team member/employee information
- Primary key: `id` (Arrivy team member ID)
- Includes fields for personal details, role, permissions, group assignments, and skills

### Arrivy_Booking
- Stores booking/appointment information (called "tasks" in Arrivy API)
- Primary key: `id` (Arrivy booking ID)
- Links to customers via foreign key relationship
- Includes scheduling, location, team assignments, and status information

### Arrivy_SyncHistory
- Tracks sync operations for each endpoint
- Stores last sync timestamps and statistics

## Management Commands

### Test Connection
```bash
python manage.py test_arrivy --endpoint customers --limit 5
```

Test the API connection and fetch sample data.

**Options:**
- `--endpoint`: Which endpoint to test (customers, team_members, bookings)
- `--limit`: Number of records to fetch (default: 5)
- `--output`: Save data to file

### Sync Customers
```bash
python manage.py sync_arrivy_customers
```

Sync customer data from Arrivy.

**Options:**
- `--full`: Perform full sync instead of incremental
- `--pages`: Maximum pages to process (0 = unlimited)
- `--lastmodifieddate`: Filter by modification date (YYYY-MM-DD)
- `--debug`: Show debug output

### Sync Team Members
```bash
python manage.py sync_arrivy_team_members
```

Sync team member data from Arrivy.

**Options:** Same as customers sync

### Sync Bookings
```bash
python manage.py sync_arrivy_bookings
```

Sync booking data from Arrivy.

**Options:** Same as customers sync, plus:
- `--start-date`: Filter bookings starting after date (YYYY-MM-DD)
- `--end-date`: Filter bookings ending before date (YYYY-MM-DD)

### Sync All Data
```bash
python manage.py sync_arrivy_all
```

Sync all Arrivy data in the correct order (customers → team members → bookings).

**Options:** All options from individual commands, plus:
- `--skip-customers`: Skip customer sync
- `--skip-team-members`: Skip team member sync
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

The `ArrivyClient` class provides asynchronous methods for interacting with the Arrivy API:

```python
from ingestion.arrivy.arrivy_client import ArrivyClient
import asyncio

client = ArrivyClient()

# Test connection
success, message = await client.test_connection()

# Get customers
result = await client.get_customers(page_size=100, page=1)

# Get team members
result = await client.get_team_members(page_size=100, page=1)

# Get bookings
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
