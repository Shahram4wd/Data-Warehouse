"""
Base validation framework for all CRM integrations
"""
from abc import ABC, abstractmethod
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from decimal import Decimal, InvalidOperation
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ingestion.base.exceptions import ValidationException

class BaseValidator(ABC):
    """Base validator class"""
    
    def __init__(self, required: bool = False, allow_empty: bool = True):
        self.required = required
        self.allow_empty = allow_empty
    
    @abstractmethod
    def validate(self, value: Any) -> Any:
        """Validate and return cleaned value"""
        pass
        
    @abstractmethod
    def get_error_message(self) -> str:
        """Return validation error message"""
        pass
    
    def _check_required(self, value: Any) -> None:
        """Check if required value is present"""
        if self.required and (value is None or (not self.allow_empty and str(value).strip() == '')):
            raise ValidationException(f"Required field cannot be empty")

class PhoneValidator(BaseValidator):
    """Phone number validator with international support"""
    
    def __init__(self, format_output: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.format_output = format_output
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate and format phone number"""
        self._check_required(value)
        
        if not value:
            return None
        
        # Convert to string and remove all non-digit characters
        phone = re.sub(r'[^\d]', '', str(value))
        
        # Validate length (international numbers can be 7-15 digits)
        if len(phone) < 7 or len(phone) > 15:
            raise ValidationException(f"Phone number must be 7-15 digits, got {len(phone)} digits: {value}")
        
        # Format output if requested
        if self.format_output:
            if len(phone) == 10:
                # US format: (123) 456-7890
                return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
            elif len(phone) == 11 and phone[0] == '1':
                # US format with country code: (123) 456-7890
                return f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
            else:
                # International format: keep digits only
                return phone
        
        return phone
    
    def get_error_message(self) -> str:
        return "Phone number must be 7-15 digits"

class EmailValidator(BaseValidator):
    """Email validator with comprehensive validation"""
    
    def __init__(self, normalize: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.normalize = normalize
        # More comprehensive email regex
        self.email_pattern = re.compile(
            r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        )
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate and normalize email"""
        self._check_required(value)
        
        if not value:
            return None
        
        email = str(value)
        
        if self.normalize:
            email = email.strip().lower()
        
        # Check basic structure
        if '@' not in email or '.' not in email:
            raise ValidationException(f"Invalid email format: missing @ or . in '{value}'")
        
        # Check regex pattern
        if not self.email_pattern.match(email):
            raise ValidationException(f"Invalid email format: '{value}'")
        
        # Additional checks
        local, domain = email.split('@', 1)
        
        # Local part validation
        if len(local) == 0 or len(local) > 64:
            raise ValidationException(f"Email local part must be 1-64 characters: '{value}'")
        
        # Domain part validation
        if len(domain) == 0 or len(domain) > 255:
            raise ValidationException(f"Email domain must be 1-255 characters: '{value}'")
        
        # Check for consecutive dots
        if '..' in email:
            raise ValidationException(f"Email cannot contain consecutive dots: '{value}'")
        
        return email
    
    def get_error_message(self) -> str:
        return "Invalid email format"

class DateValidator(BaseValidator):
    """Date validator with multiple format support"""
    
    def __init__(self, formats: List[str] = None, output_format: str = None, **kwargs):
        super().__init__(**kwargs)
        self.formats = formats or [
            '%Y-%m-%d',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ',
            '%Y-%m-%dT%H:%M:%S.%fZ',
            '%m/%d/%Y',
            '%m-%d-%Y',
            '%d/%m/%Y',
            '%d-%m-%Y',
        ]
        self.output_format = output_format
    
    def validate(self, value: Any) -> Optional[datetime]:
        """Validate and parse date"""
        self._check_required(value)
        
        if not value:
            return None
        
        # If it's already a datetime, return it
        if isinstance(value, datetime):
            return value
        
        # Handle timestamps (both seconds and milliseconds)
        if isinstance(value, (int, float)):
            try:
                timestamp = float(value)
                # Convert milliseconds to seconds if needed
                if timestamp > 10000000000:  # Likely milliseconds
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp, tz=timezone.utc)
            except (ValueError, OSError) as e:
                raise ValidationException(f"Invalid timestamp: {value} - {e}")
        
        # Handle string dates
        date_str = str(value).strip()
        
        # Try Django's parse_datetime first
        try:
            parsed = parse_datetime(date_str)
            if parsed:
                return parsed
        except (ValueError, TypeError):
            pass
        
        # Try each format
        for fmt in self.formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                # Make timezone aware if not already
                if parsed_date.tzinfo is None:
                    parsed_date = timezone.make_aware(parsed_date)
                return parsed_date
            except ValueError:
                continue
        
        raise ValidationException(f"Invalid date format: '{value}'. Supported formats: {', '.join(self.formats)}")
    
    def get_error_message(self) -> str:
        return f"Date must be in one of these formats: {', '.join(self.formats)}"

