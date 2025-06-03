from data_import.models import Appointment
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='appointments',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Appointments',
        model=Appointment,
        processor_class=AppointmentProcessor
    )

class AppointmentProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'inquiry_id': FieldMapping('inquiryId', 'inquiry_id', 'uuid'),
        'salesperson1_id': FieldMapping('salesperson1Id', 'salesperson1_id', 'uuid'),
        'salesperson2_id': FieldMapping('salesperson2Id', 'salesperson2_id', 'uuid'),
        'set_by_id': FieldMapping('setById', 'set_by_id', 'uuid'),
        'result_id': FieldMapping('resultId', 'result_id', 'uuid'),
        'last_update_by': FieldMapping('lastUpdateBy', 'last_update_by', 'uuid'),
        'created_by': FieldMapping('createdBy', 'created_by', 'uuid'),
        'appointment_date': FieldMapping('appointmentDate', 'appointment_date', 'datetime'),
        'set_date': FieldMapping('setDate', 'set_date', 'datetime'),
        'issued_date': FieldMapping('issuedDate', 'issued_date', 'datetime'),
        'note': FieldMapping('note', 'note', 'string'),
        'subject': FieldMapping('subject', 'subject', 'string'),
        'type': FieldMapping('type', 'type', 'string'),
        'result_reason': FieldMapping('resultReason', 'result_reason', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Appointment objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Appointment, self.field_mappings, batch_size)
