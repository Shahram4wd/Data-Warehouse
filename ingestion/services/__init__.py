# CRM Dashboard Services

# Import non-Django dependent services immediately
from .worker_pool import get_worker_pool, WorkerPoolService, TaskStatus

# Django-dependent imports will be lazy-loaded when needed
def get_schedule_sync_functions():
    """Lazy import for Django-dependent schedule sync functions"""
    from .schedule_sync import sync_periodic_task, delete_periodic_task
    return sync_periodic_task, delete_periodic_task

def get_ingestion_adapter_functions():
    """Lazy import for Django-dependent ingestion adapter functions"""
    from .ingestion_adapter import run_source_ingestion, get_available_sources, get_available_modes, validate_source_mode
    return run_source_ingestion, get_available_sources, get_available_modes, validate_source_mode

__all__ = [
    'get_schedule_sync_functions',
    'get_ingestion_adapter_functions',
    'get_worker_pool',
    'WorkerPoolService',
    'TaskStatus',
]