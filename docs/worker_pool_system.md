# Worker Pool System Documentation

## Overview

The Worker Pool System is a comprehensive task management solution that provides controlled execution of Celery sync tasks with configurable worker limits. It ensures that only a specified number of sync operations can run simultaneously, while queuing additional tasks until workers become available.

This system provides intelligent task queuing and worker management for CRM synchronization operations, with robust state management, monitoring, and recovery capabilities.

## Key Features

### 1. Configurable Worker Limits
- Set maximum concurrent workers via `MAX_SYNC_WORKERS` environment variable
- Default: 2 workers (balanced performance)
- Range: 1-10 workers recommended based on infrastructure

### 2. Intelligent Task Queuing
- Tasks exceeding worker limits are automatically queued
- Priority-based queue ordering
- Automatic processing when workers become available
- Persistent queue state using Redis cache

### 3. Task Status Monitoring
- Real-time tracking of task states (queued, running, completed, failed, cancelled)
- Integration with Celery task status
- Heartbeat monitoring for stale task detection
- Automatic cleanup of completed tasks

### 4. Dashboard Integration
- Visual worker pool status display
- Queue management interface
- Real-time updates every 2 seconds
- Worker utilization indicators

### 5. CLI Management
- Comprehensive command-line tools for monitoring and configuration
- JSON output support for automation
- Continuous monitoring mode
- Emergency recovery operations

### 6. Robust Error Handling
- Graceful degradation during system failures
- Automatic stale task cleanup
- Cache failure fallbacks
- Comprehensive error logging

## System Architecture

### Core Components

#### 1. WorkerPoolService (`ingestion/services/worker_pool.py`)
The central orchestrator that manages:
- Task lifecycle from submission to completion
- Worker allocation and queuing logic
- State persistence using Django cache (Redis)
- Integration with Celery for actual task execution

#### 2. Enhanced Task Decorators (`ingestion/tasks_enhanced.py`)
Enhanced Celery tasks that integrate with the worker pool:
- Automatic status reporting to worker pool
- Proper error handling and cleanup
- Heartbeat updates for monitoring
- Integration with existing sync commands

#### 3. Worker Pool Monitor Task (`ingestion/tasks.py`)
Scheduled maintenance task that runs every 2-5 minutes:
- Checks Celery task statuses
- Cleans up stale active tasks
- Processes pending queue items
- Updates task heartbeats

#### 4. Management Command (`ingestion/management/commands/manage_worker_pool.py`)
CLI interface providing:
- Real-time status monitoring
- Configuration management
- Task cancellation and queue management
- Debugging and troubleshooting tools

## Configuration

### Environment Variables

Add to your `.env` file:

```bash
# Worker Pool Configuration
MAX_SYNC_WORKERS=2                    # Maximum concurrent sync workers
WORKER_POOL_STALE_MINUTES=30         # Stale task timeout in minutes

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
CELERY_TASK_DEFAULT_QUEUE=dw-production  # or dw-local for development
```

### Django Settings Integration

Located in `data_warehouse/settings.py`:

```python
# Worker Pool Configuration
MAX_SYNC_WORKERS = config('MAX_SYNC_WORKERS', default=2, cast=int)
WORKER_POOL_STALE_MINUTES = config('WORKER_POOL_STALE_MINUTES', default=30, cast=int)

# Environment-based queue routing
if DJANGO_ENV == 'production':
    CELERY_TASK_DEFAULT_QUEUE = config('CELERY_TASK_DEFAULT_QUEUE', default='dw-production')
    CELERY_TASK_ROUTES = {
        'ingestion.tasks.*': {'queue': 'dw-production'},
    }
else:
    CELERY_TASK_DEFAULT_QUEUE = 'dw-local'
    CELERY_TASK_ROUTES = {
        'ingestion.tasks.*': {'queue': 'dw-local'},
    }
```

### Celery Beat Schedule

Defined in `data_warehouse/celery.py`:

```python
# Production Schedule
app.conf.beat_schedule = {
    'worker-pool-monitor': {
        'task': 'ingestion.tasks.worker_pool_monitor',
        'schedule': crontab(minute='*/2'),  # Every 2 minutes
    },
    'cleanup-stale-syncs-0330utc': {
        'task': 'ingestion.tasks.cleanup_stale_syncs',
        'schedule': crontab(hour=3, minute=30),  # 03:30 UTC nightly
    },
    # Additional scheduled tasks...
}
```

## Data Structures and State Management

### WorkerTask Data Model

