import requests
from urllib.parse import urlencode
from django.utils import timezone
from ingestion.models import Genius_UserData, SyncTracker, Genius_Division
from .base_sync import BaseGeniusSync
import logging
from django.db import transaction
from ingestion.models.genius import Genius_Division, Genius_DivisionGroup
from ingestion.utils import get_mysql_connection


logger = logging.getLogger(__name__)


def get_last_synced(object_name):
    tracker, _ = SyncTracker.objects.get_or_create(
        object_name=object_name,
        defaults={"last_synced_at": None}
    )
    return tracker.last_synced_at


def update_last_synced(object_name):
    SyncTracker.objects.update_or_create(
        object_name=object_name,
        defaults={"last_synced_at": timezone.now()}
    )


def sync_user_data(client):
    object_name = "users"
    last_synced = get_last_synced(object_name)

    params = {"updated_since": last_synced.isoformat()} if last_synced else {}
    query = f"?{urlencode(params)}" if params else ""
    url = f"/api/users/users/{query}"
    full_url = f"{client.base_url.rstrip('/')}{url}"

    total_synced = 0

    while full_url:
        print(f"Fetching: {full_url}")
        response = requests.get(full_url, headers=client._headers())
        response.raise_for_status()
        data = response.json()

        for item in data.get("results", []):
            Genius_UserData.objects.update_or_create(
                id=item["id"],
                defaults={
                    "division_id": item.get("division"),
                    "first_name": item.get("first_name"),
                    "first_name_alt": item.get("first_name_alt") or None,
                    "last_name": item.get("last_name") or None,
                    "email": item.get("email") or None,
                    "personal_email": item.get("personal_email") or None,
                    "birth_date": item.get("birth_date") or None,
                    "gender_id": item.get("gender", {}).get("id") if item.get("gender") else None,
                    "marital_status_id": item.get("marital_status", {}).get("id") if item.get("marital_status") else None,
                    "time_zone_name": item.get("time_zone_name") or None,
                    "title_id": item.get("title"),
                    "manager_user_id": item.get("manager"),
                    "hired_on": item.get("hired_on") or None,
                    "start_date": item.get("start_date") or None,
                    "add_user_id": item.get("add_user"),
                    "add_datetime": item.get("add_datetime") or None,
                }
            )
            total_synced += 1

        full_url = data.get("next")

    update_last_synced(object_name)
    print(f"Total users synced: {total_synced}")
    return total_synced


class DivisionSync(BaseGeniusSync):
    object_name = "divisions"
    api_endpoint = "/api/divisions/division/"
    model_class = Genius_Division
    
    def process_item(self, item):
        Genius_Division.objects.update_or_create(
            id=item["id"],
            defaults={
                "name": item.get("label"),  # Use "label" from response instead of "name"
                "abbreviation": item.get("abbreviation"),
                "is_inactive": item.get("is_inactive", False),
                "group_id": item.get("group", {}).get("id") if item.get("group") else None,
                "region_id": item.get("region", {}).get("id") if item.get("region") else None,
                "is_utility": item.get("is_utility", False),
                "is_corp": item.get("is_corp", False),
            }
        )


def sync_divisions(batch_size=500):
    """
    Synchronize divisions from Genius database to local database.
    
    Args:
        batch_size (int): Number of records to process in a batch
        
    Returns:
        tuple: (created_count, updated_count, total_count)
    """
    logger.info("Starting division sync from Genius")
    connection = None
    created_count = 0
    updated_count = 0
    total_count = 0
    
    try:
        # Database connection
        connection = get_mysql_connection()
        cursor = connection.cursor()
        
        # Get total record count
        cursor.execute("SELECT COUNT(*) FROM division")
        total_count = cursor.fetchone()[0]
        logger.info(f"Found {total_count} divisions to sync")
        
        # Preload division groups for lookup
        division_groups = {group.id: group for group in Genius_DivisionGroup.objects.all()}
        
        # Fetch all divisions
        cursor.execute("""
            SELECT id, group_id, region_id, label, abbreviation, 
                   is_utility, is_corp, is_omniscient, is_inactive
            FROM division
        """)
        
        rows = cursor.fetchall()
        existing_divisions = Genius_Division.objects.in_bulk([row[0] for row in rows])
        
        to_create = []
        to_update = []
        
        # Process rows
        for row in rows:
            (
                record_id, group_id, region_id, label, abbreviation, 
                is_utility, is_corp, is_omniscient, is_inactive
            ) = row
            
            # Convert tinyint values to appropriate types
            is_utility = int(is_utility) if is_utility is not None else 0
            is_corp = int(is_corp) if is_corp is not None else 0
            is_omniscient = int(is_omniscient) if is_omniscient is not None else 0
            is_inactive = int(is_inactive) if is_inactive is not None else 0
            
            if record_id in existing_divisions:
                # Update existing division
                division = existing_divisions[record_id]
                division.group_id = group_id
                division.region_id = region_id
                division.label = label
                division.abbreviation = abbreviation
                division.is_utility = is_utility
                division.is_corp = is_corp
                division.is_omniscient = is_omniscient
                division.is_inactive = is_inactive
                to_update.append(division)
                updated_count += 1
            else:
                # Create new division
                division = Genius_Division(
                    id=record_id,
                    group_id=group_id,
                    region_id=region_id,
                    label=label,
                    abbreviation=abbreviation,
                    is_utility=is_utility,
                    is_corp=is_corp,
                    is_omniscient=is_omniscient,
                    is_inactive=is_inactive
                )
                to_create.append(division)
                created_count += 1
            
            # Process in batches
            if len(to_create) >= batch_size:
                with transaction.atomic():
                    Genius_Division.objects.bulk_create(to_create)
                to_create = []
            
            if len(to_update) >= batch_size:
                with transaction.atomic():
                    Genius_Division.objects.bulk_update(
                        to_update,
                        ['group_id', 'region_id', 'label', 'abbreviation', 
                         'is_utility', 'is_corp', 'is_omniscient', 'is_inactive']
                    )
                to_update = []
        
        # Save any remaining records
        if to_create:
            with transaction.atomic():
                Genius_Division.objects.bulk_create(to_create)
        
        if to_update:
            with transaction.atomic():
                Genius_Division.objects.bulk_update(
                    to_update,
                    ['group_id', 'region_id', 'label', 'abbreviation', 
                     'is_utility', 'is_corp', 'is_omniscient', 'is_inactive']
                )
        
        logger.info(f"Division sync completed. Created: {created_count}, Updated: {updated_count}, Total: {total_count}")
        return created_count, updated_count, total_count
        
    except Exception as e:
        logger.error(f"Error syncing divisions: {str(e)}")
        raise
        
    finally:
        if connection:
            cursor.close()
            connection.close()
