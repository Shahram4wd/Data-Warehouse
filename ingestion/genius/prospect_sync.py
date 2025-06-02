from ingestion.models.genius import Genius_Prospect  # Updated import
from .base_sync import BaseGeniusSync

class ProspectSync(BaseGeniusSync):
    object_name = "prospects"
    api_endpoint = "/api/customers/prospect/"
    model_class = Genius_Prospect  # Updated model class
    
    def process_item(self, item):
        Genius_Prospect.objects.update_or_create(
            id=item["id"],
            defaults={
                "first_name": item.get("first_name"),
                "last_name": item.get("last_name"),
                "email": item.get("email") or None,
                "phone1": item.get("phone1") or None,
                "division_id": item.get("division"),
                "address1": item.get("address1") or None,
                "address2": item.get("address2") or None,
                "city": item.get("city") or None,
                "state": item.get("state") or None,
                "zip": item.get("zip") or None,
                "notes": item.get("notes") or None,
                "add_user_id": item.get("add_user"),
                "add_date": item.get("add_date") or None,
            }
        )