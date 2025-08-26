"""
SalesRabbit users data processor with validation and transformation
"""
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
from django.utils.dateparse import parse_datetime, parse_date
from asgiref.sync import sync_to_async
from ingestion.base.processor import BaseDataProcessor
from ingestion.models.salesrabbit import SalesRabbit_User

logger = logging.getLogger(__name__)

class SalesRabbitUsersProcessor(BaseDataProcessor):
    """Process SalesRabbit users data with validation and transformation"""
    
    def __init__(self):
        super().__init__(SalesRabbit_User)
        self.model_class = SalesRabbit_User
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from API response to model fields"""
        return {
            'id': 'id',
            'firstName': 'first_name',
            'lastName': 'last_name',
            'email': 'email',
            'phone': 'phone',
            'active': 'active',
            'hireDate': 'hire_date',
            'businessUnit': 'business_unit',
            'department': 'department',
            'role': 'role',
            'office': 'office',
            'team': 'team',
            'region': 'region',
            'orgId': 'org_id',
            'supervisorId': 'supervisor_id',
            'recruiterId': 'recruiter_id',
            'cmsId': 'cms_id',
            'leadRepCmsId': 'lead_rep_cms_id',
            'photo_url': 'photo_url',
            'externalIds': 'external_ids',
            'dateCreated': 'date_created',
            'dateModified': 'date_modified'
        }
    
    def transform_record(self, raw_record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single user record from API format to model format"""
        try:
            transformed = {}
            field_mappings = self.get_field_mappings()
            
            # Apply basic field mappings
            for api_field, model_field in field_mappings.items():
                if api_field in raw_record:
                    transformed[model_field] = raw_record[api_field]
            
            # Parse and validate specific field types
            transformed = self._parse_data_types(transformed)
            
            # Store raw data for backup
            transformed['data'] = raw_record
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming user record {raw_record.get('id', 'unknown')}: {e}")
            # Return basic transformation to avoid losing data
            return {
                'id': raw_record.get('id'),
                'first_name': raw_record.get('firstName'),
                'last_name': raw_record.get('lastName'),
                'email': raw_record.get('email'),
                'data': raw_record
            }
    
    def _parse_data_types(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Parse and validate data types for specific fields"""
        
        # Parse boolean fields
        if 'active' in record:
            record['active'] = self._parse_boolean(record['active'])
        
        # Parse date fields
        date_fields = ['hire_date', 'date_created', 'date_modified']
        for field in date_fields:
            if field in record and record[field]:
                try:
                    if field == 'hire_date':
                        # Hire date is in YYYY-MM-DD format
                        record[field] = parse_date(record[field])
                    else:
                        # Created/modified dates are in ISO format
                        record[field] = parse_datetime(record[field])
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse {field} value: '{record[field]}' for user {record.get('id', 'unknown')}")
                    record[field] = None
        
        # Parse integer fields
        int_fields = ['id', 'org_id', 'supervisor_id', 'recruiter_id', 'cms_id', 'lead_rep_cms_id']
        for field in int_fields:
            if field in record and record[field] is not None:
                try:
                    record[field] = int(record[field]) if record[field] != '' else None
                except (ValueError, TypeError):
                    logger.warning(f"Failed to parse integer field {field}: '{record[field]}' for user {record.get('id', 'unknown')}")
                    record[field] = None
        
        # Validate email format
        if 'email' in record and record['email']:
            record['email'] = self._validate_email(record['email'])
        
        # Validate phone format
        if 'phone' in record and record['phone']:
            record['phone'] = self._validate_phone(record['phone'])
        
        # Validate URL format
        if 'photo_url' in record and record['photo_url']:
            record['photo_url'] = self._validate_url(record['photo_url'])
        
        # Ensure external_ids is a list
        if 'external_ids' in record:
            if not isinstance(record['external_ids'], list):
                logger.warning(f"external_ids is not a list for user {record.get('id', 'unknown')}: {record['external_ids']}")
                record['external_ids'] = []
        
        return record
    
    def _parse_boolean(self, value: Any) -> bool:
        """Parse boolean values with various formats"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'active')
        if isinstance(value, (int, float)):
            return bool(value)
        return False
    
    def _validate_email(self, email: str) -> Optional[str]:
        """Validate email format"""
        if not email or '@' not in email:
            return None
        
        # Basic email validation
        try:
            email = email.strip().lower()
            if len(email) > 254:  # RFC 5321 limit
                logger.warning(f"Email too long: {email}")
                return None
            return email
        except Exception:
            return None
    
    def _validate_phone(self, phone: str) -> Optional[str]:
        """Validate and format phone number"""
        if not phone or not phone.strip():
            return None
        
        try:
            # Remove common phone formatting
            clean_phone = ''.join(char for char in phone if char.isdigit() or char in '+()-. ')
            return clean_phone[:20]  # Limit length
        except Exception:
            return None
    
    def _validate_url(self, url: str) -> Optional[str]:
        """Validate URL format"""
        if not url or not url.strip():
            return None
        
        try:
            url = url.strip()
            if not (url.startswith('http://') or url.startswith('https://')):
                # Assume https if no protocol specified
                url = f'https://{url}'
            return url
        except Exception:
            return None
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed user record"""
        errors = []
        warnings = []
        
        # Required fields validation
        if not record.get('id'):
            errors.append("Missing required field: id")
        
        # Business logic validation
        if record.get('active') and not record.get('email'):
            warnings.append("Active user without email address")
        
        if record.get('hire_date') and record.get('hire_date') > datetime.now().date():
            warnings.append("Hire date is in the future")
        
        if record.get('supervisor_id') == record.get('id'):
            warnings.append("User cannot be their own supervisor")
        
        # Log validation results
        user_id = record.get('id', 'unknown')
        if errors:
            for error in errors:
                logger.error(f"Validation error for user {user_id}: {error}")
        if warnings:
            for warning in warnings:
                logger.warning(f"Validation warning for user {user_id}: {warning}")
        
        # Add validation metadata
        record['_validation_errors'] = errors
        record['_validation_warnings'] = warnings
        
        return record
    
    def prepare_for_save(self, validated_record: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare record for database save by removing validation metadata"""
        # Remove validation metadata before saving
        clean_record = {k: v for k, v in validated_record.items() 
                       if not k.startswith('_validation_')}
        
        return clean_record

    def save_data(self, validated_records: List[Dict[str, Any]], 
                  batch_size: int = 100, force_overwrite: bool = False) -> Dict[str, int]:
        """Save data using efficient bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0, 'total_processed': 0}
        
        if not validated_records:
            return results
        
        try:
            # Prepare records for save
            clean_records = [self.prepare_for_save(record) for record in validated_records]
            
            # Create model objects
            objects = []
            for record in clean_records:
                try:
                    obj = self.model_class(**record)
                    objects.append(obj)
                except Exception as e:
                    logger.error(f"Failed to create object for record {record.get('id')}: {e}")
                    results['failed'] += 1
            
            if objects:
                # Use bulk_create with update_conflicts for efficient upsert
                created_objects = self.model_class.objects.bulk_create(
                    objects,
                    batch_size=batch_size,
                    update_conflicts=True,
                    update_fields=[
                        'first_name', 'last_name', 'email', 'phone', 'active', 
                        'hire_date', 'business_unit', 'department', 'role', 'office', 
                        'team', 'region', 'org_id', 'supervisor_id', 'recruiter_id',
                        'cms_id', 'lead_rep_cms_id', 'photo_url', 'external_ids',
                        'date_created', 'date_modified', 'data'  # Removed sync_updated_at (auto_now)
                    ],
                    unique_fields=['id']
                )
                
                # For bulk_create with update_conflicts, it's hard to distinguish 
                # between created and updated, so we'll count all as processed
                total_processed = len(objects)
                results['updated'] = total_processed  # Assume most are updates
                results['total_processed'] = total_processed
                
                logger.info(f"Bulk saved {total_processed} SalesRabbit users")
            
        except Exception as e:
            logger.error(f"Bulk save failed: {e}")
            results['failed'] = len(validated_records)
        
        return results
