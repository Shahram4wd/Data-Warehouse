import requests
from django.core.management.base import BaseCommand
from ingestion.models import Appointment
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm
from django.conf import settings
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.appointment_sync import AppointmentSync

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Sync appointments from Genius API. Syncs a single appointment if appointment_id is provided, otherwise syncs all appointments."

    def add_arguments(self, parser):
        parser.add_argument("--appointment_id", type=int, help="Optional: The ID of a specific appointment to sync", required=False)

    def handle(self, *args, **options):
        client = GeniusClient(
            settings.GENIUS_API_URL,
            settings.GENIUS_USERNAME,
            settings.GENIUS_PASSWORD
        )

        sync = AppointmentSync(client)
        appointment_id = options.get("appointment_id")
        
        try:
            if appointment_id:
                result_id = sync.sync_single(appointment_id)
                self.stdout.write(self.style.SUCCESS(f"Appointment {result_id} synced successfully."))
            else:
                total_synced = sync.sync_all()
                self.stdout.write(self.style.SUCCESS(f"All appointments sync complete. Total appointments synced: {total_synced}"))
        except Exception as e:
            mode = f"appointment {appointment_id}" if appointment_id else "all appointments"
            raise CommandError(f"Failed to sync {mode}: {e}")

        api_url = "https://api.example.com/genius/appointments"
        response = requests.get(api_url)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch data from API: {response.status_code}"))
            return

        appointments = response.json()
        appointment_ids = [appointment["id"] for appointment in appointments]
        existing_appointments = Appointment.objects.in_bulk(appointment_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(appointments)} appointments from API..."))

        for appointment in tqdm(appointments):
            try:
                appointment_id = appointment["id"]
                fields = {
                    "prospect_id": appointment.get("prospect_id"),
                    "user_id": appointment.get("user_id"),
                    "type_id": appointment.get("type_id"),
                    "date": parse_datetime_obj(appointment.get("date")),
                    "time": parse_datetime_obj(appointment.get("time")),
                    "duration": parse_datetime_obj(appointment.get("duration")),
                    "address1": appointment.get("address1", ""),
                    "address2": appointment.get("address2", ""),
                    "city": appointment.get("city", ""),
                    "state": appointment.get("state", ""),
                    "zip": appointment.get("zip", ""),
                    "email": appointment.get("email"),
                    "notes": appointment.get("notes"),
                    "add_user_id": appointment.get("add_user_id"),
                    "add_date": parse_datetime_obj(appointment.get("add_date")),
                    "assign_date": parse_datetime_obj(appointment.get("assign_date")),
                    "confirm_user_id": appointment.get("confirm_user_id"),
                    "confirm_date": parse_datetime_obj(appointment.get("confirm_date")),
                    "confirm_with": appointment.get("confirm_with"),
                    "spouses_present": appointment.get("spouses_present", False),
                    "is_complete": appointment.get("is_complete", False),
                    "complete_outcome_id": appointment.get("complete_outcome_id"),
                    "complete_user_id": appointment.get("complete_user_id"),
                    "complete_date": parse_datetime_obj(appointment.get("complete_date")),
                }

                if appointment_id in existing_appointments:
                    appointment_instance = existing_appointments[appointment_id]
                    for attr, val in fields.items():
                        setattr(appointment_instance, attr, val)
                    to_update.append(appointment_instance)
                else:
                    fields["id"] = appointment_id
                    to_create.append(Appointment(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, Appointment, fields.keys(), BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping appointment due to error: {appointment}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, Appointment, fields.keys(), BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("Appointment sync completed."))