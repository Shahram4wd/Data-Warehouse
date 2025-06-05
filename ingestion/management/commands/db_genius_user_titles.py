import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_UserTitle
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download user title data directly from the database and update the local database."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="user_title",
            help="The name of the table to download data from. Defaults to 'user_title'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Process records in batches
            self._process_all_records(cursor, table_name)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _process_all_records(self, cursor, table_name):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset)
    
    def _process_batch_at_offset(self, cursor, table_name, offset):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        cursor.execute(f"""
            SELECT id, title, abbreviation, roles, type_id, section_id, sort, 
                   pay_component_group_id, is_active, is_unique_per_division
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows)
    
    def _process_batch(self, rows):
        """Process a batch of user title records."""
        to_create = []
        to_update = []
        existing_records = Genius_UserTitle.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (
                    title_id, title, abbreviation, roles, type_id, section_id, sort,
                    pay_component_group_id, is_active, is_unique_per_division
                ) = row

                # Process boolean fields (tinyint)
                is_active = bool(is_active) if is_active is not None else True
                is_unique_per_division = bool(is_unique_per_division) if is_unique_per_division is not None else False

                # Create or update record
                if title_id in existing_records:
                    record = self._update_record(
                        existing_records[title_id], title, abbreviation, roles, type_id,
                        section_id, sort, pay_component_group_id, is_active,
                        is_unique_per_division
                    )
                    to_update.append(record)
                else:
                    record = self._create_record(
                        title_id, title, abbreviation, roles, type_id,
                        section_id, sort, pay_component_group_id, is_active,
                        is_unique_per_division
                    )
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _update_record(self, record, title, abbreviation, roles, type_id,
                      section_id, sort, pay_component_group_id, is_active,
                      is_unique_per_division):
        """Update an existing user title record."""
        record.title = title
        record.abbreviation = abbreviation
        record.roles = roles
        record.type_id = type_id
        record.section_id = section_id
        record.sort = sort
        record.pay_component_group_id = pay_component_group_id
        record.is_active = is_active
        record.is_unique_per_division = is_unique_per_division
        
        return record
    
    def _create_record(self, title_id, title, abbreviation, roles, type_id,
                      section_id, sort, pay_component_group_id, is_active,
                      is_unique_per_division):
        """Create a new user title record."""
        return Genius_UserTitle(
            id=title_id,
            title=title,
            abbreviation=abbreviation,
            roles=roles,
            type_id=type_id,
            section_id=section_id,
            sort=sort,
            pay_component_group_id=pay_component_group_id,
            is_active=is_active,
            is_unique_per_division=is_unique_per_division
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_UserTitle.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            
            if to_update:
                fields_to_update = [
                    'title', 'abbreviation', 'roles', 'type_id', 'section_id',
                    'sort', 'pay_component_group_id', 'is_active', 'is_unique_per_division'
                ]
                
                Genius_UserTitle.objects.bulk_update(to_update, fields_to_update, batch_size=BATCH_SIZE)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            # Fallback to individual saves
            for record in to_create + to_update:
                try:
                    record.save()
                except Exception as individual_error:
                    self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {individual_error}"))
