import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Prospect, Genius_Division
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import datetime, timezone as dt_timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download prospects directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="prospect",
            help="The name of the table to download data from. Defaults to 'prospect'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            divisions = self._preload_divisions()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, divisions)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_divisions(self):
        """Preload divisions for lookup."""
        return {division.id: division for division in Genius_Division.objects.all()}
    
    def _process_all_records(self, cursor, table_name, divisions):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, divisions)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, divisions):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        cursor.execute(f"""
            SELECT id, division_id, first_name, last_name, alt_first_name, alt_last_name,
                   address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                   add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, divisions)
    
    def _process_batch(self, rows, divisions):
        """Process a batch of prospect records."""
        to_create = []
        to_update = []
        existing_records = Genius_Prospect.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (
                    record_id, division_id, first_name, last_name, alt_first_name, alt_last_name,
                    address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                    add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id
                ) = row

                # Get division
                division = divisions.get(division_id)
                
                # Process datetime fields
                add_date = self._parse_datetime(add_date)

                # Create or update record
                if record_id in existing_records:
                    record = self._update_record(existing_records[record_id], division, first_name, last_name,
                                           alt_first_name, alt_last_name, address1, address2, city, county,
                                           state, zip, phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, third_party_source_id)
                    to_update.append(record)
                else:
                    record = self._create_record(record_id, division, first_name, last_name, alt_first_name,
                                           alt_last_name, address1, address2, city, county, state, zip,
                                           phone1, phone2, email, notes, add_user_id, add_date,
                                           marketsharp_id, leap_customer_id, third_party_source_id)
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _update_record(self, record, division, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id):
        """Update an existing prospect record."""
        record.division = division
        record.first_name = first_name
        record.last_name = last_name
        record.alt_first_name = alt_first_name
        record.alt_last_name = alt_last_name
        record.address1 = address1
        record.address2 = address2
        record.city = city
        record.county = county
        record.state = state
        record.zip = zip
        record.phone1 = phone1
        record.phone2 = phone2
        record.email = email
        record.notes = notes
        record.add_user_id = add_user_id
        record.add_date = add_date
        record.marketsharp_id = marketsharp_id
        record.leap_customer_id = leap_customer_id
        record.third_party_source_id = third_party_source_id
        return record
    
    def _create_record(self, record_id, division, first_name, last_name, alt_first_name, alt_last_name,
                     address1, address2, city, county, state, zip, phone1, phone2, email, notes,
                     add_user_id, add_date, marketsharp_id, leap_customer_id, third_party_source_id):
        """Create a new prospect record."""
        return Genius_Prospect(
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
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_Prospect.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            
            if to_update:
                Genius_Prospect.objects.bulk_update(
                    to_update,
                    [
                        'division', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
                        'address1', 'address2', 'city', 'county', 'state', 'zip', 'phone1', 'phone2',
                        'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id',
                        'third_party_source_id'
                    ],
                    batch_size=BATCH_SIZE
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            self._fallback_individual_saves(to_create + to_update)
    
    def _fallback_individual_saves(self, records):
        """Fallback to individual saves when bulk operations fail."""
        for record in records:
            try:
                record.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {e}"))
    
    def _parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value
