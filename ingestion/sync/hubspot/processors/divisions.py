"""
HubSpot divisions processor
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_Division

logger = logging.getLogger(__name__)

class HubSpotDivisionProcessor(HubSpotBaseProcessor):
    """Process HubSpot division data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Division, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.division_name': 'division_name',
            'properties.division_label': 'division_label',
            'properties.label': 'label',
            'properties.division_code': 'division_code',
            'properties.code': 'code',
            'properties.status': 'status',
            'properties.region': 'region',
            'properties.manager_name': 'manager_name',
            'properties.manager_email': 'manager_email',
            'properties.phone': 'phone',
            'properties.address1': 'address1',
            'properties.address2': 'address2',
            'properties.city': 'city',
            'properties.state': 'state',
            'properties.zip': 'zip',
            'properties.hs_object_id': 'hs_object_id',
            'properties.hs_createdate': 'hs_createdate',
            'properties.hs_lastmodifieddate': 'hs_lastmodifieddate',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot division record to model format"""
        # Use the architectural pattern: apply field mappings first
        transformed = self.apply_field_mappings(record)
        
        # Transform datetime fields
        datetime_fields = ['hs_createdate', 'hs_lastmodifieddate']
        for field in datetime_fields:
            if field in transformed:
                transformed[field] = self._parse_datetime(transformed[field])
        
        # Clean email if present
        if transformed.get('manager_email'):
            transformed['manager_email'] = self._clean_email(transformed['manager_email'])
        
        # Clean phone if present
        if transformed.get('phone'):
            transformed['phone'] = self._clean_phone(transformed['phone'])
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate division record using new validation framework"""
        if not record.get('id'):
            raise ValidationException("Division ID is required")
        
        # Validate HubSpot object ID
        if record.get('hs_object_id'):
            record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id', record)
        
        # Validate phone number
        if record.get('phone'):
            record['phone'] = self.validate_field('phone', record['phone'], 'phone', record)
        
        # Validate manager email format if present
        if record.get('manager_email'):
            record['manager_email'] = self.validate_field('manager_email', record['manager_email'], 'email', record)
        
        # Validate address fields
        if record.get('zip'):
            try:
                record['zip'] = self.validate_field('zip', record['zip'], 'zip_code', record)
            except ValidationException as e:
                logger.warning(f"Invalid zip code for division {record['id']}: {e}")
                # Keep original value if validation fails
        
        if record.get('state'):
            try:
                record['state'] = self.validate_field('state', record['state'], 'state', record)
            except ValidationException as e:
                logger.warning(f"Invalid state code for division {record['id']}: {e}")
                # Keep original value if validation fails
        
        # Validate datetime fields
        datetime_fields = ['hs_createdate', 'hs_lastmodifieddate']
        for field in datetime_fields:
            if record.get(field):
                try:
                    record[field] = self.validate_field(field, record[field], 'datetime', record)
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy datetime parsing for {field}: {e}")
                    record[field] = self._parse_datetime(record[field])
        
        # Validate required fields
        if not record.get('division_name') and not record.get('division_label'):
            raise ValidationException("Division name or label is required")
        
        return record
