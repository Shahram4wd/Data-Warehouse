import logging
import sys
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils.dateparse import parse_datetime
from ingestion.salesrabbit.base_processor import BaseSalesRabbitProcessor
from ingestion.models.salesrabbit import SalesRabbit_Lead
from ingestion.salesrabbit.salesrabbit_client import SalesRabbitClient
# Removed transaction import as it's no longer needed

logger = logging.getLogger(__name__)

def show_progress(current, total, prefix="Progress", bar_length=50):
    """Display a progress bar"""
    percent = float(current) * 100 / total
    filled_length = int(bar_length * current // total)
    bar = '█' * filled_length + '-' * (bar_length - filled_length)
    print(f'\r{prefix}: |{bar}| {percent:.1f}% ({current}/{total})', end='', flush=True)

def batch_iterable(iterable, batch_size):
    """Yield successive batches from iterable."""
    for i in range(0, len(iterable), batch_size):
        yield iterable[i:i + batch_size]

class Command(BaseCommand):
    help = "Sync leads from SalesRabbit API"

    def handle(self, *args, **options):
        from django.conf import settings  # Import settings inside the method
        try:
            self.stdout.write("Starting SalesRabbit leads sync...")
            processor = BaseSalesRabbitProcessor(sync_type="salesrabbit_leads")
            client = SalesRabbitClient(api_token=settings.SALESRABBIT_API_TOKEN)
            print("[DEBUG] About to call SalesRabbitClient.get_leads(page_size=1000)")
            # Use paginated get_leads
            response = client.get_leads(page_size=1000)
            print("[DEBUG] Finished SalesRabbitClient.get_leads, received response")

            leads = response.get('data', []) if isinstance(response, dict) else response
            print(f"[DEBUG] Total leads fetched: {len(leads)}")
            if not leads:
                self.stdout.write("No leads to sync.")
                return

            total_leads = len(leads)
            self.stdout.write(f"Found {total_leads} leads to sync...")
            if total_leads >= 10000:
                self.stdout.write(self.style.WARNING("Warning: More than 10,000 leads found. Consider increasing page_size or checking API limits."))
            
            processed_count = 0
            created_count = 0
            updated_count = 0

            batch_size = 100  # You can adjust this number as needed
            batch_num = 0
            for batch in batch_iterable(leads, batch_size):
                print(f"[DEBUG] Entering batch processing loop for batch {batch_num + 1}")
                batch_num += 1
                start_idx = processed_count + 1
                end_idx = processed_count + len(batch)
                print(f"Processing batch {batch_num} ({start_idx}-{end_idx})...")
                # Print the first 5 lead IDs in this batch for debugging
                batch_ids = [lead.get('id') for lead in batch[:5]]
                print(f"First 5 lead IDs in batch {batch_num}: {batch_ids}")
                for i, lead_data in enumerate(batch):
                    idx = processed_count + i + 1
                    # Show progress bar every 10 records or at the end
                    if idx % 10 == 0 or idx == total_leads:
                        show_progress(idx, total_leads, "Syncing leads")
                    defaults = {
                        'business_name': lead_data.get('businessName'),
                        'first_name': lead_data.get('firstName'),
                        'last_name': lead_data.get('lastName'),
                        'email': lead_data.get('email'),
                        'phone_primary': lead_data.get('phonePrimary'),
                        'phone_alternate': lead_data.get('phoneAlternate'),
                        'street1': lead_data.get('street1'),
                        'street2': lead_data.get('street2'),
                        'city': lead_data.get('city'),
                        'state': lead_data.get('state'),
                        'zip': lead_data.get('zip'),
                        'country': lead_data.get('country'),
                        'latitude': lead_data.get('latitude'),
                        'longitude': lead_data.get('longitude'),
                        'status': lead_data.get('status'),
                        'campaign_id': lead_data.get('campaignId'),
                        'user_id': lead_data.get('userId'),
                        'user_name': lead_data.get('userName'),
                        'notes': lead_data.get('notes'),
                        'custom_fields': lead_data.get('customFields'),
                        'date_created': parse_datetime(lead_data.get('dateCreated')) if lead_data.get('dateCreated') else None,
                        'date_modified': parse_datetime(lead_data.get('dateModified')) if lead_data.get('dateModified') else None,
                        'deleted_at': parse_datetime(lead_data.get('deletedAt')) if lead_data.get('deletedAt') else None,
                        'status_modified': parse_datetime(lead_data.get('statusModified')) if lead_data.get('statusModified') else None,
                        'owner_modified': parse_datetime(lead_data.get('ownerModified')) if lead_data.get('ownerModified') else None,
                        'date_of_birth': parse_datetime(lead_data.get('dateOfBirth')) if lead_data.get('dateOfBirth') else None,
                        'synced_at': datetime.now(),
                        'data': lead_data,
                    }
                    print(f"[DEBUG] Processing lead data: {lead_data}")
                    # Validate the lead_data and defaults before processing
                    if not lead_data.get('id'):
                        print(f"[ERROR] Missing 'id' in lead_data: {lead_data}")
                        continue

                    print(f"[DEBUG] Defaults for lead ID {lead_data['id']}: {defaults}")
                    try:
                        lead_obj, created = SalesRabbit_Lead.objects.update_or_create(
                            id=lead_data['id'],
                            defaults=defaults
                        )
                        if created:
                            print(f"[DEBUG] Created new lead with ID: {lead_data['id']} and data: {defaults}")
                            created_count += 1
                        else:
                            print(f"[DEBUG] Updated existing lead with ID: {lead_data['id']} and data: {defaults}")
                            updated_count += 1
                        processed_count += 1
                    except Exception as e:
                        logger.error(f"Failed to process lead {lead_data.get('id', 'unknown')}: {str(e)}")
                        print(f"[ERROR] Exception while processing lead {lead_data.get('id', 'unknown')}: {str(e)}")
                        continue
                print(f"Finished batch {batch_num} ({start_idx}-{end_idx})")

            processor.complete_sync(
                records_processed=processed_count,
                records_created=created_count,
                records_updated=updated_count
            )
            
            # Clear progress bar and show summary
            sys.stdout.write('\n')  # New line after progress bar
            self.stdout.write(
                self.style.SUCCESS(
                    f"SalesRabbit leads sync complete. "
                    f"Processed: {processed_count}, Created: {created_count}, Updated: {updated_count}"
                )
            )
            
        except Exception as e:
            logger.exception("Error during SalesRabbit leads sync")
            raise CommandError(f"Sync failed: {str(e)}")
