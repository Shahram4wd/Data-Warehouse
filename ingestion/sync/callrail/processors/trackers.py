"""
CallRail trackers data processor
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class TrackersProcessor(CallRailBaseProcessor):
    """Processor for CallRail trackers data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_Tracker
        super().__init__(model_class=CallRail_Tracker, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'name': 'name',
            'status': 'status',
            'type': 'type',
            'tracking_numbers': 'tracking_numbers',  # This is an array field
            'destination_number': 'destination_number',
            'whisper_message': 'whisper_message',
            'sms_enabled': 'sms_enabled',
            'sms_supported': 'sms_supported',
            'disabled_at': 'disabled_at',
            'company': 'company',  # JSON object
            'call_flow': 'call_flow',  # JSON object
            'source': 'source',  # JSON object
            'created_at': 'api_created_at',  # Map to api_created_at
            'updated_at': 'updated_at',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail tracker record to database format"""
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
            logger.error(f"Error transforming tracker record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed tracker record"""
        try:
            # Check required fields
            required_fields = ['id', 'name']
            for field in required_fields:
                if field not in record or record[field] is None:
                    logger.warning(f"Missing required field '{field}' in tracker record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid tracker ID (empty)")
                return False
            
            # Validate name is not empty
            if not str(record['name']).strip():
                logger.warning("Invalid tracker name (empty)")
                return False
            
            # Validate tracking_numbers array (optional but should be a list if present)
            if 'tracking_numbers' in record and record['tracking_numbers'] is not None:
                if not isinstance(record['tracking_numbers'], list):
                    logger.warning("Invalid tracking_numbers format (should be list)")
                    return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating tracker record: {e}")
            return False
