import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_Division, Genius_DivisionGroup
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))

class Command(BaseCommand):
    help = "Download divisions directly from the database and update the local database."
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="division",
            help="The name of the table to download data from. Defaults to 'division'."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        connection = None

        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            division_groups = self._preload_division_groups()
            
            # Process records in batches
            self._process_all_records(cursor, table_name, division_groups)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def _preload_division_groups(self):
        """Preload division groups for lookup."""
        return {group.id: group for group in Genius_DivisionGroup.objects.all()}
    
    def _process_all_records(self, cursor, table_name, division_groups):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, BATCH_SIZE), desc="Processing batches"):
            self._process_batch_at_offset(cursor, table_name, offset, division_groups)
    
    def _process_batch_at_offset(self, cursor, table_name, offset, division_groups):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        cursor.execute(f"""
            SELECT id, group_id, region_id, label, abbreviation, 
                   is_utility, is_corp, is_omniscient, is_inactive
            FROM {table_name}
            LIMIT {BATCH_SIZE} OFFSET {offset}
        """)
        rows = cursor.fetchall()
        
        # Process the batch
        self._process_batch(rows, division_groups)
    
    def _process_batch(self, rows, division_groups):
        """Process a batch of division records."""
        to_create = []
        to_update = []
        existing_records = Genius_Division.objects.in_bulk([row[0] for row in rows])

        for row in rows:
            try:
                # Extract fields from row
                (
                    record_id, group_id, region_id, label, abbreviation, 
                    is_utility, is_corp, is_omniscient, is_inactive
                ) = row

                # Get division group
                division_group = division_groups.get(group_id) if group_id else None
                
                # Convert tinyint values to appropriate types
                is_utility = int(is_utility) if is_utility is not None else 0
                is_corp = int(is_corp) if is_corp is not None else 0
                is_omniscient = int(is_omniscient) if is_omniscient is not None else 0
                is_inactive = int(is_inactive) if is_inactive is not None else 0

                # Create or update record
                if record_id in existing_records:
                    record = self._update_record(
                        existing_records[record_id], 
                        group_id, region_id, label, abbreviation,
                        is_utility, is_corp, is_omniscient, is_inactive
                    )
                    to_update.append(record)
                else:
                    record = self._create_record(
                        record_id, group_id, region_id, label, abbreviation,
                        is_utility, is_corp, is_omniscient, is_inactive
                    )
                    to_create.append(record)
                    
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error processing record ID {row[0] if row else 'unknown'}: {e}"))

        # Save records to database
        self._save_records(to_create, to_update)
    
    def _update_record(self, record, group_id, region_id, label, abbreviation,
                      is_utility, is_corp, is_omniscient, is_inactive):
        """Update an existing division record."""
        record.group_id = group_id
        record.region_id = region_id
        record.label = label
        record.abbreviation = abbreviation
        record.is_utility = is_utility
        record.is_corp = is_corp
        record.is_omniscient = is_omniscient
        record.is_inactive = is_inactive
        return record
    
    def _create_record(self, record_id, group_id, region_id, label, abbreviation,
                      is_utility, is_corp, is_omniscient, is_inactive):
        """Create a new division record."""
        return Genius_Division(
            id=record_id,
            group_id=group_id,
            region_id=region_id,
            label=label,
            abbreviation=abbreviation,
            is_utility=is_utility,
            is_corp=is_corp,
            is_omniscient=is_omniscient,
            is_inactive=is_inactive
        )
    
    def _save_records(self, to_create, to_update):
        """Save records to database with error handling."""
        try:
            if to_create:
                Genius_Division.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
            
            if to_update:
                Genius_Division.objects.bulk_update(
                    to_update,
                    [
                        'group_id', 'region_id', 'label', 'abbreviation',
                        'is_utility', 'is_corp', 'is_omniscient', 'is_inactive'
                    ],
                    batch_size=BATCH_SIZE
                )
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            # Fallback to individual saves
            for record in to_create + to_update:
                try:
                    record.save()
                except Exception as individual_error:
                    self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {individual_error}"))