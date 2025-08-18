"""
Base processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

logger = logging.getLogger(__name__)

class GeniusBaseProcessor:
    """Base processor for Genius CRM data transformation and validation"""
    
    def __init__(self, model_class):
        self.model_class = model_class
    
    def convert_timezone_aware(self, dt: datetime) -> datetime:
        """Convert naive datetime to timezone-aware"""
        if dt and dt.tzinfo is None:
            return timezone.make_aware(dt, timezone.get_current_timezone())
        return dt
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate record data - override in subclasses"""
        return record_data
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw database tuple to dictionary"""
        if len(raw_data) != len(field_mapping):
            raise ValueError(f"Row has {len(raw_data)} columns, expected {len(field_mapping)}")
        
        # Create dictionary from tuple and field mapping
        record = {}
        for i, field_name in enumerate(field_mapping):
            record[field_name] = raw_data[i]
        
        return record
