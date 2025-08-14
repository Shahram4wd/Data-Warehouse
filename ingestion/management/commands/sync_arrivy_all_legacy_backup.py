import logging
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync all Arrivy data using official API endpoints (customers, entities, groups, and bookings)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental for all endpoints."
        )
        parser.add_argument(
            "--debug",
            action="store_true",
            help="Show debug output"
        )
        parser.add_argument(
            "--pages",
            type=int,
            default=0,
            help="Maximum number of pages to process per endpoint (0 for unlimited)"
        )
        parser.add_argument(
            "--lastmodifieddate",
            type=str,
            help="Filter records modified after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--skip-task-statuses",
            action="store_true",
            help="Skip syncing task statuses"
        )
        parser.add_argument(
            "--skip-location-reports",
            action="store_true",
            help="Skip syncing location reports"
        )
        parser.add_argument(
            "--skip-entities",
            action="store_true",
            help="Skip syncing entities (crew members)"
        )
        parser.add_argument(
            "--skip-groups",
            action="store_true",
            help="Skip syncing groups (locations)"
        )
        parser.add_argument(
            "--skip-tasks",
            action="store_true",
            help="Skip syncing tasks"
        )
        parser.add_argument(
            "--start-date",
            type=str,
            help="For bookings: filter starting after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--end-date",
            type=str,
            help="For bookings: filter ending before this date (YYYY-MM-DD format)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        debug = options.get("debug")
        pages = options.get("pages", 0)
        lastmodifieddate = options.get("lastmodifieddate")
        skip_task_statuses = options.get("skip_task_statuses")
        skip_location_reports = options.get("skip_location_reports")
        skip_entities = options.get("skip_entities")
        skip_groups = options.get("skip_groups")
        skip_tasks = options.get("skip_tasks")
        start_date = options.get("start_date")
        end_date = options.get("end_date")

        if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
            raise CommandError("Arrivy API credentials are not properly configured in settings.")

        self.stdout.write(self.style.SUCCESS("Starting complete Arrivy data sync..."))
        
        # Prepare common arguments
        common_args = []
        common_kwargs = {}
        
        if full_sync:
            common_kwargs['full'] = True
        if debug:
            common_kwargs['debug'] = True
        if pages > 0:
            common_kwargs['pages'] = pages
        if lastmodifieddate:
            common_kwargs['lastmodifieddate'] = lastmodifieddate

        sync_results = {}        # 1. Sync Task Statuses first (as they may be referenced by tasks)
        if not skip_task_statuses:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING TASK STATUSES")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_task_status', *common_args, **common_kwargs)
                sync_results['task_statuses'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Task statuses sync completed"))
            except Exception as e:
                sync_results['task_statuses'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Task statuses sync failed: {str(e)}"))

        # 2. Sync Location Reports
        if not skip_location_reports:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING LOCATION REPORTS")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_location_reports', *common_args, **common_kwargs)
                sync_results['location_reports'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Location reports sync completed"))
            except Exception as e:
                sync_results['location_reports'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Location reports sync failed: {str(e)}"))

        # 3. Sync Entities (crew members)
        if not skip_entities:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING ENTITIES (CREW MEMBERS)")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_entities', *common_args, **common_kwargs)
                sync_results['entities'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Entities sync completed"))
            except Exception as e:
                sync_results['entities'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Entities sync failed: {str(e)}"))

        # 4. Sync Groups (locations)
        if not skip_groups:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING GROUPS (LOCATIONS)")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_groups', *common_args, **common_kwargs)
                sync_results['groups'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Groups sync completed"))
            except Exception as e:
                sync_results['groups'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Groups sync failed: {str(e)}"))        # 5. Sync Tasks (after other components)
        if not skip_tasks:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING TASKS")
            self.stdout.write("="*60)
            try:
                # Add task-specific arguments
                task_kwargs = common_kwargs.copy()
                if start_date:
                    task_kwargs['start_date'] = start_date
                if end_date:
                    task_kwargs['end_date'] = end_date
                
                call_command('sync_arrivy_tasks', *common_args, **task_kwargs)
                sync_results['tasks'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Tasks sync completed"))
            except Exception as e:
                sync_results['tasks'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Tasks sync failed: {str(e)}"))

        # Summary
        self.stdout.write("\n" + "="*60)
        self.stdout.write("📊 SYNC SUMMARY")
        self.stdout.write("="*60)
        
        for endpoint, result in sync_results.items():
            if result == 'SUCCESS':
                self.stdout.write(self.style.SUCCESS(f"✓ {endpoint.upper()}: {result}"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ {endpoint.upper()}: {result}"))

        # Overall result
        failed_syncs = [endpoint for endpoint, result in sync_results.items() if result != 'SUCCESS']
        
        if failed_syncs:
            self.stdout.write(self.style.WARNING(f"\n⚠️  {len(failed_syncs)} sync(s) failed: {', '.join(failed_syncs)}"))
        else:
            self.stdout.write(self.style.SUCCESS("\n🎉 All Arrivy syncs completed successfully!"))

        self.stdout.write("\n" + "="*60)
