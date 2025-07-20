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
            # Core fields
            'id': 'id',
            'properties.firstname': 'firstname',
            'properties.lastname': 'lastname',
            'properties.email': 'email',
            'properties.phone': 'phone',
            'properties.address': 'address',
            'properties.city': 'city',
            'properties.state': 'state',
            'properties.zip': 'zip',
            'properties.createdate': 'createdate',
            'properties.lastmodifieddate': 'lastmodifieddate',
            'properties.campaign_name': 'campaign_name',
            'properties.hs_google_click_id': 'hs_google_click_id',
            'properties.original_lead_source': 'original_lead_source',
            'properties.division': 'division',
            'properties.marketsharp_id': 'marketsharp_id',
            'properties.hs_object_id': 'hs_object_id',
            'properties.adgroupid': 'adgroupid',
            'properties.ap_leadid': 'ap_leadid',
            'properties.campaign_content': 'campaign_content',
            'properties.clickcheck': 'clickcheck',
            'properties.clicktype': 'clicktype',
            'properties.comments': 'comments',
            'properties.lead_salesrabbit_lead_id': 'lead_salesrabbit_lead_id',
            'properties.msm_source': 'msm_source',
            'properties.original_lead_source_created': 'original_lead_source_created',
            'properties.price': 'price',
            'properties.reference_code': 'reference_code',
            'properties.search_terms': 'search_terms',
            'properties.tier': 'tier',
            'properties.trustedform_cert_url': 'trustedform_cert_url',
            'properties.vendorleadid': 'vendorleadid',
            'properties.vertical': 'vertical',
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
            'properties.hge_primary_source': 'primary_source',
            'properties.hge_secondary_source': 'secondary_source',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot contact record to model format using enterprise validation framework"""
        properties = record.get('properties', {})
        record_id = record.get('id', 'UNKNOWN')
        
        # Enterprise transformation with comprehensive validation
        try:
            transformed = {
                # Core fields
                'id': self.validate_field('id', record.get('id'), 'object_id', record),
                'address': self.validate_field('address', properties.get('address'), 'string', record),
                'adgroupid': self.validate_field('adgroupid', properties.get('adgroupid'), 'string', record),
                'ap_leadid': self.validate_field('ap_leadid', properties.get('ap_leadid'), 'string', record),
                'campaign_content': self.validate_field('campaign_content', properties.get('campaign_content'), 'string', record),
                'campaign_name': self.validate_field('campaign_name', properties.get('campaign_name'), 'string', record),
                'city': self.validate_field('city', properties.get('city'), 'string', record),
                'clickcheck': self.validate_field('clickcheck', properties.get('clickcheck'), 'string', record),
                'clicktype': self.validate_field('clicktype', properties.get('clicktype'), 'string', record),
                'comments': self.validate_field('comments', properties.get('comments'), 'string', record),
                'createdate': self.validate_field('createdate', properties.get('createdate'), 'datetime', record),
                'division': self.validate_field('division', properties.get('division'), 'string', record),
                'email': self.validate_field('email', properties.get('email'), 'email', record),
                'firstname': self.validate_field('firstname', properties.get('firstname'), 'string', record),
                'hs_google_click_id': self.validate_field('hs_google_click_id', properties.get('hs_google_click_id'), 'string', record),
                'hs_object_id': self.validate_field('hs_object_id', properties.get('hs_object_id'), 'object_id', record),
                'lastmodifieddate': self.validate_field('lastmodifieddate', properties.get('lastmodifieddate'), 'datetime', record),
                'lastname': self.validate_field('lastname', properties.get('lastname'), 'string', record),
                'lead_salesrabbit_lead_id': self.validate_field('lead_salesrabbit_lead_id', properties.get('lead_salesrabbit_lead_id'), 'string', record),
                'marketsharp_id': self.validate_field('marketsharp_id', properties.get('marketsharp_id'), 'string', record),
                'msm_source': self.validate_field('msm_source', properties.get('msm_source'), 'string', record),
                'original_lead_source': self.validate_field('original_lead_source', properties.get('original_lead_source'), 'string', record),
                'original_lead_source_created': self.validate_field('original_lead_source_created', properties.get('original_lead_source_created'), 'datetime', record),
                'phone': self.validate_field('phone', properties.get('phone'), 'phone', record),
                'price': self.validate_field('price', properties.get('price'), 'decimal', record),
                'reference_code': self.validate_field('reference_code', properties.get('reference_code'), 'string', record),
                'search_terms': self.validate_field('search_terms', properties.get('search_terms'), 'string', record),
                'state': self.validate_field('state', properties.get('state'), 'string', record),
                'tier': self.validate_field('tier', properties.get('tier'), 'string', record),
                'trustedform_cert_url': self.validate_field('trustedform_cert_url', properties.get('trustedform_cert_url'), 'url', record),
                'vendorleadid': self.validate_field('vendorleadid', properties.get('vendorleadid'), 'string', record),
                'vertical': self.validate_field('vertical', properties.get('vertical'), 'string', record),
                'zip': self.validate_field('zip', properties.get('zip'), 'zip_code', record),
                # Lead-related fields
                'lead_added_by': self.validate_field('lead_added_by', properties.get('lead_added_by'), 'integer', record),
                'lead_added_by_latitude': self.validate_field('lead_added_by_latitude', properties.get('lead_added_by_latitude'), 'string', record),
                'lead_added_by_longitude': self.validate_field('lead_added_by_longitude', properties.get('lead_added_by_longitude'), 'string', record),
                'lead_added_by_supervisor': self.validate_field('lead_added_by_supervisor', properties.get('lead_added_by_supervisor'), 'string', record),
                'lead_address1': self.validate_field('lead_address1', properties.get('lead_address1'), 'string', record),
                'lead_agent_id': self.validate_field('lead_agent_id', properties.get('lead_agent_id'), 'integer', record),
                'lead_agent_name': self.validate_field('lead_agent_name', properties.get('lead_agent_name'), 'string', record),
                'lead_call_screen_viewed_by': self.validate_field('lead_call_screen_viewed_by', properties.get('lead_call_screen_viewed_by'), 'integer', record),
                'lead_call_screen_viewed_on': self.validate_field('lead_call_screen_viewed_on', properties.get('lead_call_screen_viewed_on'), 'datetime', record),
                'lead_cdyne_county': self.validate_field('lead_cdyne_county', properties.get('lead_cdyne_county'), 'string', record),
                'lead_city': self.validate_field('lead_city', properties.get('lead_city'), 'string', record),
                'lead_contact': self.validate_field('lead_contact', properties.get('lead_contact'), 'integer', record),
                'lead_copied_from_id': self.validate_field('lead_copied_from_id', properties.get('lead_copied_from_id'), 'integer', record),
                'lead_copied_from_on': self.validate_field('lead_copied_from_on', properties.get('lead_copied_from_on'), 'string', record),
                'lead_cost': self.validate_field('lead_cost', properties.get('lead_cost'), 'decimal', record),
                'lead_cwp_client': self.validate_field('lead_cwp_client', properties.get('lead_cwp_client'), 'integer', record),
                'lead_dead_by': self.validate_field('lead_dead_by', properties.get('lead_dead_by'), 'integer', record),
                'lead_dead_on': self.validate_field('lead_dead_on', properties.get('lead_dead_on'), 'datetime', record),
                'lead_division': self.validate_field('lead_division', properties.get('lead_division'), 'integer', record),
                'lead_do_not_call_before': self.validate_field('lead_do_not_call_before', properties.get('lead_do_not_call_before'), 'datetime', record),
                'lead_estimate_confirmed_by': self.validate_field('lead_estimate_confirmed_by', properties.get('lead_estimate_confirmed_by'), 'integer', record),
                'lead_estimate_confirmed_on': self.validate_field('lead_estimate_confirmed_on', properties.get('lead_estimate_confirmed_on'), 'datetime', record),
                'lead_express_consent_set_by': self.validate_field('lead_express_consent_set_by', properties.get('lead_express_consent_set_by'), 'integer', record),
                'lead_express_consent_set_on': self.validate_field('lead_express_consent_set_on', properties.get('lead_express_consent_set_on'), 'datetime', record),
                'lead_express_consent_source': self.validate_field('lead_express_consent_source', properties.get('lead_express_consent_source'), 'integer', record),
                'lead_express_consent_upload_file_id': self.validate_field('lead_express_consent_upload_file_id', properties.get('lead_express_consent_upload_file_id'), 'integer', record),
                'lead_id': self.validate_field('lead_id', properties.get('lead_id'), 'integer', record),
                'lead_import_source': self.validate_field('lead_import_source', properties.get('lead_import_source'), 'string', record),
                'lead_invalid_address': self.validate_field('lead_invalid_address', properties.get('lead_invalid_address'), 'integer', record),
                'lead_is_carpentry_followup': self.validate_field('lead_is_carpentry_followup', properties.get('lead_is_carpentry_followup'), 'integer', record),
                'lead_is_dnc': self.validate_field('lead_is_dnc', properties.get('lead_is_dnc'), 'integer', record),
                'lead_is_dummy': self.validate_field('lead_is_dummy', properties.get('lead_is_dummy'), 'integer', record),
                'lead_is_estimate_confirmed': self.validate_field('lead_is_estimate_confirmed', properties.get('lead_is_estimate_confirmed'), 'integer', record),
                'lead_is_estimate_set': self.validate_field('lead_is_estimate_set', properties.get('lead_is_estimate_set'), 'integer', record),
                'lead_is_express_consent': self.validate_field('lead_is_express_consent', properties.get('lead_is_express_consent'), 'integer', record),
                'lead_is_express_consent_being_reviewed': self.validate_field('lead_is_express_consent_being_reviewed', properties.get('lead_is_express_consent_being_reviewed'), 'integer', record),
                'lead_is_high_potential': self.validate_field('lead_is_high_potential', properties.get('lead_is_high_potential'), 'integer', record),
                'lead_is_mobile_lead': self.validate_field('lead_is_mobile_lead', properties.get('lead_is_mobile_lead'), 'integer', record),
                'lead_is_valid_address': self.validate_field('lead_is_valid_address', properties.get('lead_is_valid_address'), 'integer', record),
                'lead_is_valid_email': self.validate_field('lead_is_valid_email', properties.get('lead_is_valid_email'), 'integer', record),
                'lead_is_year_built_verified': self.validate_field('lead_is_year_built_verified', properties.get('lead_is_year_built_verified'), 'integer', record),
                'lead_is_zillow': self.validate_field('lead_is_zillow', properties.get('lead_is_zillow'), 'integer', record),
                'lead_job_type': self.validate_field('lead_job_type', properties.get('lead_job_type'), 'integer', record),
                'lead_notes': self.validate_field('lead_notes', properties.get('lead_notes'), 'string', record),
                'lead_phone1': self.validate_field('lead_phone1', properties.get('lead_phone1'), 'phone', record),
                'lead_phone2': self.validate_field('lead_phone2', properties.get('lead_phone2'), 'phone', record),
                'lead_phone3': self.validate_field('lead_phone3', properties.get('lead_phone3'), 'phone', record),
                'lead_prospect_id': self.validate_field('lead_prospect_id', properties.get('lead_prospect_id'), 'integer', record),
                'lead_rating': self.validate_field('lead_rating', properties.get('lead_rating'), 'integer', record),
                'lead_salesrabbit_lead_id_new': self.validate_field('lead_salesrabbit_lead_id_new', properties.get('lead_salesrabbit_lead_id_new'), 'integer', record),
                'lead_source': self.validate_field('lead_source', properties.get('lead_source'), 'integer', record),
                'lead_source_notes': self.validate_field('lead_source_notes', properties.get('lead_source_notes'), 'string', record),
                'lead_sourced_on': self.validate_field('lead_sourced_on', properties.get('lead_sourced_on'), 'datetime', record),
                'lead_state': self.validate_field('lead_state', properties.get('lead_state'), 'string', record),
                'lead_status': self.validate_field('lead_status', properties.get('lead_status'), 'integer', record),
                'lead_substatus': self.validate_field('lead_substatus', properties.get('lead_substatus'), 'integer', record),
                'lead_type1': self.validate_field('lead_type1', properties.get('lead_type1'), 'integer', record),
                'lead_type2': self.validate_field('lead_type2', properties.get('lead_type2'), 'integer', record),
                'lead_type4': self.validate_field('lead_type4', properties.get('lead_type4'), 'integer', record),
                'lead_viewed_on': self.validate_field('lead_viewed_on', properties.get('lead_viewed_on'), 'datetime', record),
                'lead_with_dm': self.validate_field('lead_with_dm', properties.get('lead_with_dm'), 'integer', record),
                'lead_year_built': self.validate_field('lead_year_built', properties.get('lead_year_built'), 'string', record),
                'lead_zip': self.validate_field('lead_zip', properties.get('lead_zip'), 'string', record),
                
                # Source fields (prioritize HubSpot field names)
                'primary_source': self.validate_field('primary_source', properties.get('hge_primary_source') or properties.get('primary_source'), 'string', record),
                'secondary_source': self.validate_field('secondary_source', properties.get('hge_secondary_source') or properties.get('secondary_source'), 'string', record),
            }
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming contact record {record_id}: {e} | Record data: {record}")
            raise
    
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