```python
@dataclass
class WorkerTask:
    id: str                          # Unique task identifier
    task_name: str                   # Celery task name (e.g., 'ingestion.tasks.sync_five9_contacts')
    crm_source: str                  # CRM source ('five9', 'genius', 'hubspot', etc.)
    sync_type: str                   # Sync operation type ('contacts', 'all', etc.)
    parameters: Dict[str, Any]       # Task-specific parameters
    status: TaskStatus               # Current task status
    priority: int = 0                # Task priority (higher = processed first)
    queued_at: datetime = None       # When task was submitted
    started_at: datetime = None      # When task execution began
    completed_at: datetime = None    # When task finished
    celery_task_id: str = None      # Associated Celery task ID
    error_message: str = None        # Error details if failed
    last_heartbeat: datetime = None  # Last status update timestamp
```

### TaskStatus Enumeration

```python
class TaskStatus(Enum):
    QUEUED = "queued"        # Waiting for worker
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed
    CANCELLED = "cancelled"  # Manually cancelled
```

### Cache-based State Persistence

The system uses Django cache (Redis) for state persistence:

```python
# Cache Keys
ACTIVE_WORKERS_KEY = "worker_pool:active_workers"    # Currently running tasks
TASK_QUEUE_KEY = "worker_pool:task_queue"           # Pending tasks
WORKER_STATS_KEY = "worker_pool:stats"              # Statistics cache
```

**State Serialization:**
- Tasks serialized to JSON-compatible dictionaries
- DateTime objects converted to ISO format strings
- Enum values stored as string representations
- Automatic deserialization with backward compatibility

## Task Lifecycle Management

### 1. Task Submission
Tasks are submitted through various interfaces and processed through the worker pool:

**Process:**
1. Validate and normalize input parameters
2. Generate unique task ID using UUID
3. Map CRM source/sync type to Celery task name
4. Create WorkerTask instance
5. Check worker availability:
   - If workers available: Start immediately
   - If at capacity: Add to priority queue
6. Persist state to cache

### 2. Task Execution
When a worker becomes available, tasks are started:

**Process:**
1. Update task status to RUNNING
2. Set started_at timestamp and heartbeat
3. Submit to Celery using `current_app.send_task()`
4. Store Celery task ID for tracking
5. Add to active_workers dictionary
6. Persist updated state

### 3. Status Monitoring
Multiple monitoring mechanisms ensure task health:

- Enhanced tasks automatically report status changes
- Periodic monitor task checks Celery status
- Heartbeat tracking detects stale tasks
- Automatic cleanup of completed tasks

### 4. Task Completion
**Automatic Completion:**
1. Enhanced tasks report completion status
2. Monitor task checks Celery status
3. Task moved from active_workers
4. Associated SyncHistory updated
5. Next queued task processed

## Task Mapping and Routing

### CRM Task Mappings

```python
self.task_mappings = {
    ('five9', 'contacts'): 'ingestion.tasks.sync_five9_contacts',
    ('genius', 'marketsharp_contacts'): 'ingestion.tasks.sync_genius_marketsharp_contacts',
    ('hubspot', 'all'): 'ingestion.tasks.sync_hubspot_all',
    ('genius', 'all'): 'ingestion.tasks.sync_genius_all',
    ('arrivy', 'all'): 'ingestion.tasks.sync_arrivy_all',
}
```

**Fallback Strategy:**
```python
# If no mapping found, generate fallback task name
task_name = f"ingestion.tasks.sync_{crm_source}_{sync_type}"
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

- **Celery Beat Integration**: Periodic status checks every 2 minutes in production
- **Real-time Updates**: Dashboard updates every 2 seconds
- **Status Synchronization**: Automatic Celery task status checking
- **Stale Task Detection**: Tasks without heartbeat updates are marked as failed

### Advanced Monitoring

**Continuous Monitoring:**
```bash
python manage.py manage_worker_pool monitor --continuous --interval 2
```

**Output:**
```
[2025-09-29 15:30:45] Worker Pool Status:
  Max Workers: 2
  Active: 1/2 (50%)
  Queued: 3 tasks
  
Active Tasks:
  - Task abc123: genius.all (running for 2m 15s)
  
Queued Tasks:
  - Task def456: five9.contacts (priority: 0)
  - Task ghi789: hubspot.all (priority: 1)
  - Task jkl012: arrivy.all (priority: 0)
