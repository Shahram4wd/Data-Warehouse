import asyncio
import logging
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.models import ActiveProspect_Lead, ActiveProspect_SyncHistory
from ingestion.activeprospect.activeprospect_client import ActiveProspectClient

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync leads from ActiveProspect LeadConduit API using search endpoint"

    def add_arguments(self, parser):
        parser.add_argument("--query", type=str, help="Search query for leads")
        parser.add_argument("--debug", action="store_true", help="Show debug output")
        parser.add_argument("--limit", type=int, default=10, help="Maximum number of leads")

    def handle(self, *args, **options):
        try:
            if options.get("debug"):
                logging.getLogger().setLevel(logging.DEBUG)
                logging.getLogger("activeprospect_client").setLevel(logging.DEBUG)

            query = options.get("query") or "*"
            limit = options.get("limit", 10)

            self.stdout.write("Starting ActiveProspect leads sync...")
            total = asyncio.run(self.sync_leads(query, limit))
            self.stdout.write(self.style.SUCCESS(f"Processed {total} leads."))

        except Exception as e:
            logger.exception("Error during sync")
            raise CommandError(f"Sync failed: {str(e)}")

    async def sync_leads(self, query, limit):
        client = ActiveProspectClient()
        
        try:
            self.stdout.write(f"Searching leads with query: '{query}', limit: {limit}")
            
            response = await client.search_leads(query=query, limit=limit)
            hits = response.get("hits", [])
            total = response.get("total", 0)
            
            self.stdout.write(f"Retrieved {len(hits)} leads (total available: {total})")
            
            if hits:
                await self.process_leads_batch(hits)
            
            await self.update_sync_history("leads-search", len(hits))
            return len(hits)
            
        except Exception as e:
            logger.error(f"Error: {str(e)}")
            raise

    async def process_leads_batch(self, leads_data):
        """Process a batch of leads and save to database."""
        self.stdout.write(f"Processing {len(leads_data)} leads...")
        
        # Get existing leads to avoid duplicates
        lead_ids = [str(lead.get("lead_id")) for lead in leads_data if lead.get("lead_id")]
        existing_leads = {
            lead.lead_id: lead 
            for lead in await sync_to_async(list)(ActiveProspect_Lead.objects.filter(lead_id__in=lead_ids))
        }

        leads_to_create = []
        leads_to_update = []

        for lead_data in leads_data:
            try:
                lead_id = lead_data.get("lead_id")
                if not lead_id:
                    continue

                latest_event = lead_data.get("latest_event", {})
                
                lead_fields = {
                    "lead_id": str(lead_id),
                    "flow_id": lead_data.get("flow_id"),
                    "flow_name": lead_data.get("flow_name"),
                    "source_id": lead_data.get("source_id"),
                    "source_name": lead_data.get("source_name"),
                    "reference": lead_data.get("reference"),
                    "first_name": lead_data.get("first_name"),
                    "last_name": lead_data.get("last_name"),
                    "email": lead_data.get("email"),
                    "phone_1": lead_data.get("phone_1"),
                    "phone_2": lead_data.get("phone_2"),
                    "address_1": lead_data.get("address_1"),
                    "city": lead_data.get("city"),
                    "state": lead_data.get("state"),
                    "postal_code": lead_data.get("postal_code"),
                    "highlight": lead_data.get("highlight"),
                    "latest_event_id": latest_event.get("id") if latest_event else None,
                    "latest_event_outcome": latest_event.get("outcome") if latest_event else None,
                    "latest_event_data": latest_event if latest_event else None,
                }
                
                # Parse submission timestamp
                if lead_data.get("submission_timestamp"):
                    try:
                        lead_fields["submission_timestamp"] = datetime.fromisoformat(
                            lead_data["submission_timestamp"].replace("Z", "+00:00")
                        )
                    except:
                        pass

                if str(lead_id) in existing_leads:
                    # Update existing lead
                    existing_lead = existing_leads[str(lead_id)]
                    for field, value in lead_fields.items():
                        if field != "lead_id":
                            setattr(existing_lead, field, value)
                    leads_to_update.append(existing_lead)
                else:
                    # Create new lead
                    leads_to_create.append(ActiveProspect_Lead(**lead_fields))

            except Exception as e:
                logger.error(f"Error processing lead {lead_data.get('lead_id')}: {str(e)}")

        # Save to database
        try:
            if leads_to_create:
                def create_leads():
                    ActiveProspect_Lead.objects.bulk_create(leads_to_create, ignore_conflicts=True)
                    return len(leads_to_create)
                    
                created_count = await sync_to_async(create_leads)()
                self.stdout.write(f"Created {created_count} new leads")

            if leads_to_update:
                def update_leads():
                    with transaction.atomic():
                        for lead in leads_to_update:
                            lead.save()
                    return len(leads_to_update)
                    
                updated_count = await sync_to_async(update_leads)()
                self.stdout.write(f"Updated {updated_count} existing leads")

        except Exception as e:
            logger.error(f"Error saving leads: {str(e)}")
            raise

    async def update_sync_history(self, endpoint, total_records):
        """Update sync history record."""
        try:
            def update_history():
                sync_history, created = ActiveProspect_SyncHistory.objects.get_or_create(
                    endpoint=endpoint,
                    defaults={
                        "last_synced_at": timezone.now(),
                        "total_records": total_records,
                        "success_count": total_records,
                        "error_count": 0,
                        "notes": f"Synced {total_records} leads"
                    }
                )
                
                if not created:
                    sync_history.last_synced_at = timezone.now()
                    sync_history.total_records = total_records
                    sync_history.success_count = total_records
                    sync_history.error_count = 0
                    sync_history.notes = f"Synced {total_records} leads"
                    sync_history.save()
                
                return sync_history

            await sync_to_async(update_history)()
            logger.info(f"Updated sync history for {endpoint}")

        except Exception as e:
            logger.error(f"Error updating sync history: {str(e)}")
