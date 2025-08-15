"""
Base processor for Arrivy CRM integration
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.base.processor import BaseDataProcessor

logger = logging.getLogger(__name__)


class ArrivyBaseProcessor(BaseDataProcessor):
    """Base processor for Arrivy data transformation and validation"""
    
    def __init__(self, model_class=None, **kwargs):
        """Initialize Arrivy base processor"""
        super().__init__(model_class, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy to database fields"""
        return {}
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform an Arrivy record to database format
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement transform_record")
        
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a transformed record
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement validate_record")
        
    def get_record_id(self, record: Dict[str, Any]) -> str:
        """Get the unique identifier for a record"""
        return str(record.get('id', ''))
    
    def get_unique_field_name(self) -> str:
        """Get the name of the unique field in the model"""
        # Default to 'id', can be overridden by subclasses
        return 'id'
        
    def get_record_timestamp(self, record: Dict[str, Any]) -> Optional[str]:
        """Get the timestamp for a record - override in subclasses"""
        return record.get('created') or record.get('updated')
    
    def normalize_datetime(self, dt_string: str) -> Optional[datetime]:
        """Normalize Arrivy datetime strings to timezone-aware UTC datetime objects"""
        if not dt_string:
            return None
            
        try:
            # Arrivy typically uses ISO format
            if dt_string.endswith('Z'):
                dt_string = dt_string[:-1] + '+00:00'
            
            # Parse the datetime
            dt = datetime.fromisoformat(dt_string)
            
            # Ensure it's timezone-aware and in UTC
            if dt.tzinfo is None:
                # If naive, assume it's UTC
                from django.utils import timezone
                dt = timezone.make_aware(dt, timezone.utc)
            else:
                # If already timezone-aware, convert to UTC
                from django.utils import timezone
                dt = dt.astimezone(timezone.utc)
            
            return dt
            
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse datetime '{dt_string}': {e}")
            return None
    
    def normalize_phone(self, phone: str) -> Optional[str]:
        """Normalize phone numbers"""
        if not phone:
            return None
            
        # Remove common formatting
        cleaned = ''.join(filter(str.isdigit, phone))
        
        # Add country code if missing and looks like US number
        if len(cleaned) == 10:
            cleaned = '1' + cleaned
        elif len(cleaned) == 11 and cleaned.startswith('1'):
            pass  # Already has country code
        
        return cleaned if len(cleaned) >= 10 else None
    
    def normalize_email(self, email: str) -> Optional[str]:
        """Normalize email addresses"""
        if not email:
            return None
            
        email = email.strip().lower()
        return email if '@' in email else None
    
    def safe_get_nested(self, record: Dict[str, Any], path: str, default: Any = None) -> Any:
        """Safely get nested dictionary values using dot notation"""
        try:
            keys = path.split('.')
            value = record
            for key in keys:
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return default
            return value
        except (TypeError, AttributeError):
            return default
