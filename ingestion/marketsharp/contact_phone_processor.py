from data_import.models import ContactPhone
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='contact_phones',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ContactPhones',
        model=ContactPhone,
        processor_class=ContactPhoneProcessor
    )

class ContactPhoneProcessor(BaseProcessor):
    field_mappings = {
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid', required=True),
        'assistant_phone': FieldMapping('assistantPhone', 'assistant_phone', 'string'),
        'work_fax': FieldMapping('workFax', 'work_fax', 'string'),
        'cell_phone': FieldMapping('cellPhone', 'cell_phone', 'string'),
        'company_phone': FieldMapping('companyPhone', 'company_phone', 'string'),
        'home_phone2': FieldMapping('homePhone2', 'home_phone2', 'string'),
        'home_fax': FieldMapping('homeFax', 'home_fax', 'string'),
        'pager': FieldMapping('pager', 'pager', 'string'),
        'work_phone2': FieldMapping('workPhone2', 'work_phone2', 'string'),
        'company_fax': FieldMapping('companyFax', 'company_fax', 'string'),
        'home_phone': FieldMapping('homePhone', 'home_phone', 'string'),
        'work_phone': FieldMapping('workPhone', 'work_phone', 'string'),
        'other_phone': FieldMapping('otherPhone', 'other_phone', 'string'),
        'cell_phone2': FieldMapping('cellPhone2', 'cell_phone2', 'string'),
        'other_phone2': FieldMapping('otherPhone2', 'other_phone2', 'string'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ContactPhone objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ContactPhone, self.field_mappings, batch_size)
