"""
Marketing Source processor for Genius CRM data transformation
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusMarketingSourceProcessor(GeniusBaseProcessor):
    """Processor for Genius marketing source data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Validate and clean marketing source record data"""
        
        # Convert tuple to dict using field mapping
        if isinstance(record_data, tuple) and len(record_data) == len(field_mapping):
            record_dict = dict(zip(field_mapping, record_data))
        else:
            logger.error(f"Record length {len(record_data)} does not match mapping length {len(field_mapping)}")
            return None
        
        try:
            # Map fields directly from the database query
            processed = {
                'id': self._convert_to_integer(record_dict.get('id')),
                'type_id': self._convert_to_integer(record_dict.get('type_id', 0)),
                'label': self._convert_to_string(record_dict.get('label')),
                'description': self._convert_to_string(record_dict.get('description')),
                'start_date': self._convert_to_date(record_dict.get('start_date')),
                'end_date': self._convert_to_date(record_dict.get('end_date')),
                'add_user_id': self._convert_to_integer(record_dict.get('add_user_id', 0)),
                'add_date': self._convert_to_datetime(record_dict.get('add_date')),
                'is_active': self._convert_to_boolean(record_dict.get('is_active', True)),
                'is_allow_lead_modification': self._convert_to_boolean(record_dict.get('is_allow_lead_modification', False)),
                'updated_at': self._convert_to_datetime(record_dict.get('updated_at')),
                'sync_updated_at': self.convert_timezone_aware(datetime.now()),
            }
            
            # Validate required fields
            if not processed.get('id'):
                logger.warning("Skipping record with missing id")
                return None
            
            return processed
            
        except Exception as e:
            logger.error(f"Error processing marketing source record: {e}")
            return None
    
    def _convert_to_string(self, value: Any) -> str:
        """Convert value to string or None"""
        if value is None or value == '':
            return None
            
        return str(value).strip() if str(value).strip() else None
    
    def _convert_to_boolean(self, value: Any) -> bool:
        """Convert value to boolean"""
        if value is None:
            return True  # Default to active
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'active')
        
        return bool(value)
    
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
    
    def _convert_to_date(self, value: Any):
        """Convert value to date"""
        if value is None:
            return None
        
        # If it's already a date, return it
        if hasattr(value, 'date'):
            return value.date() if hasattr(value, 'date') else value
        
        # Try to parse string date
        try:
            from dateutil.parser import parse
            dt = parse(str(value))
            return dt.date()
        except (ValueError, TypeError):
            logger.debug(f"Could not convert '{value}' to date")
            return None
