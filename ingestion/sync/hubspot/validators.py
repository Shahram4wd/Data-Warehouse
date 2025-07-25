"""
HubSpot-specific validators
"""
import re
import logging
from datetime import datetime
from decimal import Decimal, InvalidOperation
from typing import Any, Optional
from django.utils import timezone
from django.core.validators import validate_email, URLValidator
from django.core.exceptions import ValidationError
from django.utils.dateparse import parse_datetime
from ingestion.base.exceptions import ValidationException
from ingestion.base.validators import BaseValidator, StringValidator, DecimalValidator

logger = logging.getLogger(__name__)

class HubSpotEmailValidator:
    """Validator for HubSpot email fields"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate email address"""
        if not value or str(value).lower() == 'null':
            return None
        
        email = str(value).strip().lower()
        
        try:
            validate_email(email)
            return email
        except ValidationError:
            raise ValidationException(f"Invalid email format: {email}")

class HubSpotPhoneValidator:
    """Validator for HubSpot phone fields"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate and clean phone number"""
        if not value:
            return None
        
        # Basic phone cleaning - remove non-digits except +
        phone = re.sub(r'[^\d+]', '', str(value))
        
        # Basic validation - must have at least 10 digits
        digits = re.sub(r'[^\d]', '', phone)
        if len(digits) < 10:
            raise ValidationException(f"Phone number too short: {value}")
        
        # Truncate to reasonable length
        return phone[:20]

class HubSpotObjectIdValidator:
    """Validator for HubSpot object IDs"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate HubSpot object ID"""
        if not value:
            return None
        
        obj_id = str(value).strip()
        
        # HubSpot object IDs are typically numeric
        if not obj_id.isdigit():
            logger.warning(f"Non-numeric HubSpot object ID: {obj_id}")
        
        return obj_id

class HubSpotTimestampValidator:
    """Validator for HubSpot timestamps"""
    
    def validate(self, value: Any) -> Optional[datetime]:
        """Validate HubSpot timestamp"""
        if not value:
            return None
        
        # If already a datetime, ensure timezone awareness
        if isinstance(value, datetime):
            return value if value.tzinfo else timezone.make_aware(value)
        
        # Handle numeric timestamps (milliseconds)
        if isinstance(value, (int, float)):
            try:
                # Handle millisecond timestamps
                if value > 10**10:
                    value = value / 1000
                return timezone.make_aware(datetime.fromtimestamp(value))
            except (ValueError, OSError):
                raise ValidationException(f"Invalid timestamp: {value}")
        
        # Handle string timestamps
        try:
            # Normalize the datetime string to handle lowercase 'z'
            value_str = str(value).strip()
            if value_str.endswith('z'):
                value_str = value_str[:-1] + 'Z'
            
            parsed = parse_datetime(value_str)
            if parsed:
                return parsed if parsed.tzinfo else timezone.make_aware(parsed)
            else:
                raise ValidationException(f"Could not parse datetime: {value}")
        except Exception as e:
            raise ValidationException(f"Invalid datetime format: {value} - {e}")

class HubSpotCurrencyValidator:
    """Validator for HubSpot currency fields"""
    
    def validate(self, value: Any) -> Optional[Decimal]:
        """Validate currency amount"""
        if not value:
            return None
        
        try:
            # Clean currency symbols and commas
            cleaned = re.sub(r'[,$]', '', str(value))
            return Decimal(cleaned)
        except (InvalidOperation, ValueError):
            raise ValidationException(f"Invalid currency amount: {value}")

class HubSpotZipCodeValidator:
    """Validator for zip codes"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate zip code"""
        if not value:
            return None
        
        zip_code = str(value).strip()
        
        # Basic US zip code validation (5 or 9 digits)
        if not re.match(r'^\d{5}(-\d{4})?$', zip_code):
            # Also accept 9 digits without dash
            if not re.match(r'^\d{9}$', zip_code):
                logger.warning(f"Invalid zip code format: {zip_code}")
        
        return zip_code

