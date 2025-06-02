from ingestion.models.genius import Genius_Appointment  # Updated import
from .base_sync import BaseGeniusSync

class AppointmentSync(BaseGeniusSync):
    object_name = "appointments"
    api_endpoint = "/api/appointments/appointment/"
    model_class = Genius_Appointment  # Updated model class
    
    def process_item(self, item):
        Genius_Appointment.objects.update_or_create(
            id=item["id"],
            defaults={
                "prospect_id": item.get("prospect"),
                "user_id": item.get("user"),
                "type_id": item.get("type"),
                "date": item.get("date"),
                "time": item.get("time"),
                "duration": item.get("duration"),
                "address1": item.get("address1") or "",
                "address2": item.get("address2") or "",
                "city": item.get("city") or "",
                "state": item.get("state") or "",
                "zip": item.get("zip") or "",
                "email": item.get("email"),
                "notes": item.get("notes"),
                "add_user_id": item.get("add_user"),
                "add_date": item.get("add_date"),
            }
        )