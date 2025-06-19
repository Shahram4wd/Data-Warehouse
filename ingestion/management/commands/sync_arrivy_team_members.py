import asyncio
import os
import sys
import json
import logging
from datetime import datetime, timedelta

import aiohttp
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from django.conf import settings
from tqdm import tqdm

from ingestion.arrivy.arrivy_client import ArrivyClient
from ingestion.models.arrivy import Arrivy_TeamMember, Arrivy_SyncHistory

logger = logging.getLogger(__name__)

BATCH_SIZE = 100

class Command(BaseCommand):
    help = "Sync team members from Arrivy API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--full",
            action="store_true",
            help="Perform a full sync instead of incremental."
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
            help="Maximum number of pages to process (0 for unlimited)"        )
        parser.add_argument(
            "--lastmodifieddate",
            type=str,
            help="Filter team members modified after this date (YYYY-MM-DD format)"
        )
        parser.add_argument(
            "--endpoint",
            type=str,
            default="team",
            help="API endpoint to try (team, users, staff, employees, workers)"
        )

    def handle(self, *args, **options):
        full_sync = options.get("full")
        max_pages = options.get("pages", 0)
        lastmodifieddate = options.get("lastmodifieddate")
        api_endpoint = options.get("endpoint", "team")

        if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
            raise CommandError("Arrivy API credentials are not properly configured in settings.")

        self.stdout.write(self.style.SUCCESS(f"Starting Arrivy team members sync using endpoint: {api_endpoint}..."))
        
        # Get the last sync time
        endpoint = "team_members"
        
        # Priority: 1) --lastmodifieddate parameter, 2) database last sync, 3) full sync
        if lastmodifieddate:
            try:
                last_sync = datetime.strptime(lastmodifieddate, "%Y-%m-%d")
                last_sync = timezone.make_aware(last_sync)
                self.stdout.write(f"Using provided lastmodifieddate filter: {lastmodifieddate}")
            except ValueError:
                raise CommandError(f"Invalid date format for --lastmodifieddate. Use YYYY-MM-DD format.")
        elif full_sync:
            last_sync = None
        else:
            last_sync = self.get_last_sync(endpoint)
        
        if last_sync:
            self.stdout.write(f"Performing delta sync since {last_sync}")
        else:
            self.stdout.write("Performing full sync")
        
        try:
            all_team_members = []
            total_pages = 0
            
            client = ArrivyClient()
            
            self.stdout.write("Starting to fetch team members from Arrivy...")
            self.stdout.write(f"Using batch size: {BATCH_SIZE}")
            
            page = 1
            has_next = True
            
            while has_next:
                if max_pages > 0 and total_pages >= max_pages:
                    self.stdout.write(f"Reached maximum page limit of {max_pages}")
                    break

                total_pages += 1
                self.stdout.write(f"Fetching page {total_pages}...")

                page_result = asyncio.run(client.get_team_members(
                    page_size=BATCH_SIZE,
                    page=page,
                    last_sync=last_sync,
                    endpoint=api_endpoint
                ))

                if not page_result or not page_result.get('data'):
                    self.stdout.write("No more data to fetch")
                    break

                page_data = page_result['data']
                pagination = page_result.get('pagination') or {}
                
                self.stdout.write(f"Retrieved {len(page_data)} team members")
                all_team_members.extend(page_data)

                has_next = pagination.get('has_next', False)
                
                # If no pagination info, check if we got a full page
                if not pagination:
                    has_next = len(page_data) >= BATCH_SIZE
                
                page = pagination.get('next_page', page + 1)

                # Save data if we've reached a checkpoint
                if len(all_team_members) >= BATCH_SIZE * 5:
                    self.stdout.write(f"Processing checkpoint at page {total_pages}...")
                    self.process_team_members_batch(all_team_members[:BATCH_SIZE * 5])
                    all_team_members = all_team_members[BATCH_SIZE * 5:]

            # Process any remaining team members
            if all_team_members:
                self.stdout.write("Processing final batch...")
                self.process_team_members_batch(all_team_members)

            # Update sync history
            self.update_last_sync(endpoint)
            
            self.stdout.write(self.style.SUCCESS(f"Arrivy team members sync complete. Processed {total_pages} pages."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error in sync process: {str(e)}"))
            logger.exception("Error during Arrivy team members sync")
            raise CommandError(f"Sync failed: {str(e)}")

    def process_team_members_batch(self, team_members_data):
        """Process a batch of team members data."""
        if not team_members_data:
            return

        self.stdout.write(f"Processing {len(team_members_data)} team members...")

        # Get existing team members
        member_ids = [member.get('id') for member in team_members_data if member.get('id')]
        existing_members = {
            member.id: member 
            for member in Arrivy_TeamMember.objects.filter(id__in=member_ids)
        }

        members_to_create = []
        members_to_update = []

        for member_data in team_members_data:
            try:
                member_id = member_data.get('id')
                if not member_id:
                    continue

                # Parse datetime fields
                created_time = self.parse_datetime(member_data.get('created_time'))
                updated_time = self.parse_datetime(member_data.get('updated_time'))
                last_location_time = self.parse_datetime(member_data.get('last_location_time'))

                # Prepare member fields
                member_fields = {
                    'external_id': member_data.get('external_id'),
                    'name': member_data.get('name'),
                    'first_name': member_data.get('first_name'),
                    'last_name': member_data.get('last_name'),
                    'email': member_data.get('email'),
                    'phone': member_data.get('phone'),
                    'image_path': member_data.get('image_path'),
                    'image_id': member_data.get('image_id'),
                    'username': member_data.get('username'),
                    'role': member_data.get('role'),
                    'permission': member_data.get('permission'),
                    'group_id': member_data.get('group_id'),
                    'group_name': member_data.get('group_name'),
                    'timezone': member_data.get('timezone'),
                    'address': member_data.get('address'),
                    'is_active': member_data.get('is_active', True),
                    'is_online': member_data.get('is_online', False),
                    'can_turnon_location': member_data.get('can_turnon_location', False),
                    'support_sms': member_data.get('support_sms', True),
                    'support_phone': member_data.get('support_phone', True),
                    'created_time': created_time,
                    'updated_time': updated_time,
                    'last_location_time': last_location_time,
                    'extra_fields': member_data.get('extra_fields'),
                    'skills': member_data.get('skills'),
                }

                if member_id in existing_members:
                    # Update existing member
                    member = existing_members[member_id]
                    for field, value in member_fields.items():
                        setattr(member, field, value)
                    members_to_update.append(member)
                else:
                    # Create new member
                    member_fields['id'] = member_id
                    members_to_create.append(Arrivy_TeamMember(**member_fields))

            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Error processing team member {member_data.get('id', 'unknown')}: {str(e)}"))
                continue

        # Bulk save to database
        created, updated = self.save_team_members(members_to_create, members_to_update)
        self.stdout.write(f"Created {created} team members, updated {updated} team members")

    def save_team_members(self, members_to_create, members_to_update):
        """Save team members to database with error handling."""
        created_count = 0
        updated_count = 0

        try:
            with transaction.atomic():
                if members_to_create:
                    created_before = Arrivy_TeamMember.objects.count()
                    Arrivy_TeamMember.objects.bulk_create(
                        members_to_create, 
                        batch_size=BATCH_SIZE,
                        ignore_conflicts=True
                    )
                    created_after = Arrivy_TeamMember.objects.count()
                    created_count = created_after - created_before

                if members_to_update:
                    update_fields = [
                        'external_id', 'name', 'first_name', 'last_name', 'email', 'phone',
                        'image_path', 'image_id', 'username', 'role', 'permission', 'group_id',
                        'group_name', 'timezone', 'address', 'is_active', 'is_online',
                        'can_turnon_location', 'support_sms', 'support_phone', 'created_time',
                        'updated_time', 'last_location_time', 'extra_fields', 'skills'
                    ]
                    
                    Arrivy_TeamMember.objects.bulk_update(members_to_update, update_fields, batch_size=BATCH_SIZE)
                    updated_count = len(members_to_update)

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error saving team members: {str(e)}"))
            logger.exception("Error saving team members to database")
            raise

        return created_count, updated_count

    def get_last_sync(self, endpoint):
        """Get the last sync time for team members."""
        try:
            history = Arrivy_SyncHistory.objects.get(endpoint=endpoint)
            return history.last_synced_at
        except Arrivy_SyncHistory.DoesNotExist:
            return None

    def update_last_sync(self, endpoint):
        """Update the last sync time for team members."""
        now = timezone.now()
        history, created = Arrivy_SyncHistory.objects.get_or_create(
            endpoint=endpoint,
            defaults={'last_synced_at': now}
        )
        if not created:
            history.last_synced_at = now
            history.save()

    def parse_datetime(self, value):
        """Parse a datetime string into a datetime object."""
        if not value:
            return None
        
        try:
            for fmt in [
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%dT%H:%M:%S",
            ]:
                try:
                    dt = datetime.strptime(value, fmt)
                    return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                except ValueError:
                    continue
            
            logger.warning(f"Could not parse datetime: {value}")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing datetime {value}: {str(e)}")
            return None
