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
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot contact record to model format using enterprise validation framework"""
        properties = record.get('properties', {})
        record_id = record.get('id', 'UNKNOWN')
        
        # Enterprise transformation with comprehensive validation
        try:
            return {
                'id': self.validate_field('id', record.get('id'), 'object_id', record),
                'firstname': self.validate_field('firstname', properties.get('firstname'), 'string', record),
                'lastname': self.validate_field('lastname', properties.get('lastname'), 'string', record),
                'email': self.validate_field('email', properties.get('email'), 'email', record),
                'phone': self.validate_field('phone', properties.get('phone'), 'phone', record),
                'address': self.validate_field('address', properties.get('address'), 'string', record),
                'city': self.validate_field('city', properties.get('city'), 'string', record),
                'state': self.validate_field('state', properties.get('state'), 'string', record),
                'zip': self.validate_field('zip', properties.get('zip'), 'zip', record),  # Enhanced zip validation
                'createdate': self.validate_field('createdate', properties.get('createdate'), 'datetime', record),
                'lastmodifieddate': self.validate_field('lastmodifieddate', properties.get('lastmodifieddate'), 'datetime', record),
                'campaign_name': self.validate_field('campaign_name', properties.get('campaign_name'), 'string', record),
                'hs_google_click_id': self.validate_field('hs_google_click_id', properties.get('hs_google_click_id'), 'string', record),
                'original_lead_source': self.validate_field('original_lead_source', properties.get('original_lead_source'), 'string', record),
                'division': self.validate_field('division', properties.get('division'), 'string', record),
                'marketsharp_id': self.validate_field('marketsharp_id', properties.get('marketsharp_id'), 'string', record),
                'hs_object_id': self.validate_field('hs_object_id', properties.get('hs_object_id'), 'object_id', record),
                'adgroupid': self.validate_field('adgroupid', properties.get('adgroupid'), 'string', record),
                'ap_leadid': self.validate_field('ap_leadid', properties.get('ap_leadid'), 'string', record),
                'campaign_content': self.validate_field('campaign_content', properties.get('campaign_content'), 'string', record),
                'clickcheck': self.validate_field('clickcheck', properties.get('clickcheck'), 'string', record),
                'clicktype': self.validate_field('clicktype', properties.get('clicktype'), 'string', record),
                'comments': self.validate_field('comments', properties.get('comments'), 'string', record),
                'lead_salesrabbit_lead_id': self.validate_field('lead_salesrabbit_lead_id', properties.get('lead_salesrabbit_lead_id'), 'string', record),
                'msm_source': self.validate_field('msm_source', properties.get('msm_source'), 'string', record),
                'original_lead_source_created': self.validate_field('original_lead_source_created', properties.get('original_lead_source_created'), 'datetime', record),
                'price': self.validate_field('price', properties.get('price'), 'decimal', record),
                'reference_code': self.validate_field('reference_code', properties.get('reference_code'), 'string', record),
                'search_terms': self.validate_field('search_terms', properties.get('search_terms'), 'string', record),
                'tier': self.validate_field('tier', properties.get('tier'), 'string', record),
                'trustedform_cert_url': self.validate_field('trustedform_cert_url', properties.get('trustedform_cert_url'), 'url', record),  # Enhanced URL validation
                'vendorleadid': self.validate_field('vendorleadid', properties.get('vendorleadid'), 'string', record),
                'vertical': self.validate_field('vertical', properties.get('vertical'), 'string', record),
            }
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
            validated_record['id'] = self.validate_field('id', record['id'], 'object_id')
        except ValidationException as e:
            raise ValidationException(f"Invalid contact ID '{record['id']}': {e}")
        
        # Email validation (if present)
        if record.get('email'):
            try:
                validated_record['email'] = self.validate_field('email', record['email'], 'email')
            except ValidationException as e:
                logger.warning(f"Invalid email '{record['email']}' for contact {record_id}: {e}")
                validated_record['email'] = None
        
        # Phone validation (if present)
        if record.get('phone'):
            try:
                validated_record['phone'] = self.validate_field('phone', record['phone'], 'phone')
            except ValidationException as e:
                logger.warning(f"Invalid phone '{record['phone']}' for contact {record_id}: {e}")
                validated_record['phone'] = record['phone']  # Keep original if validation fails
        
        # HubSpot object ID validation
        if record.get('hs_object_id'):
            try:
                validated_record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id')
            except ValidationException as e:
                logger.warning(f"Invalid HubSpot object ID '{record['hs_object_id']}' for contact {record_id}: {e}")
                validated_record['hs_object_id'] = None
        
        # Zip code validation
        if record.get('zip'):
            try:
                validated_record['zip'] = self.validate_field('zip', record['zip'], 'zip_code')
            except ValidationException as e:
                logger.warning(f"Invalid zip code '{record['zip']}' for contact {record_id}: {e}")
                validated_record['zip'] = record['zip']  # Keep original if validation fails
        
        # URL validation
        if record.get('trustedform_cert_url'):
            try:
                validated_record['trustedform_cert_url'] = self.validate_field('trustedform_cert_url', record['trustedform_cert_url'], 'url')
            except ValidationException as e:
                logger.warning(f"Invalid trustedform_cert_url '{record['trustedform_cert_url']}' for contact {record_id}: {e}")
                validated_record['trustedform_cert_url'] = record['trustedform_cert_url']  # Keep original if validation fails
        
        # Decimal validation
        if record.get('price'):
            try:
                validated_record['price'] = self.validate_field('price', record['price'], 'decimal')
            except ValidationException as e:
                logger.warning(f"Invalid price '{record['price']}' for contact {record_id}: {e}")
                validated_record['price'] = None
        
        return validated_record
