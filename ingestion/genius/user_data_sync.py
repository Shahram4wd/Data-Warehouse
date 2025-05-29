import requests
import os
from urllib.parse import urlencode
from django.utils.timezone import now as timezone_now
from django.conf import settings
from ingestion.models import UserData, SyncTracker

def get_last_synced(object_name):
    tracker, _ = SyncTracker.objects.get_or_create(
        object_name=object_name,
        defaults={"last_synced_at": None}  # allow initial null
    )
    return tracker.last_synced_at


def update_last_synced(object_name):
    SyncTracker.objects.update_or_create(
        object_name=object_name,
        defaults={"last_synced_at": timezone_now()}
    )


def sync_user_data(client):
    object_name = "users"
    last_synced = get_last_synced(object_name)
    
    # Get batch size from environment variables, default to 100 if not set
    batch_size = int(os.environ.get('USER_SYNC_BATCH_SIZE', 100))
    
    params = {"updated_since": last_synced.isoformat()} if last_synced else {}
    # Add pagination parameter for batch size
    params["limit"] = batch_size
    
    query = f"?{urlencode(params)}" if params else ""
    url = f"/api/users/users/{query}"
    full_url = f"{client.base_url.rstrip('/')}{url}"

    total_synced = 0
    batch_count = 0

    while full_url:
        batch_count += 1
        print(f"Fetching batch {batch_count}: {full_url}")
        response = requests.get(full_url, headers=client._headers())
        response.raise_for_status()
        data = response.json()

        current_batch_count = 0
        for item in data["results"]:
            UserData.objects.update_or_create(
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
                    "time_zone_name": item.get("time_zone_name") or "",
                    "title_id": item.get("title"),
                    "manager_user_id": item.get("manager"),
                    "hired_on": item.get("hired_on") or None,
                    "start_date": item.get("start_date") or None,
                    "add_user_id": item.get("add_user"),
                    "add_datetime": item.get("add_datetime") or None,
                }
            )
            total_synced += 1
            current_batch_count += 1

        print(f"Processed batch {batch_count}: {current_batch_count} users")
        full_url = data.get("next")

    print(f"Total batches: {batch_count}, Total users synced: {total_synced}")
    update_last_synced(object_name)
    return total_synced