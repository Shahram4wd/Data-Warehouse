from ingestion.models.marketsharp import MarketSharp_Employee as Employee  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='employees',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Employees',
        model=Employee,
        processor_class=EmployeeProcessor
    )

class EmployeeProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'name': FieldMapping('name', 'name', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Employee objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Employee, self.field_mappings, batch_size)
