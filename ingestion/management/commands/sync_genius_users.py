import requests
from django.core.management.base import BaseCommand
from ingestion.models import Genius_UserData
from ingestion.utils import parse_datetime_obj, process_batches
from tqdm import tqdm

BATCH_SIZE = 500

class Command(BaseCommand):
    help = "Sync Genius users from an external API."

    def handle(self, *args, **options):
        api_url = "https://api.example.com/genius/users"
        response = requests.get(api_url)

        if response.status_code != 200:
            self.stdout.write(self.style.ERROR(f"Failed to fetch data from API: {response.status_code}"))
            return

        users = response.json()
        user_ids = [user["id"] for user in users]
        existing_users = Genius_UserData.objects.in_bulk(user_ids)

        to_create = []
        to_update = []

        self.stdout.write(self.style.SUCCESS(f"Processing {len(users)} users from API..."))

        for user in tqdm(users):
            try:
                user_id = user["id"]
                fields = {
                    "first_name": user.get("first_name", ""),
                    "last_name": user.get("last_name", ""),
                    "email": user.get("email"),
                    "birth_date": parse_datetime_obj(user.get("birth_date")),
                    "hired_on": parse_datetime_obj(user.get("hired_on")),
                    "start_date": parse_datetime_obj(user.get("start_date")),
                    "add_user_id": user.get("add_user_id"),
                    "add_datetime": parse_datetime_obj(user.get("add_datetime")),
                }

                if user_id in existing_users:
                    user_instance = existing_users[user_id]
                    for attr, val in fields.items():
                        setattr(user_instance, attr, val)
                    to_update.append(user_instance)
                else:
                    fields["id"] = user_id
                    to_create.append(Genius_UserData(**fields))

                if len(to_update) >= BATCH_SIZE or len(to_create) >= BATCH_SIZE:
                    process_batches(to_create, to_update, Genius_UserData, fields.keys(), BATCH_SIZE)

            except (ValueError, KeyError) as e:
                self.stdout.write(self.style.WARNING(f"Skipping user due to error: {user}. Error: {e}"))

        # Final batch processing
        process_batches(to_create, to_update, Genius_UserData, fields.keys(), BATCH_SIZE)

        self.stdout.write(self.style.SUCCESS("User sync completed."))