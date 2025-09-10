"""
Marketing Source Type processor for Genius CRM data transformation
"""
import logging
from datetime import datetime
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusMarketingSourceTypeProcessor(GeniusBaseProcessor):
    """Processor for Genius marketing source type data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Validate and clean marketing source type record data"""
        
        # Convert tuple to dict using field mapping
        if isinstance(record_data, tuple) and len(record_data) == len(field_mapping):
            record_dict = dict(zip(field_mapping, record_data))
        else:
            logger.error(f"Record length {len(record_data)} does not match mapping length {len(field_mapping)}")
            return None
        
        # Basic validation
        if not record_dict.get('id'):
            logger.debug("Skipping record without id")
            return None
        
        # Transform and validate fields using simple conversions
        validated_record = {}
        
        # Required fields
        validated_record['id'] = int(record_dict.get('id')) if record_dict.get('id') else None
        if not validated_record['id']:
            return None
        
        # Optional fields with transformations
        validated_record['label'] = self._clean_string(record_dict.get('label'), max_length=255)
        validated_record['description'] = self._clean_text(record_dict.get('description'))
        validated_record['is_active'] = self._convert_to_boolean(record_dict.get('is_active'))
        validated_record['list_order'] = self._convert_to_integer(record_dict.get('list_order'))
        
        # Timestamp fields
        validated_record['created_at'] = self._convert_to_datetime(record_dict.get('created_at'))
        validated_record['updated_at'] = self._convert_to_datetime(record_dict.get('updated_at'))
        
        # Add sync timestamp
        from django.utils import timezone
        validated_record['sync_updated_at'] = timezone.now()
        
        return validated_record
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw marketing source type data to dictionary"""
        
        if not raw_data or len(raw_data) != len(field_mapping):
            logger.error(f"Invalid raw data length: {len(raw_data) if raw_data else 0}, expected: {len(field_mapping)}")
            return None
        
        # Create record dictionary
        record_dict = dict(zip(field_mapping, raw_data))
        
        # Apply business rules and transformations
        transformed_record = {}
        
        # ID field (required)
        transformed_record['id'] = record_dict.get('id')
        
        # String fields with length validation
        transformed_record['label'] = self._clean_string(record_dict.get('label'), max_length=255)
        transformed_record['description'] = self._clean_text(record_dict.get('description'))
        
        # Boolean field
        transformed_record['is_active'] = self._convert_to_boolean(record_dict.get('is_active'))
        
        # Integer field (nullable)
        transformed_record['list_order'] = self._convert_to_integer(record_dict.get('list_order'))
        
        # Datetime fields
        transformed_record['created_at'] = self._convert_to_datetime(record_dict.get('created_at'))
        transformed_record['updated_at'] = self._convert_to_datetime(record_dict.get('updated_at'))
        
        return transformed_record
    
    def _clean_string(self, value: Any, max_length: int = None) -> str:
        """Clean and validate string value"""
        if value is None:
            return None
        
        # Convert to string and strip whitespace
        clean_value = str(value).strip()
        
        # Apply length limit if specified
        if max_length and len(clean_value) > max_length:
            clean_value = clean_value[:max_length]
            logger.debug(f"Truncated string to {max_length} characters")
        
        return clean_value if clean_value else None
    
    def _clean_text(self, value: Any) -> str:
        """Clean text field (longer content)"""
        if value is None:
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
