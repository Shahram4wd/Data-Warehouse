"""
Marketing Leads Data Validator for Google Sheets

Validates marketing leads data before saving to database.
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import re

logger = logging.getLogger(__name__)


class MarketingLeadsValidator:
    """
    Validates marketing leads data from Google Sheets
    """
    
    def __init__(self):
        """Initialize validator with validation rules"""
        self.email_regex = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
        self.phone_regex = re.compile(r'^[\+]?[1-9][\d]{0,15}$')  # Basic international phone format
    
    async def validate_row(self, row_data: Dict[str, Any]) -> bool:
        """
        Validate a single row of marketing leads data
        
        Args:
            row_data: Dictionary containing row data
            
        Returns:
            bool: True if row is valid, False otherwise
        """
        try:
            # Basic validation - at least one field must have data
            if not self._has_meaningful_data(row_data):
                logger.warning("Row has no meaningful data")
                return False
            
            # Validate specific fields if present
            if not self._validate_email(row_data.get('email')):
                return False
            
            if not self._validate_phone(row_data.get('phone')):
                return False
            
            if not self._validate_dates(row_data):
                return False
            
            # Validate numeric fields
            if not self._validate_numeric_fields(row_data):
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Validation error for row {row_data}: {e}")
            return False
    
    def _has_meaningful_data(self, row_data: Dict[str, Any]) -> bool:
        """Check if row has at least some meaningful data"""
        meaningful_fields = [
            'date', 'source', 'medium', 'campaign', 'leads', 'cost',
            'email', 'phone', 'first_name', 'last_name', 'company'
        ]
        
        for field in meaningful_fields:
            value = row_data.get(field)
            if value and str(value).strip():
                return True
        
        return False
    
    def _validate_email(self, email: Optional[str]) -> bool:
        """Validate email format if provided"""
        if not email:
            return True  # Email is optional
        
        email = str(email).strip()
        if not email:
            return True
        
        if not self.email_regex.match(email):
            logger.warning(f"Invalid email format: {email}")
            return False
        
        return True
    
    def _validate_phone(self, phone: Optional[str]) -> bool:
        """Validate phone format if provided"""
        if not phone:
            return True  # Phone is optional
        
        phone = str(phone).strip()
        if not phone:
            return True
        
        # Remove common phone formatting characters
        cleaned_phone = re.sub(r'[\s\-\(\)\.]+', '', phone)
        
        if not self.phone_regex.match(cleaned_phone):
            logger.warning(f"Invalid phone format: {phone}")
            return False
        
        return True
    
    def _validate_dates(self, row_data: Dict[str, Any]) -> bool:
        """Validate date fields if present"""
        date_fields = ['date', 'created_at', 'updated_at', 'sheet_last_modified']
        
        for field in date_fields:
            date_value = row_data.get(field)
            if date_value and not self._is_valid_date(date_value):
                logger.warning(f"Invalid date format in field {field}: {date_value}")
                return False
        
        return True
    
    def _validate_numeric_fields(self, row_data: Dict[str, Any]) -> bool:
        """Validate numeric fields if present"""
        numeric_fields = ['leads', 'cost', 'lead_score', 'sheet_row_number']
        
        for field in numeric_fields:
            value = row_data.get(field)
            if value is not None and not self._is_valid_number(value):
                logger.warning(f"Invalid numeric value in field {field}: {value}")
                return False
        
        return True
    
    def _is_valid_date(self, date_value: Any) -> bool:
        """Check if value can be parsed as a date"""
        if isinstance(date_value, datetime):
            return True
        
        if not date_value:
            return True
        
        # Try common date formats
        date_formats = [
            '%Y-%m-%d',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ'
        ]
        
        date_str = str(date_value).strip()
        
        for fmt in date_formats:
            try:
                datetime.strptime(date_str, fmt)
                return True
            except ValueError:
                continue
        
        return False
    
    def _is_valid_number(self, value: Any) -> bool:
        """Check if value can be converted to a number"""
        if isinstance(value, (int, float)):
            return True
        
        if not value:
            return True
        
        try:
            # Remove common formatting characters
            clean_value = str(value).replace(',', '').replace('$', '').strip()
            float(clean_value)
            return True
        except (ValueError, TypeError):
            return False
    
    def get_validation_summary(self, data: list) -> Dict[str, Any]:
        """
        Get validation summary for a list of records
        
        Args:
            data: List of dictionaries to validate
            
        Returns:
            Dictionary with validation statistics
        """
        total_records = len(data)
        valid_records = 0
        validation_errors = []
        
        for i, row in enumerate(data):
            try:
                if self.validate_row(row):
                    valid_records += 1
                else:
                    validation_errors.append(f"Row {i + 1}: Failed validation")
            except Exception as e:
                validation_errors.append(f"Row {i + 1}: {str(e)}")
        
        return {
            'total_records': total_records,
            'valid_records': valid_records,
            'invalid_records': total_records - valid_records,
            'validation_errors': validation_errors[:10],  # Limit to first 10 errors
            'validation_rate': (valid_records / total_records * 100) if total_records > 0 else 0
        }
