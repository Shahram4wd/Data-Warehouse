# HubSpot Force Overwrite Implementation

## Overview

This implementation adds a `--force-overwrite` flag to HubSpot sync commands that ensures **complete data replacement**, addressing the issue where the `--full` flag alone doesn't guarantee existing records are overwritten.

## Architecture

Following the unified architecture from `import_refactoring.md`, the implementation consists of:

### 1. Base Command Enhancement
- **File**: `ingestion/management/commands/base_hubspot_sync.py`
- **Changes**: Added `--force-overwrite` argument and logic

### 2. Sync Engine Enhancement
- **File**: `ingestion/base/sync_engine.py`
- **Changes**: Added `force_overwrite` parameter to base class

### 3. Contact Sync Engine Implementation
- **File**: `ingestion/sync/hubspot/engines/contacts.py`
- **Changes**: Implemented force overwrite methods

## Usage Examples

### Standard Operations
```bash
# Incremental sync (default behavior)
python manage.py sync_hubspot_contacts

# Full sync (fetch all from HubSpot, but may skip unchanged local records)
python manage.py sync_hubspot_contacts --full

# Sync recent changes only
python manage.py sync_hubspot_contacts --since=2025-01-01
```

### Force Overwrite Operations
```bash
# Force overwrite ALL contacts (complete replacement)
python manage.py sync_hubspot_contacts --full --force-overwrite

# Force overwrite contacts modified since specific date
python manage.py sync_hubspot_contacts --since=2025-01-01 --force-overwrite

# Force overwrite with custom batch size
python manage.py sync_hubspot_contacts --full --force-overwrite --batch-size=50

# Test force overwrite without saving (dry run)
python manage.py sync_hubspot_contacts --full --force-overwrite --dry-run
```

## Flag Behavior Matrix

| Flags | Data Fetched | Local Record Handling | Use Case |
|-------|--------------|----------------------|----------|
| (none) | Recent changes only | Normal update_or_create | Regular incremental sync |
| `--full` | All records | Normal update_or_create | Full refresh, skip unchanged |
| `--since=DATE` | Records since DATE | Normal update_or_create | Sync specific time range |
| `--force-overwrite` | Recent changes only | **Complete overwrite** | Force update recent records |
| `--full --force-overwrite` | **All records** | **Complete overwrite** | **Complete data replacement** |
| `--since=DATE --force-overwrite` | Records since DATE | **Complete overwrite** | Force update date range |

## Implementation Details

### Force Overwrite Logic

The force overwrite implementation uses a **delete-and-recreate** strategy to ensure complete data replacement:

1. **Fetch all relevant records** from HubSpot (respects --full and --since flags)
2. **Identify existing vs new records** in local database
3. **For new records**: Use bulk_create (standard behavior)
4. **For existing records**: Delete existing + bulk_create new (complete replacement)
5. **Fallback**: Individual delete-and-recreate if bulk operations fail

### Performance Considerations

- **Bulk Operations**: Uses Django's `bulk_create` and `bulk_delete` for efficiency
- **Batch Processing**: Respects batch size settings for memory management
- **Individual Fallback**: Falls back to individual operations if bulk fails
- **Transaction Safety**: Each batch is processed in transactions

### Error Handling

- **Enterprise Error Reporting**: Integrates with existing error handling system
- **Individual Record Errors**: Continues processing if single records fail
- **Bulk Operation Failures**: Falls back to individual operations
- **Detailed Logging**: Provides comprehensive logging of force overwrite operations

## Safety Features

### User Warnings
- **Console Warnings**: Clear warnings about data replacement when using force overwrite
- **Dry Run Support**: Test force overwrite operations without making changes
- **Detailed Reporting**: Shows exactly how many records were created vs overwritten

### Data Protection
- **Explicit Flag Required**: Force overwrite requires explicit `--force-overwrite` flag
- **Transaction Safety**: Operations are wrapped in database transactions
- **Error Recovery**: Detailed error logging and fallback mechanisms

## Extending to Other Entities

This pattern can be applied to other HubSpot entities (deals, companies, etc.) by:

1. **Adding force_overwrite parameter** to the entity's sync engine constructor
2. **Implementing _force_overwrite_[entity]** and **_individual_force_save_[entity]** methods
3. **Updating save_data method** to check force_overwrite flag
4. **Using the same delete-and-recreate pattern**

### Template for New Entities

```python
class HubSpot[Entity]SyncEngine(HubSpotBaseSyncEngine):
    def __init__(self, **kwargs):
        super().__init__('[entity]', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        if self.force_overwrite:
            return await self._force_overwrite_[entity](validated_data)
        else:
            return await self._normal_save_[entity](validated_data)
```

## Migration from Old Commands

Existing HubSpot sync commands can be gradually migrated to use this new architecture:

1. **Immediate**: Use `--force-overwrite` flag with existing new-architecture commands
2. **Short-term**: Migrate remaining entities to new architecture
3. **Long-term**: Deprecate old command patterns

## Testing

The implementation includes comprehensive testing capabilities:

- **Dry Run Mode**: Test operations without database changes
- **Batch Size Control**: Test with different batch sizes
- **Record Limits**: Test with `--max-records` for small-scale testing
- **Debug Mode**: Verbose logging for troubleshooting

This implementation provides a robust, safe, and performant solution for complete data replacement in HubSpot sync operations while maintaining compatibility with existing sync patterns.
