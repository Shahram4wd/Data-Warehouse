"""
Job Change Order Type processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderTypeProcessor:
    """Processor for Job Change Order Type data validation and transformation"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def validate_record(self, record_tuple: tuple, field_mapping: List[str]) -> Optional[Dict[str, Any]]:
        """
        Validate and transform a single job change order type record following CRM sync guide patterns.
        
        Args:
            record_tuple: Raw database record as tuple
            field_mapping: Field names corresponding to tuple positions
            
        Returns:
            Validated dictionary record or None if invalid
        """
        if not record_tuple or len(record_tuple) != len(field_mapping):
            logger.error(f"Record length {len(record_tuple) if record_tuple else 0} does not match mapping length {len(field_mapping)}")
            return None
        
        # Convert tuple to dict using field mapping
        record_dict = dict(zip(field_mapping, record_tuple))
        
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
        validated_record['label'] = self._clean_string(record_dict.get('label'), max_length=32)
        
        return validated_record
    
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
    
    def _convert_to_boolean(self, value: Any) -> bool:
        """Convert value to boolean"""
        if value is None:
            return True  # Default to active
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'y', 'on')
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        return True  # Default fallback
    
    def _convert_to_integer(self, value: Any) -> Optional[int]:
        """Convert value to integer with null handling"""
        if value is None or value == '':
            return None
        
        try:
            if isinstance(value, str):
                # Handle string representations
                clean_str = value.strip()
                if not clean_str:
                    return None
                return int(float(clean_str))  # Handle decimal strings
            
            if isinstance(value, (int, float)):
                return int(value)
            
            if isinstance(value, Decimal):
                return int(value)
            
            logger.warning(f"Could not convert {type(value).__name__} '{value}' to integer")
            return None
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Integer conversion failed for '{value}': {e}")
            return None
    
    def _convert_to_datetime(self, value: Any) -> Optional[datetime]:
        """Convert value to datetime with timezone awareness"""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            # Ensure timezone awareness
            if value.tzinfo is None:
                value = timezone.make_aware(value)
            return value
        
        if isinstance(value, date):
            # Convert date to datetime at midnight
            dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(dt)
        
        if isinstance(value, str):
            try:
                # Try parsing as datetime string
                from django.utils.dateparse import parse_datetime, parse_date
                
                parsed_dt = parse_datetime(value)
                if parsed_dt:
                    if parsed_dt.tzinfo is None:
                        parsed_dt = timezone.make_aware(parsed_dt)
                    return parsed_dt
                
                parsed_date = parse_date(value)
                if parsed_date:
                    dt = datetime.combine(parsed_date, datetime.min.time())
                    return timezone.make_aware(dt)
                
            except Exception as e:
                logger.warning(f"Datetime parsing failed for '{value}': {e}")
        
        return None