```

## Error Handling and Recovery

### Error Categories

**1. Task Execution Errors:**
- Handled by enhanced task decorators
- Status updated to FAILED with error message
- Worker immediately freed for next task

**2. System Errors:**
- Cache failures: Fallback to in-memory state
- Celery disconnections: Detected by monitor task
- Invalid task data: Gracefully skipped during deserialization

**3. Stale Task Detection:**
- Tasks without heartbeat updates
- Automatically marked as FAILED after timeout (default: 30 minutes)
- Prevents phantom active tasks in dashboard

### Recovery Mechanisms

**State Recovery:**
- Handle corrupt task data gracefully
- Skip invalid entries with warnings
- Maintain system operation during failures

**Automatic Cleanup:**
- Scheduled cleanup of stale syncs (nightly at 03:30 UTC)
- Clean up old SyncHistory records
- Remove orphaned worker pool references

### System Failures

- Cache failures fall back to in-memory storage
- Missing tasks are handled gracefully
- Celery disconnections are detected and handled

### Recovery

- System state is persisted in cache
- Automatic recovery on service restart
- Manual queue processing available

## Performance Considerations

### Worker Scaling Guidelines

| Setup Type | Recommended Workers | Notes |
|------------|-------------------|--------|
| Development | 1 | Safe for local testing |
| Small Production | 1-2 | Single server, limited resources |
| Medium Production | 2-3 | Dedicated database, good resources |
| Large Production | 3-5 | High-performance infrastructure |

### Resource Considerations
- Database connection pool limits
- Memory usage per sync operation
- External API rate limits
- I/O bottlenecks

### Resource Impact

- Each worker consumes database connections
- External API rate limits may apply
- Memory usage increases with concurrent tasks

### Optimization Tips

1. **Start Conservative**: Begin with 1 worker and increase gradually
2. **Monitor Resources**: Watch database connections and memory usage
3. **Check Rate Limits**: Ensure external APIs can handle the load
4. **Use Priorities**: Set higher priority for critical syncs
5. **Schedule Wisely**: Avoid peak hours for heavy operations

### Cache Optimization

**State Persistence:**
- Use Redis for production (persistent)
- Cache timeouts: 1 hour (auto-renewal)
- Optimize serialization for large queues

**Memory Management:**
- Automatic cleanup prevents memory bloat
- Configurable retention period (default: 60 minutes)
- Efficient task serialization

## Troubleshooting

### Common Issues and Solutions

**1. Tasks Stuck in Queue**
```bash
# Diagnosis
python manage.py manage_worker_pool status --verbose

# Check worker availability
python manage.py manage_worker_pool list-tasks

# Manual queue processing
python manage.py manage_worker_pool process-queue
```

**2. High Memory Usage**
```bash
# Check active task count
python manage.py manage_worker_pool status

# Reduce max workers if needed
python manage.py manage_worker_pool config --max-workers 1

# Force cleanup
python manage.py manage_worker_pool fix-stuck
```

**3. Stale Task Detection**
```bash
# Check for stale tasks
python manage.py manage_worker_pool monitor

# Manual stale cleanup
python manage.py cleanup_stale_syncs --minutes 15
```

**4. Cache Issues**
```bash
# Check Redis connectivity
redis-cli ping

# Reset worker pool state (emergency)
python -c "from django.core.cache import cache; cache.clear()"
```

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

# Fix stuck tasks automatically
python manage.py manage_worker_pool fix-stuck
```

### Log Locations

- Worker pool operations: `logs/ingestion.log`
- Celery task execution: `logs/celery.log`
- General application logs: `logs/general.log`
- Sync engine specific logs: `logs/sync_engines.log`

### Debug Logging

Enable verbose logging for troubleshooting:
```python
# settings.py
LOGGING = {
    'loggers': {
        'ingestion.services.worker_pool': {
            'level': 'DEBUG',
            'handlers': ['file'],
        },
    },
}
```

## Security Considerations

### Data Protection

**Sensitive Information:**
- Task parameters sanitized in logs
- No credentials stored in task state
- Error messages filtered for safety

**Access Control:**
- CLI requires Django application access
- API endpoints protected by CSRF tokens
- Cache data isolated by application

### Audit Trail

- Comprehensive logging at key events
- Task submission and completion tracking
- Configuration change logging
- Error condition monitoring

## Integration with Existing Systems

### CRM Dashboard

- Seamless integration with existing sync management
- Enhanced UI with worker pool status
- Backward compatible with existing workflows
- Real-time status updates

### Celery

- Works with existing Celery configuration
- Maintains task routing and queues
- Automatic task status synchronization
- Enhanced task decorators for integration

### SyncHistory Integration

The worker pool integrates with the existing SyncHistory model:
- Automatic status updates based on task completion
- Worker pool task IDs stored in configuration
- End time and error message updates
- Persistent tracking across system restarts

### Monitoring Systems

- JSON API output for external monitoring
- Status metrics for alerting systems
- Performance data for capacity planning
- CLI tools for automation

## Deployment Considerations

### Production Setup

**Infrastructure Requirements:**
- Redis instance for cache storage
- Celery workers running continuously
- Celery beat scheduler for monitoring
- Adequate database connection pool

