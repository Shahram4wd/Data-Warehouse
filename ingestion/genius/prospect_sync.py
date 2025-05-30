from ingestion.models import Prospect
from .base_sync import BaseGeniusSync

class ProspectSync(BaseGeniusSync):
    object_name = "prospects"
    api_endpoint = "/api/customers/prospect/"
    model_class = Prospect
    
    def process_item(self, item):
        Prospect.objects.update_or_create(
            id=item["id"],
            defaults={
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "email": item.get("email") or None,
                "phone": item.get("phone") or None,
                "division_id": item.get("division"),
                "address_line_1": item.get("address_line_1") or None,
                "address_line_2": item.get("address_line_2") or None,
                "city": item.get("city") or None,
                "state": item.get("state") or None,
                "postal_code": item.get("postal_code") or None,
                "source_id": item.get("source"),
                "add_user_id": item.get("add_user"),
                "add_datetime": item.get("add_datetime") or None,
                "status": item.get("status") or None,
            }
        )