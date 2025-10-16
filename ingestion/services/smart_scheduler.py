"""
Smart Task Scheduler with Environment Gates

This module provides intelligent task scheduling that respects environment 
variables to enable/disable specific data sources.
"""
import logging
from typing import Dict, List, Optional
from celery.schedules import crontab

logger = logging.getLogger(__name__)


def _get_django_settings():
    """Lazy import Django settings to avoid app loading issues"""
    try:
        from django.conf import settings
        return settings
    except Exception as e:
        logger.warning(f"Could not import Django settings: {e}")
        return None


class ConditionalSchedule:
    """Represents a schedule that can be conditionally enabled"""
    
    def __init__(self, task_name: str, schedule: crontab, 
                 enable_setting: str = None, default_enabled: bool = True):
        self.task_name = task_name
        self.schedule = schedule
        self.enable_setting = enable_setting
        self.default_enabled = default_enabled
    
    def is_enabled(self) -> bool:
        """Check if this schedule should be enabled"""
        if not self.enable_setting:
            return self.default_enabled
        
        settings = _get_django_settings()
        if not settings:
            return self.default_enabled
            
        return getattr(settings, self.enable_setting, self.default_enabled)
    
    def to_beat_config(self) -> Dict:
        """Convert to celery beat configuration format"""
        return {
            'task': self.task_name,
            'schedule': self.schedule
        }


class SmartScheduler:
    """Smart scheduler that respects environment gates"""
    
    def __init__(self):
        self.schedules = []
    
    def add_schedule(self, schedule: ConditionalSchedule):
        """Add a conditional schedule"""
        self.schedules.append(schedule)
    
    def get_enabled_schedules(self) -> Dict[str, Dict]:
        """Get all enabled schedules in celery beat format"""
        enabled = {}
        
        for schedule in self.schedules:
            if schedule.is_enabled():
                # Create a safe schedule name
                schedule_name = schedule.task_name.replace('.', '-')
                if schedule_name.startswith('ingestion-tasks-'):
                    schedule_name = schedule_name[16:]  # Remove prefix
                schedule_name = f"{schedule_name}-hourly"
                
                enabled[schedule_name] = schedule.to_beat_config()
                logger.info(f"Enabled schedule: {schedule_name} -> {schedule.task_name}")
            else:
                logger.info(f"Disabled schedule: {schedule.task_name} (setting: {schedule.enable_setting})")
        
        return enabled


def create_production_scheduler() -> SmartScheduler:
    """Create production scheduler with all sync tasks"""
    scheduler = SmartScheduler()
    
    # Staggered hourly sync tasks (spread across :00 to :16 past the hour)
    sync_schedules = [
        ConditionalSchedule(
            'ingestion.tasks.sync_hubspot_all',
            crontab(minute=0),  # :00 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_arrivy_all',
            crontab(minute=2),  # :02 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_leadconduit_all',
            crontab(minute=4),  # :04 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_five9_contacts',
            crontab(minute=6),  # :06 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_genius_all',
            crontab(minute=8),  # :08 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_salespro_all',
            crontab(minute=10),  # :10 past every hour (will skip if no credentials)
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_callrail_all',
            crontab(minute=12),  # :12 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_gsheet_all',
            crontab(minute=14),  # :14 past every hour
        ),
        ConditionalSchedule(
            'ingestion.tasks.sync_salesrabbit_all',
            crontab(minute=16),  # :16 past every hour
        ),
    ]
    
    for schedule in sync_schedules:
        scheduler.add_schedule(schedule)
    
    return scheduler


def get_smart_beat_schedule(environment: str = 'production') -> Dict[str, Dict]:
    """
    Get smart beat schedule that respects environment gates
    
    Args:
        environment: 'production' or 'development'
        
    Returns:
        Dictionary of enabled schedules in celery beat format
    """
    if environment == 'production':
        scheduler = create_production_scheduler()
        smart_schedules = scheduler.get_enabled_schedules()
        
        # Add fixed schedules that don't need gating
        fixed_schedules = {
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
            'sweeper-cleanup-stuck-tasks': {
                'task': 'ingestion.tasks.sweeper_cleanup_stuck_tasks',
                'schedule': crontab(minute='*/2'),  # Every 2 minutes
            },
            'sweeper-cleanup-old-sync-runs': {
                'task': 'ingestion.tasks.sweeper_cleanup_old_sync_runs',
                'schedule': crontab(hour=2, minute=0),  # 2:00 AM UTC daily
            },
            'sweeper-memory-monitor': {
                'task': 'ingestion.tasks.sweeper_memory_monitor',
                'schedule': crontab(minute='*/10'),  # Every 10 minutes
            },
        }
        
        # Combine smart and fixed schedules
        return {**smart_schedules, **fixed_schedules}
    
    else:
        # Development - minimal schedules
        return {
            'worker-pool-monitor': {
                'task': 'ingestion.tasks.worker_pool_monitor',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes in development
            },
            'cleanup-stale-syncs-0330utc': {
                'task': 'ingestion.tasks.cleanup_stale_syncs',
                'schedule': crontab(hour=3, minute=30),  # 03:30 UTC nightly (dev)
            },
            'sweeper-cleanup-stuck-tasks': {
                'task': 'ingestion.tasks.sweeper_cleanup_stuck_tasks',
                'schedule': crontab(minute='*/5'),  # Every 5 minutes in dev
            },
            'sweeper-memory-monitor': {
                'task': 'ingestion.tasks.sweeper_memory_monitor',
                'schedule': crontab(minute='*/15'),  # Every 15 minutes in dev
            },
        }