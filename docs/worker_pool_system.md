# Worker Pool System Documentation

## Overview

The Worker Pool System is a comprehensive task management solution that provides controlled execution of Celery sync tasks with configurable worker limits. It ensures that only a specified number of sync operations can run simultaneously, while queuing additional tasks until workers become available.

## Key Features

### 1. Configurable Worker Limits
- Set maximum concurrent workers via `MAX_SYNC_WORKERS` environment variable
- Default: 1 worker (sequential processing)
- Range: 1-10 workers recommended

### 2. Intelligent Task Queuing
- Tasks exceeding worker limits are automatically queued
- Priority-based queue ordering
- Automatic processing when workers become available

### 3. Task Status Monitoring
- Real-time tracking of task states (queued, running, completed, failed)
- Integration with Celery task status
- Automatic cleanup of completed tasks

### 4. Dashboard Integration
- Visual worker pool status display
- Queue management interface
- Real-time updates every 2 seconds

### 5. CLI Management
- Command-line tools for monitoring and configuration
- JSON output support for automation

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Maximum number of concurrent sync workers
MAX_SYNC_WORKERS=1
```

### Settings

The system automatically configures itself based on the environment variable:

```python
# In settings.py
MAX_SYNC_WORKERS = config('MAX_SYNC_WORKERS', default=1, cast=int)
```

## Usage

### Via CRM Dashboard

1. **Submit Tasks**: Use the existing sync interface - tasks automatically go through the worker pool
2. **Monitor Status**: View worker pool status, active tasks, and queue in the dashboard
3. **Configure Workers**: Use the worker pool configuration modal
4. **Process Queue**: Manually trigger queue processing if needed

### Via Management Command

```bash
# Check status
python manage.py manage_worker_pool status

# Set max workers
python manage.py manage_worker_pool config --max-workers 2

# Monitor continuously
python manage.py manage_worker_pool monitor --continuous --interval 5

# Process queue manually
python manage.py manage_worker_pool process-queue

# Cancel a task
python manage.py manage_worker_pool cancel --task-id <task-id>

# List all tasks
python manage.py manage_worker_pool list-tasks --verbose
```

### Via API

```bash
# Get worker pool status
curl http://localhost:8000/ingestion/crm-dashboard/api/worker-pool/status/

# Submit a sync task
curl -X POST http://localhost:8000/ingestion/crm-dashboard/api/worker-pool/submit/ \
  -H "Content-Type: application/json" \
  -d '{"crm_source": "five9", "sync_type": "contacts", "parameters": {}, "priority": 0}'

# Update configuration
curl -X POST http://localhost:8000/ingestion/crm-dashboard/api/worker-pool/config/ \
  -H "Content-Type: application/json" \
  -d '{"max_workers": 2}'
```

## Architecture

### Components

1. **WorkerPoolService**: Core service managing worker allocation and queuing
2. **WorkerTask**: Data structure representing individual tasks
3. **TaskStatus**: Enum for task states
4. **API Views**: REST endpoints for frontend integration
5. **Management Command**: CLI interface
6. **JavaScript Integration**: Frontend worker pool management

### Task Lifecycle

1. **Submission**: Task submitted via dashboard, API, or direct call
2. **Queuing**: If workers available, start immediately; otherwise, queue
3. **Execution**: Task runs in Celery worker, status tracked
4. **Completion**: Task completes/fails, worker freed, next task processed
5. **Cleanup**: Completed tasks cleaned up after timeout

### Data Storage

- **Active Workers**: Stored in Django cache (Redis)
- **Task Queue**: Stored in Django cache (Redis)
- **Statistics**: Real-time calculation from current state

## Task Types

### Supported Sync Tasks

- `five9.contacts`: Five9 contact synchronization
- `genius.marketsharp_contacts`: MarketSharp contact sync
- `hubspot.all`: HubSpot data synchronization
- `genius.all`: All Genius CRM data
- `arrivy.all`: Arrivy data synchronization

### Task Parameters

```python
{
    "crm_source": "five9",      # CRM source identifier
    "sync_type": "contacts",    # Type of sync operation
    "parameters": {             # Sync-specific parameters
        "full": False,          # Full vs incremental sync
        "batch_size": 1000,     # Processing batch size
        "dry_run": False        # Dry run mode
    },
    "priority": 0               # Task priority (higher = higher priority)
}
```

## Monitoring

### Dashboard Metrics

- **Active Count**: Currently running workers
- **Queued Count**: Tasks waiting in queue
- **Available Workers**: Free worker slots
- **Worker Utilization**: Visual progress bar

### Status Indicators

- 🟢 **Available**: Workers ready for new tasks
- 🟡 **Busy**: All workers occupied
- 🔴 **Overloaded**: Queue building up

### Automatic Monitoring

- **Celery Beat Integration**: Periodic status checks every 2-5 minutes
- **Real-time Updates**: Dashboard updates every 2 seconds
- **Status Synchronization**: Automatic Celery task status checking

## Error Handling

### Task Failures

- Failed tasks are marked with error status
- Error messages are captured and displayed
- Worker is immediately freed for next task

### System Failures

- Cache failures fall back to in-memory storage
- Missing tasks are handled gracefully
- Celery disconnections are detected and handled

### Recovery

- System state is persisted in cache
- Automatic recovery on service restart
- Manual queue processing available

## Performance Considerations

### Worker Limits

- **1 Worker**: Safest for most setups, prevents resource contention
- **2-3 Workers**: Good for medium setups with adequate resources
- **4+ Workers**: Only for high-performance infrastructure

### Resource Impact

- Each worker consumes database connections
- External API rate limits may apply
- Memory usage increases with concurrent tasks

### Optimization Tips

1. Start with 1 worker and monitor performance
2. Gradually increase workers if resources allow
3. Monitor database connection pool usage
4. Watch for API rate limit errors
5. Use priority settings for important tasks

## Troubleshooting

### Common Issues

1. **Tasks Stuck in Queue**: Check if workers are running
2. **High Memory Usage**: Reduce max workers
3. **Database Timeouts**: Lower worker count
4. **API Rate Limits**: Implement delays or reduce concurrency

### Debug Commands

```bash
# Check worker pool status
python manage.py manage_worker_pool status --verbose

# Monitor in real-time
python manage.py manage_worker_pool monitor --continuous

# Check specific task
python manage.py manage_worker_pool list-tasks --json

# View Celery worker status
celery -A data_warehouse inspect active
```

### Log Locations

- Worker pool logs: `logs/ingestion.log`
- Celery task logs: `logs/celery.log`
- General application logs: `logs/general.log`

## Security Considerations

- API endpoints require CSRF tokens
- No sensitive data in task parameters
- Cache data has appropriate timeouts
- Error messages don't expose internals

## Integration with Existing Systems

### CRM Dashboard

- Seamless integration with existing sync management
- Enhanced UI with worker pool status
- Backward compatible with existing workflows

### Celery

- Works with existing Celery configuration
- Maintains task routing and queues
- Automatic task status synchronization

### Monitoring Systems

- JSON API output for external monitoring
- Status metrics for alerting systems
- Performance data for capacity planning

## Future Enhancements

### Planned Features

- Task scheduling and recurring tasks
- Resource-based worker allocation
- Advanced priority algorithms
- Detailed performance metrics
- Multi-tenant worker pools

### API Improvements

- GraphQL endpoint for complex queries
- Webhook notifications for task completion
- Bulk task submission
- Task dependency management