from ingestion.models.marketsharp import MarketSharp_InquirySourceSecondary as InquirySourceSecondary  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='inquiry_source_secondaries',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/InquirySourceSecondaries',
        model=InquirySourceSecondary,
        processor_class=InquirySourceSecondaryProcessor
    )

class InquirySourceSecondaryProcessor(BaseProcessor):
    def __init__(self, logger, data_processor):
        super().__init__(logger, data_processor)
        self._logger = logger  # Initialize the logger
        
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'inquiry_source_primary_id': FieldMapping('inquirySourcePrimaryId', 'inquiry_source_primary_id', 'uuid'),
        'name': FieldMapping('name', 'name', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process InquirySourceSecondary objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, InquirySourceSecondary, self.field_mappings, batch_size)