**Configuration Checklist:**
- [ ] `MAX_SYNC_WORKERS` set appropriately (start with 2)
- [ ] `WORKER_POOL_STALE_MINUTES` configured (default: 30)
- [ ] Redis cache configured and accessible
- [ ] Celery broker and result backend configured
- [ ] Proper queue routing (production vs development)
- [ ] Monitoring tasks scheduled in beat

### Development Setup

**Local Development:**
- Use lower worker counts (1-2)
- Separate queue names (`dw-local`)
- More frequent monitoring (every 5 minutes)
- Memory fallback for cache if Redis unavailable

### Docker Deployment

The system integrates with existing Docker setup:
```yaml
# docker-compose.yml includes:
# - Redis service for cache
# - Celery worker containers
# - Celery beat scheduler
# - Web application with worker pool
```

## Emergency Procedures

### Complete System Reset
```bash
# 1. Stop all Celery workers
sudo systemctl stop celery-worker

# 2. Clear worker pool state
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 3. Clean up database
python manage.py cleanup_stale_syncs --minutes 0

# 4. Restart services
sudo systemctl start celery-worker
sudo systemctl restart celery-beat
```

### Recover from Stuck State
```bash
# 1. Identify stuck tasks
python manage.py manage_worker_pool list-tasks --verbose

# 2. Cancel problem tasks
python manage.py manage_worker_pool cancel --task-id <task-id>

# 3. Fix stuck tasks automatically
python manage.py manage_worker_pool fix-stuck

# 4. Reset max workers if needed
python manage.py manage_worker_pool config --max-workers 1
```

## Integration Examples

### Custom Task Submission
```python
# Submit custom task to worker pool
from ingestion.services.worker_pool import get_worker_pool

def submit_custom_sync(crm_source, sync_type, **params):
    worker_pool = get_worker_pool()
    task_id = worker_pool.submit_task(
        crm_source=crm_source,
        sync_type=sync_type,
        parameters=params,
        priority=1  # Higher priority
    )
    print(f"Submitted task: {task_id}")
    return task_id
```

### Status Monitoring
```python
# Monitor specific task
from ingestion.services.worker_pool import get_worker_pool
import time

def monitor_task(task_id):
    worker_pool = get_worker_pool()
    
    while True:
        task = worker_pool.get_task_status(task_id)
        if not task:
            print("Task not found")
            break
            
        print(f"Task {task_id}: {task.status.value}")
        
        if task.status in ['completed', 'failed', 'cancelled']:
            break
            
        time.sleep(5)
```

## Future Enhancements

### Planned Improvements

**Enhanced Monitoring:**
- Detailed performance metrics
- Resource utilization tracking
- Predictive queue management

**Advanced Features:**
- Task dependencies and workflows
- Multi-tenant worker pools
- Resource-aware scheduling
- Dynamic worker scaling

**API Enhancements:**
- GraphQL endpoints
- Webhook notifications
- Bulk operations
- Advanced filtering

### Extensibility Points

**Custom Task Types:**
- Extend task mappings for new CRM sources
- Implement custom priority algorithms
- Add specialized monitoring logic

**Integration Opportunities:**
- External monitoring systems
- Alerting and notification services
- Performance analytics platforms
- Workflow orchestration tools

## Key Files and Components

### Core Files
- **Core Service**: `ingestion/services/worker_pool.py`
- **Enhanced Tasks**: `ingestion/tasks_enhanced.py`
- **CLI Command**: `ingestion/management/commands/manage_worker_pool.py`
- **Configuration**: `data_warehouse/settings.py`
- **Monitoring**: `ingestion/tasks.py` (worker_pool_monitor)

### Documentation
- **This Guide**: `docs/worker_pool_system.md`
- **Technical Guide**: `docs/celery_worker_pool_technical_guide.md`
- **Architecture**: `docs/worker_pool_architecture.md`
- **Quick Reference**: `docs/worker_pool_quick_reference.md`

## Conclusion

The Celery Worker Pool System provides a robust, scalable solution for managing CRM synchronization tasks. Its design emphasizes reliability, monitoring, and operational simplicity while providing the flexibility needed for various deployment scenarios.

Key benefits:
- **Controlled Concurrency**: Prevents resource exhaustion through configurable worker limits
- **Intelligent Queuing**: Ensures optimal task execution order with priority-based processing
- **Comprehensive Monitoring**: Real-time visibility into system state with automatic health checks
- **Robust Error Handling**: Graceful recovery from failures with automatic cleanup
- **Easy Management**: CLI and GUI interfaces for operations and troubleshooting
- **Production Ready**: Battle-tested with comprehensive logging and recovery mechanisms

The system is production-ready and continues to evolve with new features and optimizations based on operational experience and user feedback.