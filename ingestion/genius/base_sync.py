import os
import requests
from urllib.parse import urlencode
from django.utils.timezone import now as timezone_now
from ingestion.models import SyncTracker

class BaseGeniusSync:
    """Base class for syncing data from Genius API"""
    
    # Override these in subclasses
    object_name = None  # e.g. "users", "divisions", "prospects"
    api_endpoint = None  # e.g. "/api/users/users/"
    model_class = None  # e.g. UserData, Division, Prospect
    env_batch_size_key = None  # e.g. "USER_SYNC_BATCH_SIZE"
    default_batch_size = 100
    
    def __init__(self, client):
        self.client = client
        self.batch_size = int(os.environ.get(self.env_batch_size_key, self.default_batch_size))
    
    def get_last_synced(self):
        """Get the timestamp of the last successful sync for this object type"""
        tracker, _ = SyncTracker.objects.get_or_create(
            object_name=self.object_name,
            defaults={"last_synced_at": None}
        )
        return tracker.last_synced_at
    
    def update_last_synced(self):
        """Update the last sync timestamp to now"""
        SyncTracker.objects.update_or_create(
            object_name=self.object_name,
            defaults={"last_synced_at": timezone_now()}
        )
    
    def build_api_url(self, last_synced):
        """Build the API URL with parameters"""
        params = {"updated_since": last_synced.isoformat()} if last_synced else {}
        params["limit"] = self.batch_size
        
        query = f"?{urlencode(params)}" if params else ""
        url = f"{self.api_endpoint}{query}"
        return f"{self.client.base_url.rstrip('/')}{url}"
    
    def process_item(self, item):
        """Process a single item from the API response.
        Override this in subclasses to handle model-specific field mapping.
        """
        raise NotImplementedError("Subclasses must implement process_item()")
    
    def sync_all(self):
        """Sync all objects of this type"""
        last_synced = self.get_last_synced()
        full_url = self.build_api_url(last_synced)
        
        total_synced = 0
        batch_count = 0
        
        while full_url:
            batch_count += 1
            print(f"Fetching batch {batch_count} of {self.object_name}: {full_url}")
            
            try:
                response = requests.get(full_url, headers=self.client._headers())
                response.raise_for_status()  # This will raise an exception for HTTP errors
                
                # Debug info to help troubleshoot
                print(f"Response status: {response.status_code}")
                print(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
                print(f"Response content preview: {response.text[:100]}...")
                
                # Try to parse JSON response
                try:
                    data = response.json()
                except ValueError as e:
                    print(f"Failed to parse JSON: {e}")
                    print(f"Full response content: {response.text}")
                    raise
                
                # Check if the expected fields exist in the response
                if "results" not in data:
                    raise ValueError(f"API response missing 'results' field. Response structure: {data.keys()}")
                
                current_batch_count = 0
                for item in data["results"]:
                    self.process_item(item)
                    total_synced += 1
                    current_batch_count += 1
                
                print(f"Processed batch {batch_count}: {current_batch_count} {self.object_name}")
                full_url = data.get("next")
                
            except requests.exceptions.RequestException as e:
                print(f"HTTP request failed: {e}")
                raise
        
        print(f"Total batches: {batch_count}, Total {self.object_name} synced: {total_synced}")
        self.update_last_synced()
        return total_synced
    
    def sync_single(self, item_id):
        """Sync a single object by ID"""
        url = f"{self.client.base_url.rstrip('/')}{self.api_endpoint}{item_id}/"
        print(f"Fetching single {self.object_name} with ID {item_id} from: {url}")
        
        try:
            response = requests.get(url, headers=self.client._headers())
            response.raise_for_status()
            
            # Debug info
            print(f"Response status: {response.status_code}")
            print(f"Response content type: {response.headers.get('Content-Type', 'unknown')}")
            
            try:
                item = response.json()
            except ValueError as e:
                print(f"Failed to parse JSON: {e}")
                print(f"Full response content: {response.text}")
                raise
            
            self.process_item(item)
            return item["id"]
            
        except requests.exceptions.RequestException as e:
            print(f"HTTP request failed: {e}")
            raise