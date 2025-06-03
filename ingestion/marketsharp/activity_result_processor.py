from data_import.models import ActivityResult
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='activity_results',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ActivityResults',
        model=ActivityResult,
        processor_class=ActivityResultProcessor
    )

class ActivityResultProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'int', required=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
        'name': FieldMapping('name', 'name', 'string'),
        'email_success': FieldMapping('emailSuccess', 'email_success', 'boolean', default=False),
        'email_failure': FieldMapping('emailFailure', 'email_failure', 'boolean', default=False),
        'confirmed': FieldMapping('confirmed', 'confirmed', 'boolean', default=False),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update_by': FieldMapping('lastUpdateBy', 'last_update_by', 'uuid'),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'created_by': FieldMapping('createdBy', 'created_by', 'string'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
        'count_as_appt_confirmed': FieldMapping('countAsApptConfirmed', 'count_as_appt_confirmed', 'boolean', default=False),
        'count_as_appt_created': FieldMapping('countAsApptCreated', 'count_as_appt_created', 'boolean', default=False),
        'count_as_contacted': FieldMapping('countAsContacted', 'count_as_contacted', 'boolean', default=False),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ActivityResult objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ActivityResult, self.field_mappings, batch_size)
