"""
HubSpot-specific validators
"""
import re
from typing import Any, Optional
from ingestion.base.validators import BaseValidator, StringValidator, DecimalValidator
from ingestion.base.exceptions import ValidationException

class HubSpotObjectIdValidator(BaseValidator):
    """Validator for HubSpot object IDs"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate HubSpot object ID"""
        self._check_required(value)
        
        if not value:
            return None
        
        object_id = str(value).strip()
        
        # HubSpot IDs are typically numeric strings
        if not object_id.isdigit():
            raise ValidationException(f"HubSpot object ID must be numeric: '{value}'")
        
        # Check reasonable length (HubSpot IDs are usually 6-12 digits)
        if len(object_id) < 1 or len(object_id) > 20:
            raise ValidationException(f"HubSpot object ID length invalid: '{value}'")
        
        return object_id
    
    def get_error_message(self) -> str:
        return "HubSpot object ID must be a numeric string"

class HubSpotEmailValidator(BaseValidator):
    """HubSpot-specific email validator with additional checks"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.base_validator = StringValidator(max_length=254, **kwargs)
        # HubSpot has some specific email validation rules
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate email for HubSpot"""
        self._check_required(value)
        
        if not value:
            return None
        
        # First run basic string validation
        email = self.base_validator.validate(value)
        if not email:
            return None
        
        email = email.lower().strip()
        
        # Check basic structure
        if '@' not in email or '.' not in email:
            raise ValidationException(f"Invalid email format: missing @ or . in '{value}'")
        
        # Check regex pattern
        if not self.email_pattern.match(email):
            raise ValidationException(f"Invalid email format: '{value}'")
        
        # HubSpot-specific checks
        local, domain = email.split('@', 1)
        
        # Check for valid domain structure
        domain_parts = domain.split('.')
        if len(domain_parts) < 2:
            raise ValidationException(f"Invalid email domain: '{value}'")
        
        # Check for valid TLD
        tld = domain_parts[-1]
        if len(tld) < 2:
            raise ValidationException(f"Invalid email TLD: '{value}'")
        
        return email
    
    def get_error_message(self) -> str:
        return "Invalid email format for HubSpot"

class HubSpotPhoneValidator(BaseValidator):
    """HubSpot-specific phone validator"""
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate phone for HubSpot"""
        self._check_required(value)
        
        if not value:
            return None
        
        # Remove all non-digit characters
        phone = re.sub(r'[^\d]', '', str(value))
        
        # HubSpot accepts various phone formats, but we need at least 7 digits
        if len(phone) < 7 or len(phone) > 15:
            raise ValidationException(f"Phone number must be 7-15 digits: '{value}'")
        
        # Format for consistency (US format if 10 digits)
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone[0] == '1':
            return f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        else:
            return phone
    
    def get_error_message(self) -> str:
        return "Phone number must be 7-15 digits"

class HubSpotTimestampValidator(BaseValidator):
    """Validator for HubSpot timestamps (milliseconds since epoch)"""
    
    def validate(self, value: Any) -> Optional[int]:
        """Validate HubSpot timestamp"""
        self._check_required(value)
        
        if not value:
            return None
        
        try:
            timestamp = int(value)
        except (ValueError, TypeError):
            raise ValidationException(f"HubSpot timestamp must be numeric: '{value}'")
        
        # HubSpot timestamps are in milliseconds since epoch
        # Reasonable range: 2000-01-01 to 2100-01-01
        min_timestamp = 946684800000  # 2000-01-01 in milliseconds
        max_timestamp = 4102444800000  # 2100-01-01 in milliseconds
        
        if timestamp < min_timestamp or timestamp > max_timestamp:
            raise ValidationException(f"HubSpot timestamp out of reasonable range: {timestamp}")
        
        return timestamp
    
    def get_error_message(self) -> str:
        return "HubSpot timestamp must be milliseconds since epoch"

class HubSpotCurrencyValidator(DecimalValidator):
    """Validator for HubSpot currency amounts"""
    
    def __init__(self, **kwargs):
        # HubSpot typically uses 2 decimal places for currency
        super().__init__(
            min_value=0,  # Usually non-negative
            max_digits=15,  # Reasonable max for currency
            decimal_places=2,
            **kwargs
        )
    
    def get_error_message(self) -> str:
        return "Currency amount must be a positive decimal with up to 2 decimal places"

class HubSpotPipelineValidator(BaseValidator):
    """Validator for HubSpot pipeline values"""
    
    def __init__(self, valid_pipelines: list = None, **kwargs):
        super().__init__(**kwargs)
        self.valid_pipelines = valid_pipelines or []
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate pipeline value"""
        self._check_required(value)
        
        if not value:
            return None
        
        pipeline = str(value).strip()
        
        # If we have a list of valid pipelines, check against it
        if self.valid_pipelines and pipeline not in self.valid_pipelines:
            raise ValidationException(f"Invalid pipeline: '{pipeline}'. Valid: {self.valid_pipelines}")
        
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
    'pipeline': HubSpotPipelineValidator,
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
