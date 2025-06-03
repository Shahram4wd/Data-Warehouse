import logging
import os
import aiohttp
import asyncio
from asgiref.sync import sync_to_async
from django.core.management.base import BaseCommand
from data_import.marketsharp_api import MarketSharpAPI
from data_import.data_processor import DataProcessor
from data_import.registry import ProcessorRegistry
from datetime import datetime as DateTime, timedelta

logger = logging.getLogger(__name__)
BATCH_SIZE = 5000

class Command(BaseCommand):
    
    help = 'Imports data from MarketSharp API and processes it.'

    def __init__(self, logger=None):
        super().__init__()
        self._logger = logger or logging.getLogger(__name__)
        if not logger:
            logging.basicConfig(level=logging.DEBUG)
        # Initialize registry before adding arguments
        self.registry = ProcessorRegistry.get_instance()

    def add_arguments(self, parser):
        # Adding custom argument for endpoint selection
        parser.add_argument(
            '--endpoint', 
            type=str, 
            choices=list(self.registry.endpoints.keys()),  
            help='Specify which endpoint to fetch data from. Leave empty to fetch all.'
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

    def handle(self, *args, **kwargs):
        logging.basicConfig(level=logging.INFO)
        endpoint = kwargs.get('endpoint')
        asyncio.run(self.async_handle(endpoint))

    async def async_handle(self, endpoint=None, *args, **kwargs):
        if endpoint:
            await self.process_endpoint(endpoint)
        else:
            # Process all endpoints sequentially
            for endpoint in self.registry.endpoints.keys():
                await self.process_endpoint(endpoint)

    async def process_endpoint(self, endpoint):
        start_time = DateTime.now()

        secret_key = os.getenv('MARKETSHARP_SECRET_KEY')
        api_key = os.getenv('MARKETSHARP_API_KEY')
        company_id = os.getenv('MARKETSHARP_COMPANY_ID')

        url = self.registry.endpoints[endpoint]
        latest_update = await self.get_latest_update(endpoint)

        self._logger.info(f"Started fetching {endpoint} from MarketSharp API.")
        ms_api = MarketSharpAPI(company_id, api_key, secret_key, self._logger)
        data_processor = DataProcessor(self._logger)
        processor_class = self.registry.processors[endpoint]
        processor = processor_class(self._logger, data_processor)

        async with aiohttp.ClientSession() as session:
            skip = 0
            total_records_processed = 0

            while True:
                try:
                    self._logger.debug(f"Fetching {endpoint}: {url}, updated after {latest_update}, skip {skip}")
                    xml_data = await ms_api.get_data(session, url, latest_update, skip=skip)
                    if xml_data:
                        num_records = await processor.process_objects(xml_data, BATCH_SIZE)

                        if isinstance(num_records, int):
                            total_records_processed += num_records
                        elif hasattr(num_records, 'total_processed'):
                            total_records_processed += num_records.total_processed  # Adjust based on your `ProcessingResult` structure.
                        else:
                            raise TypeError("Unexpected return type from process_objects.")
                        
                        total_records_processed += num_records
                        self._logger.info(f"Processed {num_records} {endpoint}. Total processed: {total_records_processed}")

                        if num_records < BATCH_SIZE:
                            break

                        skip += BATCH_SIZE
                    else:
                        self._logger.error(f"Failed to fetch {endpoint} from the API.")
                        break
                except Exception as e:
                    self._logger.error(f"Error occurred while processing {endpoint}: {e}")
                    break

        duration = DateTime.now() - start_time
        self._logger.info(f"Finished processing {endpoint}. Total records: {total_records_processed}. Duration: {duration}.")
