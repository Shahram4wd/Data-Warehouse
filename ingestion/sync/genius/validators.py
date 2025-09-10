"""
Genius CRM validation rules and utilities
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from decimal import Decimal, InvalidOperation

logger = logging.getLogger(__name__)


class GeniusValidator:
    """Genius CRM-specific validation rules"""
    
    @staticmethod
    def validate_id_field(value: Any) -> Optional[int]:
        """Validate and convert ID fields"""
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid ID value: {value}")
            return None
    
    @staticmethod
    def validate_string_field(value: Any, max_length: int = None, required: bool = False) -> Optional[str]:
        """Validate and clean string fields"""
        if value is None:
            return None if not required else ""
        
        str_value = str(value).strip()
        
        if not str_value and required:
            raise ValueError("Required string field cannot be empty")
        
        if max_length and len(str_value) > max_length:
            logger.warning(f"String too long ({len(str_value)}), truncating to {max_length}")
            str_value = str_value[:max_length]
        
        return str_value if str_value else None
    
    @staticmethod
    def validate_decimal_field(value: Any, max_digits: int = None, decimal_places: int = None) -> Optional[Decimal]:
        """Validate and convert decimal fields"""
        if value is None:
            return None
        
        try:
            decimal_value = Decimal(str(value))
            
            if max_digits and len(str(decimal_value).replace('.', '').replace('-', '')) > max_digits:
                raise ValueError(f"Decimal has too many digits: {decimal_value}")
            
            if decimal_places is not None:
                # Round to specified decimal places
                decimal_value = decimal_value.quantize(Decimal('0.1') ** decimal_places)
            
            return decimal_value
        except (InvalidOperation, ValueError, TypeError) as e:
            logger.warning(f"Invalid decimal value: {value}, error: {e}")
            return None
    
    @staticmethod
    def validate_boolean_field(value: Any) -> bool:
        """Validate and convert boolean fields"""
        if value is None:
            return False
        
        if isinstance(value, bool):
            return value
        
        if isinstance(value, (int, float)):
            return bool(value)
        
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on', 'y')
        
        return bool(value)
    
    @staticmethod
    def validate_datetime_field(value: Any) -> Optional[datetime]:
        """Validate and convert datetime fields"""
        if value is None:
            return None
        
        if isinstance(value, datetime):
            return value
        
        # Handle date objects (convert to datetime)
        from datetime import date
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        if isinstance(value, str):
            try:
                # Try common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.strptime(value, fmt)
                    except ValueError:
                        continue
            except Exception:
                pass
        
        logger.warning(f"Invalid datetime value: {value}")
        return None
    
    @staticmethod
    def validate_date_field(value: Any) -> Optional[datetime]:
        """Validate and convert date fields to datetime for Django DateField compatibility"""
        if value is None:
            return None
        
        # Handle date objects directly
        from datetime import date
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        
        if isinstance(value, datetime):
            return value
        
        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        parsed = datetime.strptime(value, fmt)
                        return parsed
                    except ValueError:
                        continue
            except Exception:
                pass
        
        logger.warning(f"Invalid date value: {value}")
        return None
    
    @staticmethod
    def validate_phone_field(value: Any) -> Optional[str]:
        """Validate and clean phone number fields"""
        if value is None:
            return None
        
        phone = str(value).strip()
        if not phone:
            return None
        
        # Remove common formatting
        phone = ''.join(filter(str.isdigit, phone))
        
        # Basic US phone number validation
        if len(phone) == 10:
            return f"({phone[:3]}) {phone[3:6]}-{phone[6:]}"
        elif len(phone) == 11 and phone.startswith('1'):
            return f"({phone[1:4]}) {phone[4:7]}-{phone[7:]}"
        
        # Return original if it doesn't fit standard US format
        return str(value).strip()
    
    @staticmethod
    def validate_email_field(value: Any) -> Optional[str]:
        """Validate and clean email fields"""
        if value is None:
            return None
        
        email = str(value).strip().lower()
        if not email:
            return None
        
        # Basic email validation
        if '@' in email and '.' in email:
            return email
        
        logger.warning(f"Invalid email format: {email}")
        return None


class GeniusFieldValidator:
    """Field-specific validators for common Genius entities"""
    
    @staticmethod
    def validate_division_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate division record"""
        validated = {}
        
        # Validate based on actual model fields
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['group_id'] = GeniusValidator.validate_id_field(record.get('group_id'))
        validated['region_id'] = GeniusValidator.validate_id_field(record.get('region_id'))
        validated['label'] = GeniusValidator.validate_string_field(record.get('label'), max_length=255, required=True)
        validated['abbreviation'] = GeniusValidator.validate_string_field(record.get('abbreviation'), max_length=50)
        validated['is_utility'] = GeniusValidator.validate_boolean_field(record.get('is_utility'))
        validated['is_corp'] = GeniusValidator.validate_boolean_field(record.get('is_corp'))
        validated['is_omniscient'] = GeniusValidator.validate_boolean_field(record.get('is_omniscient'))
        validated['is_inactive'] = GeniusValidator.validate_id_field(record.get('is_inactive'))
        validated['account_scheduler_id'] = GeniusValidator.validate_id_field(record.get('account_scheduler_id'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_prospect_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prospect record"""
        validated = {}
        
        validated['genius_id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['first_name'] = GeniusValidator.validate_string_field(record.get('first_name'), max_length=100)
        validated['last_name'] = GeniusValidator.validate_string_field(record.get('last_name'), max_length=100)
        validated['email'] = GeniusValidator.validate_email_field(record.get('email'))
        validated['phone'] = GeniusValidator.validate_phone_field(record.get('phone'))
        validated['address'] = GeniusValidator.validate_string_field(record.get('address'), max_length=500)
        validated['city'] = GeniusValidator.validate_string_field(record.get('city'), max_length=100)
        validated['state'] = GeniusValidator.validate_string_field(record.get('state'), max_length=50)
        validated['zip_code'] = GeniusValidator.validate_string_field(record.get('zip_code'), max_length=20)
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_appointment_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate appointment record"""
        validated = {}
        
        validated['genius_id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['prospect_id'] = GeniusValidator.validate_id_field(record.get('prospect_id'))
        validated['user_id'] = GeniusValidator.validate_id_field(record.get('user_id'))
        validated['appointment_type_id'] = GeniusValidator.validate_id_field(record.get('appointment_type_id'))
        validated['scheduled_date'] = GeniusValidator.validate_datetime_field(record.get('scheduled_date'))
        validated['duration'] = GeniusValidator.validate_id_field(record.get('duration'))  # in minutes
        validated['notes'] = GeniusValidator.validate_string_field(record.get('notes'), max_length=2000)
        validated['status'] = GeniusValidator.validate_string_field(record.get('status'), max_length=50)
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_user_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate user record"""
        validated = {}
        
        validated['genius_id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['first_name'] = GeniusValidator.validate_string_field(record.get('first_name'), max_length=100)
        validated['last_name'] = GeniusValidator.validate_string_field(record.get('last_name'), max_length=100)
        validated['email'] = GeniusValidator.validate_email_field(record.get('email'))
        validated['username'] = GeniusValidator.validate_string_field(record.get('username'), max_length=100)
        validated['active'] = GeniusValidator.validate_boolean_field(record.get('active'))
        validated['user_title_id'] = GeniusValidator.validate_id_field(record.get('user_title_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record.get('division_id'))
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_job_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate job record"""
        from django.utils import timezone
        validated = {}
        
        # Use 'id' as the field name (not 'genius_id') to match the Django model
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['prospect_id'] = GeniusValidator.validate_id_field(record.get('prospect_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record.get('division_id'))
        
        # Use correct field names that match the actual database schema
        validated['status'] = GeniusValidator.validate_string_field(record.get('status'), max_length=50)
        validated['contract_amount'] = GeniusValidator.validate_decimal_field(record.get('contract_amount'), max_digits=10, decimal_places=2)
        validated['start_date'] = GeniusValidator.validate_datetime_field(record.get('start_date'))
        validated['end_date'] = GeniusValidator.validate_datetime_field(record.get('end_date'))
        validated['add_user_id'] = GeniusValidator.validate_id_field(record.get('add_user_id'))
        validated['add_date'] = GeniusValidator.validate_datetime_field(record.get('add_date'))
        
        # Workaround: Handle NULL updated_at values from Genius by setting to current time
        # TODO: Fix this in Genius database in the future
        updated_at_value = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        if updated_at_value is None:
            updated_at_value = timezone.now()
            logger.warning(f"Job {record.get('id')}: updated_at was NULL, setting to current time as workaround")
        validated['updated_at'] = updated_at_value
        
        validated['service_id'] = GeniusValidator.validate_id_field(record.get('service_id', 8))  # Default to 8
        
        return validated
    
    @staticmethod
    def validate_job_change_order_item_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate job change order item record"""
        validated = {}
        
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['change_order_id'] = GeniusValidator.validate_id_field(record.get('change_order_id'))
        validated['description'] = GeniusValidator.validate_string_field(record.get('description'), max_length=256, required=False)
        validated['amount'] = GeniusValidator.validate_decimal_field(record.get('amount'), max_digits=8, decimal_places=2)
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_job_change_order_reason_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate job change order reason record"""
        validated = {}
        
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['label'] = GeniusValidator.validate_string_field(record.get('label'), max_length=100, required=False)
        validated['description'] = GeniusValidator.validate_string_field(record.get('description'), max_length=255, required=False)
        
        return validated
    
    @staticmethod
    def validate_job_change_order_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate job change order record"""
        validated = {}
        
        # Map database fields to Django model fields
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['job_id'] = GeniusValidator.validate_id_field(record.get('job_id'))
        validated['number'] = GeniusValidator.validate_string_field(record.get('number'), max_length=20, required=False)
        validated['status_id'] = GeniusValidator.validate_id_field(record.get('status_id'))
        validated['type_id'] = GeniusValidator.validate_id_field(record.get('type_id'))
        validated['adjustment_change_order_id'] = GeniusValidator.validate_id_field(record.get('adjustment_change_order_id'))
        validated['effective_date'] = GeniusValidator.validate_date_field(record.get('effective_date'))
        validated['total_amount'] = GeniusValidator.validate_decimal_field(record.get('total_amount'), max_digits=9, decimal_places=2)
        validated['add_user_id'] = GeniusValidator.validate_id_field(record.get('add_user_id'))
        validated['add_date'] = GeniusValidator.validate_datetime_field(record.get('add_date'))
        validated['sold_user_id'] = GeniusValidator.validate_id_field(record.get('sold_user_id'))
        validated['sold_date'] = GeniusValidator.validate_datetime_field(record.get('sold_date'))
        validated['cancel_user_id'] = GeniusValidator.validate_id_field(record.get('cancel_user_id'))
        validated['cancel_date'] = GeniusValidator.validate_datetime_field(record.get('cancel_date'))
        validated['reason_id'] = GeniusValidator.validate_id_field(record.get('reason_id'))
        validated['envelope_id'] = GeniusValidator.validate_string_field(record.get('envelope_id'), max_length=64, required=False)
        validated['total_contract_amount'] = GeniusValidator.validate_decimal_field(record.get('total_contract_amount'), max_digits=9, decimal_places=2)
        validated['total_pre_change_orders_amount'] = GeniusValidator.validate_decimal_field(record.get('total_pre_change_orders_amount'), max_digits=9, decimal_places=2)
        validated['signer_name'] = GeniusValidator.validate_string_field(record.get('signer_name'), max_length=100, required=False)
        validated['signer_email'] = GeniusValidator.validate_string_field(record.get('signer_email'), max_length=100, required=False)
        validated['financing_note'] = GeniusValidator.validate_string_field(record.get('financing_note'), max_length=255, required=False)
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated


class GeniusRecordValidator:
    """High-level record validation with business logic"""
    
    @staticmethod
    def validate_required_relationships(record_type: str, record: Dict[str, Any]) -> List[str]:
        """Validate required foreign key relationships"""
        errors = []
        
        if record_type == 'appointment':
            if not record.get('prospect_id'):
                errors.append("Appointment must have a prospect_id")
            if not record.get('user_id'):
                errors.append("Appointment must have a user_id")
        
        elif record_type == 'job':
            if not record.get('prospect_id'):
                errors.append("Job must have a prospect_id")
            if not record.get('division_id'):
                errors.append("Job must have a division_id")
        
        elif record_type == 'user':
            if not record.get('division_id'):
                errors.append("User must have a division_id")
        
        return errors
    
    @staticmethod
    def validate_business_rules(record_type: str, record: Dict[str, Any]) -> List[str]:
        """Validate business-specific rules"""
        errors = []
        
        if record_type == 'appointment':
            if record.get('scheduled_date') and record['scheduled_date'] < datetime.now():
                logger.warning(f"Appointment {record.get('genius_id')} is scheduled in the past")
        
        elif record_type == 'job':
            start_date = record.get('start_date')
            completion_date = record.get('completion_date')
            
            if start_date and completion_date and start_date > completion_date:
                errors.append("Job start_date cannot be after completion_date")
            
            contract_amount = record.get('contract_amount')
            if contract_amount and contract_amount < 0:
                errors.append("Job contract_amount cannot be negative")
        
        return errors
