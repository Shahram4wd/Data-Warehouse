"""
Test script to verify cron job configuration
"""
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django_celery_beat.models import PeriodicTask
from data_warehouse.celery import app


def test_celery_configuration():
    """Test Celery configuration and periodic tasks"""
    print("=" * 60)
    print("🔍 CELERY CRON JOB CONFIGURATION TEST")
    print("=" * 60)
    
    # 1. Check environment
    django_env = os.environ.get('DJANGO_ENV', 'development')
    print(f"📍 DJANGO_ENV: {django_env}")
    
    # 2. Check Celery Beat schedule configuration
    print(f"\n📋 Celery Beat Schedule (from celery.py):")
    if hasattr(app.conf, 'beat_schedule') and app.conf.beat_schedule:
        for task_name, config in app.conf.beat_schedule.items():
            print(f"  ✓ {task_name}: {config['schedule']} -> {config['task']}")
    else:
        print("  ❌ No beat_schedule configured")
    
    # 3. Check database periodic tasks
    print(f"\n📊 Database Periodic Tasks:")
    try:
        tasks = PeriodicTask.objects.all()
        if tasks:
            for task in tasks:
                status = "✅ ENABLED" if task.enabled else "❌ DISABLED"
                schedule = task.crontab if task.crontab else task.interval
                print(f"  {status} {task.name}: {schedule}")
        else:
            print("  ❌ No periodic tasks found in database")
    except Exception as e:
        print(f"  ❌ Error accessing database: {e}")
    
    # 4. Check production-specific tasks
    print(f"\n🎯 Production Automation Report Tasks:")
    production_tasks = [
        'generate-automation-reports-afternoon',
        'generate-automation-reports-morning'
    ]
    
    for task_name in production_tasks:
        try:
            task = PeriodicTask.objects.get(name=task_name)
            status = "✅ ENABLED" if task.enabled else "❌ DISABLED"
            print(f"  {status} {task.name}: {task.crontab}")
        except PeriodicTask.DoesNotExist:
            print(f"  ❌ NOT FOUND: {task_name}")
    
    # 5. Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    
    if django_env != 'production':
        print(f"  ⚠️  Set DJANGO_ENV=production in your Render environment")
    
    disabled_production_tasks = PeriodicTask.objects.filter(
        name__in=production_tasks,
        enabled=False
    ).count()
    
    if disabled_production_tasks > 0:
        print(f"  ⚠️  Run: python manage.py enable_production_tasks")
    
    if django_env == 'production':
        enabled_tasks = PeriodicTask.objects.filter(
            name__in=production_tasks,
            enabled=True
        ).count()
        
        if enabled_tasks == len(production_tasks):
            print(f"  ✅ All production cron jobs are properly configured!")
        else:
            print(f"  ❌ Only {enabled_tasks}/{len(production_tasks)} production tasks enabled")
    
    print("=" * 60)


if __name__ == "__main__":
    test_celery_configuration()
