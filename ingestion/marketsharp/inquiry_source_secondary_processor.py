from data_import.models import InquirySourceSecondary
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='inquiry_source_secondaries',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/InquirySourceSecondaries',
        model=InquirySourceSecondary,
        processor_class=InquirySourceSecondaryProcessor
    )

class InquirySourceSecondaryProcessor(BaseProcessor):
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
