"""
Management command to enable production periodic tasks for Celery Beat
"""
from django.core.management.base import BaseCommand
from django_celery_beat.models import PeriodicTask, CrontabSchedule
from celery.schedules import crontab
import os


class Command(BaseCommand):
    help = 'Enable production periodic tasks and verify environment settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be done without making changes',
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        
        # Check environment
        django_env = os.environ.get('DJANGO_ENV', 'development')
        self.stdout.write(f"Current DJANGO_ENV: {django_env}")
        
        if django_env != 'production':
            self.stdout.write(
                self.style.WARNING(
                    'WARNING: DJANGO_ENV is not set to "production". '
                    'This may cause issues with task scheduling.'
                )
            )
        
        # Define the tasks that should be enabled in production
        production_tasks = [
            'generate-automation-reports-afternoon',
            'generate-automation-reports-morning',
        ]
        
        # Check and enable production tasks
        for task_name in production_tasks:
            try:
                task = PeriodicTask.objects.get(name=task_name)
                
                if not task.enabled:
                    if dry_run:
                        self.stdout.write(f"[DRY RUN] Would enable task: {task_name}")
                    else:
                        task.enabled = True
                        task.save()
                        self.stdout.write(
                            self.style.SUCCESS(f"✓ Enabled task: {task_name}")
                        )
                else:
                    self.stdout.write(f"✓ Task already enabled: {task_name}")
                    
            except PeriodicTask.DoesNotExist:
                self.stdout.write(
                    self.style.ERROR(f"✗ Task not found: {task_name}")
                )
        
        # List all current periodic tasks
        self.stdout.write("\nAll periodic tasks:")
        self.stdout.write("-" * 50)
        
        for task in PeriodicTask.objects.all().order_by('name'):
            status = "ENABLED" if task.enabled else "DISABLED"
            style = self.style.SUCCESS if task.enabled else self.style.ERROR
            
            schedule_info = ""
            if task.crontab:
                schedule_info = f"({task.crontab})"
            elif task.interval:
                schedule_info = f"(every {task.interval})"
                
            self.stdout.write(
                f"  {style(status)} {task.name} {schedule_info}"
            )
        
        self.stdout.write("\n" + "="*50)
        
        if django_env == 'production':
            enabled_production_tasks = PeriodicTask.objects.filter(
                name__in=production_tasks, 
                enabled=True
            ).count()
            
            if enabled_production_tasks == len(production_tasks):
                self.stdout.write(
                    self.style.SUCCESS(
                        f"✓ All {len(production_tasks)} production tasks are enabled"
                    )
                )
            else:
                self.stdout.write(
                    self.style.WARNING(
                        f"⚠ Only {enabled_production_tasks}/{len(production_tasks)} "
                        "production tasks are enabled"
                    )
                )
        else:
            self.stdout.write(
                self.style.WARNING(
                    "Environment is not production - tasks may not be scheduled properly"
                )
            )
