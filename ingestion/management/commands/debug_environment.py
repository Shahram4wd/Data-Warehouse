from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Display current environment configuration for debugging Redis connection issues'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS('=== Environment Configuration Debug ==='))
        
        # Show all Redis-related environment variables
        redis_vars = [
            'CELERY_BROKER_URL',
            'CELERY_RESULT_BACKEND',
            'REDIS_URL',
            'DATABASE_URL',
            'DJANGO_SECRET_KEY'
        ]
        
        self.stdout.write('\n🔧 Environment Variables:')
        for var in redis_vars:
            value = os.getenv(var, 'NOT SET')
            if 'SECRET' in var or 'PASSWORD' in var:
                # Mask sensitive values
                if value != 'NOT SET':
                    value = f"{value[:10]}...{value[-4:]}" if len(value) > 14 else "***MASKED***"
            elif 'DATABASE_URL' in var:
                # Mask database password
                if value != 'NOT SET' and 'postgres://' in value:
                    import re
                    value = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', value)
            
            self.stdout.write(f"  {var}: {value}")
        
        # Show Django settings
        self.stdout.write('\n⚙️  Django Settings:')
        celery_broker = getattr(settings, 'CELERY_BROKER_URL', 'NOT SET')
        celery_result = getattr(settings, 'CELERY_RESULT_BACKEND', 'NOT SET')
        
        # Mask sensitive parts of URLs
        if celery_broker != 'NOT SET' and '://' in celery_broker:
            import re
            celery_broker = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', celery_broker)
        if celery_result != 'NOT SET' and '://' in celery_result:
            import re
            celery_result = re.sub(r'://([^:]+):([^@]+)@', r'://\1:***@', celery_result)
            
        self.stdout.write(f"  CELERY_BROKER_URL: {celery_broker}")
        self.stdout.write(f"  CELERY_RESULT_BACKEND: {celery_result}")
        
        # Check if Redis hostname is hardcoded
        if 'redis:6379' in celery_broker or 'redis:6379' in celery_result:
            self.stdout.write(self.style.ERROR('\n❌ PROBLEM DETECTED:'))
            self.stdout.write('  Redis is using hardcoded hostname "redis:6379"')
            self.stdout.write('  This will not work on Render.com')
            
            self.stdout.write(self.style.WARNING('\n🔧 SOLUTION:'))
            self.stdout.write('  1. Ensure render.yaml has been deployed with Redis service configuration')
            self.stdout.write('  2. Check that Redis service is running in Render dashboard')
            self.stdout.write('  3. Verify environment variables are properly set from Redis service')
            
        # Show Render-specific information
        render_info = {
            'RENDER_SERVICE_ID': os.getenv('RENDER_SERVICE_ID', 'NOT SET'),
            'RENDER_SERVICE_NAME': os.getenv('RENDER_SERVICE_NAME', 'NOT SET'),
            'RENDER_INSTANCE_ID': os.getenv('RENDER_INSTANCE_ID', 'NOT SET')
        }
        
        self.stdout.write('\n🌐 Render.com Information:')
        for key, value in render_info.items():
            self.stdout.write(f"  {key}: {value}")
            
        # Check for Redis connectivity
        self.stdout.write('\n🔗 Redis Connectivity Test:')
        try:
            import redis
            
            # Try environment variable first
            redis_url = os.getenv('REDIS_URL') or os.getenv('CELERY_BROKER_URL')
            if redis_url and redis_url != 'NOT SET':
                self.stdout.write(f"  Testing connection to: {redis_url[:20]}...")
                r = redis.from_url(redis_url)
                r.ping()
                self.stdout.write(self.style.SUCCESS('  ✅ Redis connection successful'))
            else:
                self.stdout.write(self.style.ERROR('  ❌ No Redis URL found in environment'))
                
        except ImportError:
            self.stdout.write(self.style.WARNING('  ⚠️  Redis package not available'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'  ❌ Redis connection failed: {e}'))
            
        # Deployment recommendations
        self.stdout.write(self.style.SUCCESS('\n📋 Next Steps:'))
        self.stdout.write('  1. Check Render.com dashboard for Redis service status')
        self.stdout.write('  2. Verify render.yaml deployment completed successfully')  
        self.stdout.write('  3. Restart all services if environment variables updated')
        self.stdout.write('  4. Check service logs for Redis connection attempts')
        
        self.stdout.write('\n' + '='*50)
