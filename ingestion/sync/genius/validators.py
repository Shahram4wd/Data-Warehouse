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
        """Validate and convert datetime fields with timezone awareness"""
        if value is None:
            return None
        
        from django.utils import timezone
        from datetime import date
        
        if isinstance(value, datetime):
            # If already a datetime, make it timezone-aware if it's naive
            if timezone.is_naive(value):
                return timezone.make_aware(value)
            return value
        
        # Handle date objects (convert to datetime)
        if isinstance(value, date):
            dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(dt)
        
        if isinstance(value, str):
            try:
                # Try common datetime formats
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return timezone.make_aware(dt)
                    except ValueError:
                        continue
            except Exception:
                pass
        
        logger.warning(f"Invalid datetime value: {value}")
        return None
    
    @staticmethod
    def validate_date_field(value: Any) -> Optional[datetime]:
        """Validate and convert date fields to timezone-aware datetime for Django DateField compatibility"""
        if value is None:
            return None
        
        from django.utils import timezone
        from datetime import date
        
        # Handle date objects directly
        if isinstance(value, date):
            dt = datetime.combine(value, datetime.min.time())
            return timezone.make_aware(dt)
        
        if isinstance(value, datetime):
            # If already a datetime, make it timezone-aware if it's naive
            if timezone.is_naive(value):
                return timezone.make_aware(value)
            return value
        
        if isinstance(value, str):
            try:
                # Try common date formats
                for fmt in ['%Y-%m-%d', '%Y-%m-%d %H:%M:%S']:
                    try:
                        dt = datetime.strptime(value, fmt)
                        return timezone.make_aware(dt)
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
        """Validate job record with comprehensive field mapping"""
        from django.utils import timezone
        validated = {}
        
        # Basic job identification
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        validated['client_cid'] = GeniusValidator.validate_id_field(record.get('client_cid'))
        validated['prospect_id'] = GeniusValidator.validate_id_field(record.get('prospect_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record.get('division_id'))
        validated['user_id'] = GeniusValidator.validate_id_field(record.get('user_id'))
        validated['production_user_id'] = GeniusValidator.validate_id_field(record.get('production_user_id'))
        validated['project_coordinator_user_id'] = GeniusValidator.validate_id_field(record.get('project_coordinator_user_id'))
        validated['production_month'] = GeniusValidator.validate_id_field(record.get('production_month'))
        
        # Subcontractor fields
        validated['subcontractor_id'] = GeniusValidator.validate_id_field(record.get('subcontractor_id'))
        validated['subcontractor_status_id'] = GeniusValidator.validate_id_field(record.get('subcontractor_status_id'))
        validated['subcontractor_confirmed'] = GeniusValidator.validate_id_field(record.get('subcontractor_confirmed'))
        
        # Status fields
        validated['status'] = GeniusValidator.validate_id_field(record.get('status'))
        validated['is_in_progress'] = GeniusValidator.validate_id_field(record.get('is_in_progress'))
        validated['ready_status'] = GeniusValidator.validate_id_field(record.get('ready_status'))
        
        # Prep status fields
        validated['prep_status_id'] = GeniusValidator.validate_id_field(record.get('prep_status_id'))
        validated['prep_status_set_date'] = GeniusValidator.validate_datetime_field(record.get('prep_status_set_date'))
        validated['prep_status_is_reset'] = GeniusValidator.validate_id_field(record.get('prep_status_is_reset'))
        validated['prep_status_notes'] = GeniusValidator.validate_string_field(record.get('prep_status_notes'))
        validated['prep_issue_id'] = GeniusValidator.validate_string_field(record.get('prep_issue_id'), max_length=32)
        
        # Service and lead info
        validated['service_id'] = GeniusValidator.validate_id_field(record.get('service_id', 8))  # Default to 8
        validated['is_lead_pb'] = GeniusValidator.validate_id_field(record.get('is_lead_pb'))
        
        # Contract information
        validated['contract_number'] = GeniusValidator.validate_string_field(record.get('contract_number'), max_length=50)
        validated['contract_date'] = GeniusValidator.validate_date_field(record.get('contract_date'))
        validated['contract_amount'] = GeniusValidator.validate_decimal_field(record.get('contract_amount'), max_digits=11, decimal_places=2)
        validated['contract_amount_difference'] = GeniusValidator.validate_string_field(record.get('contract_amount_difference'))
        validated['contract_hours'] = GeniusValidator.validate_id_field(record.get('contract_hours'))
        validated['contract_file_id'] = GeniusValidator.validate_id_field(record.get('contract_file_id'))
        
        # Financial information
        validated['job_value'] = GeniusValidator.validate_decimal_field(record.get('job_value'), max_digits=11, decimal_places=2)
        validated['deposit_amount'] = GeniusValidator.validate_decimal_field(record.get('deposit_amount'), max_digits=11, decimal_places=2)
        validated['deposit_type_id'] = GeniusValidator.validate_id_field(record.get('deposit_type_id'))
        validated['is_financing'] = GeniusValidator.validate_id_field(record.get('is_financing'))
        validated['sales_tax_rate'] = GeniusValidator.validate_decimal_field(record.get('sales_tax_rate'), max_digits=7, decimal_places=5)
        validated['is_sales_tax_exempt'] = GeniusValidator.validate_id_field(record.get('is_sales_tax_exempt'))
        validated['commission_payout'] = GeniusValidator.validate_decimal_field(record.get('commission_payout'), max_digits=11, decimal_places=2)
        validated['accrued_commission_payout'] = GeniusValidator.validate_decimal_field(record.get('accrued_commission_payout'), max_digits=11, decimal_places=2)
        
        # Sales information - INCLUDING sold_date!
        validated['sold_user_id'] = GeniusValidator.validate_id_field(record.get('sold_user_id'))
        validated['sold_date'] = GeniusValidator.validate_date_field(record.get('sold_date'))
        
        # Scheduling information
        validated['start_request_date'] = GeniusValidator.validate_date_field(record.get('start_request_date'))
        validated['deadline_date'] = GeniusValidator.validate_date_field(record.get('deadline_date'))
        validated['ready_date'] = GeniusValidator.validate_date_field(record.get('ready_date'))
        validated['jsa_sent'] = GeniusValidator.validate_id_field(record.get('jsa_sent'))
        validated['start_date'] = GeniusValidator.validate_date_field(record.get('start_date'))
        validated['end_date'] = GeniusValidator.validate_date_field(record.get('end_date'))
        
        # Add and audit information
        validated['add_user_id'] = GeniusValidator.validate_id_field(record.get('add_user_id'))
        validated['add_date'] = GeniusValidator.validate_datetime_field(record.get('add_date'))
        
        # Cancellation information
        validated['cancel_date'] = GeniusValidator.validate_date_field(record.get('cancel_date'))
        validated['cancel_user_id'] = GeniusValidator.validate_id_field(record.get('cancel_user_id'))
        validated['cancel_reason_id'] = GeniusValidator.validate_id_field(record.get('cancel_reason_id'))
        
        # Refund information
        validated['is_refund'] = GeniusValidator.validate_id_field(record.get('is_refund'))
        validated['refund_date'] = GeniusValidator.validate_date_field(record.get('refund_date'))
        validated['refund_user_id'] = GeniusValidator.validate_id_field(record.get('refund_user_id'))
        
        # Completion information
        validated['finish_date'] = GeniusValidator.validate_date_field(record.get('finish_date'))
        validated['is_earned_not_paid'] = GeniusValidator.validate_id_field(record.get('is_earned_not_paid'))
        
        # Materials and measurement information
        validated['materials_arrival_date'] = GeniusValidator.validate_date_field(record.get('materials_arrival_date'))
        validated['measure_date'] = GeniusValidator.validate_date_field(record.get('measure_date'))
        validated['measure_time'] = GeniusValidator.validate_string_field(record.get('measure_time'))
        validated['measure_user_id'] = GeniusValidator.validate_id_field(record.get('measure_user_id'))
        validated['time_format'] = GeniusValidator.validate_string_field(record.get('time_format'))
        validated['materials_estimated_arrival_date'] = GeniusValidator.validate_date_field(record.get('materials_estimated_arrival_date'))
        validated['materials_ordered'] = GeniusValidator.validate_date_field(record.get('materials_ordered'))
        
        # Installation information
        validated['install_date'] = GeniusValidator.validate_date_field(record.get('install_date'))
        validated['install_time'] = GeniusValidator.validate_string_field(record.get('install_time'))
        validated['install_time_format'] = GeniusValidator.validate_string_field(record.get('install_time_format'))
        
        # Pricing and commission details
        validated['price_level'] = GeniusValidator.validate_string_field(record.get('price_level'), max_length=32)
        validated['price_level_goal'] = GeniusValidator.validate_id_field(record.get('price_level_goal'))
        validated['price_level_commission'] = GeniusValidator.validate_decimal_field(record.get('price_level_commission'), max_digits=3, decimal_places=1)
        validated['price_level_commission_reduction'] = GeniusValidator.validate_id_field(record.get('price_level_commission_reduction'))
        validated['is_reviewed'] = GeniusValidator.validate_id_field(record.get('is_reviewed'))
        validated['reviewed_by'] = GeniusValidator.validate_id_field(record.get('reviewed_by'))
        
        # Additional fields
        validated['pp_id_updated'] = GeniusValidator.validate_id_field(record.get('pp_id_updated'))
        validated['hoa'] = GeniusValidator.validate_id_field(record.get('hoa'))
        validated['hoa_approved'] = GeniusValidator.validate_id_field(record.get('hoa_approved'))
        validated['materials_ordered_old'] = GeniusValidator.validate_id_field(record.get('materials_ordered_old'))
        validated['start_month_old'] = GeniusValidator.validate_id_field(record.get('start_month_old'))
        validated['cogs_report_month'] = GeniusValidator.validate_string_field(record.get('cogs_report_month'), max_length=50)
        validated['is_cogs_report_month_updated'] = GeniusValidator.validate_id_field(record.get('is_cogs_report_month_updated'))
        validated['forecast_month'] = GeniusValidator.validate_string_field(record.get('forecast_month'), max_length=50)
        validated['coc_sent_on'] = GeniusValidator.validate_datetime_field(record.get('coc_sent_on'))
        validated['coc_sent_by'] = GeniusValidator.validate_id_field(record.get('coc_sent_by'))
        validated['company_cam_link'] = GeniusValidator.validate_string_field(record.get('company_cam_link'), max_length=256)
        validated['pm_finished_on'] = GeniusValidator.validate_date_field(record.get('pm_finished_on'))
        validated['estimate_job_duration'] = GeniusValidator.validate_id_field(record.get('estimate_job_duration'))
        validated['payment_not_finalized_reason'] = GeniusValidator.validate_id_field(record.get('payment_not_finalized_reason'))
        validated['reasons_other'] = GeniusValidator.validate_string_field(record.get('reasons_other'), max_length=255)
        validated['payment_type'] = GeniusValidator.validate_id_field(record.get('payment_type'))
        validated['payment_amount'] = GeniusValidator.validate_decimal_field(record.get('payment_amount'), max_digits=11, decimal_places=2)
        validated['is_payment_finalized'] = GeniusValidator.validate_id_field(record.get('is_payment_finalized'))
        validated['is_company_cam'] = GeniusValidator.validate_id_field(record.get('is_company_cam'))
        validated['is_five_star_review'] = GeniusValidator.validate_id_field(record.get('is_five_star_review'))
        validated['projected_end_date'] = GeniusValidator.validate_date_field(record.get('projected_end_date'))
        validated['is_company_cam_images_correct'] = GeniusValidator.validate_id_field(record.get('is_company_cam_images_correct'))
        validated['post_pm_closeout_date'] = GeniusValidator.validate_date_field(record.get('post_pm_closeout_date'))
        validated['pre_pm_closeout_date'] = GeniusValidator.validate_date_field(record.get('pre_pm_closeout_date'))
        validated['actual_install_date'] = GeniusValidator.validate_datetime_field(record.get('actual_install_date'))
        validated['in_progress_substatus_id'] = GeniusValidator.validate_id_field(record.get('in_progress_substatus_id'))
        validated['is_loan_document_uptodate'] = GeniusValidator.validate_id_field(record.get('is_loan_document_uptodate'))
        validated['is_labor_adjustment_correct'] = GeniusValidator.validate_id_field(record.get('is_labor_adjustment_correct'))
        validated['is_change_order_correct'] = GeniusValidator.validate_id_field(record.get('is_change_order_correct'))
        validated['is_coc_pdf_attached'] = GeniusValidator.validate_id_field(record.get('is_coc_pdf_attached'))
        
        # Workaround: Handle NULL updated_at values from Genius by setting to current time
        # TODO: Fix this in Genius database in the future
        updated_at_value = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        if updated_at_value is None:
            updated_at_value = timezone.now()
            logger.warning(f"Job {record.get('id')}: updated_at was NULL, setting to current time as workaround")
        validated['updated_at'] = updated_at_value
        
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
    def validate_integration_field_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration field record data"""
        validated = {}
        
        # Validate required fields
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        if validated['id'] is None:
            raise ValueError("Integration field must have a valid id")
        
        validated['definition_id'] = GeniusValidator.validate_id_field(record.get('definition_id'))
        if validated['definition_id'] is None:
            raise ValueError("Integration field must have a valid definition_id")
        
        # Validate optional fields
        validated['user_id'] = GeniusValidator.validate_id_field(record.get('user_id'))
        validated['division_id'] = GeniusValidator.validate_id_field(record.get('division_id'))
        
        # Validate field_value (max 128 chars)
        validated['field_value'] = GeniusValidator.validate_string_field(
            record.get('field_value'), max_length=128, required=False
        )
        
        # Validate datetime fields
        validated['created_at'] = GeniusValidator.validate_datetime_field(record.get('created_at'))
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        
        return validated
    
    @staticmethod
    def validate_integration_field_definition_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate integration field definition record data"""
        validated = {}
        
        # Validate required fields
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        if validated['id'] is None:
            raise ValueError("Integration field definition must have a valid id")
        
        validated['integration_id'] = GeniusValidator.validate_id_field(record.get('integration_id'))
        if validated['integration_id'] is None:
            raise ValueError("Integration field definition must have a valid integration_id")
        
        # Validate required string fields
        validated['label'] = GeniusValidator.validate_string_field(
            record.get('label'), max_length=32, required=True
        )
        validated['key_name'] = GeniusValidator.validate_string_field(
            record.get('key_name'), max_length=64, required=True
        )
        
        # Validate optional string fields
        validated['hint'] = GeniusValidator.validate_string_field(
            record.get('hint'), max_length=255, required=False
        )
        validated['input_type'] = GeniusValidator.validate_string_field(
            record.get('input_type'), max_length=50, required=False
        )
        
        # Validate boolean fields
        validated['is_user'] = GeniusValidator.validate_boolean_field(record.get('is_user'))
        validated['is_division'] = GeniusValidator.validate_boolean_field(record.get('is_division'))
        
        return validated
    
    @staticmethod
    def validate_prospect_source_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate prospect source record data following CRM sync guide patterns"""
        validated = {}
        
        # Validate required ID field (primary key)
        validated['id'] = GeniusValidator.validate_id_field(record.get('id'))
        
        # Validate required foreign keys
        validated['prospect_id'] = GeniusValidator.validate_id_field(record.get('prospect_id'))
        if validated['prospect_id'] is None:
            raise ValueError("ProspectSource must have a valid prospect_id")
        
        validated['marketing_source_id'] = GeniusValidator.validate_id_field(record.get('marketing_source_id'))
        if validated['marketing_source_id'] is None:
            raise ValueError("ProspectSource must have a valid marketing_source_id")
        
        # Validate optional datetime field
        validated['source_date'] = GeniusValidator.validate_datetime_field(record.get('source_date'))
        
        # Validate optional text field
        validated['notes'] = GeniusValidator.validate_string_field(record.get('notes'))
        
        # Validate required user ID
        validated['add_user_id'] = GeniusValidator.validate_id_field(record.get('add_user_id'))
        if validated['add_user_id'] is None:
            validated['add_user_id'] = 0  # Default fallback as per processor pattern
        
        # Validate NEW field: source_user_id (nullable)
        validated['source_user_id'] = GeniusValidator.validate_id_field(record.get('source_user_id'))
        
        # Validate required datetime fields
        validated['add_date'] = GeniusValidator.validate_datetime_field(record.get('add_date'))
        if validated['add_date'] is None:
            raise ValueError("ProspectSource must have a valid add_date")
        
        validated['updated_at'] = GeniusValidator.validate_datetime_field(record.get('updated_at'))
        if validated['updated_at'] is None:
            raise ValueError("ProspectSource must have a valid updated_at")
        
        return validated
    
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
