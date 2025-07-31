"""
CallRail users data processor
"""
import logging
from typing import Dict, Any
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class UsersProcessor(CallRailBaseProcessor):
    """Processor for CallRail users data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_User
        super().__init__(model_class=CallRail_User, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'email': 'email',
            'role': 'role',
            'permissions': 'permissions',
            'is_active': 'is_active',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail user record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle boolean fields
                    if source_field == 'is_active' and value is not None:
                        value = bool(value)
                    
                    # Handle JSON fields
                    elif source_field == 'permissions' and value is not None:
                        # Ensure permissions is a dict
                        if not isinstance(value, dict):
                            logger.warning(f"User permissions is not a dict: {type(value)}")
                            value = {}
                    
                    transformed[target_field] = value
            
            # Ensure required fields have default values
            if 'is_active' not in transformed or transformed['is_active'] is None:
                transformed['is_active'] = True
            if 'permissions' not in transformed or transformed['permissions'] is None:
                transformed['permissions'] = {}
                
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming user record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed user record"""
        try:
            # Check required fields
            required_fields = ['id', 'first_name', 'last_name', 'email']
            for field in required_fields:
                if field not in record or record[field] is None or record[field] == '':
                    logger.warning(f"Missing required field '{field}' in user record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid user ID (empty)")
                return False
            
            # Validate email format (basic check)
            email = record.get('email', '')
            if '@' not in email:
                logger.warning(f"Invalid email format: {email}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating user record: {e}")
            return False
