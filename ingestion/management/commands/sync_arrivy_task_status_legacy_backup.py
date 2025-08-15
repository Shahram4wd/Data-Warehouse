import logging
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from ingestion.models.arrivy import Arrivy_TaskStatus, Arrivy_SyncHistory
from ingestion.arrivy.arrivy_client import ArrivyClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Sync task statuses from Arrivy API (Legacy backup command with --full support)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync - fetch all available statuses from multiple endpoints'
        )
        
        parser.add_argument(
            '--include-inactive',
            action='store_true',
            help='Include inactive/deprecated status definitions'
        )
        
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes'
        )

    def handle(self, *args, **options):
        try:
            self.stdout.write("Starting Arrivy task status sync...")
            
            # Initialize client
            client = ArrivyClient()
            all_statuses = []
            
            if options.get('full', False):
                self.stdout.write("🔄 Full sync mode: Checking multiple endpoints...")
                
                # Try multiple endpoints for comprehensive status collection
                endpoints_to_try = [
                    "task-statuses",
                    "task_statuses", 
                    "statuses",
                    "taskstatuses",
                    "workflows/statuses",
                    "admin/statuses",
                    "config/task-statuses"
                ]
                
                for endpoint in endpoints_to_try:
                    try:
                        self.stdout.write(f"  📡 Trying endpoint: {endpoint}")
                        response = client._make_request_to_endpoint(endpoint)
                        
                        if response and isinstance(response, dict) and response.get("data"):
                            endpoint_statuses = response["data"]
                            self.stdout.write(f"    ✅ Found {len(endpoint_statuses)} statuses")
                            all_statuses.extend(endpoint_statuses)
                        elif response and isinstance(response, list):
                            self.stdout.write(f"    ✅ Found {len(response)} statuses")
                            all_statuses.extend(response)
                        else:
                            self.stdout.write(f"    ⚠️  No data from {endpoint}")
                            
                    except Exception as e:
                        self.stdout.write(f"    ❌ Error with {endpoint}: {str(e)}")
                        continue
                
                # Remove duplicates based on ID
                seen_ids = set()
                unique_statuses = []
                for status in all_statuses:
                    status_id = status.get('id') or status.get('status_id') or status.get('name')
                    if status_id and status_id not in seen_ids:
                        seen_ids.add(status_id)
                        unique_statuses.append(status)
                
                statuses = unique_statuses
                self.stdout.write(f"📊 Total unique statuses found: {len(statuses)}")
                
            else:
                # Standard mode - use original method
                response = client.get_task_statuses()
                
                # Handle both dictionary and list responses
                if isinstance(response, dict):
                    statuses = response.get("data", [])
                elif isinstance(response, list):
                    statuses = response
                else:
                    statuses = []

            if not statuses:
                self.stdout.write("No task statuses to process.")
                return

            # Filter out inactive statuses if not requested
            if not options.get('include_inactive', False):
                original_count = len(statuses)
                statuses = [s for s in statuses if s.get('is_active', True) != False]
                filtered_count = original_count - len(statuses)
                if filtered_count > 0:
                    self.stdout.write(f"🔽 Filtered out {filtered_count} inactive statuses")

            # Show what would be processed in dry-run mode
            if options.get('dry_run', False):
                self.stdout.write(f"🔍 DRY RUN: Would process {len(statuses)} statuses:")
                for i, status in enumerate(statuses[:10]):  # Show first 10
                    status_name = status.get('title') or status.get('name') or status.get('type', 'Unknown')
                    status_id = status.get('id', 'N/A')
                    self.stdout.write(f"  {i+1}. {status_name} (ID: {status_id})")
                if len(statuses) > 10:
                    self.stdout.write(f"  ... and {len(statuses) - 10} more")
                return

            # Process each task status
            created_count = 0
            updated_count = 0
            
            with transaction.atomic():
                for status in statuses:
                    status_id = status.get("id")
                    if not status_id:
                        # Try alternative ID fields
                        status_id = status.get("status_id") or status.get("pk")
                        
                    if not status_id:
                        self.stdout.write(f"⚠️  Skipping status without ID: {status}")
                        continue
                    
                    obj, created = Arrivy_TaskStatus.objects.update_or_create(
                        id=status_id,
                        defaults={
                            "name": status.get("title") or status.get("name") or status.get("type") or f"Status_{status_id}",
                            "title": status.get("title") or status.get("name") or status.get("type") or f"Status_{status_id}",
                            "description": status.get("description") or status.get("desc", ""),
                            "is_active": status.get("is_active", True),
                            "created": status.get("created_time") or status.get("created"),
                            "updated": status.get("updated_time") or status.get("updated"),
                            "color": status.get("color"),
                            "type_id": status.get("type_id"),
                            "visible_to_customer": status.get("visible_to_customer"),
                            "require_signature": status.get("require_signature"),
                            "require_rating": status.get("require_rating"),
                        },
                    )
                    
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1

            # Update sync history
            Arrivy_SyncHistory.objects.update_or_create(
                sync_type="task_statuses",
                defaults={"last_synced_at": timezone.now()},
            )

            # Display results
            self.stdout.write(
                self.style.SUCCESS(
                    f"✅ Arrivy task status sync complete!\n"
                    f"📊 Results: {len(statuses)} total, {created_count} created, {updated_count} updated"
                )
            )

        except Exception as e:
            logger.exception("Error during Arrivy task status sync")
            raise CommandError(f"Sync failed: {str(e)}")
