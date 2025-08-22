"""
MarketSharp Marketing Source Map processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date

from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusMarketSharpMarketingSourceMapProcessor:
    """Processor for MarketSharp marketing source map data validation and transformation"""
    
    def __init__(self):
        self.validator = GeniusValidator()
    
    def process_marketsharp_marketing_source_maps(self, raw_data: List[tuple], field_mapping: List[str]) -> List[Dict[str, Any]]:
        """Process raw MarketSharp marketing source map data into validated dictionaries"""
        processed_records = []
        
        for row in raw_data:
            try:
                # Convert tuple to dictionary using field mapping
                record = dict(zip(field_mapping, row))
                
                # Validate and transform the record
                validated_record = self._validate_and_transform_record(record)
                if validated_record:
                    processed_records.append(validated_record)
                    
            except Exception as e:
                logger.error(f"Error processing MarketSharp marketing source map record: {e}")
                logger.error(f"Problematic record: {row}")
                continue
        
        logger.info(f"Processed {len(processed_records)} MarketSharp marketing source map records")
        return processed_records
    
    def _validate_and_transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and transform a single MarketSharp marketing source map record"""
        try:
            validated_record = {}
            
            # Required ID field
            if not self.validator.validate_id_field(record.get('id')):
                logger.error(f"Invalid ID for MarketSharp marketing source map: {record.get('id')}")
                return None
            validated_record['id'] = record['id']
            
            # Foreign key references (required)
            if not self.validator.validate_id_field(record.get('marketsharp_source_id')):
                logger.error(f"Invalid marketsharp_source_id for MarketSharp marketing source map: {record.get('marketsharp_source_id')}")
                return None
            validated_record['marketsharp_source_id'] = record['marketsharp_source_id']
            
            if not self.validator.validate_id_field(record.get('marketing_source_id')):
                logger.error(f"Invalid marketing_source_id for MarketSharp marketing source map: {record.get('marketing_source_id')}")
                return None
            validated_record['marketing_source_id'] = record['marketing_source_id']
            
            # Optional foreign key reference
            validated_record['prospect_source_id'] = record.get('prospect_source_id')
            
            # Priority (integer)
            priority = record.get('priority')
            if priority is not None:
                validated_record['priority'] = int(priority)
            else:
                validated_record['priority'] = 0  # Default priority
            
            # Active flag (boolean)
            active = record.get('active')
            if isinstance(active, (bool, int)):
                validated_record['active'] = bool(active)
            else:
                validated_record['active'] = True  # Default to active
            
            # Timestamps
            validated_record['created_at'] = self._validate_datetime(record.get('created_at'))
            validated_record['updated_at'] = self._validate_datetime(record.get('updated_at'))
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Error validating MarketSharp marketing source map record: {e}")
            return None
    
    def _validate_datetime(self, value: Any) -> Optional[datetime]:
        """Validate datetime field"""
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, date):
            return datetime.combine(value, datetime.min.time())
        try:
            # Try to parse string datetime
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            pass
        return None
