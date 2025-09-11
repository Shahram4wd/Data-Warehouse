"""
MarketSharp Source processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from django.utils.timezone import utc

logger = logging.getLogger(__name__)


class GeniusMarketSharpSourceProcessor:
    """Processor for MarketSharp source data validation and transformation"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def validate_record(self, record_tuple: tuple, field_mapping: List[str]) -> Optional[Dict[str, Any]]:
        """
        Validate and transform a single marketsharp source record following CRM sync guide patterns.
        
        Args:
            record_tuple: Raw database record as tuple
            field_mapping: Field names corresponding to tuple positions
            
        Returns:
            Validated dictionary record or None if invalid
        """
        try:
            # Convert tuple to dictionary using field mapping
            record = dict(zip(field_mapping, record_tuple))
            
            # Validate and transform the record
            return self._validate_and_transform_record(record)
            
        except Exception as e:
            logger.error(f"Error validating MarketSharp source record: {e}")
            logger.error(f"Problematic record: {record_tuple}")
            return None
    
    def _validate_and_transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and transform a single MarketSharp source record"""
        try:
            validated_record = {}
            
            # ID field (primary key, should not be empty)
            id_value = record.get('id')
            if not id_value:
                logger.error(f"Invalid id for MarketSharp source: {id_value}")
                return None
            validated_record['id'] = int(id_value)
            
            # MarketSharp ID (varchar(256), can be empty but not null based on model)
            marketsharp_id = record.get('marketsharp_id')
            validated_record['marketsharp_id'] = str(marketsharp_id) if marketsharp_id is not None else ''
            
            # Source name (varchar(128), can be empty but not null based on model)
            source_name = record.get('source_name')
            validated_record['source_name'] = str(source_name) if source_name is not None else ''
            
            # Inactive flag (SmallIntegerField with default 0)
            inactive = record.get('inactive')
            if inactive is not None:
                validated_record['inactive'] = int(inactive)
            else:
                validated_record['inactive'] = 0
            
            # Timestamps (DateTimeField, not nullable based on model)
            validated_record['created_at'] = self._validate_datetime(record.get('created_at'))
            validated_record['updated_at'] = self._validate_datetime(record.get('updated_at'))
            
            # Ensure required datetime fields are not None
            if validated_record['created_at'] is None:
                validated_record['created_at'] = timezone.now()
            if validated_record['updated_at'] is None:
                validated_record['updated_at'] = timezone.now()
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Error validating MarketSharp source record: {e}")
            logger.error(f"Problematic record: {record}")
            return None
    
    def _validate_datetime(self, value: Any) -> Optional[datetime]:
        """Validate datetime field ensuring timezone awareness"""
        if value is None:
            return None
            
        if isinstance(value, datetime):
            # If datetime is naive, assume it's UTC and make it timezone-aware
            if timezone.is_naive(value):
                return timezone.make_aware(value, utc)
            return value
            
        if isinstance(value, date):
            # Convert date to timezone-aware datetime at midnight UTC
            naive_dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(naive_dt, utc)
            
        try:
            # Try to parse string datetime
            if isinstance(value, str):
                parsed_dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                # If the parsed datetime is still naive, make it UTC
                if timezone.is_naive(parsed_dt):
                    return timezone.make_aware(parsed_dt, utc)
                return parsed_dt
        except (ValueError, AttributeError):
            pass
            
        return None
