import logging
from django.core.management.base import BaseCommand, CommandError
from django.core.management import call_command
from django.conf import settings

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync all Arrivy data (customers, team members, and bookings)"

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
            "--skip-customers",
            action="store_true",
            help="Skip syncing customers"
        )
        parser.add_argument(
            "--skip-team-members",
            action="store_true",
            help="Skip syncing team members"
        )
        parser.add_argument(
            "--skip-bookings",
            action="store_true",
            help="Skip syncing bookings"
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
        skip_customers = options.get("skip_customers")
        skip_team_members = options.get("skip_team_members")
        skip_bookings = options.get("skip_bookings")
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

        sync_results = {}

        # 1. Sync Customers first (as they are referenced by bookings)
        if not skip_customers:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING CUSTOMERS")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_customers', *common_args, **common_kwargs)
                sync_results['customers'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Customers sync completed"))
            except Exception as e:
                sync_results['customers'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Customers sync failed: {str(e)}"))
                if not options.get('continue_on_error'):
                    raise CommandError("Customers sync failed. Stopping.")

        # 2. Sync Team Members
        if not skip_team_members:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING TEAM MEMBERS")
            self.stdout.write("="*60)
            try:
                call_command('sync_arrivy_team_members', *common_args, **common_kwargs)
                sync_results['team_members'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Team members sync completed"))
            except Exception as e:
                sync_results['team_members'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Team members sync failed: {str(e)}"))

        # 3. Sync Bookings (after customers and team members)
        if not skip_bookings:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔄 SYNCING BOOKINGS")
            self.stdout.write("="*60)
            try:
                # Add booking-specific arguments
                booking_kwargs = common_kwargs.copy()
                if start_date:
                    booking_kwargs['start_date'] = start_date
                if end_date:
                    booking_kwargs['end_date'] = end_date
                
                call_command('sync_arrivy_bookings', *common_args, **booking_kwargs)
                sync_results['bookings'] = 'SUCCESS'
                self.stdout.write(self.style.SUCCESS("✓ Bookings sync completed"))
            except Exception as e:
                sync_results['bookings'] = f'FAILED: {str(e)}'
                self.stdout.write(self.style.ERROR(f"✗ Bookings sync failed: {str(e)}"))

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