class DecimalValidator(BaseValidator):
    """Decimal validator with precision control"""
    
    def __init__(self, min_value: Decimal = None, max_value: Decimal = None, 
                 max_digits: int = None, decimal_places: int = None, **kwargs):
        super().__init__(**kwargs)
        self.min_value = min_value
        self.max_value = max_value
        self.max_digits = max_digits
        self.decimal_places = decimal_places
    
    def validate(self, value: Any) -> Optional[Decimal]:
        """Validate and convert to decimal"""
        self._check_required(value)
        
        if not value and value != 0:
            return None
        
        try:
            decimal_value = Decimal(str(value))
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationException(f"Invalid decimal value: '{value}'")
        
        # Check range
        if self.min_value is not None and decimal_value < self.min_value:
            raise ValidationException(f"Value {decimal_value} is below minimum {self.min_value}")
        
        if self.max_value is not None and decimal_value > self.max_value:
            raise ValidationException(f"Value {decimal_value} is above maximum {self.max_value}")
        
        # Check precision
        if self.max_digits is not None:
            sign, digits, exponent = decimal_value.as_tuple()
            if len(digits) > self.max_digits:
                raise ValidationException(f"Value has {len(digits)} digits, maximum allowed is {self.max_digits}")
        
        if self.decimal_places is not None:
            sign, digits, exponent = decimal_value.as_tuple()
            if exponent < -self.decimal_places:
                raise ValidationException(f"Value has more than {self.decimal_places} decimal places")
        
        return decimal_value
    
    def get_error_message(self) -> str:
        parts = ["Invalid decimal value"]
        if self.min_value is not None or self.max_value is not None:
            parts.append(f"range: {self.min_value or 'unlimited'} to {self.max_value or 'unlimited'}")
        if self.max_digits is not None:
            parts.append(f"max digits: {self.max_digits}")
        if self.decimal_places is not None:
            parts.append(f"max decimal places: {self.decimal_places}")
        return ", ".join(parts)

