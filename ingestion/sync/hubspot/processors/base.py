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
            
            # Handle HH:MM:SS format
            if ':' in str(value):
                parts = str(value).split(':')
                if len(parts) >= 2:
                    hours = int(parts[0])
                    minutes = int(parts[1])
                    return hours * 60 + minutes
            
            # Handle numeric values (seconds or milliseconds)
            numeric_value = float(value)
            
            # If very large, assume milliseconds and convert to seconds
            if numeric_value > 86400:  # More than 24 hours in seconds
                numeric_value = numeric_value / 1000
            
            # Convert seconds to minutes
            return int(numeric_value / 60)
            
        except Exception as e:
            logger.warning(f"Failed to parse duration '{value}': {e}")
            return 0
    
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
            elif field_type == 'datetime':
                return self.timestamp_validator.validate(value)
            elif field_type == 'currency':
                return self.currency_validator.validate(value)
            elif field_type == 'zip_code':
                return self.zip_code_validator.validate(value)
            elif field_type == 'state':
                return self.state_validator.validate(value)
            elif field_type == 'url':
                return self.url_validator.validate(value)
            elif field_type == 'date':
                return self.date_validator.validate(value)
            elif field_type == 'time':
                return self.time_validator.validate(value)
            elif field_type == 'decimal':
                return self.decimal_validator.validate(value)
            elif field_type == 'boolean':
                return self.boolean_validator.validate(value)
            else:
                return value
            
        except ValidationException as e:
            context_info = self.build_context_info(context)
            logger.warning(
                f"Validation warning for field '{field_name}' "
                f"with value '{value}'{context_info}: {e}"
            )
            return value
        except Exception as e:
            logger.error(f"Unexpected validation error for field '{field_name}': {e}")
            return value
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from HubSpot format using validator"""
        try:
            return self.timestamp_validator.validate(value)
        except ValidationException:
            return self._legacy_parse_datetime(value)
    
    def _legacy_parse_datetime(self, value: Any) -> Optional[datetime]:
        """Legacy datetime parsing for backward compatibility"""
        if not value:
            return None
        
        # If it's already a datetime object, return it
        if isinstance(value, datetime):
            return value if value.tzinfo else timezone.make_aware(value)
        
        # Convert to string if it's a number (timestamp)
        if isinstance(value, (int, float)):
            try:
                # Handle millisecond timestamps
                if value > 10**10:
                    value = value / 1000
                return timezone.make_aware(datetime.fromtimestamp(value))
            except (ValueError, OSError):
                return None
        
        # Normalize the datetime string to handle lowercase 'z'
        value_str = str(value).strip()
        if value_str.endswith('z'):
            value_str = value_str[:-1] + 'Z'
        
        # Try to parse as datetime
        try:
            parsed = parse_datetime(value_str)
            return parsed if parsed and parsed.tzinfo else timezone.make_aware(parsed) if parsed else None
        except (ValueError, OSError) as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
            return None
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer value, handling empty strings and null values"""
        if value is None:
            return None
        
        # Handle empty string case - return None for BigIntegerField compatibility
        if isinstance(value, str) and value.strip() == '':
            return None
        
        try:
            return int(float(value))  # Handle decimal strings
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse integer '{value}': {e}")
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
            logger.warning(f"Failed to parse decimal '{value}' for record {record_id}, field {field_name}")
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
            return value.lower() in ('true', '1', 'yes', 'on')
        
        return None
    
    def _clean_phone(self, phone: str) -> str:
        """Clean phone number using validator"""
        try:
            return self.phone_validator.validate(phone)
        except ValidationException:
            return self._legacy_clean_phone(phone)
    
    def _legacy_clean_phone(self, phone: str) -> str:
        """Legacy phone cleaning for backward compatibility"""
        if not phone:
            return phone
        
        # Basic phone cleaning
        import re
        cleaned = re.sub(r'[^\d]', '', str(phone))
        
        # Format phone number if it's a valid US number
        if len(cleaned) == 10:
            return f"({cleaned[:3]}) {cleaned[3:6]}-{cleaned[6:]}"
        elif len(cleaned) == 11 and cleaned[0] == '1':
            return f"({cleaned[1:4]}) {cleaned[4:7]}-{cleaned[7:]}"
        
        return cleaned[:20]  # Truncate to max length
    
    def _clean_email(self, email: str) -> str:
        """Clean email using validator"""
        try:
            return self.email_validator.validate(email)
        except ValidationException:
            return self._legacy_clean_email(email)
    
    def _legacy_clean_email(self, email: str) -> str:
        """Legacy email cleaning for backward compatibility"""
        if not email:
            return email
        
        return str(email).strip().lower()
    
    def _get_nested_value(self, data: dict, key_path: str) -> Any:
        """Extract nested value using dot notation"""
        keys = key_path.split('.')
        value = data
        
        for key in keys:
            if isinstance(value, dict) and key in value:
                value = value[key]
            else:
                return None
        
        return value
    
    def log_database_error(self, error: Exception, record_data: Dict[str, Any], operation: str = "save") -> None:
        """Log database errors with context"""
        record_id = record_data.get('id', 'UNKNOWN')
        logger.error(f"Database error during {operation} for record {record_id}: {error}")
    
    def validate_field_length(self, field_name: str, value: Any, max_length: int, record_id: str = None) -> str:
        """Validate and truncate field length"""
        if value is None:
            return None
        
        str_value = str(value)
        if len(str_value) > max_length:
            logger.warning(f"Truncating field '{field_name}' from {len(str_value)} to {max_length} chars for record {record_id}")
            return str_value[:max_length]
        
        return str_value

    def build_context_info(self, context: Dict) -> str:
        """Build context string for logging"""
        if not context:
            return " (Record: no context provided)"
        
        record_id = context.get('id')
        if record_id:
            return f" (Record: id={record_id})"
        else:
            return f" (Record: no ID found in context keys: {list(context.keys())})"

    def _truncate_field(self, value: Any, max_length: int, field_name: str, record_id: str) -> str:
        """Truncate field to maximum length"""
        return self.validate_field_length(field_name, value, max_length, record_id)

    def _parse_time(self, value: Any, record_id: str, field_name: str) -> Optional[datetime.time]:
        """Parse time value"""
        if not value:
            return None
        
        try:
            if isinstance(value, str):
                # Handle various time formats
                if ':' in value:
                    parts = value.split(':')
                    hour = int(parts[0])
                    minute = int(parts[1]) if len(parts) > 1 else 0
                    second = int(parts[2]) if len(parts) > 2 else 0
                    return datetime.time(hour, minute, second)
            
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse time '{value}' for record {record_id}, field {field_name}: {e}")
            return None

    def _parse_date(self, value: Any, record_id: str, field_name: str) -> Optional[datetime.date]:
        """Parse date value"""
        if not value:
            return None
        
        try:
            if isinstance(value, str):
                parsed_dt = parse_datetime(value)
                if parsed_dt:
                    return parsed_dt.date()
            elif isinstance(value, datetime):
                return value.date()
            
            return None
        except (ValueError, TypeError) as e:
            logger.warning(f"Failed to parse date '{value}' for record {record_id}, field {field_name}: {e}")
            return None

    def _parse_boolean_not_null(self, value: Any) -> bool:
        """Parse boolean value, defaulting to False if None"""
        result = self._parse_boolean(value)
        return result if result is not None else False
    
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
