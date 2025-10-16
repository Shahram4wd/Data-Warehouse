from __future__ import absolute_import, unicode_literals
import os

# Graceful import of Celery for development environments
try:
    from celery import Celery
    from celery.schedules import crontab
    CELERY_AVAILABLE = True
except ImportError:
    # Celery not available in development - create mock objects
    import logging
    logging.getLogger(__name__).warning("Celery not available - running without Celery support")
    
    class MockCelery:
        def __init__(self, *args, **kwargs):
            pass
        def config_from_object(self, *args, **kwargs):
            pass
        def autodiscover_tasks(self, *args, **kwargs):
            pass
        @property
        def conf(self):
            return MockConf()
    
    class MockConf:
        def __init__(self):
            self.beat_schedule = {}
            self.timezone = 'UTC'
    
    class MockCrontab:
        def __init__(self, *args, **kwargs):
            pass
    
    Celery = MockCelery
    crontab = MockCrontab
    CELERY_AVAILABLE = False

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')

# Only configure Celery if it's available
if CELERY_AVAILABLE:
    app = Celery('data_warehouse')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    
    # Force configuration for worker concurrency and memory limits
    from decouple import config
    
    # Concurrency and memory protection settings
    app.conf.worker_concurrency = config('CELERY_WORKER_CONCURRENCY', default=2, cast=int)
    app.conf.worker_prefetch_multiplier = 1
    app.conf.task_acks_late = True
    app.conf.task_reject_on_worker_lost = True
    app.conf.worker_max_memory_per_child = 300_000  # ~300MB in KB
    app.conf.worker_max_tasks_per_child = 50
    app.conf.task_time_limit = 1800  # 30 minutes hard limit
    app.conf.task_soft_time_limit = 1500  # 25 minutes soft limit

    # Force discovery of tasks from Django apps
    from django.conf import settings
    app.autodiscover_tasks(lambda: settings.INSTALLED_APPS)

    # Tasks will be auto-discovered, no need for explicit imports that cause circular dependencies
    # The autodiscover_tasks call above will handle loading tasks when Django is ready

    # Configure periodic tasks only for production environment
    # Check if we're in production using existing DJANGO_ENV variable
    DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')
else:
    # Create mock app for development
    app = Celery('data_warehouse')
    DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

if CELERY_AVAILABLE and DJANGO_ENV == 'production':
    # Use smart scheduler that respects environment gates
    try:
        from ingestion.services.smart_scheduler import get_smart_beat_schedule
        app.conf.beat_schedule = get_smart_beat_schedule('production')
    except ImportError:
        # Fallback to basic schedule if smart scheduler not available
        app.conf.beat_schedule = {
            'generate-automation-reports-afternoon': {
                'task': 'ingestion.tasks.generate_automation_reports',
                'schedule': crontab(hour=16, minute=0),  # 4:00 PM UTC daily
            },
            'generate-automation-reports-morning': {
                'task': 'ingestion.tasks.generate_automation_reports',
                'schedule': crontab(hour=4, minute=0),   # 4:00 AM UTC daily
            },
            'worker-pool-monitor': {
                'task': 'ingestion.tasks.worker_pool_monitor',
                'schedule': crontab(minute='*/2'),  # Every 2 minutes
            },
            'cleanup-stale-syncs-0330utc': {
                'task': 'ingestion.tasks.cleanup_stale_syncs',
                'schedule': crontab(hour=3, minute=30),  # 03:30 UTC nightly
            },
        }
elif CELERY_AVAILABLE:
    # Limited scheduled tasks for local development
    try:
        from ingestion.services.smart_scheduler import get_smart_beat_schedule
        app.conf.beat_schedule = get_smart_beat_schedule('development')
    except ImportError:
        # Fallback to basic schedule if smart scheduler not available
        app.conf.beat_schedule = {
            'worker-pool-monitor': {
                'task': 'ingestion.tasks.worker_pool_monitor',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes in development
            },
            'cleanup-stale-syncs-0330utc': {
                'task': 'ingestion.tasks.cleanup_stale_syncs',
                'schedule': crontab(hour=3, minute=30),  # 03:30 UTC nightly (dev)
            },
        }

if CELERY_AVAILABLE:
    app.conf.timezone = 'UTC'