"""
Base processor for CallRail CRM integration
"""
import logging
from typing import Dict, Any, Optional
from ingestion.base.processor import BaseDataProcessor

logger = logging.getLogger(__name__)


class CallRailBaseProcessor(BaseDataProcessor):
    """Base processor for CallRail data transformation and validation"""
    
    def __init__(self, model_class=None, **kwargs):
        """Initialize CallRail base processor"""
        super().__init__(model_class, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from CallRail to database fields"""
        return {}
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a CallRail record to database format
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement transform_record")
        
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a transformed record
        Must be implemented by subclasses
        """
        raise NotImplementedError("Subclasses must implement validate_record")
        
    def get_record_id(self, record: Dict[str, Any]) -> str:
        """Get the unique identifier for a record"""
        return str(record.get('id', ''))
        
    def get_record_timestamp(self, record: Dict[str, Any]) -> Optional[str]:
        """Get the timestamp for a record - override in subclasses"""
        return record.get('created_at') or record.get('updated_at')
