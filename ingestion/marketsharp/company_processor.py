from data_import.models import Company
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='companies',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Companies',
        model=Company,
        processor_class=CompanyProcessor
    )

class CompanyProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'int', required=True),
        'number': FieldMapping('number', 'number', 'int'),
        'name': FieldMapping('name', 'name', 'string'),
        'owner': FieldMapping('owner', 'owner', 'string'),
        'address_line1': FieldMapping('addressLine1', 'address_line1', 'string'),
        'address_line2': FieldMapping('addressLine2', 'address_line2', 'string'),
        'address_city': FieldMapping('addressCity', 'address_city', 'string'),
        'address_state': FieldMapping('addressState', 'address_state', 'string'),
        'address_zip': FieldMapping('addressZip', 'address_zip', 'string'),
        'email': FieldMapping('email', 'email', 'string'),
        'website': FieldMapping('website', 'website', 'string'),
        'contact_name': FieldMapping('contactName', 'contact_name', 'string'),
        'contact_title': FieldMapping('contactTitle', 'contact_title', 'string'),
        'phone': FieldMapping('phone', 'phone', 'string'),
        'fax': FieldMapping('fax', 'fax', 'string'),
        'time_zone': FieldMapping('timeZone', 'time_zone', 'string'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Company objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Company, self.field_mappings, batch_size)
