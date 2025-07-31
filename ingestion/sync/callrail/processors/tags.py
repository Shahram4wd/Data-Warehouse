"""
CallRail tags data processor
"""
import logging
from typing import Dict, Any
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class TagsProcessor(CallRailBaseProcessor):
    """Processor for CallRail tags data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_Tag
        super().__init__(model_class=CallRail_Tag, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'name': 'name',
            'color': 'color',
            'company_id': 'company_id',
            'configuration': 'configuration',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail tag record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle JSON fields
                    if source_field == 'configuration' and value is not None:
                        # Ensure configuration is a dict
                        if not isinstance(value, dict):
                            logger.warning(f"Tag configuration is not a dict: {type(value)}")
                            value = {}
                    
                    transformed[target_field] = value
            
            # Ensure configuration has default value
            if 'configuration' not in transformed or transformed['configuration'] is None:
                transformed['configuration'] = {}
                
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming tag record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed tag record"""
        try:
            # Check required fields
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in record or record[field] is None or record[field] == '':
                    logger.warning(f"Missing required field '{field}' in tag record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid tag ID (empty)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating tag record: {e}")
            return False
