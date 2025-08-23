"""
Base Five9 Data Processor
Handles data transformation and validation for Five9 records
"""
from typing import Dict, Any, Optional, List
from datetime import datetime, date
from decimal import Decimal, InvalidOperation
import logging
from django.utils.dateparse import parse_datetime, parse_date
from django.core.exceptions import ValidationError
from django.core.validators import validate_email

logger = logging.getLogger(__name__)


class BaseFive9Processor:
    """Base processor for Five9 data transformation and validation"""
    
    def __init__(self):
        self.field_processors = {
            'PHONE': self._process_phone,
            'STRING': self._process_string,
            'EMAIL': self._process_email,
            'DATE_TIME': self._process_datetime,
            'DATE': self._process_date,
            'NUMBER': self._process_number,
            'BOOLEAN': self._process_boolean,
        }
    
    def process_field(self, field_name: str, value: Any, field_type: str) -> Any:
        """
        Process a single field value based on its type
        
        Args:
            field_name: Name of the field
            value: Raw value from Five9
            field_type: Five9 field type (PHONE, STRING, EMAIL, etc.)
            
        Returns:
            Processed value suitable for Django model
        """
        if value is None or value == '':
            return None
        
        processor = self.field_processors.get(field_type, self._process_string)
        
        try:
            processed_value = processor(value)
            logger.debug(f"Processed {field_name} ({field_type}): {repr(value)} -> {repr(processed_value)}")
            return processed_value
        except Exception as e:
            logger.warning(f"Error processing field {field_name} ({field_type}) with value {repr(value)}: {e}")
            # Return string representation as fallback
            return str(value) if value is not None else None
    
    def _process_phone(self, value: Any) -> Optional[str]:
        """Process phone number field"""
        if not value:
            return None
        
        phone_str = str(value).strip()
        if not phone_str:
            return None
        
        # Remove common phone formatting
        phone_clean = ''.join(char for char in phone_str if char.isdigit())
        
        # Validate phone number length (US format)
        if len(phone_clean) == 10:
            return phone_clean
        elif len(phone_clean) == 11 and phone_clean.startswith('1'):
            return phone_clean[1:]  # Remove country code
        elif len(phone_clean) >= 7:  # Allow partial numbers
            return phone_clean
        else:
            return phone_str  # Return original if can't parse
    
    def _process_string(self, value: Any) -> Optional[str]:
        """Process string field"""
        if not value:
            return None
        
        string_val = str(value).strip()
        return string_val if string_val else None
    
    def _process_email(self, value: Any) -> Optional[str]:
        """Process email field with validation"""
        if not value:
            return None
        
        email_str = str(value).strip().lower()
        if not email_str:
            return None
        
        try:
            validate_email(email_str)
            return email_str
        except ValidationError:
            logger.warning(f"Invalid email format: {email_str}")
            return email_str  # Return as-is, let Django handle validation
    
    def _process_datetime(self, value: Any) -> Optional[datetime]:
        """Process datetime field"""
        if not value:
            return None
        
        # Handle various datetime formats from Five9
        if isinstance(value, datetime):
            return value
        
        datetime_str = str(value).strip()
        if not datetime_str:
            return None
        
        # Try parsing different datetime formats
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S.%f',  # 2024-04-12 13:12:44.767
            '%Y-%m-%d %H:%M:%S',     # 2024-04-12 13:12:44
            '%m/%d/%Y %H:%M:%S',     # 04/12/2024 13:12:44
            '%Y-%m-%dT%H:%M:%S',     # ISO format
            '%Y-%m-%d',              # Date only
        ]
        
        for fmt in datetime_formats:
            try:
                return datetime.strptime(datetime_str, fmt)
            except ValueError:
                continue
        
        # Try Django's built-in parser
        parsed_dt = parse_datetime(datetime_str)
        if parsed_dt:
            return parsed_dt
        
        # Try parsing as date and convert to datetime
        parsed_date = parse_date(datetime_str)
        if parsed_date:
            return datetime.combine(parsed_date, datetime.min.time())
        
        logger.warning(f"Could not parse datetime: {datetime_str}")
        return None
    
    def _process_date(self, value: Any) -> Optional[date]:
        """Process date field"""
        if not value:
            return None
        
        if isinstance(value, date):
            return value
        
        if isinstance(value, datetime):
            return value.date()
        
        date_str = str(value).strip()
        if not date_str:
            return None
        
        # Try parsing different date formats
        date_formats = [
            '%Y-%m-%d',      # 2024-04-12
            '%m/%d/%Y',      # 04/12/2024
            '%d/%m/%Y',      # 12/04/2024
            '%Y/%m/%d',      # 2024/04/12
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Try Django's built-in parser
        parsed_date = parse_date(date_str)
        if parsed_date:
            return parsed_date
        
        logger.warning(f"Could not parse date: {date_str}")
        return None
    
    def _process_number(self, value: Any) -> Optional[Decimal]:
        """Process number field"""
        if not value:
            return None
        
        # Handle string representations of numbers
        if isinstance(value, str):
            value = value.strip().replace(',', '')  # Remove commas
            if not value:
                return None
        
        try:
            return Decimal(str(value))
        except (InvalidOperation, ValueError) as e:
            logger.warning(f"Could not parse number: {value} - {e}")
            return None
    
    def _process_boolean(self, value: Any) -> Optional[bool]:
        """Process boolean field"""
        if value is None:
            return None
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, str):
            value = value.strip().lower()
            if value in ('true', '1', 'yes', 'y', 'on'):
                return True
            elif value in ('false', '0', 'no', 'n', 'off'):
                return False
        
        # Try numeric conversion
        try:
            num_value = float(value)
            return bool(num_value)
        except (ValueError, TypeError):
            pass
        
        logger.warning(f"Could not parse boolean: {value}")
        return None
    
    def validate_required_fields(self, record: Dict[str, Any], required_fields: List[str]) -> bool:
        """
        Validate that required fields are present and not empty
        
        Args:
            record: Processed record dictionary
            required_fields: List of field names that are required
            
        Returns:
            True if all required fields are valid, False otherwise
        """
        for field in required_fields:
            if field not in record or record[field] is None or record[field] == '':
                logger.warning(f"Missing required field: {field}")
                return False
        
        return True
    
    def clean_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Clean a record by removing empty string values and None values
        where appropriate
        
        Args:
            record: Raw record dictionary
            
        Returns:
            Cleaned record dictionary
        """
        cleaned = {}
        
        for key, value in record.items():
            # Skip completely empty values
            if value is None:
                cleaned[key] = None
            elif isinstance(value, str) and value.strip() == '':
                cleaned[key] = None
            else:
                cleaned[key] = value
        
        return cleaned
