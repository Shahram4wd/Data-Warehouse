from ingestion.models import Service
from .base_sync import BaseGeniusSync

class ServiceSync(BaseGeniusSync):
    object_name = "services"
    api_endpoint = "/api/services/service/"
    model_class = Service
    
    def process_item(self, item):
        Service.objects.update_or_create(
            id=item["id"],
            defaults={
                "name": item.get("name"),
                "description": item.get("description") or "",
                "division_id": item.get("division"),
                "is_active": item.get("is_active", True),
                "price": item.get("price") or 0.0,
                "category_id": item.get("category"),
                "add_user_id": item.get("add_user"),
                "add_datetime": item.get("add_datetime") or None,
            }
        )