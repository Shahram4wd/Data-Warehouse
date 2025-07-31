"""
CallRail accounts data processor
"""
import logging
from typing import Dict, Any
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class AccountsProcessor(CallRailBaseProcessor):
    """Processor for CallRail accounts data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_Account
        super().__init__(model_class=CallRail_Account, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'name': 'name',
            'outbound_recording_enabled': 'outbound_recording_enabled',
            'hipaa_account': 'hipaa_account',
            'numeric_id': 'numeric_id',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail account record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle boolean fields
                    if source_field in ['outbound_recording_enabled', 'hipaa_account'] and value is not None:
                        value = bool(value)
                    
                    # Handle integer fields
                    elif source_field == 'numeric_id' and value is not None:
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            logger.warning(f"Invalid numeric_id format: {value}")
                            value = None
                    
                    transformed[target_field] = value
            
            # Ensure boolean fields have default values
            if 'outbound_recording_enabled' not in transformed or transformed['outbound_recording_enabled'] is None:
                transformed['outbound_recording_enabled'] = False
            if 'hipaa_account' not in transformed or transformed['hipaa_account'] is None:
                transformed['hipaa_account'] = False
                
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming account record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed account record"""
        try:
            # Check required fields
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in record or record[field] is None or record[field] == '':
                    logger.warning(f"Missing required field '{field}' in account record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid account ID (empty)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating account record: {e}")
            return False
