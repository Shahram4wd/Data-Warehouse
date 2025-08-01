"""
CallRail calls data processor
"""
import logging
from typing import Dict, Any
from datetime import datetime
from .base import CallRailBaseProcessor

logger = logging.getLogger(__name__)


class CallsProcessor(CallRailBaseProcessor):
    """Processor for CallRail calls data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.callrail import CallRail_Call
        super().__init__(model_class=CallRail_Call, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail API to database fields"""
        return {
            'id': 'id',
            'answered': 'answered',
            'business_phone_number': 'business_phone_number',
            'customer_city': 'customer_city',
            'customer_country': 'customer_country',
            'customer_name': 'customer_name',
            'customer_phone_number': 'customer_phone_number',
            'customer_state': 'customer_state',
            'direction': 'direction',
            'duration': 'duration',
            'start_time': 'start_time',
            'tracking_phone_number': 'tracking_phone_number',
            'voicemail': 'voicemail',
            'company_id': 'company_id',
            'created_at': 'created_at',
            'updated_at': 'updated_at',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CallRail call record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Handle datetime fields
                    if source_field in ['start_time', 'created_at', 'updated_at'] and value:
                        if isinstance(value, str):
                            try:
                                # Parse ISO datetime string
                                value = datetime.fromisoformat(value.replace('Z', '+00:00'))
                            except ValueError:
                                logger.warning(f"Invalid datetime format: {value}")
                                value = None
                    
                    # Handle duration field (ensure it's an integer)
                    elif source_field == 'duration' and value is not None:
                        try:
                            value = int(value)
                        except (ValueError, TypeError):
                            value = 0
                    
                    # Handle boolean fields
                    elif source_field in ['answered', 'voicemail'] and value is not None:
                        value = bool(value)
                    
                    transformed[target_field] = value
            
            # Ensure required fields have default values
            if 'duration' not in transformed or transformed['duration'] is None:
                transformed['duration'] = 0
            if 'answered' not in transformed or transformed['answered'] is None:
                transformed['answered'] = False
            if 'voicemail' not in transformed or transformed['voicemail'] is None:
                transformed['voicemail'] = False
                
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming call record {record.get('id', 'unknown')}: {e}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate transformed call record"""
        try:
            # Check required fields
            required_fields = ['id', 'start_time', 'duration']
            for field in required_fields:
                if field not in record or record[field] is None:
                    logger.warning(f"Missing required field '{field}' in call record")
                    return False
            
            # Validate ID format
            if not str(record['id']).strip():
                logger.warning("Invalid call ID (empty)")
                return False
            
            # Validate duration is non-negative
            if record['duration'] < 0:
                logger.warning(f"Invalid duration {record['duration']} (negative)")
                return False
            
            # Validate start_time is a datetime
            if not isinstance(record['start_time'], datetime):
                logger.warning("Invalid start_time (not datetime)")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"Error validating call record: {e}")
            return False
