from ingestion.models.marketsharp import MarketSharp_Address as Address  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='addresses',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Addresses',
        model=Address,
        processor_class=AddressProcessor
    )

class AddressProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
        'line1': FieldMapping('line1', 'line1', 'string'),
        'line2': FieldMapping('line2', 'line2', 'string'),
        'city': FieldMapping('city', 'city', 'string'),
        'state': FieldMapping('state', 'state', 'string'),
        'county': FieldMapping('county', 'county', 'string'),
        'zip': FieldMapping('zip', 'zip', 'string'),
        'country': FieldMapping('country', 'country', 'string'),
        'carrier_route': FieldMapping('carrierRoute', 'carrier_route', 'string'),
        'cass': FieldMapping('cass', 'cass', 'string'),
        'latitude': FieldMapping('latitude', 'latitude', 'float'),
        'longitude': FieldMapping('longitude', 'longitude', 'float'),
        'zip4': FieldMapping('zip4', 'zip4', 'string'),
        'dpbc2': FieldMapping('dpbc2', 'dpbc2', 'string'),
        'bar_code': FieldMapping('barCode', 'bar_code', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Address objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Address, self.field_mappings, batch_size)
