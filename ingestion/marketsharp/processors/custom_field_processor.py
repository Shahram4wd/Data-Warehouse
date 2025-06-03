from ingestion.models.marketsharp import MarketSharp_CustomField as CustomField  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='custom_fields',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/CustomFields',
        model=CustomField,
        processor_class=CustomFieldProcessor
    )

class CustomFieldProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'name': FieldMapping('name', 'name', 'string'),
        'value': FieldMapping('value', 'value', 'string'),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process CustomField objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, CustomField, self.field_mappings, batch_size)
