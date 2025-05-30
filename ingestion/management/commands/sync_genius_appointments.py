from django.core.management.base import BaseCommand, CommandError
from ingestion.genius.genius_client import GeniusClient
from ingestion.genius.appointment_sync import AppointmentSync
from django.conf import settings

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