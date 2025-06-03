from ingestion.models.marketsharp import MarketSharp_InquirySourcePrimary as InquirySourcePrimary  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='inquiry_source_primaries',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/InquirySourcePrimaries',
        model=InquirySourcePrimary,
        processor_class=InquirySourcePrimaryProcessor
    )

class InquirySourcePrimaryProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'inquiry_source_primary_id': FieldMapping('inquirySourcePrimaryId', 'inquiry_source_primary_id', 'uuid'),
        'name': FieldMapping('name', 'name', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process InquirySourcePrimary objects using shared logic in BaseProcessor."""
        self._logger.info("Starting to process InquirySourcePrimary data...")
        entries = self.data_processor.parse_xml(xml_data)
        self._logger.info(f"Parsed {len(entries)} records from the XML data.")
        processed_count = await self.process_entries(entries, InquirySourcePrimary, self.field_mappings, batch_size)
        self._logger.info(f"Successfully processed {processed_count} InquirySourcePrimary records.")
        return processed_count