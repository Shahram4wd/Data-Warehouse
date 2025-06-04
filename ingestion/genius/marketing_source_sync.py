from ingestion.models import MarketingSource
from .base_sync import BaseGeniusSync

class MarketingSourceSync(BaseGeniusSync):
    """
    Synchronizes marketing sources from Genius API to the local database.
    """
    object_name = "marketing_sources"
    api_endpoint = "/api/marketing_sources/"
    model_class = MarketingSource
    
    def map_fields(self, item):
        """Map API fields to model fields"""
        return {
            "id": item.get("id"),
            "name": item.get("name", "Unnamed Source"),
            "description": item.get("description", ""),
            "is_active": item.get("is_active", True),
        }
    
    def process_item(self, item):
        """Process a single marketing source item"""
        defaults = self.map_fields(item)
        item_id = defaults.pop("id")
        
        # Create or update the marketing source
        obj, created = MarketingSource.objects.update_or_create(
            id=item_id,
            defaults=defaults
        )
        
        return obj, created
    
    def sync(self, full=False):
        """
        Synchronize marketing sources with the Genius API.
        
        Args:
            full (bool): Whether to perform a full sync or an incremental sync.
            
        Returns:
            dict: Results of the sync operation.
        """
        results = self.sync_objects(full=full)
        return {
            "created": results.get("created", 0),
            "updated": results.get("updated", 0),
            "total": results.get("total", 0)
        }