class BooleanValidator(BaseValidator):
    """Boolean validator with flexible input handling"""
    
    def __init__(self, true_values: List[str] = None, false_values: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.true_values = true_values or ['true', '1', 'yes', 'on', 'y', 't']
        self.false_values = false_values or ['false', '0', 'no', 'off', 'n', 'f']
    
    def validate(self, value: Any) -> Optional[bool]:
        """Validate and convert to boolean"""
        self._check_required(value)
        
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        if isinstance(value, str):
            value_lower = value.lower().strip()
            if value_lower in self.true_values:
                return True
            elif value_lower in self.false_values:
                return False
        
        raise ValidationException(f"Invalid boolean value: '{value}'. "
                                f"Valid true values: {self.true_values}. "
                                f"Valid false values: {self.false_values}")
    
    def get_error_message(self) -> str:
        return f"Must be boolean-like. True: {self.true_values}, False: {self.false_values}"

class StringValidator(BaseValidator):
    """String validator with length and pattern constraints"""
    
    def __init__(self, min_length: int = None, max_length: int = None, 
                 pattern: str = None, strip: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.min_length = min_length
        self.max_length = max_length
        self.pattern = re.compile(pattern) if pattern else None
        self.strip = strip
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate string value"""
        self._check_required(value)
        
        if value is None:
            return None
        
        string_value = str(value)
        
        if self.strip:
            string_value = string_value.strip()
        
        # Check length constraints
        if self.min_length is not None and len(string_value) < self.min_length:
            raise ValidationException(f"String too short: {len(string_value)} < {self.min_length}")
        
        if self.max_length is not None and len(string_value) > self.max_length:
            raise ValidationException(f"String too long: {len(string_value)} > {self.max_length}")
        
        # Check pattern
        if self.pattern and not self.pattern.match(string_value):
            raise ValidationException(f"String does not match required pattern: '{string_value}'")
        
        return string_value
    
    def get_error_message(self) -> str:
        parts = ["Invalid string"]
        if self.min_length is not None or self.max_length is not None:
            parts.append(f"length: {self.min_length or 0}-{self.max_length or 'unlimited'}")
        if self.pattern:
            parts.append(f"pattern: {self.pattern.pattern}")
        return ", ".join(parts)

class ChoiceValidator(BaseValidator):
    """Validator for enumerated choices"""
    
    def __init__(self, choices: List[Any], case_sensitive: bool = True, **kwargs):
        super().__init__(**kwargs)
        self.choices = choices
        self.case_sensitive = case_sensitive
        if not case_sensitive:
            self.choices_lower = [str(choice).lower() for choice in choices]
    
    def validate(self, value: Any) -> Any:
        """Validate choice value"""
        self._check_required(value)
        
        if value is None:
            return None
        
        if self.case_sensitive:
            if value in self.choices:
                return value
        else:
            value_str = str(value).lower()
            if value_str in self.choices_lower:
                # Return the original case version
                index = self.choices_lower.index(value_str)
                return self.choices[index]
        
        raise ValidationException(f"Invalid choice: '{value}'. Valid choices: {self.choices}")
    
    def get_error_message(self) -> str:
        return f"Must be one of: {self.choices}"

class TimeValidator(BaseValidator):
    """Time validator that extracts time from datetime strings"""
    
    def __init__(self, formats: List[str] = None, **kwargs):
        super().__init__(**kwargs)
        self.formats = formats or [
            '%H:%M:%S',
            '%H:%M',
            '%H:%M:%S.%f',
        ]
    
    def validate(self, value: Any) -> Optional[str]:
        """Validate and extract time from datetime string"""
        self._check_required(value)
        
        if not value:
            return None
        
        # If it's already a time object, format it
        if hasattr(value, 'time'):
            return value.time().strftime('%H:%M:%S')
        
        value_str = str(value).strip()
        
        # Handle full datetime strings like "2025-06-10T14:00:00"
        if 'T' in value_str:
            try:
                # Split on T and take the time part
                datetime_part = value_str.split('T')[1]
                # Remove timezone info if present
                time_part = datetime_part.split('+')[0].split('Z')[0].split('-')[0]
                
                # Validate time format
                if ':' in time_part:
                    parts = time_part.split(':')
                    if len(parts) >= 2:
                        hour = int(parts[0])
                        minute = int(parts[1])
                        second = int(parts[2]) if len(parts) > 2 else 0
                        
                        # Validate ranges
                        if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                            return f"{hour:02d}:{minute:02d}:{second:02d}"
                        else:
                            raise ValidationException(f"Invalid time values: {hour}:{minute}:{second}")
            except (ValueError, IndexError) as e:
                raise ValidationException(f"Invalid datetime format for time extraction: '{value}' - {e}")
        
        # Handle time-only strings like "14:00:00" or "14:00"
        elif ':' in value_str:
            try:
                parts = value_str.split(':')
                if len(parts) >= 2:
                    hour = int(parts[0])
                    minute = int(parts[1])
                    second = int(parts[2]) if len(parts) > 2 else 0
                    
                    # Validate ranges
                    if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                        return f"{hour:02d}:{minute:02d}:{second:02d}"
                    else:
                        raise ValidationException(f"Invalid time values: {hour}:{minute}:{second}")
            except (ValueError, IndexError) as e:
                raise ValidationException(f"Invalid time format: '{value}' - {e}")
        
        # Try parsing as full datetime and extract time
        try:
            # Use DateValidator to parse the datetime
            date_validator = DateValidator()
            parsed_datetime = date_validator.validate(value)
            if parsed_datetime and hasattr(parsed_datetime, 'time'):
                return parsed_datetime.time().strftime('%H:%M:%S')
        except ValidationException:
            pass
        
        raise ValidationException(f"Invalid time format: '{value}'. Expected HH:MM:SS or datetime string.")
    
    def get_error_message(self) -> str:
        return "Time must be in HH:MM:SS format or extractable from datetime string"

# Validation registry for easy access
VALIDATORS = {
    'phone': PhoneValidator,
    'email': EmailValidator,
    'date': DateValidator,
    'datetime': DateValidator,
    'decimal': DecimalValidator,
    'boolean': BooleanValidator,
    'string': StringValidator,
    'choice': ChoiceValidator,
    'time': TimeValidator,
}

def get_validator(validator_type: str, **kwargs) -> BaseValidator:
    """Get validator instance by type"""
    if validator_type not in VALIDATORS:
        raise ValueError(f"Unknown validator type: {validator_type}. Available: {list(VALIDATORS.keys())}")
    
    return VALIDATORS[validator_type](**kwargs)
