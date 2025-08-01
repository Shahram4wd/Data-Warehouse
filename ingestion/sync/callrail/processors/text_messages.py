"""
CallRail text messages data processor
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class TextMessagesProcessor(CallRailBaseProcessor):
    """Processor for CallRail text messages data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_TextMessage
        super().__init__(model_class=CallRail_TextMessage, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'company_id': 'company_id',
            'direction': 'direction',
            'tracking_phone_number': 'tracking_phone_number',
            'customer_phone_number': 'customer_phone_number',
            'message': 'message',
            'sent_at': 'sent_at',
            'status': 'status',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail text message record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle datetime fields
                    if source_field == 'sent_at' and value:
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
            logger.error(f"Error transforming text message record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed text message record"""
        try:
            # Check required fields
            required_fields = ['id', 'direction', 'tracking_phone_number', 'customer_phone_number', 'message', 'sent_at']
            for field in required_fields:
                if field not in record or record[field] is None:
                    logger.warning(f"Missing required field '{field}' in text message record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid text message ID (empty)")
                return False
            
            # Validate direction
            valid_directions = ['inbound', 'outbound']
            if record['direction'] not in valid_directions:
                logger.warning(f"Invalid direction '{record['direction']}' (must be one of {valid_directions})")
                return False
            
            # Validate sent_at is a datetime
            if not isinstance(record['sent_at'], datetime):
                logger.warning("Invalid sent_at (not datetime)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating text message record: {e}")
            return False
