"""
Base processor for SalesPro data following CRM sync framework standards
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from ingestion.base.processor import BaseDataProcessor
from ingestion.base.exceptions import ValidationException
from ingestion.base.validators import (
    EmailValidator, PhoneValidator, DateValidator, DecimalValidator, 
    BooleanValidator, StringValidator, ZipValidator
)

logger = logging.getLogger(__name__)


class SalesProBaseProcessor(BaseDataProcessor):
    """Base processor for SalesPro data with CRM sync framework compliance"""
    
    # CRM sync guide standard field type validators
    FIELD_TYPE_VALIDATORS = {
        'email': 'email_validator',
        'phone': 'phone_validator', 
        'date': 'date_validator',
        'datetime': 'date_validator',
        'decimal': 'decimal_validator',
        'integer': '_parse_integer',
        'boolean': 'boolean_validator',
        'zip_code': 'zip_validator',
        'state': '_validate_state',
        'string': 'string_validator'
    }
    
    def __init__(self, model_class, crm_source: str = 'salespro', **kwargs):
        super().__init__(model_class, **kwargs)
        self.crm_source = crm_source
        self.field_mappings = self.get_field_mappings()
        
        # Initialize validators following framework standards
        self.email_validator = EmailValidator()
        self.phone_validator = PhoneValidator()
        self.date_validator = DateValidator()
        self.decimal_validator = DecimalValidator()
        self.boolean_validator = BooleanValidator()
        self.string_validator = StringValidator()
        self.zip_validator = ZipValidator()
        
        # Enhanced error logging settings
        self.enable_detailed_logging = True
        self.salespro_base_url = "https://app.salespro.com"  # Update with actual SalesPro URL
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get SalesPro-specific field mappings following CRM sync guide patterns"""
        return {
            # Primary identifier fields - support both customer records and activity logs
            'id': 'id',
            'customer_id': 'customer_id',
            'user_id': 'user_id',
            'activity_identifier': 'activity_identifier',
            
            # Core entity fields
            'estimate_id': 'estimate_id', 
            'company_id': 'company_id',
            'company_name': 'company_name',
            'customer_first_name': 'customer_first_name',
            'customer_last_name': 'customer_last_name',
            'email_address': 'email',
            'phone_number': 'phone',
            'address_1': 'address_1',
            'address_2': 'address_2',
            'city': 'city',
            'state': 'state',
            'zip_code': 'zip_code',
            'crm_source': 'crm_source',
            'crm_source_id': 'crm_source_id',
            
            # Activity-specific fields
            'activity_note': 'activity_note',
            'key_metric': 'key_metric',
            'price_type': 'price_type',
            'price': 'price',
            'local_customer_uuid': 'local_customer_uuid',
            'original_row_num': 'original_row_num',
            
            # Timestamps
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
    
    def get_field_types(self) -> Dict[str, str]:
        """Return field type mappings for validation following CRM sync guide"""
        return {
            # Primary identifier fields
            'id': 'string',
            'customer_id': 'string',
            'user_id': 'string',
            'activity_identifier': 'string',
            
            # String fields
            'estimate_id': 'string',
            'company_id': 'string',
            'company_name': 'string',
            'customer_first_name': 'string',
            'customer_last_name': 'string',
            'address_1': 'string',
            'address_2': 'string',
            'city': 'string',
            'state': 'state',
            'crm_source': 'string',
            'crm_source_id': 'string',
            
            # Activity fields
            'activity_note': 'string',
            'key_metric': 'string',
            'price_type': 'string',
            'local_customer_uuid': 'string',
            'original_row_num': 'integer',
            
            # Validated fields
            'email': 'email',
            'phone': 'phone',
            'zip_code': 'zip_code',
            
            # Date/time fields
            'created_at': 'datetime',
            'updated_at': 'datetime',
            
            # Decimal fields
            'amount': 'decimal',
            'price': 'decimal',
            'total': 'decimal',
            
            # Boolean fields
            'is_active': 'boolean',
            'is_deleted': 'boolean',
        }
    
    def extract_nested_value(self, record: Dict, field_path: str) -> Any:
        """Extract values using dot notation for nested fields following CRM sync guide"""
        try:
            value = record
            for key in field_path.split('.'):
                if isinstance(value, dict) and key in value:
                    value = value[key]
                else:
                    return None
            return value
        except (KeyError, TypeError, AttributeError):
            return None
    
    def validate_field(self, field_name: str, value: Any, field_type: str, 
                      context: Dict = None) -> Any:
        """Validate field using framework standards with context following CRM sync guide"""
        if context is None:
            context = {}
        
        try:
            if field_type == 'email':
                return self.email_validator.validate(value)
            elif field_type == 'phone':
                return self.phone_validator.validate(value)
            elif field_type == 'date' or field_type == 'datetime':
                return self.date_validator.validate(value)
            elif field_type == 'decimal':
                return self.decimal_validator.validate(value)
            elif field_type == 'boolean':
                return self.boolean_validator.validate(value)
            elif field_type == 'integer':
                return self._parse_integer(value)
            elif field_type == 'zip_code':
                return self.zip_validator.validate(value)
            elif field_type == 'state':
                return self._validate_state(value)
            else:
                # Default string validation
                return self.string_validator.validate(value)
                
        except ValidationException as e:
            # Build context info for logging following CRM sync guide pattern
            record_id = context.get('id', 'unknown')
            context_info = f" (Record: id={record_id})"
            
            logger.warning(
                f"Validation warning for field '{field_name}' with value '{value}' "
                f"{context_info}: {str(e)}"
            )
            return value  # Return original value on validation failure
    
    def validate_field_with_enhanced_logging(self, field_name: str, value: Any, field_type: str, 
                                           context: Dict = None) -> Any:
        """Validate field with enhanced error logging following CRM sync guide patterns"""
        if context is None:
            context = {}
        
        try:
            # Use standardized field type validators
            validator_method = self.FIELD_TYPE_VALIDATORS.get(field_type, 'string_validator')
            
            if hasattr(self, validator_method):
                validator = getattr(self, validator_method)
                validated_value = validator.validate(value) if hasattr(validator, 'validate') else validator(value)
            else:
                # Fallback to original validation method
                validated_value = self.validate_field(field_name, value, field_type, context)
            
            # Additional field length validation with enhanced logging
            if isinstance(validated_value, str):
                max_lengths = {
                    'customer_first_name': 255,
                    'customer_last_name': 255,
                    'company_name': 255,
                    'email': 254,
                    'phone': 20,
                    'address_1': 255,
                    'address_2': 255,
                    'city': 100,
                    'state': 50,
                    'zip_code': 20,
                    'crm_source': 50,
                    'crm_source_id': 255,
                }
                
                max_length = max_lengths.get(field_name)
                if max_length and len(validated_value) > max_length:
                    # Enhanced error logging with standardized context
                    context_info = self.build_context_string(context)
                    
                    logger.warning(
                        f"SalesPro field '{field_name}' too long ({len(validated_value)} chars), "
                        f"truncating to {max_length} for value: "
                        f"'{validated_value[:50]}{'...' if len(validated_value) > 50 else ''}'"
                        f"{context_info}"
                    )
                    
                    # Truncate the value
                    validated_value = validated_value[:max_length]
            
            return validated_value
            
        except ValidationException as e:
            # Enhanced validation error logging with standardized format
            context_info = self.build_context_string(context)
            
            logger.warning(
                f"SalesPro validation warning for field '{field_name}' with value '{value}'"
                f"{context_info}: {e}"
            )
            
            # Return original value in non-strict mode (following CRM sync guide pattern)
            return value
            
        except Exception as e:
            # Enhanced general error logging with standardized format
            context_info = self.build_context_string(context)
            
            logger.error(
                f"SalesPro unexpected error validating field '{field_name}' with value '{value}'"
                f"{context_info}: {e}"
            )
            
            return value
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw SalesPro record to model format following CRM sync guide"""
        transformed = {}
        # Better context handling for different record types
        context = {
            'id': record.get('customer_id', record.get('id', record.get('user_id', 'unknown')))
        }
        
        for source_field, target_field in self.field_mappings.items():
            value = self.extract_nested_value(record, source_field)
            if value is not None:
                # Apply field-specific validation
                field_type = self.get_field_types().get(target_field, 'string')
                validated_value = self.validate_field_with_enhanced_logging(
                    target_field, value, field_type, context
                )
                transformed[target_field] = validated_value
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete record following CRM sync guide patterns"""
        
        # Different validation rules for different record types
        if self.is_activity_record(record):
            # Activity records need user_id and activity_identifier or created_at
            if not record.get('user_id') and not record.get('activity_identifier'):
                raise ValidationException("Activity record missing required 'user_id' or 'activity_identifier' field")
        elif self.model_class.__name__ == 'SalesPro_LeadResult':
            # LeadResult records use estimate_id as primary key
            if not record.get('estimate_id'):
                raise ValidationException("LeadResult record missing required 'estimate_id' field")
        else:
            # Customer/entity records need customer_id or id
            if not record.get('customer_id') and not record.get('id'):
                raise ValidationException("Record missing required 'customer_id' or 'id' field")
        
        # Business rule validation following CRM sync guide
        warnings = self.validate_record_completeness(record)
        if warnings:
            record_id = record.get('customer_id', record.get('id', record.get('user_id', 'unknown')))
            logger.warning(f"Record completeness warnings for {record_id}: {'; '.join(warnings)}")
        
        return record
    
    def is_activity_record(self, record: Dict[str, Any]) -> bool:
        """Determine if this is an activity/log record vs customer/entity record"""
        # Activity records typically have activity_note, user_id, or activity_identifier
        activity_fields = ['activity_note', 'activity_identifier', 'key_metric']
        return any(record.get(field) for field in activity_fields)
    
    def validate_record_completeness(self, record: Dict[str, Any]) -> List[str]:
        """Validate record completeness following CRM sync guide business rules"""
        warnings = []
        
        # Skip detailed completeness checks for activity records (they're logs, not customer data)
        if self.is_activity_record(record):
            return warnings
            
        # Skip detailed completeness checks for LeadResult records (they have different validation requirements)
        if self.model_class.__name__ == 'SalesPro_LeadResult':
            return warnings
        
        # Check for minimum required information for customer/entity records
        if not record.get('customer_first_name') and not record.get('customer_last_name'):
            warnings.append("Customer missing both first and last name")
        
        if not record.get('email') and not record.get('phone'):
            warnings.append("Customer missing both email and phone")
        
        # Check for data consistency
        if record.get('created_at') and record.get('updated_at'):
            try:
                created = self._parse_datetime(record['created_at'])
                updated = self._parse_datetime(record['updated_at'])
                if created and updated and updated < created:
                    warnings.append("Updated date is before created date")
            except Exception:
                pass  # Ignore datetime parsing errors here
        
        return warnings
    
    def get_salespro_url(self, record_id: str) -> str:
        """Get SalesPro URL for a record following CRM sync guide pattern"""
        if not record_id or record_id == 'unknown':
            return ""
        return f"{self.salespro_base_url}/customer/{record_id}"
    
    def build_context_string(self, context: Dict = None) -> str:
        """Build standardized context string following CRM sync guide"""
        if not context:
            return ""
        
        record_id = context.get('id', 'unknown')
        context_parts = [f"Record: id={record_id}"]
        
        # Add SalesPro URL if available
        if record_id != 'unknown':
            salespro_url = self.get_salespro_url(record_id)
            if salespro_url:
                context_parts.append(f"SalesPro URL: {salespro_url}")
        
        return f" ({'; '.join(context_parts)})"
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer value safely following CRM sync guide"""
        if value is None or value == '':
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def _validate_state(self, value: Any) -> Optional[str]:
        """Validate state format following CRM sync guide"""
        if not value:
            return None
        return str(value).strip().upper()
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime following CRM sync guide patterns"""
        if not value:
            return None
            
        try:
            # If it's already a datetime object, make it timezone-aware
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    return timezone.make_aware(value)
                return value
            
            # Use the framework date validator
            return self.date_validator.validate(value)
            
        except (ValueError, ValidationException) as e:
            logger.warning(f"Could not parse datetime '{value}': {e}")
            return None
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal value following CRM sync guide"""
        if not value:
            return None
        try:
            return self.decimal_validator.validate(value)
        except (ValueError, ValidationException):
            logger.warning(f"Could not parse decimal: {value}")
            return None
    
    def _parse_boolean(self, value: Any) -> bool:
        """Parse boolean value following CRM sync guide"""
        try:
            return self.boolean_validator.validate(value)
        except ValidationException:
            # Fallback to simple parsing
            if not value:
                return False
            return str(value).upper() in ('TRUE', '1', 'YES', 'Y')
    
    async def process_records(self, records: List[Dict[str, Any]], **kwargs) -> Dict[str, Any]:
        """Process a list of records and return processing results"""
        results = {
            'created': 0,
            'updated': 0,
            'failed': 0,
            'total_processed': len(records)
        }
        
        logger.info(f"Processing {len(records)} records with {self.__class__.__name__}")
        
        for record in records:
            try:
                # Transform and validate the record
                transformed_record = self.transform_record(record)
                validated_record = self.validate_record(transformed_record)
                
                # Save to database (implement based on your existing save logic)
                # This would need to be implemented based on your existing patterns
                logger.debug(f"Processed record: {validated_record.get('id', 'unknown')}")
                results['created'] += 1
                
            except Exception as e:
                logger.error(f"Failed to process record: {e}")
                results['failed'] += 1
        
        logger.info(f"Processing complete: {results}")
        return results
