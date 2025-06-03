from ingestion.models.marketsharp import MarketSharp_ProductType as ProductType  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='product_types',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/ProductTypes',
        model=ProductType,
        processor_class=ProductTypeProcessor
    )

class ProductTypeProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'name': FieldMapping('name', 'name', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process ProductType objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, ProductType, self.field_mappings, batch_size)
