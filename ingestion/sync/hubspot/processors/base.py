"""
Base processor for HubSpot data
"""
import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ingestion.base.processor import BaseDataProcessor
from ingestion.base.exceptions import (
    ValidationException, RetryableException, NonRetryableException
)
from ingestion.base.validators import (
    EmailValidator, PhoneValidator, DateValidator, TimeValidator,
    DecimalValidator, BooleanValidator, StringValidator
)
from ingestion.base.retry import retry_with_backoff, RetryConfig
from ingestion.base.config import SyncConfiguration
from ingestion.base.performance import performance_monitor
from ingestion.sync.hubspot.validators import (
    HubSpotEmailValidator, HubSpotPhoneValidator, HubSpotObjectIdValidator,
    HubSpotTimestampValidator, HubSpotCurrencyValidator, HubSpotZipCodeValidator,
    HubSpotStateValidator, HubSpotUrlValidator
)

logger = logging.getLogger(__name__)

class HubSpotBaseProcessor(BaseDataProcessor):
    """Base processor for HubSpot data"""
    
    def __init__(self, model_class, **kwargs):
        super().__init__(model_class, **kwargs)
        
        # Initialize configuration
        self.config = SyncConfiguration('hubspot')
        
        # Initialize validators
        self.email_validator = HubSpotEmailValidator()
        self.phone_validator = HubSpotPhoneValidator()
        self.object_id_validator = HubSpotObjectIdValidator()
        self.timestamp_validator = HubSpotTimestampValidator()
        self.currency_validator = HubSpotCurrencyValidator()
        self.zip_code_validator = HubSpotZipCodeValidator()
        self.state_validator = HubSpotStateValidator()
        self.url_validator = HubSpotUrlValidator()
        self.date_validator = DateValidator()
        self.time_validator = TimeValidator()
        self.decimal_validator = DecimalValidator()
        self.boolean_validator = BooleanValidator()
        
        # Initialize retry configuration
        self.retry_config = RetryConfig(**self.config.get_retry_config())

    def apply_field_mappings(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field mappings to transform a record"""
        field_mappings = self.get_field_mappings()
        transformed = {}
        
        for source_field, target_field in field_mappings.items():
            # Handle nested fields using dot notation
            value = self._get_nested_value(record, source_field)
            if value is not None:
                transformed[target_field] = value
        
        return transformed
    
    def parse_duration(self, value: str) -> int:
        """Convert duration to minutes
        
        Args:
            value: Duration string in various formats:
                - 'HH:MM:SS' format (e.g., '2:00:00')
                - Numeric string representing seconds (e.g., '7200')
                - Numeric string representing milliseconds (e.g., '7200000')
            
        Returns:
            Duration in minutes as integer
            
        Raises:
            Returns 0 if parsing fails to maintain data integrity
        """
        try:
            if not value:
                return 0
            
            # Handle string input    
            if isinstance(value, str):
                # Check if it's in HH:MM:SS format (contains colons)
                if ':' in value:
                    parts = value.split(":")
                    if len(parts) == 3:
                        h, m, s = map(int, parts)
                        return h * 60 + m + s // 60
                    elif len(parts) == 2:
                        # MM:SS format
                        m, s = map(int, parts)
                        return m + s // 60
                    else:
                        # Invalid colon format, treat as numeric
                        numeric_value = float(value.replace(':', ''))
                else:
                    # Numeric string - determine if it's seconds or milliseconds
                    numeric_value = float(value)
                
                # Convert numeric value to minutes
                if numeric_value > 86400:  # > 24 hours in seconds, likely milliseconds
                    return int(numeric_value / 1000 / 60)  # milliseconds to minutes
                else:  # likely seconds
                    return int(numeric_value / 60)  # seconds to minutes
            
            # Handle numeric input (assume it's already in minutes)
            if isinstance(value, (int, float)):
                return int(value)
                
            return 0
        except Exception as e:
            logger.warning(f"Failed to parse duration '{value}': {e}")
            return 0  # Return 0 instead of raising exception for data integrity
    
    def validate_field(self, field_name: str, value: Any, field_type: str = 'string', context: Dict[str, Any] = None) -> Any:
        """Validate a field using appropriate validator with optional context"""
        # Check if validation is enabled
        if not self.config.is_validation_enabled():
            return value
        
        try:
            if field_type == 'email':
                return self.email_validator.validate(value)
            elif field_type == 'phone':
                return self.phone_validator.validate(value)
            elif field_type == 'object_id':
                return self.object_id_validator.validate(value)
            elif field_type == 'timestamp':
                return self.timestamp_validator.validate(value)
            elif field_type == 'currency':
                return self.currency_validator.validate(value)
            elif field_type == 'zip_code' or field_type == 'zip':
                return self.zip_code_validator.validate(value)
            elif field_type == 'state':
                return self.state_validator.validate(value)
            elif field_type == 'url':
                return self.url_validator.validate(value)
            elif field_type == 'date' or field_type == 'datetime':
                return self.date_validator.validate(value)
            elif field_type == 'time':
                return self.time_validator.validate(value)
            elif field_type == 'decimal':
                return self.decimal_validator.validate(value)
            elif field_type == 'boolean':
                return self.boolean_validator.validate(value)
            else:
                # Default string validation
                return StringValidator().validate(value)
        except ValidationException as e:
            # Handle validation errors based on strict mode
            context_info = ""
            hubspot_url = ""
            record_id = None
            
            if context:
                # Build context string with available identifiers
                identifiers = []
                record_id = context.get('id')
                for id_field in ['id']:
                    if context.get(id_field):
                        identifiers.append(f"{id_field}={context[id_field]}")
                
                if identifiers:
                    context_info = f" (Record: {', '.join(identifiers)})"
                else:
                    # Debug: context exists but no ID found
                    context_info = f" (Record: no ID found in context keys: {list(context.keys())})"
            else:
                # Debug: no context provided
                context_info = " (Record: no context provided)"
                
            # Add HubSpot URL for easy access
            if record_id:
                    # Determine object type based on context or default to contacts
                    object_type_map = {
                        'appointment': '0-421',  # Custom object for appointments
                        'contact': '0-1',       # Standard contact object
                        'deal': '0-3',          # Standard deal object
                        'company': '0-2'        # Standard company object
                    }
                    # Try to determine object type from context or use contact as default
                    object_type = '0-1'  # Default to contacts
                    if hasattr(self, 'model_class') and self.model_class:
                        model_name = self.model_class.__name__.lower()
                        if 'appointment' in model_name:
                            object_type = '0-421'
                        elif 'deal' in model_name:
                            object_type = '0-3'
                        elif 'company' in model_name:
                            object_type = '0-2'
                    
                    hubspot_url = f" - HubSpot URL: https://app.hubspot.com/contacts/[PORTAL_ID]/object/{object_type}/{record_id}"
            
            if self.config.is_strict_validation():
                logger.error(f"Strict validation failed for field '{field_name}' with value '{value}'{context_info}: {e}{hubspot_url}")
                raise ValidationException(f"Field '{field_name}': {e}")
            else:
                logger.warning(f"Validation warning for field '{field_name}' with value '{value}'{context_info}: {e}{hubspot_url}")
                return value  # Return original value in non-strict mode
        except Exception as e:
            context_info = ""
            hubspot_url = ""
            if context and context.get('id'):
                context_info = f" (Record ID: {context['id']})"
                record_id = context['id']
                # Add HubSpot URL based on model type
                object_type = '0-1'  # Default to contacts
                if hasattr(self, 'model_class') and self.model_class:
                    model_name = self.model_class.__name__.lower()
                    if 'appointment' in model_name:
                        object_type = '0-421'
                    elif 'deal' in model_name:
                        object_type = '0-3'
                    elif 'company' in model_name:
                        object_type = '0-2'
                hubspot_url = f" - HubSpot URL: https://app.hubspot.com/contacts/[PORTAL_ID]/object/{object_type}/{record_id}"
            
            logger.error(f"Unexpected error validating field '{field_name}' with value '{value}'{context_info}: {e}{hubspot_url}")
            if self.config.is_strict_validation():
                raise ValidationException(f"Field '{field_name}': Validation error")
            return value
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from HubSpot format using validator"""
        try:
            return self.date_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_datetime(value)
    
    def _legacy_parse_datetime(self, value: Any) -> Optional[datetime]:
        """Legacy datetime parsing for backward compatibility"""
        if not value:
            return None
        
        # If it's already a datetime object, return it
        if isinstance(value, datetime):
            return value
        
        # Convert to string if it's a number (timestamp)
        if isinstance(value, (int, float)):
            value = str(int(value))
        
        # Try to parse as datetime
        try:
            # HubSpot timestamps are in milliseconds
            if str(value).isdigit():
                timestamp = int(value)
                # Convert from milliseconds to seconds
                if timestamp > 10000000000:  # If timestamp is in milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            else:
                # Try to parse as ISO format
                parsed = parse_datetime(str(value))
                if parsed:
                    return parsed
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
        
        return None
    
    def _parse_decimal(self, value: Any) -> Optional[Decimal]:
        """Parse decimal value using validator"""
        try:
            return self.decimal_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_decimal(value)
    
    def _legacy_parse_decimal(self, value: Any, record_id: str = None, field_name: str = None) -> Optional[Decimal]:
        """Legacy decimal parsing for backward compatibility"""
        if not value:
            return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError):
            record_context = f" for record {record_id}" if record_id else ""
            field_context = f" in field '{field_name}'" if field_name else ""
            logger.warning(f"Failed to parse decimal '{value}'{field_context}{record_context} - HubSpot URL: https://app.hubspot.com/contacts/[PORTAL_ID]/object/0-421/{record_id}")
            return None
    
    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """Parse boolean value using validator"""
        try:
            return self.boolean_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_boolean(value)
    
    def _legacy_parse_boolean(self, value: Any) -> Optional[bool]:
        """Legacy boolean parsing for backward compatibility"""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.lower()
            if value in ('true', '1', 'yes', 'on'):
                return True
            elif value in ('false', '0', 'no', 'off'):
                return False
        
        return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number using validator"""
        try:
            return self.phone_validator.validate(phone) or phone
        except ValidationException:
            return self._legacy_clean_phone(phone)
    
    def _legacy_clean_phone(self, phone: str) -> str:
        """Legacy phone cleaning for backward compatibility"""
        if not phone:
            return phone
        
        # Remove all non-digit characters
        cleaned = re.sub(r'\D', '', phone)
        
        # Format as standard phone number if it's 10 digits
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        
        return phone
    
    def _clean_email(self, email: str) -> str:
        """Clean and validate email using validator"""
        try:
            return self.email_validator.validate(email) or email
        except ValidationException:
            return self._legacy_clean_email(email)
    
    def _legacy_clean_email(self, email: str) -> str:
        """Legacy email cleaning for backward compatibility"""
        if not email:
            return email
        
        email = email.lower().strip()
        
        # Basic email validation
        if '@' not in email or '.' not in email:
            raise ValidationException(f"Invalid email format: {email}")
        
        return email
    
    def _get_nested_value(self, data: dict, key_path: str) -> Any:
        """Get value from nested dictionary using dot notation"""
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def log_database_error(self, error: Exception, record_data: Dict[str, Any], operation: str = "save") -> None:
        """Log database errors with comprehensive record context for debugging"""
        record_id = record_data.get('id', 'UNKNOWN')
        
        # Determine object type and HubSpot URL
        object_type = '0-1'  # Default to contacts
        if hasattr(self, 'model_class') and self.model_class:
            model_name = self.model_class.__name__.lower()
            if 'appointment' in model_name:
                object_type = '0-421'
            elif 'deal' in model_name:
                object_type = '0-3'
            elif 'company' in model_name:
                object_type = '0-2'
        
        hubspot_url = f"https://app.hubspot.com/contacts/[PORTAL_ID]/object/{object_type}/{record_id}"
        
        # Extract field information from error message
        error_msg = str(error)
        field_info = ""
        
        if "value too long for type character varying" in error_msg:
            # Try to identify which field is too long
            long_fields = []
            for field_name, field_value in record_data.items():
                if field_value and isinstance(field_value, str):
                    if "character varying(10)" in error_msg and len(field_value) > 10:
                        long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:50]}{'...' if len(field_value) > 50 else ''}'")
                    elif "character varying(50)" in error_msg and len(field_value) > 50:
                        long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:50]}{'...' if len(field_value) > 50 else ''}'")
                    elif "character varying(100)" in error_msg and len(field_value) > 100:
                        long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:50]}{'...' if len(field_value) > 50 else ''}'")
                    elif "character varying(255)" in error_msg and len(field_value) > 255:
                        long_fields.append(f"{field_name}({len(field_value)} chars): '{field_value[:50]}{'...' if len(field_value) > 50 else ''}'")
            
            if long_fields:
                field_info = f" - Possible long fields: {'; '.join(long_fields)}"
        
        # Log comprehensive error information
        logger.error(f"Database {operation} failed for record {record_id}: {error_msg}{field_info} - HubSpot URL: {hubspot_url}")
        
        # Also log some key field values for debugging
        debug_fields = ['first_name', 'last_name', 'email', 'phone1', 'state', 'zip', 'city', 'address1']
        field_values = []
        for field in debug_fields:
            if field in record_data and record_data[field]:
                value = str(record_data[field])
                display_value = value[:30] + ('...' if len(value) > 30 else '')
                field_values.append(f"{field}='{display_value}'")
        
        if field_values:
            logger.error(f"Record {record_id} key fields: {', '.join(field_values)}")
    
    def validate_field_length(self, field_name: str, value: Any, max_length: int, record_id: str = None) -> str:
        """Validate and truncate field length to prevent database errors"""
        if not value:
            return value
        
        str_value = str(value)
        if len(str_value) > max_length:
            record_context = f" for record {record_id}" if record_id else ""
            logger.warning(f"Field '{field_name}' too long ({len(str_value)} chars), truncating to {max_length}{record_context}: '{str_value[:50]}{'...' if len(str_value) > 50 else ''}'")
            return str_value[:max_length]
        
        return str_value
