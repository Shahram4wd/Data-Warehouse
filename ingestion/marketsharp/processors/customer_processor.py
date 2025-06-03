from ingestion.models.marketsharp import MarketSharp_Customer as Customer  # Updated import
from ingestion.marketsharp.base_processor import BaseProcessor, FieldMapping  # Updated import
from ingestion.marketsharp.registry import ProcessorRegistry  # Updated import

def register_processor(registry: ProcessorRegistry):
    registry.register(
        endpoint='customers',
        api_url='https://api4.marketsharpm.com/WcfDataService.svc/Customers',
        model=Customer,
        processor_class=CustomerProcessor
    )

class CustomerProcessor(BaseProcessor):
    field_mappings = {
        'id': FieldMapping('id', 'id', 'uuid', required=True),
        'company_id': FieldMapping('companyId', 'company_id', 'int'),
        'first_name': FieldMapping('firstName', 'first_name', 'string'),
        'last_name': FieldMapping('lastName', 'last_name', 'string'),
        'middle_initial': FieldMapping('middleInitial', 'middle_initial', 'string'),
        'title': FieldMapping('title', 'title', 'string'),
        'income_code': FieldMapping('incomeCode', 'income_code', 'string'),
        'age_code': FieldMapping('ageCode', 'age_code', 'string'),
        'structure_age_code': FieldMapping('structureAgeCode', 'structure_age_code', 'string'),
        'reference': FieldMapping('reference', 'reference', 'string'),
        'business_name': FieldMapping('businessName', 'business_name', 'string'),
        'contact_phone_id': FieldMapping('contactPhoneId', 'contact_phone_id', 'uuid'),
        'primary_address_id': FieldMapping('primaryAddressId', 'primary_address_id', 'uuid'),
        'website1': FieldMapping('website1', 'website1', 'string'),
        'website2': FieldMapping('website2', 'website2', 'string'),
        'website3': FieldMapping('website3', 'website3', 'string'),
        'email1': FieldMapping('email1', 'email1', 'string'),
        'email1_can_mail': FieldMapping('email1CanMail', 'email1_can_mail', 'boolean', default=False),
        'email2': FieldMapping('email2', 'email2', 'string'),
        'email2_can_mail': FieldMapping('email2CanMail', 'email2_can_mail', 'boolean', default=False),
        'email3': FieldMapping('email3', 'email3', 'string'),
        'email3_can_mail': FieldMapping('email3CanMail', 'email3_can_mail', 'boolean', default=False),
        'is_tagged': FieldMapping('isTagged', 'is_tagged', 'boolean'),
        'structure_value_code': FieldMapping('structureValueCode', 'structure_value_code', 'string'),
        'do_not_mail': FieldMapping('doNotMail', 'do_not_mail', 'boolean', default=False),
        'year_home_built': FieldMapping('yearHomeBuilt', 'year_home_built', 'string'),
        'marital_status': FieldMapping('maritalStatus', 'marital_status', 'string'),
        'length_of_residence': FieldMapping('lengthOfResidence', 'length_of_residence', 'string'),
        'style_of_home': FieldMapping('styleOfHome', 'style_of_home', 'string'),
        'mail_merge_name': FieldMapping('mailMergeName', 'mail_merge_name', 'string'),
        'source': FieldMapping('source', 'source', 'string'),
        'creation_date': FieldMapping('creationDate', 'creation_date', 'datetime'),
        'qb_sync_date': FieldMapping('qbSyncDate', 'qb_sync_date', 'datetime'),
        'qb_id': FieldMapping('qbId', 'qb_id', 'string'),
        'is_active': FieldMapping('isActive', 'is_active', 'boolean', default=True),
        'last_update': FieldMapping('lastUpdate', 'last_update', 'datetime'),
        'has_dnc_phone': FieldMapping('hasDncPhone', 'has_dnc_phone', 'boolean', default=False),
        'has_dne_email': FieldMapping('hasDneEmail', 'has_dne_email', 'boolean', default=False),
        'qb_edit_sequence': FieldMapping('qbEditSequence', 'qb_edit_sequence', 'string'),
        'qb_sync_data': FieldMapping('qbSyncData', 'qb_sync_data', 'boolean'),
        'qb_name': FieldMapping('qbName', 'qb_name', 'string'),
        'created_date': FieldMapping('createdDate', 'created_date', 'datetime'),
    }

    async def process_objects(self, xml_data: str, batch_size: int) -> int:
        """Process Customer objects using shared logic in BaseProcessor."""
        entries = self.data_processor.parse_xml(xml_data)
        return await self.process_entries(entries, Customer, self.field_mappings, batch_size)
