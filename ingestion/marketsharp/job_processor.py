from data_import.models import Job
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='jobs',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Jobs',
        model=Job,
        processor_class=JobProcessor
    )

class JobProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
        'inquiry_id': FieldMapping('inquiryId', 'inquiry_id', 'uuid'),
        'site': FieldMapping('site', 'site', 'string'),
        'number': FieldMapping('number', 'number', 'string'),
        'name': FieldMapping('name', 'name', 'string'),
        'description': FieldMapping('description', 'description', 'string'),
        'type': FieldMapping('type', 'type', 'string'),
        'status': FieldMapping('status', 'status', 'string'),
        'address_line1': FieldMapping('addressLine1', 'address_line1', 'string'),
        'address_line2': FieldMapping('addressLine2', 'address_line2', 'string'),
        'city': FieldMapping('city', 'city', 'string'),
        'state': FieldMapping('state', 'state', 'string'),
        'zip': FieldMapping('zip', 'zip', 'string'),
        'structure_value_code': FieldMapping('structureValueCode', 'structure_value_code', 'string'),
        'note': FieldMapping('note', 'note', 'string'),
        'start_date': FieldMapping('startDate', 'start_date', 'datetime'),
        'sale_date': FieldMapping('saleDate', 'sale_date', 'datetime'),
        'completed_date': FieldMapping('completedDate', 'completed_date', 'datetime'),
        'appointment_id': FieldMapping('appointmentId', 'appointment_id', 'uuid'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
        'exported_to_guild_quality': FieldMapping('exportedToGuildQuality', 'exported_to_guild_quality', 'boolean', default=False),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Job objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Job, self.field_mappings, batch_size)
