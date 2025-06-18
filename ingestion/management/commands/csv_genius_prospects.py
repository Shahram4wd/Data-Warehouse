import os
from django.core.management.base import BaseCommand
from django.db import transaction
from ingestion.models.genius import Genius_Prospect, Genius_Division
from ingestion.utils import get_mysql_connection
from tqdm import tqdm

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 100))  # Reduce batch size for memory

class Command(BaseCommand):
    help = "Download prospects directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="prospect",
            help="The name of the table to download data from. Defaults to 'prospect'."
        )
        parser.add_argument(
            "--limit",
            type=int,
            help="Limit the number of records to process (for testing)"
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        limit = options.get("limit")

        connection = None
        try:
            connection = get_mysql_connection()
            cursor = connection.cursor()

            # Get total record count
            count_query = f"SELECT COUNT(*) FROM {table_name}"
            if limit:
                count_query += f" LIMIT {limit}"
            
            cursor.execute(count_query)
            total_records = cursor.fetchone()[0]
            self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))

            # Preload divisions once to avoid repeated queries
            divisions_dict = {div.id: div for div in Genius_Division.objects.all()}

            # Process records in smaller batches with progress tracking
            processed = 0
            for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
                batch_query = f"""
                    SELECT id, division_id, first_name, last_name, alt_first_name, alt_last_name,
                           address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                           add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id
                    FROM {table_name}
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """
                if limit and offset >= limit:
                    break
                    
                cursor.execute(batch_query)
                rows = cursor.fetchall()
                
                if not rows:
                    break
                    
                self._process_batch(rows, divisions_dict)
                processed += len(rows)
                
                # Memory cleanup
                if processed % (BATCH_SIZE * 10) == 0:
                    self.stdout.write(f"Processed {processed} records...")

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
            raise
        finally:
            if connection:
                cursor.close()
                connection.close()

    @transaction.atomic
    def _process_batch(self, rows, divisions_dict):
        """Process a single batch of records with database transaction."""
        to_create = []
        to_update = []
        
        # Get existing records in one query
        existing_records = Genius_Prospect.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                (
                    record_id, division_id, first_name, last_name, alt_first_name, alt_last_name,
                    address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                    add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id
                ) = row

                # Use preloaded divisions
                division = divisions_dict.get(division_id)

                if record_id in existing_records:
                    record_instance = existing_records[record_id]
                    # Update fields
                    record_instance.division = division
                    record_instance.first_name = first_name
                    record_instance.last_name = last_name
                    record_instance.alt_first_name = alt_first_name
                    record_instance.alt_last_name = alt_last_name
                    record_instance.address1 = address1
                    record_instance.address2 = address2
                    record_instance.city = city
                    record_instance.county = county
                    record_instance.state = state
                    record_instance.zip = zip
                    record_instance.phone1 = phone1
                    record_instance.phone2 = phone2
                    record_instance.email = email
                    record_instance.notes = notes
                    record_instance.add_user_id = add_user_id
                    record_instance.add_date = add_date
                    record_instance.marketsharp_id = marketsharp_id
                    record_instance.leap_customer_id = leap_customer_id
                    record_instance.third_party_source_id = third_party_source_id
                    to_update.append(record_instance)
                else:
                    to_create.append(Genius_Prospect(
                        id=record_id,
                        division=division,
                        first_name=first_name,
                        last_name=last_name,
                        alt_first_name=alt_first_name,
                        alt_last_name=alt_last_name,
                        address1=address1,
                        address2=address2,
                        city=city,
                        county=county,
                        state=state,
                        zip=zip,
                        phone1=phone1,
                        phone2=phone2,
                        email=email,
                        notes=notes,
                        add_user_id=add_user_id,
                        add_date=add_date,
                        marketsharp_id=marketsharp_id,
                        leap_customer_id=leap_customer_id,
                        third_party_source_id=third_party_source_id
                    ))
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"Skipping record {record_id}: {e}"))

        # Bulk operations with smaller batches
        if to_create:
            Genius_Prospect.objects.bulk_create(to_create, batch_size=50, ignore_conflicts=True)
        if to_update:
            Genius_Prospect.objects.bulk_update(
                to_update,
                [
                    'division', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                    'address1', 'address2', 'city', 'county', 'state', 'zip', 'phone1', 'phone2',
                    'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                    'third_party_source_id'
                ],
                batch_size=50
            )