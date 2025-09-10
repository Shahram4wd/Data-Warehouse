"""
Lead processor for Genius CRM data transformation
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusLeadProcessor(GeniusBaseProcessor):
    """Processor for Genius lead data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Validate and clean lead record data"""
        
        # Convert tuple to dict using field mapping
        if isinstance(record_data, tuple) and len(record_data) == len(field_mapping):
            record_dict = dict(zip(field_mapping, record_data))
        else:
            logger.error(f"Record length {len(record_data)} does not match mapping length {len(field_mapping)}")
            return None
        
        try:
            # Map fields according to the proper field names
            processed = {
                'lead_id': self._convert_to_integer(record_dict.get('lead_id')),
                'first_name': self._convert_to_string(record_dict.get('first_name')),
                'last_name': self._convert_to_string(record_dict.get('last_name')),
                'email': self._convert_to_string(record_dict.get('email')),
                'phone1': self._convert_to_string(record_dict.get('phone')),  # Maps to phone1
                'address1': self._convert_to_string(record_dict.get('address')),  # Maps to address1
                'city': self._convert_to_string(record_dict.get('city')),
                'state': self._convert_to_string(record_dict.get('state')),
                'zip': self._convert_to_string(record_dict.get('zip_code')),  # Maps to zip
                'source': self._convert_to_integer(record_dict.get('prospect_source_id')),  # Maps to source
                'added_by': self._convert_to_integer(record_dict.get('user_id')),  # Maps to added_by
                'division_id': self._convert_to_integer(record_dict.get('division_id')),
                'notes': self._convert_to_string(record_dict.get('notes')),
                'status': self._convert_to_string(record_dict.get('status')),
                'copied_to_id': self._convert_to_integer(record_dict.get('converted_to_prospect_id')),  # Maps to copied_to_id
                'added_on': self._convert_to_datetime(record_dict.get('created_at')),  # Maps to added_on
                'updated_at': self._convert_to_datetime(record_dict.get('updated_at')),
                'sync_updated_at': self.convert_timezone_aware(datetime.now()),
            }
            
            # Validate required fields
            if not processed.get('lead_id'):
                logger.warning("Skipping record with missing lead_id")
                return None
            
            # Validate at least some name info exists
            if not processed.get('first_name') and not processed.get('last_name'):
                logger.warning(f"Lead {processed['lead_id']} has no first or last name")
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing lead record: {e}")
            return None
    
    def _convert_to_string(self, value: Any) -> str:
        """Convert value to string or None"""
        if value is None or value == '':
            return None
            
        return str(value).strip() if str(value).strip() else None
    
    def _convert_to_integer(self, value: Any) -> int:
        """Convert value to integer or None"""
        if value is None or value == '':
            return None
        
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert '{value}' to integer")
            return None
    
    def _convert_to_datetime(self, value: Any):
        """Convert value to datetime"""
        if value is None:
            return None
        
        # If it's already a datetime, make it timezone-aware
        if isinstance(value, datetime):
            return self.convert_timezone_aware(value)
        
        # Try to parse string datetime
        try:
            from dateutil.parser import parse
            dt = parse(str(value))
            return self.convert_timezone_aware(dt)
        except (ValueError, TypeError):
            logger.debug(f"Could not convert '{value}' to datetime")
            return None
