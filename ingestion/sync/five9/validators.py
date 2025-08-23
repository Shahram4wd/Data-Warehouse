"""
Five9 Data Validators
Validation rules and functions specific to Five9 data
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging
from django.core.validators import validate_email
from django.core.exceptions import ValidationError

logger = logging.getLogger(__name__)


def validate_phone_number(phone: str) -> bool:
    """
    Validate phone number format
    
    Args:
        phone: Phone number string
        
    Returns:
        True if valid, False otherwise
    """
    if not phone:
        return False
    
    # Remove all non-digit characters
    digits_only = re.sub(r'\D', '', phone)
    
    # Valid US phone number patterns
    if len(digits_only) == 10:
        return True
    elif len(digits_only) == 11 and digits_only.startswith('1'):
        return True
    elif len(digits_only) >= 7:  # Allow partial numbers
        return True
    
    return False


def validate_email_address(email: str) -> bool:
    """
    Validate email address format
    
    Args:
        email: Email address string
        
    Returns:
        True if valid, False otherwise
    """
    if not email:
        return False
    
    try:
        validate_email(email.strip().lower())
        return True
    except ValidationError:
        return False


def validate_contact_id(contact_id: str) -> bool:
    """
    Validate Five9 contact ID format
    
    Args:
        contact_id: Contact ID string
        
    Returns:
        True if valid, False otherwise
    """
    if not contact_id:
        return False
    
    # Five9 contact IDs are typically UUIDs
    uuid_pattern = r'^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$'
    return bool(re.match(uuid_pattern, contact_id.lower()))


def validate_datetime_string(datetime_str: str) -> bool:
    """
    Validate datetime string can be parsed
    
    Args:
        datetime_str: Datetime string
        
    Returns:
        True if can be parsed, False otherwise
    """
    if not datetime_str:
        return False
    
    # Try common Five9 datetime formats
    formats = [
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%m/%d/%Y %H:%M:%S',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%d',
    ]
    
    for fmt in formats:
        try:
            datetime.strptime(datetime_str.strip(), fmt)
            return True
        except ValueError:
            continue
    
    return False


def validate_list_name(list_name: str) -> bool:
    """
    Validate Five9 list name
    
    Args:
        list_name: List name string
        
    Returns:
        True if valid, False otherwise
    """
    if not list_name or not list_name.strip():
        return False
    
    # List name should not be too long and should contain valid characters
    clean_name = list_name.strip()
    if len(clean_name) > 255:
        return False
    
    return True


def validate_contact_record(record: Dict[str, Any]) -> Dict[str, List[str]]:
    """
    Validate a complete contact record
    
    Args:
        record: Contact record dictionary
        
    Returns:
        Dictionary of field_name -> list of validation errors
    """
    errors = {}
    
    # Validate required fields
    if not record.get('list_name'):
        errors['list_name'] = ['List name is required']
    elif not validate_list_name(record['list_name']):
        errors['list_name'] = ['Invalid list name format']
    
    # Validate contact ID if present
    contact_id = record.get('contactID')
    if contact_id and not validate_contact_id(contact_id):
        errors['contactID'] = ['Invalid contact ID format']
    
    # Validate email if present
    email = record.get('email')
    if email and not validate_email_address(email):
        errors['email'] = ['Invalid email address format']
    
    # Validate phone numbers if present
    for phone_field in ['number1', 'number2', 'number3']:
        phone = record.get(phone_field)
        if phone and not validate_phone_number(phone):
            errors[phone_field] = ['Invalid phone number format']
    
    # Validate datetime fields if present
    datetime_fields = [
        'sys_created_date', 'sys_last_disposition_time',
        'field_4f347541_7c4d_4812_9190_e8dea6c0eb49',
        'New_Contact_Field', 'Last_Agent_Disposition_Date_Time',
        'Appointment_Date_and_Time'
    ]
    
    for dt_field in datetime_fields:
        dt_value = record.get(dt_field)
        if dt_value and isinstance(dt_value, str) and not validate_datetime_string(dt_value):
            errors[dt_field] = ['Invalid datetime format']
    
    # Validate that record has at least one identifying field
    identifying_fields = ['contactID', 'email', 'number1', 'first_name', 'last_name']
    has_identifier = any(record.get(field) for field in identifying_fields)
    
    if not has_identifier:
        errors['_record'] = ['Record must have at least one identifying field (contactID, email, number1, first_name, or last_name)']
    
    return errors


def validate_sync_batch(records: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Validate a batch of contact records
    
    Args:
        records: List of contact records
        
    Returns:
        Dictionary with validation results
    """
    if not records:
        return {
            'valid': True,
            'total_records': 0,
            'valid_records': 0,
            'invalid_records': 0,
            'errors': []
        }
    
    valid_records = []
    invalid_records = []
    all_errors = []
    
    for i, record in enumerate(records):
        record_errors = validate_contact_record(record)
        
        if record_errors:
            invalid_records.append({
                'index': i,
                'record': record,
                'errors': record_errors
            })
            all_errors.extend([
                f"Record {i+1}: {field} - {error}"
                for field, field_errors in record_errors.items()
                for error in field_errors
            ])
        else:
            valid_records.append(record)
    
    return {
        'valid': len(invalid_records) == 0,
        'total_records': len(records),
        'valid_records': len(valid_records),
        'invalid_records': len(invalid_records),
        'errors': all_errors,
        'invalid_record_details': invalid_records
    }


def sanitize_field_value(value: Any, field_type: str) -> Any:
    """
    Sanitize a field value to ensure it's safe for database storage
    
    Args:
        value: Raw field value
        field_type: Five9 field type
        
    Returns:
        Sanitized value
    """
    if value is None:
        return None
    
    if field_type == 'STRING':
        # Ensure string values are properly truncated and cleaned
        if isinstance(value, str):
            # Remove null bytes and control characters
            cleaned = re.sub(r'[\x00-\x08\x0B\x0C\x0E-\x1F\x7F]', '', value)
            return cleaned.strip()[:255]  # Truncate to common field length
        return str(value)[:255]
    
    elif field_type == 'PHONE':
        if isinstance(value, str):
            # Keep only digits and common phone characters
            return re.sub(r'[^\d\+\-\(\)\s]', '', value)[:20]
        return str(value)[:20]
    
    elif field_type == 'EMAIL':
        if isinstance(value, str):
            return value.strip().lower()[:254]  # Email field max length
        return str(value)[:254]
    
    return value


def get_validation_summary(validation_result: Dict[str, Any]) -> str:
    """
    Get a human-readable summary of validation results
    
    Args:
        validation_result: Result from validate_sync_batch
        
    Returns:
        Summary string
    """
    total = validation_result['total_records']
    valid = validation_result['valid_records'] 
    invalid = validation_result['invalid_records']
    
    if total == 0:
        return "No records to validate"
    
    if invalid == 0:
        return f"All {total} records passed validation"
    
    error_summary = []
    if validation_result['errors']:
        # Group similar errors
        error_counts = {}
        for error in validation_result['errors']:
            error_type = error.split(' - ')[-1] if ' - ' in error else error
            error_counts[error_type] = error_counts.get(error_type, 0) + 1
        
        for error_type, count in sorted(error_counts.items()):
            error_summary.append(f"{error_type} ({count})")
    
    return (
        f"Validation results: {valid}/{total} valid records, "
        f"{invalid} invalid. Errors: {', '.join(error_summary[:3])}"
        + ("..." if len(error_summary) > 3 else "")
    )
