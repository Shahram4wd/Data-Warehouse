"""
HubSpot contacts processor
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_Contact

logger = logging.getLogger(__name__)

class HubSpotContactProcessor(HubSpotBaseProcessor):
    """Process HubSpot contact data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Contact, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.address': 'address',
            'properties.adgroupid': 'adgroupid',
            'properties.ap_leadid': 'ap_leadid',
            'properties.campaign_content': 'campaign_content',
            'properties.campaign_name': 'campaign_name',
            'properties.city': 'city',
            'properties.clickcheck': 'clickcheck',
            'properties.clicktype': 'clicktype',
            'properties.comments': 'comments',
            'properties.createdate': 'createdate',
            'properties.division': 'division',
            'properties.email': 'email',
            'properties.firstname': 'firstname',
            'properties.hs_google_click_id': 'hs_google_click_id',
            'properties.hs_object_id': 'hs_object_id',
            'properties.lastmodifieddate': 'lastmodifieddate',
            'properties.lastname': 'lastname',
            'properties.lead_salesrabbit_lead_id': 'lead_salesrabbit_lead_id',
            'properties.marketsharp_id': 'marketsharp_id',
            'properties.msm_source': 'msm_source',
            'properties.original_lead_source': 'original_lead_source',
            'properties.original_lead_source_created': 'original_lead_source_created',
            'properties.phone': 'phone',
            'properties.price': 'price',
            'properties.reference_code': 'reference_code',
            'properties.search_terms': 'search_terms',
            'properties.state': 'state',
            'properties.tier': 'tier',
            'properties.trustedform_cert_url': 'trustedform_cert_url',
            'properties.vendorleadid': 'vendorleadid',
            'properties.vertical': 'vertical',
            'properties.zip': 'zip',
            
            # Lead-related fields
            'properties.lead_added_by': 'lead_added_by',
            'properties.lead_added_by_latitude': 'lead_added_by_latitude',
            'properties.lead_added_by_longitude': 'lead_added_by_longitude',
            'properties.lead_added_by_supervisor': 'lead_added_by_supervisor',
            'properties.lead_address1': 'lead_address1',
            'properties.lead_agent_id': 'lead_agent_id',
            'properties.lead_agent_name': 'lead_agent_name',
            'properties.lead_call_screen_viewed_by': 'lead_call_screen_viewed_by',
            'properties.lead_call_screen_viewed_on': 'lead_call_screen_viewed_on',
            'properties.lead_cdyne_county': 'lead_cdyne_county',
            'properties.lead_city': 'lead_city',
            'properties.lead_contact': 'lead_contact',
            'properties.lead_copied_from_id': 'lead_copied_from_id',
            'properties.lead_copied_from_on': 'lead_copied_from_on',
            'properties.lead_cost': 'lead_cost',
            'properties.lead_cwp_client': 'lead_cwp_client',
            'properties.lead_dead_by': 'lead_dead_by',
            'properties.lead_dead_on': 'lead_dead_on',
            'properties.lead_division': 'lead_division',
            'properties.lead_do_not_call_before': 'lead_do_not_call_before',
            'properties.lead_estimate_confirmed_by': 'lead_estimate_confirmed_by',
            'properties.lead_estimate_confirmed_on': 'lead_estimate_confirmed_on',
            'properties.lead_express_consent_set_by': 'lead_express_consent_set_by',
            'properties.lead_express_consent_set_on': 'lead_express_consent_set_on',
            'properties.lead_express_consent_source': 'lead_express_consent_source',
            'properties.lead_express_consent_upload_file_id': 'lead_express_consent_upload_file_id',
            'properties.lead_id': 'lead_id',
            'properties.lead_import_source': 'lead_import_source',
            'properties.lead_invalid_address': 'lead_invalid_address',
            'properties.lead_is_carpentry_followup': 'lead_is_carpentry_followup',
            'properties.lead_is_dnc': 'lead_is_dnc',
            'properties.lead_is_dummy': 'lead_is_dummy',
            'properties.lead_is_estimate_confirmed': 'lead_is_estimate_confirmed',
            'properties.lead_is_estimate_set': 'lead_is_estimate_set',
            'properties.lead_is_express_consent': 'lead_is_express_consent',
            'properties.lead_is_express_consent_being_reviewed': 'lead_is_express_consent_being_reviewed',
            'properties.lead_is_high_potential': 'lead_is_high_potential',
            'properties.lead_is_mobile_lead': 'lead_is_mobile_lead',
            'properties.lead_is_valid_address': 'lead_is_valid_address',
            'properties.lead_is_valid_email': 'lead_is_valid_email',
            'properties.lead_is_year_built_verified': 'lead_is_year_built_verified',
            'properties.lead_is_zillow': 'lead_is_zillow',
            'properties.lead_job_type': 'lead_job_type',
            'properties.lead_notes': 'lead_notes',
            'properties.lead_phone1': 'lead_phone1',
            'properties.lead_phone2': 'lead_phone2',
            'properties.lead_phone3': 'lead_phone3',
            'properties.lead_prospect_id': 'lead_prospect_id',
            'properties.lead_rating': 'lead_rating',
            'properties.lead_salesrabbit_lead_id_new': 'lead_salesrabbit_lead_id_new',
            'properties.lead_source': 'lead_source',
            'properties.lead_source_notes': 'lead_source_notes',
            'properties.lead_sourced_on': 'lead_sourced_on',
            'properties.lead_state': 'lead_state',
            'properties.lead_status': 'lead_status',
            'properties.lead_substatus': 'lead_substatus',
            'properties.lead_type1': 'lead_type1',
            'properties.lead_type2': 'lead_type2',
            'properties.lead_type4': 'lead_type4',
            'properties.lead_viewed_on': 'lead_viewed_on',
            'properties.lead_with_dm': 'lead_with_dm',
            'properties.lead_year_built': 'lead_year_built',
            'properties.lead_zip': 'lead_zip',
            
            # Analytics Fields
            'properties.dedupe_record_id': 'dedupe_record_id',
            'properties.hs_analytics_average_page_views': 'hs_analytics_average_page_views',
            'properties.hs_analytics_first_timestamp': 'hs_analytics_first_timestamp',
            'properties.hs_analytics_num_event_completions': 'hs_analytics_num_event_completions',
            'properties.hs_analytics_num_page_views': 'hs_analytics_num_page_views',
            'properties.hs_analytics_num_visits': 'hs_analytics_num_visits',
            'properties.hs_analytics_revenue': 'hs_analytics_revenue',
            'properties.hs_analytics_source': 'hs_analytics_source',
            'properties.hs_analytics_source_data_1': 'hs_analytics_source_data_1',
            'properties.hs_analytics_source_data_2': 'hs_analytics_source_data_2',
            
            # HubSpot System Fields
            'properties.hs_created_by_user_id': 'hs_created_by_user_id',
            'properties.hs_currently_enrolled_in_prospecting_agent': 'hs_currently_enrolled_in_prospecting_agent',
            'properties.hs_email_domain': 'hs_email_domain',
            'properties.hs_is_unworked': 'hs_is_unworked',
            'properties.hs_latest_source': 'hs_latest_source',
            'properties.hs_latest_source_data_1': 'hs_latest_source_data_1',
            'properties.hs_latest_source_data_2': 'hs_latest_source_data_2',
            'properties.hs_latest_source_timestamp': 'hs_latest_source_timestamp',
            'properties.hs_marketable_status': 'hs_marketable_status',
            'properties.hs_marketable_until_renewal': 'hs_marketable_until_renewal',
            'properties.hs_membership_has_accessed_private_content': 'hs_membership_has_accessed_private_content',
            'properties.hs_object_source_label': 'hs_object_source_label',
            'properties.hs_predictivecontactscore_v2': 'hs_predictivecontactscore_v2',
            'properties.hs_predictivescoringtier': 'hs_predictivescoringtier',
            'properties.hs_prospecting_agent_total_enrolled_count': 'hs_prospecting_agent_total_enrolled_count',
            'properties.hs_registered_member': 'hs_registered_member',
            'properties.hs_timezone': 'hs_timezone',
            'properties.hs_updated_by_user_id': 'hs_updated_by_user_id',
            'properties.hs_v2_date_entered_lead': 'hs_v2_date_entered_lead',
            
            # Lifecycle Fields
            'properties.currentlyinworkflow': 'currentlyinworkflow',
            'properties.lifecyclestage': 'lifecyclestage',
            'properties.num_conversion_events': 'num_conversion_events',
            'properties.num_unique_conversion_events': 'num_unique_conversion_events',
            
            # Contact Info Fields
            'properties.contact_id': 'contact_id',
            'properties.contact_type': 'contact_type',
            'properties.phone1_type': 'phone1_type',
            'properties.phone2_type': 'phone2_type',
            'properties.num_notes': 'num_notes',
            'properties.notes_last_updated': 'notes_last_updated',
            'properties.notes_last_contacted': 'notes_last_contacted',
            'properties.num_contacted_notes': 'num_contacted_notes',
            'properties.last_scheduled_appointment_start_time': 'last_scheduled_appointment_start_time',
            'properties.sales_rabbit_lead_id': 'sales_rabbit_lead_id',
            
            # Prospect Fields
            'properties.prospect_id': 'prospect_id',
            'properties.prospect_add_date': 'prospect_add_date',
            'properties.prospect_add_user_id': 'prospect_add_user_id',
            'properties.prospect_is_address_valid': 'prospect_is_address_valid',
            'properties.prospect_is_year_built_valid': 'prospect_is_year_built_valid',
            'properties.prospect_phone1': 'prospect_phone1',
            'properties.prospect_phone1_type': 'prospect_phone1_type',
            'properties.prospect_phone2_type': 'prospect_phone2_type',
            'properties.prospect_user_id': 'prospect_user_id',
            'properties.prospect_year_built': 'prospect_year_built',
            'properties.prospect_marketsharp_id': 'prospect_marketsharp_id',
            
            # Source fields
            'properties.hge_primary_source': 'hge_primary_source',
            'properties.hge_secondary_source': 'hge_secondary_source',
            'properties.service_of_interest': 'service_of_interest',
            
            # Canvasser fields
            'properties.canvasser': 'canvasser',
            'properties.canvasser_email': 'canvasser_email',
            'properties.canvasser_id': 'canvasser_id',
            
            # Additional Fields
            'properties.country': 'country',
            'properties.hatch_id': 'hatch_id',
            'properties.address_url': 'address_url',
            'properties.division_id': 'division_id',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot contact record to model format"""
        # Use the architectural pattern: apply field mappings first
        transformed = self.apply_field_mappings(record)
        
        # Apply validation and transformation for specific field types
        record_id = record.get('id', 'UNKNOWN')
        
        # Transform datetime fields
        datetime_fields = ['createdate', 'lastmodifieddate', 'original_lead_source_created', 
                          'lead_call_screen_viewed_on', 'lead_copied_from_on', 'lead_dead_on',
                          'lead_estimate_confirmed_on', 'lead_express_consent_set_on', 'lead_sourced_on', 'lead_viewed_on']
        for field in datetime_fields:
            if field in transformed:
                transformed[field] = self._parse_datetime(transformed[field])
        
        # Transform decimal fields
        decimal_fields = ['lead_added_by_latitude', 'lead_added_by_longitude', 'lead_cost', 'price']
        for field in decimal_fields:
            if field in transformed:
                transformed[field] = self._parse_decimal(transformed[field])
        
        # Transform integer fields
        integer_fields = ['lead_year_built', 'lead_cwp_client', 'lead_express_consent_source', 'lead_job_type', 
                         'lead_rating', 'lead_source', 'lead_status', 'lead_substatus', 'lead_type1', 'lead_type2', 
                         'lead_type4', 'lead_with_dm']
        
        # Transform big integer fields
        big_integer_fields = ['lead_added_by', 'lead_agent_id', 'lead_call_screen_viewed_by', 'lead_contact',
                             'lead_copied_from_id', 'lead_dead_by', 'lead_division', 'lead_estimate_confirmed_by',
                             'lead_express_consent_set_by', 'lead_express_consent_upload_file_id', 'lead_id',
                             'lead_prospect_id', 'lead_salesrabbit_lead_id_new']
        
        for field in integer_fields:
            if field in transformed:
                transformed[field] = self._parse_integer(transformed[field])
                
        for field in big_integer_fields:
            if field in transformed:
                transformed[field] = self._parse_integer(transformed[field])
        
        # Transform boolean fields
        boolean_fields = ['lead_invalid_address', 'lead_is_carpentry_followup', 'lead_is_dnc', 'lead_is_dummy',
                         'lead_is_estimate_confirmed', 'lead_is_estimate_set', 'lead_is_express_consent',
                         'lead_is_express_consent_being_reviewed', 'lead_is_high_potential', 'lead_is_mobile_lead',
                         'lead_is_valid_address', 'lead_is_valid_email', 'lead_is_year_built_verified', 'lead_is_zillow',
                         'lead_with_dm']
        for field in boolean_fields:
            if field in transformed:
                transformed[field] = self._parse_boolean(transformed[field])
        
        # Clean and validate specific fields
        if transformed.get('email'):
            transformed['email'] = self._clean_email(transformed['email'])
        
        if transformed.get('phone'):
            transformed['phone'] = self._clean_phone(transformed['phone'])
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact record"""
        record_id = record.get('id', 'UNKNOWN')
        
        if not record.get('id'):
            raise ValidationException("Contact ID is required")
        
        # Additional business rule validation can be added here
        return record
    
    def process_chunk_individually_sync(self, chunk: List[Dict]) -> Dict[str, int]:
        """Process chunk of contacts individually for synchronous operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in chunk:
            try:
                transformed = self.transform_record(record)
                validated = self.validate_record(transformed)
                
                contact, created = Hubspot_Contact.objects.get_or_create(
                    id=validated['id'],
                    defaults=validated
                )
                
                if not created:
                    for field, value in validated.items():
                        if hasattr(contact, field):
                            setattr(contact, field, value)
                    contact.save()
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error processing contact {record.get('id', 'UNKNOWN')}: {e}")
                results['failed'] += 1
        
        return results
    
    def log_database_error(self, error: Exception, record_data: Dict, operation: str):
        """Log database error with contact context"""
        contact_id = record_data.get('id', 'UNKNOWN')
        logger.error(f"Database error during {operation} for contact {contact_id}: {error}")
    
    def get_portal_id(self) -> str:
        """Get portal ID for this contact processor"""
        return "default"  # Implementation depends on your portal configuration
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate contact record with enhanced validation"""
        record_id = record.get('id', 'UNKNOWN')
        
        if not record.get('id'):
            raise ValidationException("Contact ID is required")
        
        # Enhanced validation using the new framework
        validated_record = record.copy()
        
        # ID validation
        try:
            validated_record['id'] = self.validate_field('id', record['id'], 'object_id', record)
        except ValidationException as e:
            raise ValidationException(f"Invalid contact ID '{record['id']}': {e}")
        
        # Email validation (if present)
        if record.get('email'):
            try:
                validated_record['email'] = self.validate_field('email', record['email'], 'email', record)
            except ValidationException as e:
                logger.warning(f"Invalid email '{record['email']}' for contact {record_id}: {e}")
                validated_record['email'] = None
        
        # Phone validation (if present)
        if record.get('phone'):
            try:
                validated_record['phone'] = self.validate_field('phone', record['phone'], 'phone', record)
            except ValidationException as e:
                logger.warning(f"Invalid phone '{record['phone']}' for contact {record_id}: {e}")
                validated_record['phone'] = record['phone']  # Keep original if validation fails
        
        # HubSpot object ID validation
        if record.get('hs_object_id'):
            try:
                validated_record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id', record)
            except ValidationException as e:
                logger.warning(f"Invalid HubSpot object ID '{record['hs_object_id']}' for contact {record_id}: {e}")
                validated_record['hs_object_id'] = None
        
        # Zip code validation
        if record.get('zip'):
            try:
                validated_record['zip'] = self.validate_field('zip', record['zip'], 'zip_code', record)
            except ValidationException as e:
                logger.warning(f"Invalid zip code '{record['zip']}' for contact {record_id}: {e}")
                validated_record['zip'] = record['zip']  # Keep original if validation fails
        
        # URL validation
        if record.get('trustedform_cert_url'):
            try:
                validated_record['trustedform_cert_url'] = self.validate_field('trustedform_cert_url', record['trustedform_cert_url'], 'url', record)
            except ValidationException as e:
                logger.warning(f"Invalid trustedform_cert_url '{record['trustedform_cert_url']}' for contact {record_id}: {e}")
                validated_record['trustedform_cert_url'] = record['trustedform_cert_url']  # Keep original if validation fails
        
        # Decimal validation
        if record.get('price'):
            try:
                validated_record['price'] = self.validate_field('price', record['price'], 'decimal', record)
            except ValidationException as e:
                logger.warning(f"Invalid price '{record['price']}' for contact {record_id}: {e}")
                validated_record['price'] = None
        
        return validated_record
    
    def process_chunk_individually_sync(self, chunk: List[Dict]) -> Dict[str, int]:
        """Process chunk individually with enhanced error handling"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record_data in chunk:
            try:
                # Process individual record
                processed_record = self.process(record_data)
                if processed_record:
                    # Save individual record
                    contact, created = Hubspot_Contact.objects.update_or_create(
                        id=processed_record['id'],
                        defaults=processed_record
                    )
                    
                    if created:
                        results['created'] += 1
                    else:
                        results['updated'] += 1
                        
                    logger.debug(f"{'Created' if created else 'Updated'} contact {processed_record['id']}")
                
            except Exception as e:
                results['failed'] += 1
                # Enhanced error logging following import_refactoring.md patterns
                contact_id = record_data.get('id', 'UNKNOWN')
                hubspot_url = f"https://app.hubspot.com/contacts/{self.get_portal_id()}/contact/{contact_id}" if contact_id != 'UNKNOWN' else "URL unavailable"
                
                logger.error(
                    f"Error processing contact {contact_id}: {e} - "
                    f"HubSpot URL: {hubspot_url}"
                )
                
                self.log_database_error(e, record_data, "individual_save")
        
        return results
    
    def log_database_error(self, error: Exception, record_data: Dict, operation: str):
        """Enhanced database error logging with context"""
        contact_id = record_data.get('id', 'UNKNOWN')
        error_context = {
            'operation': operation,
            'contact_id': contact_id,
            'error_type': type(error).__name__,
            'error_message': str(error)
        }
        
        # Log with HubSpot URL for easy debugging
        hubspot_url = f"https://app.hubspot.com/contacts/{self.get_portal_id()}/contact/{contact_id}" if contact_id != 'UNKNOWN' else "URL unavailable"
        
        logger.error(
            f"Database error during {operation} for contact {contact_id}: {error} - "
            f"HubSpot URL: {hubspot_url} - "
            f"Context: {error_context}"
        )
    
    def get_portal_id(self) -> str:
        """Get HubSpot portal ID from settings"""
        from django.conf import settings
        return getattr(settings, 'HUBSPOT_PORTAL_ID', '[PORTAL_ID]')
    