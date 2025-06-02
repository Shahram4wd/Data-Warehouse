from ingestion.models.genius import Genius_Service  # Updated import
from .base_sync import BaseGeniusSync

class ServiceSync(BaseGeniusSync):
    object_name = "services"
    api_endpoint = "/api/services/service/"
    model_class = Genius_Service  # Updated model class
    
    def process_item(self, item):
        Genius_Service.objects.update_or_create(
            id=item["id"],
            defaults={
                "label": item.get("label"),
                "is_active": item.get("is_active", True),
                "is_lead_required": item.get("is_lead_required", False),
                "order_number": item.get("order_number") or 0,
            }
        )