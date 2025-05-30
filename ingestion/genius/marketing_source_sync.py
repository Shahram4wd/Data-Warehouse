from ingestion.models import MarketingSource
from .base_sync import BaseGeniusSync

class MarketingSourceSync(BaseGeniusSync):
    object_name = "marketing_sources"
    api_endpoint = "/api/marketing/marketing-sources/"
    model_class = MarketingSource
    
    def process_item(self, item):
        MarketingSource.objects.update_or_create(
            id=item["id"],
            defaults={
                "label": item.get("label"),  # Using 'label' instead of 'name'
                "marketing_source_type_id": item.get("  ", {}).get("id") if item.get("marketing_source_type") else None,  # Using proper nested field
                "division_id": item.get("division"),
                "is_active": item.get("is_active", True),
                "description": item.get("description") or "",
                "start_date": item.get("start_date") or None,
                "end_date": item.get("end_date") or None,
                "add_user_id": item.get("add_user"),
                "add_date": item.get("add_date") or None,
                "is_allow_lead_modification": item.get("is_allow_lead_modification", False),
            }
        )