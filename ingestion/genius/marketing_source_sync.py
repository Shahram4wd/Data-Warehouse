from ingestion.models import MarketingSource
from .base_sync import BaseGeniusSync

class MarketingSourceSync(BaseGeniusSync):
    object_name = "marketing_sources"
    api_endpoint = "/api/marketing/marketing-sources/"
    model_class = MarketingSource
    
    def process_item(self, item):
        # Extract the marketing source type ID from the nested object
        marketing_source_type_id = None
        if item.get("marketing_source_type"):
            marketing_source_type_id = item["marketing_source_type"].get("id")
        
        MarketingSource.objects.update_or_create(
            id=item["id"],
            defaults={
                "label": item.get("label"),
                "type_id": marketing_source_type_id,  # Just use the ID directly
                "is_active": item.get("is_active", True),
                "description": item.get("description") or "",
                "start_date": item.get("start_date") or None,
                "end_date": item.get("end_date") or None,
                "add_user_id": item.get("add_user"),
                "add_date": item.get("add_date") or None,
                "is_allow_lead_modification": item.get("is_allow_lead_modification", False),
            }
        )