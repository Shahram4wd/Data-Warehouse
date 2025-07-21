"""
Base processor for SalesRabbit data following framework standards
"""
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from ingestion.base.processor import BaseDataProcessor
from ingestion.base.exceptions import ValidationException
from ingestion.base.validators import (
    EmailValidator, PhoneValidator, DateValidator, DecimalValidator, 
    BooleanValidator, StringValidator
)

logger = logging.getLogger(__name__)

class SalesRabbitBaseProcessor(BaseDataProcessor):
    """Base processor for SalesRabbit with framework validation and enhanced error logging"""
    
    def __init__(self, model_class, crm_source: str = 'salesrabbit', **kwargs):
        super().__init__(model_class, **kwargs)
        self.crm_source = crm_source
        self.field_mappings = self.get_field_mappings()
        
        # Initialize validators
        self.email_validator = EmailValidator()
        self.phone_validator = PhoneValidator()
        self.date_validator = DateValidator()
        self.decimal_validator = DecimalValidator()
        self.boolean_validator = BooleanValidator()
        self.string_validator = StringValidator()
        
        # Enhanced error logging settings
        self.enable_detailed_logging = True
        self.salesrabbit_base_url = "https://app.salesrabbit.com"  # Update with actual SalesRabbit URL pattern
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get SalesRabbit-specific field mappings"""
        return {
            'id': 'id',
            'firstName': 'first_name',
            'lastName': 'last_name',
            'businessName': 'business_name',
            'email': 'email',
            'phonePrimary': 'phone_primary',
            'phoneAlternate': 'phone_alternate',
            'address.street1': 'street1',
            'address.street2': 'street2',
            'address.city': 'city',
            'address.state': 'state',
            'address.zip': 'zip',
            'address.country': 'country',
            'coordinates.latitude': 'latitude',
            'coordinates.longitude': 'longitude',
            'status': 'status',
            'statusModified': 'status_modified',
            'notes': 'notes',
            'campaignId': 'campaign_id',
            'userId': 'user_id',
            'userName': 'user_name',
            'dateCreated': 'date_created',
            'dateModified': 'date_modified',
            'ownerModified': 'owner_modified',
            'dateOfBirth': 'date_of_birth',
            'deletedAt': 'deleted_at'
        }
    
    def extract_nested_value(self, record: Dict, field_path: str) -> Any:
        """Extract values using dot notation for nested fields"""
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
        """Validate field using framework standards with context"""
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
                return self._validate_zip_code(value)
            elif field_type == 'state':
                return self._validate_state(value)
            elif field_type == 'salesrabbit_status':
                return self._validate_salesrabbit_status(value)
            elif field_type == 'salesrabbit_id':
                return self._validate_salesrabbit_id(value)
            else:
                # Default string validation
                return self.string_validator.validate(value)
                
        except ValidationException as e:
            # Build context info for logging
            record_id = context.get('id', 'unknown')
            context_info = f" (Record: id={record_id})"
            
            logger.warning(
                f"Validation warning for field '{field_name}' with value '{value}' "
                f"{context_info}: {str(e)}"
            )
            return value  # Return original value on validation failure
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer value safely"""
        if value is None or value == '':
            return None
        try:
            return int(float(str(value)))
        except (ValueError, TypeError):
            return None
    
    def _validate_zip_code(self, value: Any) -> Optional[str]:
        """Validate ZIP code format"""
        if not value:
            return None
        
        value_str = str(value).strip()
        # Basic ZIP code validation (5 digits or 5+4 format)
        import re
        if re.match(r'^\d{5}(-\d{4})?$', value_str):
            return value_str
        return value_str  # Return as-is for international formats
    
    def _validate_state(self, value: Any) -> Optional[str]:
        """Validate state format"""
        if not value:
            return None
        return str(value).strip().upper()
    
    def _validate_salesrabbit_status(self, value: Any) -> Optional[str]:
        """Validate SalesRabbit status values"""
        if not value:
            return None
            
        # Comprehensive SalesRabbit status values based on real API responses
        valid_statuses = [
            # Basic statuses
            'new', 'contacted', 'qualified', 'unqualified', 'closed',
            'lead', 'prospect', 'opportunity', 'customer', 'inactive', 'active',
            'pending', 'in_progress', 'completed', 'cancelled',
            
            # Door-to-door sales specific statuses
            'not home', 'not interested', 'callback', 'follow up', 'appointment set',
            'no answer', 'busy', 'moved', 'deceased', 'do not call', 'duplicate',
            'wrong number', 'disconnected', 'voicemail', 'answering machine',
            
            # Sales pipeline statuses
            'cold', 'warm', 'hot', 'sold', 'lost', 'nurture', 'demo', 'proposal',
            'negotiation', 'contract', 'onboarding', 'churned',
            
            # Common variations with spaces/underscores
            'not_home', 'not_interested', 'follow_up', 'do_not_call'
        ]
        value_str = str(value).lower().strip()
        
        if value_str in valid_statuses:
            return value_str
        else:
            # Log as info instead of warning since we're discovering valid statuses
            #logger.info(f"New SalesRabbit status discovered: '{value}' - accepting as valid")
            return value_str  # Return as-is for unknown statuses
    
    def _validate_salesrabbit_id(self, value: Any) -> Optional[int]:
        """Validate SalesRabbit ID format"""
        if not value:
            return None
            
        try:
            return int(value)
        except (ValueError, TypeError):
            logger.warning(f"Invalid SalesRabbit ID: {value}")
            return None
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform raw SalesRabbit record to model format"""
        transformed = {}
        context = {'id': record.get('id', 'unknown')}
        
        for source_field, target_field in self.field_mappings.items():
            value = self.extract_nested_value(record, source_field)
            if value is not None:
                # Apply field-specific validation
                field_type = self.get_field_type(target_field)
                validated_value = self.validate_field(
                    target_field, value, field_type, context
                )
                transformed[target_field] = validated_value
        
        # Store raw data for reference
        transformed['data'] = record
        transformed['custom_fields'] = record.get('customFields', {})
        
        return transformed
    
    def transform_record_with_enhanced_validation(self, record: Dict[str, Any], context: Dict = None) -> Dict[str, Any]:
        """Transform raw SalesRabbit record with enhanced validation and error logging"""
        if context is None:
            context = {'id': record.get('id', 'unknown')}
        
        transformed = {}
        
        for source_field, target_field in self.field_mappings.items():
            value = self.extract_nested_value(record, source_field)
            if value is not None:
                # Apply field-specific validation with enhanced logging
                field_type = self.get_field_type(target_field)
                validated_value = self.validate_field_with_enhanced_logging(
                    target_field, value, field_type, context
                )
                transformed[target_field] = validated_value
        
        # Store raw data for reference
        transformed['data'] = record
        transformed['custom_fields'] = record.get('customFields', {})
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a complete record"""
        # Basic validation - ensure required fields
        if not record.get('id'):
            raise ValidationException("Record missing required 'id' field")
        
        return record
    
    def get_field_type(self, field_name: str) -> str:
        """Get field type for validation"""
        field_types = {
            'id': 'salesrabbit_id',
            'email': 'email',
            'phone_primary': 'phone',
            'phone_alternate': 'phone',
            'zip': 'zip_code',
            'state': 'state',
            'latitude': 'decimal',
            'longitude': 'decimal',
            'date_created': 'datetime',
            'date_modified': 'datetime',
            'status_modified': 'datetime',
            'owner_modified': 'datetime',
            'date_of_birth': 'date',
            'deleted_at': 'datetime',
            'status': 'salesrabbit_status',
            'campaign_id': 'integer',
            'user_id': 'integer'
        }
        return field_types.get(field_name, 'string')
    
    def chunk_data(self, data: List[Dict], chunk_size: int) -> List[List[Dict]]:
        """Split data into chunks for batch processing"""
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    def get_salesrabbit_url(self, record_id: str) -> str:
        """Generate SalesRabbit URL for easy access to records"""
        # Update this URL pattern based on actual SalesRabbit URL structure
        return f"{self.salesrabbit_base_url}/leads/{record_id}"
    
    def validate_field_with_enhanced_logging(self, field_name: str, value: Any, field_type: str, 
                                           context: Dict = None) -> Any:
        """Validate field with enhanced error logging similar to HubSpot pattern"""
        if context is None:
            context = {}
        
        record_id = context.get('id', 'unknown')
        salesrabbit_url = ""
        context_info = ""
        
        try:
            # Basic validation using existing methods
            validated_value = self.validate_field(field_name, value, field_type, context)
            
            # Additional field length validation with enhanced logging
            if isinstance(validated_value, str):
                max_lengths = {
                    'first_name': 255,
                    'last_name': 255,
                    'business_name': 255,
                    'email': 254,
                    'phone_primary': 20,
                    'phone_alternate': 20,
                    'street1': 255,
                    'street2': 255,
                    'city': 100,
                    'state': 50,
                    'zip': 20,
                    'country': 100,
                    'status': 100,
                    'notes': None,  # TextField, no length limit
                    'user_name': 255
                }
                
                max_length = max_lengths.get(field_name)
                if max_length and len(validated_value) > max_length:
                    # Enhanced error logging with SalesRabbit URL
                    if record_id != 'unknown':
                        salesrabbit_url = f" - SalesRabbit URL: {self.get_salesrabbit_url(record_id)}"
                        context_info = f" (Record: id={record_id})"
                    
                    logger.warning(
                        f"Field '{field_name}' too long ({len(validated_value)} chars), truncating to {max_length} "
                        f"for record {record_id}: '{validated_value[:50]}{'...' if len(validated_value) > 50 else ''}'"
                        f"{salesrabbit_url}"
                    )
                    
                    # Truncate the value
                    validated_value = validated_value[:max_length]
            
            return validated_value
            
        except ValidationException as e:
            # Enhanced validation error logging
            if record_id != 'unknown':
                salesrabbit_url = f" - SalesRabbit URL: {self.get_salesrabbit_url(record_id)}"
                context_info = f" (Record: id={record_id})"
            
            logger.warning(
                f"Validation warning for field '{field_name}' with value '{value}'"
                f"{context_info}: {e}{salesrabbit_url}"
            )
            
            # Return original value in non-strict mode (following HubSpot pattern)
            return value
            
        except Exception as e:
            # Enhanced general error logging
            if record_id != 'unknown':
                salesrabbit_url = f" - SalesRabbit URL: {self.get_salesrabbit_url(record_id)}"
                context_info = f" (Record: id={record_id})"
            
            logger.error(
                f"Unexpected error validating field '{field_name}' with value '{value}'"
                f"{context_info}: {e}{salesrabbit_url}"
            )
            
            return value
    
    def log_database_error(self, error: Exception, record_data: Dict[str, Any], operation: str = "save") -> None:
        """Log database errors with comprehensive record context for debugging"""
        record_id = record_data.get('id', 'UNKNOWN')
        salesrabbit_url = self.get_salesrabbit_url(record_id) if record_id != 'UNKNOWN' else ""
        
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
                    elif "character varying(20)" in error_msg and len(field_value) > 20:
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
        logger.error(f"Database {operation} failed for record {record_id}: {error_msg}{field_info} - SalesRabbit URL: {salesrabbit_url}")
        
        # Also log some key field values for debugging
        debug_fields = ['first_name', 'last_name', 'business_name', 'email', 'phone_primary', 'state', 'zip', 'city', 'street1']
        field_values = []
        for field in debug_fields:
            if field in record_data and record_data[field]:
                value = str(record_data[field])
                display_value = value[:30] + ('...' if len(value) > 30 else '')
                field_values.append(f"{field}='{display_value}'")
        
        if field_values:
            logger.error(f"Record {record_id} key fields: {', '.join(field_values)}")
    
    def log_batch_error(self, error: Exception, batch_data: List[Dict[str, Any]], batch_index: int = 0) -> None:
        """Log batch processing errors with enhanced context"""
        record_count = len(batch_data)
        
        logger.error(f"Batch {batch_index} processing failed ({record_count} records): {str(error)}")
        
        # Log first few record IDs for debugging
        record_ids = [str(record.get('id', 'UNKNOWN')) for record in batch_data[:5]]
        if len(batch_data) > 5:
            record_ids.append(f"... and {len(batch_data) - 5} more")
        
        logger.error(f"Batch {batch_index} record IDs: {', '.join(record_ids)}")
        
        # If it's a database error, provide SalesRabbit URLs for first few records
        if "value too long" in str(error) or "duplicate key" in str(error):
            urls = []
            for record in batch_data[:3]:
                record_id = record.get('id')
                if record_id:
                    urls.append(self.get_salesrabbit_url(record_id))
            
            if urls:
                logger.error(f"SalesRabbit URLs for debugging: {'; '.join(urls)}")
