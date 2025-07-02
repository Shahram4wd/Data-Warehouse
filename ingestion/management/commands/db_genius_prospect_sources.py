import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models import Genius_ProspectSource, Genius_Prospect, Genius_MarketingSource
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone  # Import Python's datetime timezone

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 500))  # Default to 500 if not set

class Command(BaseCommand):
    help = "Download prospect sources directly from the database and update the local database."

    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default="prospect_source",
            help="The name of the table to download data from. Defaults to 'prospect_source'."
        )
        parser.add_argument(
            "--page",
            type=int,
            default=1,
            help="Starting page number (each page is BATCH_SIZE records). Defaults to 1."
        )

    def handle(self, *args, **options):
        table_name = options["table"]
        start_page = options["page"]

        connection = None  # Initialize the connection variable
        try:
            # Use the utility function to get the database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()

            # Preload related data into dictionaries for quick lookups
            prospects = {prospect.id: prospect for prospect in Genius_Prospect.objects.all()}
            marketing_sources = {source.id: source for source in Genius_MarketingSource.objects.all()}

            # Fetch total record count
            cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
            total_records = cursor.fetchone()[0]
            
            # Calculate starting offset based on page number
            start_offset = (start_page - 1) * BATCH_SIZE
            remaining_records = total_records - start_offset
            
            if start_offset >= total_records:
                self.stdout.write(self.style.ERROR(f"Starting page {start_page} exceeds total records. Total pages: {(total_records + BATCH_SIZE - 1) // BATCH_SIZE}"))
                return
            
            self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records:,}"))
            self.stdout.write(self.style.WARNING(f"Starting from page {start_page} (offset {start_offset:,}), processing {remaining_records:,} remaining records"))

            # Process records in batches starting from the specified page
            for offset in tqdm(range(start_offset, total_records, BATCH_SIZE), desc=f"Processing from page {start_page}"):
                cursor.execute(f"""
                    SELECT id, prospect_id, marketing_source_id, source_date, notes, add_user_id, add_date
                    FROM {table_name}
                    LIMIT {BATCH_SIZE} OFFSET {offset}
                """)
                rows = cursor.fetchall()
                if not rows:
                    break
                self._process_batch(rows, prospects, marketing_sources)

            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:  # Ensure the connection is closed only if it was established
                cursor.close()
                connection.close()

    def _process_batch(self, rows, prospects, marketing_sources):
        """Process a single batch of records."""
        to_create = []
        to_update = []
        skipped_records = []
        existing_records = Genius_ProspectSource.objects.in_bulk([row[0] for row in rows])  # Assuming the first column is the primary key

        for row in rows:
            (
                record_id, prospect_id, marketing_source_id, source_date, notes, add_user_id, add_date
            ) = row

            prospect = prospects.get(prospect_id)
            marketing_source = marketing_sources.get(marketing_source_id)

            # Skip records with missing foreign key references
            if prospect is None or marketing_source is None:
                missing_refs = []
                if prospect is None:
                    missing_refs.append(f"prospect_id={prospect_id}")
                if marketing_source is None:
                    missing_refs.append(f"marketing_source_id={marketing_source_id}")
                
                skipped_records.append({
                    'id': record_id,
                    'missing': ', '.join(missing_refs)
                })
                continue

            # Make dates timezone-aware
            if add_date:
                add_date = timezone.make_aware(add_date, dt_timezone.utc)
            if source_date:
                source_date = timezone.make_aware(source_date, dt_timezone.utc)

            if record_id in existing_records:
                record_instance = existing_records[record_id]
                record_instance.prospect = prospect
                record_instance.marketing_source = marketing_source
                record_instance.source_date = source_date
                record_instance.notes = notes
                record_instance.add_user_id = add_user_id
                record_instance.add_date = add_date
                to_update.append(record_instance)
            else:
                to_create.append(Genius_ProspectSource(
                    id=record_id,
                    prospect=prospect,
                    marketing_source=marketing_source,
                    source_date=source_date,
                    notes=notes,
                    add_user_id=add_user_id,
                    add_date=add_date
                ))

        # Bulk create and update
        if to_create:
            Genius_ProspectSource.objects.bulk_create(to_create, batch_size=BATCH_SIZE)
        if to_update:
            Genius_ProspectSource.objects.bulk_update(
                to_update,
                ['prospect', 'marketing_source', 'source_date', 'notes', 'add_user_id', 'add_date'],
                batch_size=BATCH_SIZE
            )
        
        # Log skipped records if any
        if skipped_records:
            self.stdout.write(self.style.WARNING(f"Skipped {len(skipped_records)} records due to missing foreign key references:"))
            for skipped in skipped_records[:5]:  # Show first 5 examples
                self.stdout.write(f"  - Record ID {skipped['id']}: missing {skipped['missing']}")
            if len(skipped_records) > 5:
                self.stdout.write(f"  ... and {len(skipped_records) - 5} more")
