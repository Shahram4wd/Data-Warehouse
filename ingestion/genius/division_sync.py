import requests
from urllib.parse import urlencode
from django.utils import timezone
from ingestion.models import UserData, SyncTracker


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
