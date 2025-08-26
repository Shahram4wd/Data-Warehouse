import logging
import os
import aiohttp
import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import CommandError
from ingestion.base.commands import BaseSyncCommand
from ingestion.marketsharp.marketsharp_api import MarketSharpAPI  # Updated import path
from ingestion.marketsharp.data_processor import DataProcessor  # Updated import path
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import path
from datetime import datetime as DateTime, timedelta

logger = logging.getLogger(__name__)
BATCH_SIZE = 5000

class Command(BaseSyncCommand):
    help = 'Imports data from MarketSharp API and processes it.'
    crm_name = 'MarketSharp'
    entity_name = 'data'

    def __init__(self, logger=None):
        super().__init__()
        self._logger = logger or logging.getLogger(__name__)
        if not logger:
            logging.basicConfig(level=logging.DEBUG)
        # Initialize registry before adding arguments
        self.registry = ProcessorRegistry.get_instance()

    def add_arguments(self, parser):
        # Add base sync arguments (--full, --force, --start-date, etc.)
        super().add_arguments(parser)
        
        # Adding MarketSharp-specific arguments
        parser.add_argument(
            '--endpoint', 
            type=str, 
            choices=list(self.registry.endpoints.keys()),  
            help='Specify which endpoint to fetch data from. Leave empty to fetch all.'
        )
        parser.add_argument(
            '--concurrent',
            type=int,
            default=1,
            help='Number of concurrent tasks to run (default: 1).'
        )

    async def get_latest_update(self, endpoint):
        if endpoint not in [
            "companies", "activity_references", "addresses", 
            "appointment_results", "contact_phones", "contact_types",
            "custom_fields", "product_details", "product_types", 
            "product_interests", "inquiry_statuses", "inquiry_source_primaries",
            "inquiry_source_secondaries"
        ]:
            model_class = self.registry.models[endpoint]
            latest_update = await sync_to_async(
                model_class.objects.order_by('-last_update').values_list('last_update', flat=True).first
            )()
            latest_update = latest_update if latest_update else DateTime(1970, 1, 1)
        else:
            latest_update = ""
        return latest_update

    def handle(self, *args, **options):
        """Handle the sync command with standardized parameters"""
        # Configure logging
        if options.get('debug'):
            logging.basicConfig(level=logging.DEBUG)
        elif options.get('quiet'):
            logging.basicConfig(level=logging.WARNING)
        else:
            logging.basicConfig(level=logging.INFO)
            
        endpoint = options.get('endpoint')
        concurrent = options.get('concurrent', 1)
        
        self.stdout.write(
            self.style.SUCCESS('Starting MarketSharp data sync...')
        )
        
        if options.get('dry_run'):
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No data will be saved')
            )
        
        try:
            asyncio.run(self.async_handle(endpoint, concurrent, options))
        except Exception as e:
            logger.exception("MarketSharp sync failed")
            raise CommandError(f"Sync failed: {e}")

    async def async_handle(self, endpoint=None, concurrent=1, options=None):
        """Async handle method with standardized options"""
        if endpoint:
            await self.process_endpoint(endpoint, options)
        else:
            # Process all endpoints sequentially
            for endpoint_name in self.registry.endpoints.keys():
                await self.process_endpoint(endpoint_name, options)

    async def process_endpoint(self, endpoint, options=None):
        """Process a single endpoint with standardized options"""
        start_time = DateTime.now()
        self._logger.info(f"Starting data sync for endpoint: {endpoint}")

        secret_key = os.getenv('MARKETSHARP_SECRET_KEY')
        api_key = os.getenv('MARKETSHARP_API_KEY')
        company_id = os.getenv('MARKETSHARP_COMPANY_ID')

        url = self.registry.endpoints[endpoint]
        
        # Use start_date parameter if provided, otherwise get latest update
        if options and options.get('start_date'):
            latest_update = DateTime.strptime(options['start_date'], '%Y-%m-%d')
        elif options and options.get('full'):
            latest_update = DateTime(1970, 1, 1)  # Full sync from beginning
        else:
            latest_update = await self.get_latest_update(endpoint)

        self._logger.info(f"Fetching data from MarketSharp API for endpoint: {endpoint}")
        self._logger.info(f"API URL: {url}")
        self._logger.info(f"Latest update timestamp: {latest_update if latest_update else 'None'}")

        ms_api = MarketSharpAPI(company_id, api_key, secret_key, self._logger)
        data_processor = DataProcessor(self._logger)
        processor_class = self.registry.processors[endpoint]
        processor = processor_class(self._logger, data_processor)

        # Apply dry-run mode if specified
        dry_run = options.get('dry_run', False) if options else False
        max_records = options.get('max_records', 0) if options else 0

        async with aiohttp.ClientSession() as session:
            skip = 0
            total_records_processed = 0
            batch_size = options.get('batch_size', BATCH_SIZE) if options else BATCH_SIZE

            while True:
                try:
                    # Check max_records limit
                    if max_records > 0 and total_records_processed >= max_records:
                        self._logger.info(f"Reached max records limit ({max_records}) for endpoint: {endpoint}")
                        break
                        
                    self._logger.info(f"Fetching batch starting at record {skip}...")
                    xml_data = await ms_api.get_data(session, url, latest_update, skip=skip)
                    
                    if xml_data:
                        # Adjust batch size if approaching max_records limit
                        effective_batch_size = batch_size
                        if max_records > 0:
                            remaining = max_records - total_records_processed
                            effective_batch_size = min(batch_size, remaining)
                        
                        if dry_run:
                            # In dry-run mode, just count records without processing
                            num_records = min(effective_batch_size, len(xml_data))  
                            self._logger.info(f"DRY RUN: Would process {num_records} records for endpoint: {endpoint}")
                        else:
                            num_records = await processor.process_objects(xml_data, effective_batch_size)
                            
                        total_records_processed += num_records
                        self._logger.info(f"Processed {num_records} records for endpoint: {endpoint}. Total processed: {total_records_processed}")

                        if num_records < effective_batch_size:
                            self._logger.info(f"All records processed for endpoint: {endpoint}.")
                            break

                        skip += effective_batch_size
                    else:
                        self._logger.warning(f"No data returned for endpoint: {endpoint}.")
                        break
                except Exception as e:
                    self._logger.error(f"Error occurred while processing endpoint {endpoint}: {e}")
                    break

        duration = DateTime.now() - start_time
        self._logger.info(f"Finished processing endpoint: {endpoint}. Total records processed: {total_records_processed}. Duration: {duration}.")
        
        if dry_run:
            self._logger.info(f"DRY RUN COMPLETE - No data was actually saved for endpoint: {endpoint}")
