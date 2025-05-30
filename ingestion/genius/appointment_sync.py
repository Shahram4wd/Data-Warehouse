from ingestion.models import Appointment
from .base_sync import BaseGeniusSync

class AppointmentSync(BaseGeniusSync):
    object_name = "appointments"
    api_endpoint = "/api/appointments/appointment/"
    model_class = Appointment
    env_batch_size_key = "APPOINTMENT_SYNC_BATCH_SIZE"
    
    def process_item(self, item):
        Appointment.objects.update_or_create(
            id=item["id"],
            defaults={
                "prospect_id": item.get("prospect"),
                "division_id": item.get("division"),
                "appointment_type_id": item.get("appointment_type"),
                "outcome_id": item.get("outcome"),
                "scheduled_datetime": item.get("scheduled_datetime"),
                "completed_datetime": item.get("completed_datetime") or None,
                "canceled_datetime": item.get("canceled_datetime") or None,
                "assigned_user_id": item.get("assigned_user"),
                "created_by_user_id": item.get("created_by_user"),
                "notes": item.get("notes") or "",
                "status": item.get("status"),
            }
        )