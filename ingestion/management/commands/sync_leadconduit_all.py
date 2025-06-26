from django.core.management.base import BaseCommand
from ingestion.leadconduit.leadconduit_client import LeadConduitClient
from ingestion.leadconduit.base_processor import BaseLeadConduitProcessor
from ingestion.models.leadconduit import LeadConduit_Event, LeadConduit_Lead, LeadConduit_SyncHistory
from django.db import transaction
from tqdm import tqdm
from datetime import datetime, timezone as tz
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand, BaseLeadConduitProcessor):
    help = "Synchronize all LeadConduit data (events, leads, etc.)"

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of records to fetch (default: 1000)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days back to fetch data (default: 7)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to the database'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        days_back = options.get('days', 7)
        start_date = options.get('start_date')
        end_date = options.get('end_date')
        dry_run = options.get('dry_run', False)

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN MODE - No changes will be made"))

        self.stdout.write(self.style.SUCCESS("=== LEADCONDUIT SYNC ALL ==="))

        try:
            # Initialize client
            client = LeadConduitClient()

            # Parse date range
            end_dt = None
            start_dt = None

            if end_date:
                end_dt = datetime.strptime(end_date, '%Y-%m-%d').replace(tzinfo=tz.utc)
            if start_date:
                start_dt = datetime.strptime(start_date, '%Y-%m-%d').replace(tzinfo=tz.utc)
            elif not start_dt and days_back:
                from datetime import timedelta
                end_dt = end_dt or datetime.now(tz=tz.utc)
                start_dt = end_dt - timedelta(days=days_back)

            self.stdout.write(f"📅 Date range: {start_dt} to {end_dt}")
            self.stdout.write(f"📊 Max records: {limit}")

            # Fetch events
            self.stdout.write("Fetching events from LeadConduit...")
            events = client.get_events_paginated(limit_per_page=1000, max_total=limit, start=start_dt, end=end_dt)

            if not events:
                self.stdout.write(self.style.WARNING("No events found"))
                return

            self.stdout.write(f"✅ Fetched {len(events)} events")

            # Save events to the database
            self.stdout.write("Saving events to the database...")
            created_events, updated_events = self._save_events_to_db(events)
            self.stdout.write(f"✅ Events saved: {created_events} created, {updated_events} updated")

            # Extract and save leads
            self.stdout.write("Extracting and saving leads...")
            leads_created, leads_updated = self._extract_and_save_leads(events, dry_run)
            self.stdout.write(f"✅ Leads saved: {leads_created} created, {leads_updated} updated")

            self.stdout.write(self.style.SUCCESS("=== LEADCONDUIT SYNC ALL COMPLETED ==="))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error: {str(e)}"))
            logger.error(f"LeadConduit sync failed: {str(e)}")

    def _save_events_to_db(self, events):
        """Save events to the database."""
        created_count = 0
        updated_count = 0

        with transaction.atomic():
            for event in tqdm(events, desc="Saving events"):
                event_obj, created = LeadConduit_Event.objects.update_or_create(
                    id=event['id'],
                    defaults={
                        'outcome': event.get('outcome'),
                        'reason': event.get('reason'),
                        'event_type': event.get('event_type'),
                        'vars_data': event.get('vars', {}),
                        'appended_data': event.get('appended', {}),
                        'start_timestamp': event.get('start'),
                        'end_timestamp': event.get('end'),
                    }
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1

        return created_count, updated_count

    def _extract_and_save_leads(self, events, dry_run):
        """Extract leads from events and save them to the database."""
        leads_created = 0
        leads_updated = 0

        for event in tqdm(events, desc="Extracting leads"):
            lead_data = self._extract_lead_from_event(event)
            if not lead_data:
                continue

            if dry_run:
                self.stdout.write(f"DRY RUN: Would save lead {lead_data.get('lead_id')}")
                continue

            lead_obj, created = LeadConduit_Lead.objects.update_or_create(
                lead_id=lead_data['lead_id'],
                defaults=lead_data
            )
            if created:
                leads_created += 1
            else:
                leads_updated += 1

        return leads_created, leads_updated

    def _extract_lead_from_event(self, event):
        """Extract lead data from a single event."""
        vars_data = event.get('vars', {})
        appended_data = event.get('appended', {})
        combined_data = {**vars_data, **appended_data}

        return {
            'lead_id': combined_data.get('lead_id'),
            'first_name': combined_data.get('first_name'),
            'last_name': combined_data.get('last_name'),
            'email': combined_data.get('email'),
            'phone_1': combined_data.get('phone_1'),
            'phone_2': combined_data.get('phone_2'),
            'address_1': combined_data.get('address_1'),
            'address_2': combined_data.get('address_2'),
            'city': combined_data.get('city'),
            'state': combined_data.get('state'),
            'postal_code': combined_data.get('postal_code'),
            'country': combined_data.get('country'),
            'submission_timestamp': combined_data.get('submission_timestamp'),
            'full_data': combined_data,
        }