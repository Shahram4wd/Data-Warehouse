"""
HubSpot Genius Users processor
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_GeniusUser

logger = logging.getLogger(__name__)

class HubSpotGeniusUsersProcessor(HubSpotBaseProcessor):
    """Process HubSpot Genius Users data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_GeniusUser, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.hs_object_id': 'hs_object_id',
            'properties.hs_createdate': 'hs_createdate',
            'properties.hs_lastmodifieddate': 'hs_lastmodifieddate',
            'properties.arrivy_user_id': 'arrivy_user_id',
            'properties.division': 'division',
            'properties.division_id': 'division_id',
            'properties.email': 'email',
            'properties.job_title': 'job_title',
            'properties.name': 'name',
            'properties.title_id': 'title_id',
            'properties.user_account_type': 'user_account_type',
            'properties.user_id': 'user_id',
            'properties.user_status_inactive': 'user_status_inactive',
        }
    
    def process(self, user_record: Dict[str, Any]) -> Dict[str, Any]:
        """Process a single user record (legacy method)"""
        try:
            transformed = self.transform_record(user_record)
            validated = self.validate_record(transformed)
            return validated
        except Exception as e:
            logger.error(f"Error processing genius user {user_record.get('id', 'UNKNOWN')}: {e}")
            raise
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot genius user record to model format"""
        # Use the architectural pattern: apply field mappings first
        transformed = self.apply_field_mappings(record)
        
        # Transform datetime fields
        datetime_fields = ['hs_createdate', 'hs_lastmodifieddate']
        for field in datetime_fields:
            if field in transformed:
                transformed[field] = self._parse_datetime(transformed[field])
        
        # Transform boolean fields
        if 'user_status_inactive' in transformed:
            transformed['user_status_inactive'] = self._parse_boolean(transformed['user_status_inactive'])
        
        # Clean email if present
        if transformed.get('email') and transformed['email'] != 'null':
            transformed['email'] = self._clean_email(transformed['email'])
        elif transformed.get('email') == 'null' or not transformed.get('email'):
            transformed['email'] = None
        
        # Set archived status based on HubSpot data
        transformed['archived'] = record.get('archived', False)
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate genius user record"""
        if not record.get('id'):
            raise ValidationException("Genius User ID is required")
        
        return record
