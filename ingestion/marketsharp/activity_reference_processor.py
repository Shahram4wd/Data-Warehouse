from data_import.models import ActivityReference
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='activity_references',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ActivityReferences',
        model=ActivityReference,
        processor_class=ActivityReferenceProcessor
    )

class ActivityReferenceProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'int', required=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
        'name': FieldMapping('name', 'name', 'string'),
        'inquiry_required': FieldMapping('inquiryRequired', 'inquiry_required', 'boolean', default=False),
        'appointment_required': FieldMapping('appointmentRequired', 'appointment_required', 'boolean', default=False),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=False),
        'created_by': FieldMapping('createdBy', 'created_by', 'string'),
        'created_date_utc': FieldMapping('createdDateUtc', 'created_date_utc', 'datetime'),
        'last_update_by': FieldMapping('lastUpdateBy', 'last_update_by', 'uuid'),
        'last_update_utc': FieldMapping('lastUpdateUtc', 'last_update_utc', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ActivityReference objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ActivityReference, self.field_mappings, batch_size)
