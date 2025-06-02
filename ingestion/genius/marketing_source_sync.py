from ingestion.models.genius import Genius_MarketingSource  # Updated import
from .base_sync import BaseGeniusSync

class MarketingSourceSync(BaseGeniusSync):
    object_name = "marketing_sources"
    api_endpoint = "/api/marketing/marketing-sources/"
    model_class = Genius_MarketingSource  # Updated model class
    
    def process_item(self, item):
        Genius_MarketingSource.objects.update_or_create(
            id=item["id"],
            defaults={
                "label": item.get("label"),
                "type_id": item.get("type_id"),
                "description": item.get("description") or "",
                "start_date": item.get("start_date") or None,
                "end_date": item.get("end_date") or None,
                "add_user_id": item.get("add_user"),
                "add_date": item.get("add_date") or None,
                "is_active": item.get("is_active", True),
                "is_allow_lead_modification": item.get("is_allow_lead_modification", False),
            }
        )