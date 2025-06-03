from data_import.models import InquiryStatus
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='inquiry_statuses',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/InquiryStatuses',
        model=InquiryStatus,
        processor_class=InquiryStatusProcessor
    )

class InquiryStatusProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'int', required=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
        'name': FieldMapping('name', 'name', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update_by': FieldMapping('lastUpdateBy', 'last_update_by', 'uuid'),
        'last_update_utc': FieldMapping('lastUpdateUtc', 'last_update_utc', 'datetime'),
        'created_by': FieldMapping('createdBy', 'created_by', 'string'),
        'created_date_utc': FieldMapping('createdDateUtc', 'created_date_utc', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process InquiryStatus objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, InquiryStatus, self.field_mappings, batch_size)
