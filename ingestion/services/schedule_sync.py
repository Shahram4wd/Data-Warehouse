from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import json

def _ensure_interval(every: int, period: str) -> IntervalSchedule:
    """Get or create an IntervalSchedule instance."""
    return IntervalSchedule.objects.get_or_create(every=every, period=period)[0]

def _ensure_crontab(minute, hour, dow, dom, moy) -> CrontabSchedule:
    """Get or create a CrontabSchedule instance."""
    return CrontabSchedule.objects.get_or_create(
        minute=minute or "*", 
        hour=hour or "*", 
        day_of_week=dow or "*", 
        day_of_month=dom or "*", 
        month_of_year=moy or "*", 
        timezone=getattr(settings, 'TIME_ZONE', 'UTC')
    )[0]

@transaction.atomic
def sync_periodic_task(schedule):
    """Create or update a PeriodicTask for the given SyncSchedule."""
    task_name = "ingestion.run_ingestion"
    task_kwargs = {"schedule_id": schedule.id}
    
    # Prepare the schedule (interval or crontab)
    if schedule.recurrence_type == "interval":
        interval = _ensure_interval(schedule.every, schedule.period)
        pt_kwargs = {
            "task": task_name,
            "interval": interval,
            "args": json.dumps([]),
            "kwargs": json.dumps(task_kwargs)
        }
    else:  # crontab
        crontab = _ensure_crontab(
            schedule.minute, 
            schedule.hour, 
            schedule.day_of_week, 
            schedule.day_of_month, 
            schedule.month_of_year
        )
        pt_kwargs = {
            "task": task_name,
            "crontab": crontab,
            "args": json.dumps([]),
            "kwargs": json.dumps(task_kwargs)
        }

    # Create or update the PeriodicTask
    if schedule.periodic_task_id:
        # Update existing task
        pt = schedule.periodic_task
        for k, v in pt_kwargs.items():
            setattr(pt, k, v)
        pt.name = f"{schedule.source_key}:{schedule.mode}:{schedule.name}"
        pt.enabled = schedule.enabled
        pt.start_time = schedule.start_at
        pt.expires = schedule.end_at
        pt.save()
    else:
        # Create new task
        pt = PeriodicTask.objects.create(
            name=f"{schedule.source_key}:{schedule.mode}:{schedule.name}",
            enabled=schedule.enabled,
            start_time=schedule.start_at,
            expires=schedule.end_at,
            **pt_kwargs,
        )
        schedule.periodic_task = pt
        schedule.save(update_fields=["periodic_task"])

    return schedule

def delete_periodic_task(schedule):
    """Delete the PeriodicTask associated with the given SyncSchedule."""
    if schedule.periodic_task:
        schedule.periodic_task.delete()
        schedule.periodic_task = None
        schedule.save(update_fields=["periodic_task"])
