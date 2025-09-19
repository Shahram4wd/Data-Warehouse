from __future__ import absolute_import, unicode_literals
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')

app = Celery('data_warehouse')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Configure periodic tasks only for production environment
# Check if we're in production using existing DJANGO_ENV variable
DJANGO_ENV = os.environ.get('DJANGO_ENV', 'development')

if DJANGO_ENV == 'production':
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
    }
else:
    # Limited scheduled tasks for local development
    app.conf.beat_schedule = {
        'worker-pool-monitor': {
            'task': 'ingestion.tasks.worker_pool_monitor',
            'schedule': crontab(minute='*/5'),  # Every 5 minutes in development
        },
    }

app.conf.timezone = 'UTC'