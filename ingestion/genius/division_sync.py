import requests
from ingestion.models import Division
from ingestion.genius.genius_client import GeniusClient
from django.conf import settings

def sync_divisions():
    client = GeniusClient(
        settings.GENIUS_API_URL,
        settings.GENIUS_USERNAME,
        settings.GENIUS_PASSWORD
    )

    url = "/api/divisions/division/"
    full_url = f"{client.base_url.rstrip('/')}{url}"

    while full_url:
        print(f"Fetching: {full_url}")
        response = requests.get(full_url, headers=client._headers())
        response.raise_for_status()
        data = response.json()

        for item in data["results"]:
            Division.objects.update_or_create(
                id=item["id"],
                defaults={
                    "group_id": item.get("group", {}).get("id"),
                    "region_id": item.get("region", {}).get("id") if item.get("region") else None,
                    "label": item.get("label"),
                    "abbreviation": item.get("abbreviation"),
                    "is_utility": item.get("is_utility", False),
                    "is_corp": item.get("is_corp", False),
                    "is_omniscient": item.get("is_omniscient", False),
                }
            )

        full_url = data.get("next")  # move to next page if paginated
