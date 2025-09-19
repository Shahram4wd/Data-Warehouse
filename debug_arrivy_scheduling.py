#!/usr/bin/env python
"""
Debug script to check Arrivy scheduling issues
"""
import os
import sys
import django

# Setup Django
sys.path.append('.')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def debug_arrivy_scheduling():
    """Debug Arrivy booking scheduling issues"""
    from django_celery_beat.models import PeriodicTask
    from ingestion.models import SyncSchedule
    
    print("=" * 60)
    print("🔍 ARRIVY BOOKING SCHEDULING DEBUG")
    print("=" * 60)
    
    # 1. Check specific problematic schedule
    print("\n📋 Checking Schedule ID 430:")
    try:
        schedule = SyncSchedule.objects.get(id=430)
        print(f"Schedule {schedule.id}: {schedule.name}")
        print(f"Source: {schedule.source_key}")
        print(f"Mode: {schedule.mode}")
        print(f"Model: {schedule.model_name}")
        print(f"Enabled: {schedule.enabled}")
        print(f"Options: {schedule.options}")
        
        if schedule.periodic_task:
            pt = schedule.periodic_task
            print(f"PeriodicTask Details:")
            print(f"  Name: {pt.name}")
            print(f"  Task: {pt.task}")
            print(f"  Enabled: {pt.enabled}")
            print(f"  Schedule: {pt.crontab or pt.interval}")
            print(f"  Args: {pt.args}")
            print(f"  Kwargs: {pt.kwargs}")
        else:
            print("No PeriodicTask linked!")
    except SyncSchedule.DoesNotExist:
        print("Schedule ID 430 not found!")
    
    # 2. Check Arrivy booking schedules
    print("\n📋 All Arrivy Booking Schedules:")
    schedules = SyncSchedule.objects.filter(
        source_key__icontains='arrivy', 
        mode__icontains='booking'
    )
    
    if schedules.exists():
        for schedule in schedules:
            print(f"\nSchedule {schedule.id}: {schedule.name}")
            print(f"  Source: {schedule.source_key}")
            print(f"  Mode: {schedule.mode}")
            print(f"  Enabled: {schedule.enabled}")
            print(f"  Periodic Task ID: {schedule.periodic_task_id}")
            
            if schedule.periodic_task:
                pt = schedule.periodic_task
                print(f"  PeriodicTask Details:")
                print(f"    Name: {pt.name}")
                print(f"    Task: {pt.task}")
                print(f"    Enabled: {pt.enabled}")
                print(f"    Schedule: {pt.crontab or pt.interval}")
                print(f"    Args: {pt.args}")
                print(f"    Kwargs: {pt.kwargs}")
            else:
                print(f"  ❌ No PeriodicTask linked!")
    else:
        print("  No Arrivy booking schedules found")
    
    # 2. Check all ingestion-related periodic tasks
    print("\n📊 All Ingestion PeriodicTasks:")
    tasks = PeriodicTask.objects.filter(task__contains='ingestion')
    
    if tasks.exists():
        for task in tasks:
            print(f"\nPeriodicTask: {task.name}")
            print(f"  Task: {task.task}")
            print(f"  Enabled: {task.enabled}")
            print(f"  Schedule: {task.crontab or task.interval}")
            print(f"  Args: {task.args}")
            print(f"  Kwargs: {task.kwargs}")
    else:
        print("  No ingestion periodic tasks found")
    
    # 3. Check for orphaned tasks (PeriodicTasks without SyncSchedules)
    print("\n🔍 Checking for Orphaned Tasks:")
    all_periodic_tasks = PeriodicTask.objects.filter(task='ingestion.run_ingestion')
    schedule_task_ids = set(SyncSchedule.objects.exclude(periodic_task_id=None).values_list('periodic_task_id', flat=True))
    
    orphaned_tasks = []
    for task in all_periodic_tasks:
        if task.id not in schedule_task_ids:
            orphaned_tasks.append(task)
    
    if orphaned_tasks:
        print(f"  Found {len(orphaned_tasks)} orphaned PeriodicTasks:")
        for task in orphaned_tasks:
            print(f"    - {task.name} (ID: {task.id}) - Enabled: {task.enabled}")
            print(f"      Args: {task.args}, Kwargs: {task.kwargs}")
    else:
        print("  No orphaned tasks found")
    
    # 4. Recommendations
    print("\n💡 RECOMMENDATIONS:")
    
    # Check for disabled schedules with enabled tasks
    for schedule in schedules:
        if schedule.periodic_task and not schedule.enabled and schedule.periodic_task.enabled:
            print(f"  ⚠️  Schedule '{schedule.name}' is disabled but PeriodicTask is enabled!")
            print(f"      Run: python manage.py shell -c \"from ingestion.services.schedule_sync import sync_periodic_task; from ingestion.models import SyncSchedule; s=SyncSchedule.objects.get(id={schedule.id}); sync_periodic_task(s)\"")
    
    # Check for orphaned enabled tasks
    for task in orphaned_tasks:
        if task.enabled:
            print(f"  ⚠️  Orphaned task '{task.name}' is still enabled and may be running!")
            print(f"      Consider disabling or deleting this task (ID: {task.id})")
    
    print("\n✅ Debug complete!")

if __name__ == "__main__":
    debug_arrivy_scheduling()