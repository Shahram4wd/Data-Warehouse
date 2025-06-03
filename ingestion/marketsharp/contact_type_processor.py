from data_import.models import ContactType
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='contact_types',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ContactTypes',
        model=ContactType,
        processor_class=ContactTypeProcessor
    )

class ContactTypeProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
        'contact_type': FieldMapping('contactType', 'contact_type', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ContactType objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ContactType, self.field_mappings, batch_size)
