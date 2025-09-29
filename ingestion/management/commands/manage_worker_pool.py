"""
Worker Pool Management Command

This command provides CLI access to worker pool management functions
including status monitoring, configuration updates, and task management.
"""
import logging
import asyncio
import time
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.services.worker_pool import get_worker_pool, TaskStatus

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage the worker pool for sync tasks'
    
    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['status', 'config', 'monitor', 'process-queue', 'cancel', 'list-tasks', 'fix-stuck'],
            help='Action to perform'
        )
        
        # Configuration options
        parser.add_argument(
            '--max-workers',
            type=int,
            help='Set maximum number of workers (for config action)'
        )
        
        # Task management options
        parser.add_argument(
            '--task-id',
            type=str,
            help='Task ID (for cancel action)'
        )
        
        # Monitoring options
        parser.add_argument(
            '--interval',
            type=int,
            default=5,
            help='Monitoring interval in seconds (for monitor action)'
        )
        
        parser.add_argument(
            '--continuous',
            action='store_true',
            help='Continuous monitoring (for monitor action)'
        )
        
        # Output options
        parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )
        
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Verbose output'
        )
    
    def handle(self, *args, **options):
        """Handle the command"""
        action = options['action']
        
        try:
            worker_pool = get_worker_pool()
            
            if action == 'status':
                self.handle_status(worker_pool, options)
            elif action == 'config':
                self.handle_config(worker_pool, options)
            elif action == 'monitor':
                self.handle_monitor(worker_pool, options)
            elif action == 'process-queue':
                self.handle_process_queue(worker_pool, options)
            elif action == 'cancel':
                self.handle_cancel(worker_pool, options)
            elif action == 'list-tasks':
                self.handle_list_tasks(worker_pool, options)
            elif action == 'fix-stuck':
                self.handle_fix_stuck(worker_pool, options)
            else:
                raise CommandError(f"Unknown action: {action}")
                
        except Exception as e:
            logger.exception("Worker pool command failed")
            raise CommandError(f"Command failed: {e}")
    
    def handle_status(self, worker_pool, options):
        """Handle status action"""
        stats = worker_pool.get_stats()
        
        if options['json']:
            import json
            self.stdout.write(json.dumps(stats, indent=2))
        else:
            self.stdout.write(
                self.style.SUCCESS('Worker Pool Status:')
            )
            self.stdout.write(f"  Max Workers: {stats['max_workers']}")
            self.stdout.write(f"  Active: {stats['active_count']}")
            self.stdout.write(f"  Queued: {stats['queued_count']}")
            self.stdout.write(f"  Available: {stats['available_workers']}")
            
            if stats['active_tasks']:
                self.stdout.write(f"\n{self.style.WARNING('Active Tasks:')}")
                for task in stats['active_tasks']:
                    self.stdout.write(f"  - {task['id']}: {task['crm_source']}.{task['sync_type']} ({task['status']})")
            
            if stats['queued_tasks']:
                self.stdout.write(f"\n{self.style.WARNING('Queued Tasks:')}")
                for task in stats['queued_tasks']:
                    self.stdout.write(f"  - {task['position']}. {task['id']}: {task['crm_source']}.{task['sync_type']} (priority: {task['priority']})")
    
    def handle_config(self, worker_pool, options):
        """Handle config action"""
        if options['max_workers'] is not None:
            max_workers = options['max_workers']
            
            if max_workers < 1:
                raise CommandError("Max workers must be at least 1")
            
            try:
                worker_pool.set_max_workers(max_workers)
                self.stdout.write(
                    self.style.SUCCESS(f"Successfully updated max workers to {max_workers}")
                )
                
                # Show updated status
                stats = worker_pool.get_stats()
                self.stdout.write(f"Current status: {stats['active_count']} active, {stats['queued_count']} queued")
                
            except Exception as e:
                raise CommandError(f"Failed to update max workers: {e}")
        else:
            # Show current configuration
            current_max = worker_pool.get_max_workers()
            self.stdout.write(f"Current max workers: {current_max}")
    
    def handle_monitor(self, worker_pool, options):
        """Handle monitor action"""
        interval = options['interval']
        continuous = options['continuous']
        
        self.stdout.write(
            self.style.SUCCESS(f"Monitoring worker pool (interval: {interval}s, continuous: {continuous})")
        )
        
        try:
            while True:
                # Clear screen for continuous monitoring
                if continuous and not options['json']:
                    import os
                    os.system('cls' if os.name == 'nt' else 'clear')
                
                # Check task statuses
                worker_pool.check_celery_task_statuses()
                
                # Get stats
                stats = worker_pool.get_stats()
                
                if options['json']:
                    import json
                    self.stdout.write(json.dumps(stats, indent=2))
                else:
                    timestamp = time.strftime('%Y-%m-%d %H:%M:%S')
                    self.stdout.write(f"[{timestamp}] Active: {stats['active_count']}, Queued: {stats['queued_count']}, Available: {stats['available_workers']}")
                    
                    if options['verbose']:
                        for task in stats['active_tasks']:
                            self.stdout.write(f"  Active: {task['crm_source']}.{task['sync_type']} ({task['status']})")
                        for task in stats['queued_tasks']:
                            self.stdout.write(f"  Queued #{task['position']}: {task['crm_source']}.{task['sync_type']}")
                
                if not continuous:
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            self.stdout.write(
                self.style.WARNING('\nMonitoring stopped by user')
            )
    
    def handle_process_queue(self, worker_pool, options):
        """Handle process-queue action"""
        self.stdout.write("Processing queue...")
        
        stats_before = worker_pool.get_stats()
        worker_pool.process_queue()
        stats_after = worker_pool.get_stats()
        
        tasks_started = stats_after['active_count'] - stats_before['active_count']
        
        self.stdout.write(
            self.style.SUCCESS(f"Queue processed. Started {tasks_started} new tasks.")
        )
        self.stdout.write(f"Active: {stats_after['active_count']}, Queued: {stats_after['queued_count']}")
    
    def handle_cancel(self, worker_pool, options):
        """Handle cancel action"""
        task_id = options['task_id']
        
        if not task_id:
            raise CommandError("Task ID is required for cancel action (use --task-id)")
        
        success = worker_pool.cancel_task(task_id)
        
        if success:
            self.stdout.write(
                self.style.SUCCESS(f"Successfully cancelled task {task_id}")
            )
        else:
            self.stdout.write(
                self.style.ERROR(f"Failed to cancel task {task_id} (not found or not cancellable)")
            )
    
    def handle_list_tasks(self, worker_pool, options):
        """Handle list-tasks action"""
        active_tasks = worker_pool.get_active_tasks()
        queued_tasks = worker_pool.get_queued_tasks()
        
        if options['json']:
            import json
            data = {
                'active_tasks': [
                    {
                        'id': task.id,
                        'crm_source': task.crm_source,
                        'sync_type': task.sync_type,
                        'status': task.status.value,
                        'started_at': task.started_at.isoformat() if task.started_at else None,
                        'celery_task_id': task.celery_task_id
                    }
                    for task in active_tasks
                ],
                'queued_tasks': [
                    {
                        'id': task.id,
                        'crm_source': task.crm_source,
                        'sync_type': task.sync_type,
                        'priority': task.priority,
                        'queued_at': task.queued_at.isoformat() if task.queued_at else None
                    }
                    for task in queued_tasks
                ]
            }
            self.stdout.write(json.dumps(data, indent=2))
        else:
            self.stdout.write(f"{self.style.SUCCESS('Active Tasks:')} ({len(active_tasks)})")
            for task in active_tasks:
                status_color = self.style.SUCCESS if task.status == TaskStatus.RUNNING else self.style.WARNING
                self.stdout.write(f"  {task.id}: {task.crm_source}.{task.sync_type} - {status_color(task.status.value)}")
                if options['verbose'] and task.celery_task_id:
                    self.stdout.write(f"    Celery Task: {task.celery_task_id}")
            
            self.stdout.write(f"\n{self.style.SUCCESS('Queued Tasks:')} ({len(queued_tasks)})")
            for i, task in enumerate(queued_tasks, 1):
                priority_info = f" (priority: {task.priority})" if task.priority > 0 else ""
                self.stdout.write(f"  {i}. {task.id}: {task.crm_source}.{task.sync_type}{priority_info}")
    
    def handle_fix_stuck(self, worker_pool, options):
        """Handle fix-stuck action - delegates to existing cleanup_stale_syncs command"""
        self.stdout.write("Running cleanup for stuck SyncHistory records...")
        
        from django.core.management import call_command
        
        try:
            # Use existing cleanup_stale_syncs with a shorter threshold for immediate cleanup
            call_command('cleanup_stale_syncs', '--minutes', '5')
            self.stdout.write(self.style.SUCCESS("Cleanup completed using existing cleanup_stale_syncs command"))
            self.stdout.write("Note: Regular cleanup runs nightly and uses WORKER_POOL_STALE_MINUTES setting")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Cleanup failed: {e}"))