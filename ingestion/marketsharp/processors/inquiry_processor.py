from ingestion.models.marketsharp import MarketSharp_Inquiry as Inquiry  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='inquiries',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Inquiries',
        model=Inquiry,
        processor_class=InquiryProcessor
    )

class InquiryProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'contact_id': FieldMapping('contactId', 'contact_id', 'uuid'),
        'description': FieldMapping('description', 'description', 'string'),
        'inquiry_source_primary_id': FieldMapping('inquirySourcePrimaryId', 'inquiry_source_primary_id', 'uuid'),
        'inquiry_source_secondary_id': FieldMapping('inquirySourceSecondaryId', 'inquiry_source_secondary_id', 'uuid'),
        'creation_date': FieldMapping('creationDate', 'creation_date', 'datetime'),
        'inquiry_date': FieldMapping('inquiryDate', 'inquiry_date', 'datetime'),
        'set_date': FieldMapping('setDate', 'set_date', 'datetime'),
        'note': FieldMapping('note', 'note', 'string'),
        'promoter_id': FieldMapping('promoterId', 'promoter_id', 'uuid'),
        'canvasser_id': FieldMapping('canvasserId', 'canvasser_id', 'uuid'),
        'telemarketer_id': FieldMapping('telemarketerId', 'telemarketer_id', 'uuid'),
        'job_site_address_line1': FieldMapping('jobSiteAddressLine1', 'job_site_address_line1', 'string'),
        'job_site_address_line2': FieldMapping('jobSiteAddressLine2', 'job_site_address_line2', 'string'),
        'job_site_city': FieldMapping('jobSiteCity', 'job_site_city', 'string'),
        'job_site_state': FieldMapping('jobSiteState', 'job_site_state', 'string'),
        'job_site_zip': FieldMapping('jobSiteZip', 'job_site_zip', 'string'),
        'job_site_directions': FieldMapping('jobSiteDirections', 'job_site_directions', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'set_by_id': FieldMapping('setById', 'set_by_id', 'uuid'),
        'division': FieldMapping('division', 'division', 'string'),
        'inquiry_status_id': FieldMapping('inquiryStatusId', 'inquiry_status_id', 'int'),
        'last_update_by': FieldMapping('lastUpdateBy', 'last_update_by', 'uuid'),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'created_by': FieldMapping('createdBy', 'created_by', 'string'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Inquiry objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Inquiry, self.field_mappings, batch_size)
