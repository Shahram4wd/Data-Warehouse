from django.core.management.base import BaseCommand
from django.conf import settings
import redis
from celery import Celery
import os


class Command(BaseCommand):
    help = 'Test Redis connection and Celery configuration'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fix-url',
            action='store_true',
            help='Attempt to fix Redis URL format for Render.com',
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('Testing Redis and Celery configuration...'))
        
        # Display current configuration
        broker_url = getattr(settings, 'CELERY_BROKER_URL', 'Not configured')
        result_backend = getattr(settings, 'CELERY_RESULT_BACKEND', 'Not configured')
        
        self.stdout.write(f"CELERY_BROKER_URL: {broker_url}")
        self.stdout.write(f"CELERY_RESULT_BACKEND: {result_backend}")
        
        # Check environment variables
        env_broker = os.getenv('CELERY_BROKER_URL', 'Not set')
        env_result = os.getenv('CELERY_RESULT_BACKEND', 'Not set')
        
        self.stdout.write(f"ENV CELERY_BROKER_URL: {env_broker}")
        self.stdout.write(f"ENV CELERY_RESULT_BACKEND: {env_result}")
        
        # Test Redis connection
        try:
            # Try to parse Redis URL
            if broker_url.startswith('redis://'):
                # Extract connection info
                redis_url = broker_url
                self.stdout.write(f"Attempting Redis connection to: {redis_url}")
                
                # Test direct Redis connection
                r = redis.from_url(redis_url)
                r.ping()
                self.stdout.write(self.style.SUCCESS('✓ Redis connection successful'))
                
                # Test Redis info
                info = r.info()
                self.stdout.write(f"Redis version: {info.get('redis_version', 'Unknown')}")
                self.stdout.write(f"Redis memory used: {info.get('used_memory_human', 'Unknown')}")
                
            else:
                self.stdout.write(self.style.ERROR(f'Invalid Redis URL format: {broker_url}'))
                
        except redis.ConnectionError as e:
            self.stdout.write(self.style.ERROR(f'✗ Redis connection failed: {e}'))
            
            if 'redis:6379' in str(e) and options['fix_url']:
                self.stdout.write('Attempting to suggest fix for Render.com...')
                self.stdout.write('You need to update your environment variables to use:')
                self.stdout.write('CELERY_BROKER_URL=$REDIS_URL')
                self.stdout.write('CELERY_RESULT_BACKEND=$REDIS_URL')
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Unexpected error: {e}'))
        
        # Test Celery app initialization
        try:
            from data_warehouse.celery import app
            self.stdout.write(f"Celery app broker: {app.conf.broker_url}")
            self.stdout.write(f"Celery app result backend: {app.conf.result_backend}")
            self.stdout.write(self.style.SUCCESS('✓ Celery app initialized successfully'))
            
            # Test Celery broker connection
            inspect = app.control.inspect()
            stats = inspect.stats()
            if stats:
                self.stdout.write(self.style.SUCCESS('✓ Celery broker connection successful'))
                self.stdout.write(f"Active workers: {list(stats.keys())}")
            else:
                self.stdout.write(self.style.WARNING('⚠ No active Celery workers found'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Celery initialization failed: {e}'))
        
        # Test django-celery-beat
        try:
            from django_celery_beat.models import PeriodicTask
            task_count = PeriodicTask.objects.count()
            self.stdout.write(f"Periodic tasks in database: {task_count}")
            
            # Show any tasks that might be problematic
            if task_count > 0:
                enabled_tasks = PeriodicTask.objects.filter(enabled=True)
                self.stdout.write(f"Enabled periodic tasks: {enabled_tasks.count()}")
                
                for task in enabled_tasks[:5]:  # Show first 5
                    self.stdout.write(f"  - {task.name}: {task.task} (interval: {task.interval})")
                    
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'✗ Django-celery-beat check failed: {e}'))
        
        self.stdout.write(self.style.SUCCESS('Redis and Celery configuration test completed.'))
