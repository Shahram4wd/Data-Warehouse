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
            
            # Required marketsharp_id field (varchar(128), should not be empty)
            marketsharp_id = record.get('marketsharp_id')
            if not marketsharp_id or str(marketsharp_id).strip() == '':
                logger.error(f"Invalid marketsharp_id for MarketSharp marketing source map: {marketsharp_id}")
                return None
            validated_record['marketsharp_id'] = str(marketsharp_id).strip()
            
            # Marketing source ID (int, can be NULL based on schema)
            marketing_source_id = record.get('marketing_source_id')
            if marketing_source_id is not None:
                validated_record['marketing_source_id'] = int(marketing_source_id)
            else:
                validated_record['marketing_source_id'] = None
            
            # Timestamps (can be NULL based on schema)
            validated_record['created_at'] = self._validate_datetime(record.get('created_at'))
            validated_record['updated_at'] = self._validate_datetime(record.get('updated_at'))
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Error validating MarketSharp marketing source map record: {e}")
            logger.error(f"Problematic record: {record}")
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
