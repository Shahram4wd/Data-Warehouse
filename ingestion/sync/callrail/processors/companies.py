"""
CallRail companies data processor
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class CompaniesProcessor(CallRailBaseProcessor):
    """Processor for CallRail companies data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_Company
        super().__init__(model_class=CallRail_Company, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'name': 'name',
            'status': 'status',
            'time_zone': 'time_zone',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
            'account_id': 'account_id',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail company record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle datetime fields
                    if source_field in ['created_at', 'updated_at'] and value:
                        if isinstance(value, str):
                            try:
                                # Parse ISO datetime string
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except ValueError:
                                logger.warning(f"Invalid datetime format: {value}")
                                value = None
                    
                    transformed[target_field] = value
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming company record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed company record"""
        try:
            # Check required fields
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in record or record[field] is None:
                    logger.warning(f"Missing required field '{field}' in company record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid company ID (empty)")
                return False
            
            # Validate name is not empty
            if not str(record['name']).strip():
                logger.warning("Invalid company name (empty)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating company record: {e}")
            return False
