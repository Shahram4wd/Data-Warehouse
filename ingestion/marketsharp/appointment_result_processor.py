from data_import.models import AppointmentResult
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='appointment_results',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/AppointmentResults',
        model=AppointmentResult,
        processor_class=AppointmentResultProcessor
    )

class AppointmentResultProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'name': FieldMapping('name', 'name', 'string'),
        'presentation': FieldMapping('presentation', 'presentation', 'boolean', default=False),
        'sold': FieldMapping('sold', 'sold', 'boolean', default=False),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process AppointmentResult objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, AppointmentResult, self.field_mappings, batch_size)
