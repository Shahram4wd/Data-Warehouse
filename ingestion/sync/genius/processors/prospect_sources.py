"""
Prospect Source processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date
from django.utils import timezone
from django.utils.timezone import utc

logger = logging.getLogger(__name__)


class GeniusProspectSourceProcessor:
    """Processor for Prospect Source data validation and transformation"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def validate_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate and transform a single prospect source record following CRM sync guide patterns.
        
        Args:
            record: Record data as dictionary
            
        Returns:
            Validated dictionary record or None if invalid
        """
        try:
            # Validate and transform the record directly
            return self._validate_and_transform_record(record)
            
        except Exception as e:
            logger.error(f"Error validating Prospect Source record: {e}")
            logger.error(f"Problematic record: {record}")
            return None
    
    def _validate_and_transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and transform a single Prospect Source record"""
        try:
            validated_record = {}
            
            # ID field (primary key, should not be empty)
            id_value = record.get('id')
            if not id_value:
                logger.error(f"Invalid id for Prospect Source: {id_value}")
                return None
            validated_record['id'] = int(id_value)
            
            # Prospect ID (required, foreign key)
            prospect_id = record.get('prospect_id')
            if not prospect_id:
                logger.error(f"Invalid prospect_id for Prospect Source: {prospect_id}")
                return None
            validated_record['prospect_id'] = int(prospect_id)
            
            # Marketing Source ID (required, foreign key)
            marketing_source_id = record.get('marketing_source_id')
            if not marketing_source_id:
                logger.error(f"Invalid marketing_source_id for Prospect Source: {marketing_source_id}")
                return None
            validated_record['marketing_source_id'] = int(marketing_source_id)
            
            # Source date (nullable datetime)
            source_date = record.get('source_date')
            validated_record['source_date'] = self._validate_datetime(source_date)
            
            # Notes (nullable text field)
            notes = record.get('notes')
            validated_record['notes'] = str(notes) if notes is not None else None
            
            # Add user ID (required integer)
            add_user_id = record.get('add_user_id')
            if add_user_id is not None:
                validated_record['add_user_id'] = int(add_user_id)
            else:
                validated_record['add_user_id'] = 0  # Default fallback
            
            # Source user ID (nullable integer field)
            source_user_id = record.get('source_user_id')
            if source_user_id is not None:
                try:
                    validated_record['source_user_id'] = int(source_user_id)
                except (ValueError, TypeError):
                    logger.warning(f"Invalid source_user_id value: {source_user_id}, setting to None")
                    validated_record['source_user_id'] = None
            else:
                validated_record['source_user_id'] = None
            
            # Timestamps (DateTimeField, not nullable based on model)
            validated_record['add_date'] = self._validate_datetime(record.get('add_date'))
            validated_record['updated_at'] = self._validate_datetime(record.get('updated_at'))
            
            # Ensure required datetime fields are not None
            if validated_record['add_date'] is None:
                validated_record['add_date'] = timezone.now()
            if validated_record['updated_at'] is None:
                validated_record['updated_at'] = timezone.now()
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Error validating Prospect Source record: {e}")
            logger.error(f"Problematic record: {record}")
            return None
    
    def _validate_datetime(self, value: Any) -> Optional[datetime]:
        """Validate datetime field ensuring timezone awareness"""
        if value is None:
            return None
            
        if isinstance(value, datetime):
            # If datetime is naive, assume it's UTC and make it timezone-aware
            if timezone.is_naive(value):
                return timezone.make_aware(value, timezone.get_default_timezone())
            return value
            
        if isinstance(value, date):
            # Convert date to timezone-aware datetime at midnight in default timezone
            naive_dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(naive_dt, timezone.get_default_timezone())
            
        try:
            # Try to parse string datetime with various formats
            if isinstance(value, str):
                # Handle ISO format with Z suffix
                if value.endswith('Z'):
                    parsed_dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    return parsed_dt
                
                # Try common datetime formats
                datetime_formats = [
                    '%Y-%m-%d %H:%M:%S.%f',  # 2025-08-28 07:14:07.949436
                    '%Y-%m-%d %H:%M:%S',     # 2020-11-21 07:38:52
                    '%Y-%m-%d',              # 2020-10-28
                ]
                
                for fmt in datetime_formats:
                    try:
                        parsed_dt = datetime.strptime(value, fmt)
                        # Make timezone-aware using default timezone
                        return timezone.make_aware(parsed_dt, timezone.get_default_timezone())
                    except ValueError:
                        continue
                
                # Fallback: try fromisoformat
                parsed_dt = datetime.fromisoformat(value)
                if timezone.is_naive(parsed_dt):
                    return timezone.make_aware(parsed_dt, timezone.get_default_timezone())
                return parsed_dt
                
        except (ValueError, AttributeError) as e:
            logger.warning(f"Could not parse datetime value '{value}': {e}")
            
        return None

    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw prospect source data to dictionary with proper timezone handling"""
        
        # Apply the full validation and transformation logic
        # This ensures datetime fields are properly converted to timezone-aware datetimes
        return self._validate_and_transform_record(record)
