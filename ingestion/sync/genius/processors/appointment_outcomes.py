"""
Processor for Genius appointment outcomes data transformation and validation.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from django.utils import timezone

logger = logging.getLogger(__name__)


class GeniusAppointmentOutcomeProcessor:
    """Processor for Genius appointment outcome records."""
    
    def __init__(self, model_class):
        self.model_class = model_class
        self.processed_count = 0
        self.error_count = 0
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw Genius appointment outcome record to match our model.
        
        Database fields (from SELECT *):
        - id: Primary key
        - type_id: FK to appointment outcome types
        - label: Display name/description
        - is_active: Boolean status
        - created_at: Timestamp
        - updated_at: Timestamp
        """
        try:
            transformed = {
                'id': self._parse_integer(record.get('id')),
                'type_id': self._parse_integer(record.get('type_id')),
                'label': self._parse_string(record.get('label')),
                'is_active': self._parse_boolean(record.get('is_active')),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            # Remove any None values for optional fields
            transformed = {k: v for k, v in transformed.items() if v is not None}
            
            self.processed_count += 1
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming appointment outcome record {record.get('id', 'unknown')}: {e}")
            self.error_count += 1
            raise
    
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate that the record has required fields."""
        required_fields = ['id']
        
        for field in required_fields:
            if field not in record or record[field] is None:
                logger.warning(f"Missing required field '{field}' in appointment outcome record")
                return False
        
        return True
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer values safely."""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Failed to parse integer value: {value}")
            return None
    
    def _parse_string(self, value: Any) -> Optional[str]:
        """Parse string values safely."""
        if value is None:
            return None
        return str(value).strip() if str(value).strip() else None
    
    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """Parse boolean values safely."""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, str)):
            # Handle common boolean representations
            str_value = str(value).lower().strip()
            if str_value in ('1', 'true', 'yes', 'y', 'on'):
                return True
            elif str_value in ('0', 'false', 'no', 'n', 'off'):
                return False
        
        logger.warning(f"Failed to parse boolean value: {value}")
        return None
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime values safely."""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return timezone.make_aware(value) if timezone.is_naive(value) else value
        
        if isinstance(value, str):
            try:
                # Try common datetime formats
                for fmt in ('%Y-%m-%d %H:%M:%S', '%Y-%m-%d'):
                    try:
                        dt = datetime.strptime(value, fmt)
                        return timezone.make_aware(dt)
                    except ValueError:
                        continue
            except Exception:
                pass
        
        logger.warning(f"Failed to parse datetime value: {value}")
        return None
    
    def get_stats(self) -> Dict[str, int]:
        """Get processing statistics."""
        return {
            'processed': self.processed_count,
            'errors': self.error_count
        }
