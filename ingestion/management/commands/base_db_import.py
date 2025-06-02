import os
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import datetime, timezone as dt_timezone

class BaseDBImportCommand(BaseCommand):
    """Base command for importing data from external databases."""
    
    help = "Base command for database imports."
    model = None  # Override in subclass
    table_name = None  # Override in subclass
    batch_size = int(os.getenv("BATCH_SIZE", 500))
    
    def add_arguments(self, parser):
        parser.add_argument(
            "--table",
            type=str,
            default=self.table_name,
            help=f"The name of the table to download data from. Defaults to '{self.table_name}'."
        )
    
    def handle(self, *args, **options):
        table_name = options["table"] or self.table_name
        if not table_name:
            self.stdout.write(self.style.ERROR("No table name specified"))
            return
            
        connection = None
        try:
            # Database connection
            connection = get_mysql_connection()
            cursor = connection.cursor()
            
            # Preload lookup data
            lookup_data = self.preload_lookup_data(cursor)
            
            # Process records in batches
            self.process_all_records(cursor, table_name, lookup_data)
            
            self.stdout.write(self.style.SUCCESS(f"Data from table '{table_name}' successfully downloaded and updated."))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"An error occurred: {e}"))
        finally:
            if connection:
                cursor.close()
                connection.close()
    
    def preload_lookup_data(self, cursor):
        """Preload lookup data needed for processing. Override in subclass."""
        return {}
    
    def process_all_records(self, cursor, table_name, lookup_data):
        """Process all records in batches."""
        # Get total record count
        cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
        total_records = cursor.fetchone()[0]
        self.stdout.write(self.style.SUCCESS(f"Total records in table '{table_name}': {total_records}"))
        
        # Process records in batches
        for offset in tqdm(range(0, total_records, self.batch_size), desc="Processing batches"):
            self.process_batch_at_offset(cursor, table_name, offset, lookup_data)
    
    def process_batch_at_offset(self, cursor, table_name, offset, lookup_data):
        """Process a batch of records starting at the specified offset."""
        # Get the batch of records
        query = self.get_batch_query(table_name)
        cursor.execute(f"{query} LIMIT {self.batch_size} OFFSET {offset}")
        rows = cursor.fetchall()
        
        # Process the batch
        self.process_batch(rows, **lookup_data)
    
    def get_batch_query(self, table_name):
        """Get the SQL query for fetching a batch of records. Override in subclass."""
        raise NotImplementedError("Subclasses must implement get_batch_query")
    
    def process_batch(self, rows, **lookup_data):
        """Process a batch of records. Override in subclass."""
        raise NotImplementedError("Subclasses must implement process_batch")
    
    def parse_datetime(self, value):
        """Helper function to safely parse and make datetime timezone-aware."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value, dt_timezone.utc) if timezone.is_naive(value) else value
        
        return value
    
    def save_records(self, to_create, to_update, update_fields):
        """Save records to database with error handling."""
        model = self.model
        if not model:
            raise ValueError("model attribute must be set in the subclass")
            
        try:
            if to_create:
                model.objects.bulk_create(to_create, batch_size=self.batch_size)
            
            if to_update:
                model.objects.bulk_update(to_update, update_fields, batch_size=self.batch_size)
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error during bulk operations: {e}"))
            self.fallback_individual_saves(to_create + to_update)
    
    def fallback_individual_saves(self, records):
        """Fallback to individual saves when bulk operations fail."""
        for record in records:
            try:
                record.save()
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error saving record {record.id}: {e}"))
