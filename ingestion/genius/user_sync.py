from ingestion.models import UserData
from .base_sync import BaseGeniusSync

class UserSync(BaseGeniusSync):
    object_name = "users"
    api_endpoint = "/api/users/users/"
    model_class = UserData
    
    def process_item(self, item):
        UserData.objects.update_or_create(
            id=item["id"],
            defaults={
                "division_id": item.get("division"),
                "first_name": item.get("first_name"),
                "first_name_alt": item.get("first_name_alt") or None,
                "last_name": item.get("last_name") or None,
                "email": item.get("email") or None,
                "personal_email": item.get("personal_email") or None,
                "birth_date": item.get("birth_date") or None,
                "gender_id": item.get("gender", {}).get("id") if item.get("gender") else None,
                "marital_status_id": item.get("marital_status", {}).get("id") if item.get("marital_status") else None,
                "time_zone_name": item.get("time_zone_name") or "",
                "title_id": item.get("title"),
                "manager_user_id": item.get("manager"),
                "hired_on": item.get("hired_on") or None,
                "start_date": item.get("start_date") or None,
                "add_user_id": item.get("add_user"),
                "add_datetime": item.get("add_datetime") or None,
            }
        )