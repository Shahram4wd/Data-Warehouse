import asyncio
import aiohttp
import os
import pprint


# Setup Django environment for standalone script
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "data_warehouse.settings")  # Adjust if needed
django.setup()
from ingestion.models.hubspot import Hubspot_GeniusUser

HUBSPOT_API_TOKEN = os.environ.get("HUBSPOT_API_TOKEN")
BASE_URL = "https://api.hubapi.com"
ENDPOINT = "/crm/v3/objects/2-42119425/"

def get_required_fields():
    # Return all NOT NULL fields except auto fields
    return [f.name for f in Hubspot_GeniusUser._meta.fields if not f.null and not f.blank and not f.auto_created]

def get_all_model_fields():
    # Return all model fields except auto fields
    return [f.name for f in Hubspot_GeniusUser._meta.fields if not f.auto_created]

async def fetch_sample_user():
    headers = {
        "Authorization": f"Bearer {HUBSPOT_API_TOKEN}",
        "Content-Type": "application/json"
    }
    url = f"{BASE_URL}{ENDPOINT}"
    # Request all model fields as properties from the API
    all_fields = get_all_model_fields()
    params = {"limit": 1, "properties": ",".join(all_fields)}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers, params=params) as response:
            print(f"Status: {response.status}")
            data = await response.json()
            print("\nAPI Response:")
            pprint.pprint(data)
            if data.get("results"):
                user = data["results"][0]
                props = user.get("properties", {})
                required_fields = get_required_fields()
                missing = []
                for field in required_fields:
                    # Check both top-level and properties
                    if field not in user and field not in props:
                        missing.append(field)
                print("\nRequired NOT NULL fields in Hubspot_GeniusUser:")
                print(required_fields)
                print("\nMissing in API response:")
                print(missing)
            else:
                print("No results in API response.")

if __name__ == "__main__":
    asyncio.run(fetch_sample_user())
