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
            'properties.hs_lastmodifieddate': 'hs_lastmodifieddate',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform HubSpot deal record to model format"""
        # Use the architectural pattern: apply field mappings first
        transformed = self.apply_field_mappings(record)
        
        # Transform datetime fields
        datetime_fields = ['closedate', 'createdate', 'hs_lastmodifieddate']
        for field in datetime_fields:
            if field in transformed:
                transformed[field] = self._parse_datetime(transformed[field])
        
        # Transform decimal fields
        if 'amount' in transformed:
            transformed['amount'] = self._parse_decimal(transformed['amount'])
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate deal record"""
        if not record.get('id'):
            raise ValidationException("Deal ID is required")
        
        return record
    
    def _parse_decimal(self, value: Any, record_id: str = None, field_name: str = None) -> Optional[float]:
        """Parse decimal value safely"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse decimal value: '{value}' in field '{field_name}' for deal {record_id}")
            return None
    
    def validate_record_extended(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Extended validation for deal record"""
        # Validate HubSpot object ID
        if record.get('hs_object_id'):
            try:
                record['hs_object_id'] = self.validate_field('hs_object_id', record['hs_object_id'], 'object_id', record)
            except ValidationException as e:
                record_id = record.get('id', 'UNKNOWN')
                logger.warning(f"Invalid HubSpot object ID '{record['hs_object_id']}' for deal {record_id}: {e}")
        
        # Validate HubSpot owner ID
        if record.get('hubspot_owner_id'):
            try:
                record['hubspot_owner_id'] = self.validate_field('hubspot_owner_id', record['hubspot_owner_id'], 'object_id', record)
            except ValidationException as e:
                record_id = record.get('id', 'UNKNOWN')
                logger.warning(f"Invalid HubSpot owner ID '{record['hubspot_owner_id']}' for deal {record_id}: {e}")
        
        # Validate currency amount
        if record.get('amount'):
            try:
                record['amount'] = self.validate_field('amount', record['amount'], 'currency', record)
                # Ensure amount is positive
                if record['amount'] and record['amount'] < 0:
                    record_id = record.get('id', 'UNKNOWN')
                    logger.warning(f"Deal amount is negative: '{record['amount']}' for deal {record_id}")
            except ValidationException as e:
                # Use legacy parsing as fallback
                record_id = record.get('id', 'UNKNOWN')
                logger.warning(f"Using legacy decimal parsing for amount '{record['amount']}' for deal {record_id}: {e}")
                record['amount'] = self._parse_decimal(record['amount'], record_id, 'amount')
        
        # Validate datetime fields
        datetime_fields = ['closedate', 'createdate']
        for field in datetime_fields:
            if record.get(field):
                try:
                    record[field] = self.validate_field(field, record[field], 'datetime', record)
                except ValidationException as e:
                    # Use legacy parsing as fallback
                    record_id = record.get('id', 'UNKNOWN')
                    logger.warning(f"Using legacy datetime parsing for field '{field}' with value '{record[field]}' for deal {record_id}: {e}")
                    record[field] = self._parse_datetime(record[field])
        
        return record