class HubSpotStateValidator:
    """Validator for US state codes"""
    
    US_STATES = {
        'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
        'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
        'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
        'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
        'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
        'DC'  # District of Columbia
    }
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate US state code"""
        if not value:
            return None
        
        state = str(value).strip().upper()
        
        # Accept full state names or abbreviations
        if len(state) == 2 and state not in self.US_STATES:
            logger.warning(f"Unknown state code: {state}")
        
        return state

class HubSpotUrlValidator:
    """Validator for URL fields"""
    
    def __init__(self):
        self.django_validator = URLValidator()
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate URL"""
        if not value:
            return None
        
        url = str(value).strip()
        
        try:
            self.django_validator(url)
            return url
        except ValidationError:
            raise ValidationException(f"Invalid URL format: {url}")
        return pipeline
    
    def get_error_message(self) -> str:
        if self.valid_pipelines:
            return f"Pipeline must be one of: {self.valid_pipelines}"
        return "Invalid pipeline value"

class HubSpotPropertyValidator(BaseValidator):
    """Generic validator for HubSpot properties with type checking"""
    
    def __init__(self, property_type: str, **kwargs):
        super().__init__(**kwargs)
        self.property_type = property_type.lower()
        
        # Map HubSpot property types to validators
        self.type_validators = {
            'string': StringValidator(**kwargs),
            'number': DecimalValidator(**kwargs),
            'bool': lambda v: str(v).lower() in ('true', '1', 'yes') if v else False,
            'datetime': HubSpotTimestampValidator(**kwargs),
            'enumeration': lambda v: str(v) if v else None,
        }
    
    def validate(self, value: Any) -> Any:
        """Validate based on HubSpot property type"""
        self._check_required(value)
        
        if not value:
            return None
        
        if self.property_type in self.type_validators:
            validator = self.type_validators[self.property_type]
            if callable(validator):
                if hasattr(validator, 'validate'):
                    return validator.validate(value)
                else:
                    return validator(value)
            return value
        
        # Default: return as string
        return str(value)
    
    def get_error_message(self) -> str:
        return f"Invalid value for HubSpot {self.property_type} property"

class HubSpotZipCodeValidator(BaseValidator):
    """Validator for US zip codes"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.zip_pattern = re.compile(r'^\d{5}(-\d{4})?$')
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate zip code"""
        self._check_required(value)
        
        if not value:
            return None
        
        zip_code = str(value).strip()
        
        if not self.zip_pattern.match(zip_code):
            raise ValidationException(f"Invalid zip code format: '{zip_code}'. Expected: 12345 or 12345-6789")
        
        return zip_code
    
    def get_error_message(self) -> str:
        return "Zip code must be in format 12345 or 12345-6789"

class HubSpotStateValidator(BaseValidator):
    """Validator for US state codes"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.valid_states = {
            'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
            'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
            'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
            'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
            'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY',
            'DC'  # District of Columbia
        }
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate state code"""
        self._check_required(value)
        
        if not value:
            return None
        
        state = str(value).strip().upper()
        
        if state not in self.valid_states:
            raise ValidationException(f"Invalid state code: '{state}'. Must be a valid US state code")
        
        return state
    
    def get_error_message(self) -> str:
        return "State must be a valid US state code (e.g., CA, NY, TX)"

class HubSpotUrlValidator(BaseValidator):
    """Validator for URLs"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate URL"""
        self._check_required(value)
        
        if not value:
            return None
        
        url = str(value).strip()
        
        if not self.url_pattern.match(url):
            raise ValidationException(f"Invalid URL format: '{url}'")
        
        return url
    
    def get_error_message(self) -> str:
        return "URL must be a valid HTTP or HTTPS URL"

# HubSpot-specific validator registry
HUBSPOT_VALIDATORS = {
    'object_id': HubSpotObjectIdValidator,
    'email': HubSpotEmailValidator,
    'phone': HubSpotPhoneValidator,
    'timestamp': HubSpotTimestampValidator,
    'currency': HubSpotCurrencyValidator,
    'property': HubSpotPropertyValidator,
    'zip_code': HubSpotZipCodeValidator,
    'state': HubSpotStateValidator,
    'url': HubSpotUrlValidator,
}

def get_hubspot_validator(validator_type: str, **kwargs) -> BaseValidator:
    """Get HubSpot-specific validator instance by type"""
    if validator_type not in HUBSPOT_VALIDATORS:
        raise ValueError(f"Unknown HubSpot validator type: {validator_type}. "
                        f"Available: {list(HUBSPOT_VALIDATORS.keys())}")
    
    return HUBSPOT_VALIDATORS[validator_type](**kwargs)
