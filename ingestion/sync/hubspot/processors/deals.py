"""
HubSpot deals processor
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_Deal

logger = logging.getLogger(__name__)

class HubSpotDealProcessor(HubSpotBaseProcessor):
    """Process HubSpot deal data"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_Deal, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from HubSpot to model"""
        return {
            'id': 'id',
            'properties.dealname': 'dealname',
            'properties.amount': 'amount',
            'properties.closedate': 'closedate',
            'properties.createdate': 'createdate',
            'properties.dealstage': 'dealstage',
            'properties.dealtype': 'dealtype',
            'properties.description': 'description',
            'properties.hs_object_id': 'hs_object_id',
            'properties.hubspot_owner_id': 'hubspot_owner_id',
            'properties.pipeline': 'pipeline',
            'properties.division': 'division',
            'properties.priority': 'priority',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot deal record to model format"""
        properties = record.get('properties', {})
        
        return {
            'id': record.get('id'),
            'dealname': properties.get('dealname'),
            'amount': self._parse_decimal(properties.get('amount')),
            'closedate': self._parse_datetime(properties.get('closedate')),
            'createdate': self._parse_datetime(properties.get('createdate')),
            'dealstage': properties.get('dealstage'),
            'dealtype': properties.get('dealtype'),
            'description': properties.get('description'),
            'hs_object_id': properties.get('hs_object_id'),
            'hubspot_owner_id': properties.get('hubspot_owner_id'),
            'pipeline': properties.get('pipeline'),
            'division': properties.get('division'),
            'priority': properties.get('priority'),
        }
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate deal record using new validation framework"""
        if not record.get('id'):
            raise ValidationException("Deal ID is required")
        
        # Validate deal name is present
        if not record.get('dealname'):
            raise ValidationException("Deal name is required")
        
        # Validate HubSpot object ID
        if record.get('hs_object_id'):
            record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id')
        
        # Validate HubSpot owner ID
        if record.get('hubspot_owner_id'):
            record['hubspot_owner_id'] = self.validate_field('hubspot_owner_id', record['hubspot_owner_id'], 'object_id')
        
        # Validate currency amount
        if record.get('amount'):
            try:
                record['amount'] = self.validate_field('amount', record['amount'], 'currency')
                # Ensure amount is positive
                if record['amount'] and record['amount'] < 0:
                    logger.warning(f"Deal {record['id']} has negative amount: {record['amount']}")
            except ValidationException as e:
                # Use legacy parsing as fallback
                logger.warning(f"Using legacy decimal parsing for amount: {e}")
                record['amount'] = self._parse_decimal(record['amount'])
        
        # Validate datetime fields
        datetime_fields = ['closedate', 'createdate']
        for field in datetime_fields:
            if record.get(field):
                try:
                    record[field] = self.validate_field(field, record[field], 'datetime')
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    logger.warning(f"Using legacy datetime parsing for {field}: {e}")
                    record[field] = self._parse_datetime(record[field])
        
        return record
