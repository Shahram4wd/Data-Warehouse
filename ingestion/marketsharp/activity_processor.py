from data_import.models import Activity
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='activities',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Activities',
        model=Activity,
        processor_class=ActivityProcessor
    )

class ActivityProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
        'name': FieldMapping('name', 'name', 'string'),
        'type': FieldMapping('type', 'type', 'string'),
        'completed_date': FieldMapping('completedDate', 'completed_date', 'datetime'),
        'due_date': FieldMapping('dueDate', 'due_date', 'datetime'),
        'reminder_minutes': FieldMapping('reminderMinutes', 'reminder_minutes', 'int'),
        'notes': FieldMapping('notes', 'notes', 'string'),
        'appointment_id': FieldMapping('appointmentId', 'appointment_id', 'uuid'),
        'assign_to_employee_id': FieldMapping('assignToEmployeeId', 'assign_to_employee_id', 'uuid'),
        'scheduled_by_employee_id': FieldMapping('scheduledByEmployeeId', 'scheduled_by_employee_id', 'uuid'),
        'reminder_dismissed': FieldMapping('reminderDismissed', 'reminder_dismissed', 'boolean', default=False),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_updated_by': FieldMapping('lastUpdatedBy', 'last_updated_by', 'string', default=''),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'created_by': FieldMapping('createdBy', 'created_by', 'string'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
        'inquiry_id': FieldMapping('inquiryId', 'inquiry_id', 'uuid'),
        'activity_result_id': FieldMapping('activityResultId', 'activity_result_id', 'int'),
        'activity_reference_id': FieldMapping('activityReferenceId', 'activity_reference_id', 'int')
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process activity objects using the shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Activity, self.field_mappings, batch_size)