from data_import.models import ProductInterest
from data_import.base_processor import BaseProcessor, FieldMapping
from data_import.registry import ProcessorRegistry

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='product_interests',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ProductInterests',
        model=ProductInterest,
        processor_class=ProductInterestProcessor
    )

class ProductInterestProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'inquiry_id': FieldMapping('inquiryId', 'inquiry_id', 'uuid'),
        'product_type_id': FieldMapping('productTypeId', 'product_type_id', 'uuid'),
        'product_detail_id': FieldMapping('productDetailId', 'product_detail_id', 'uuid'),
        'price_quoted': FieldMapping('priceQuoted', 'price_quoted', 'decimal'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ProductInterest objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ProductInterest, self.field_mappings, batch_size)
