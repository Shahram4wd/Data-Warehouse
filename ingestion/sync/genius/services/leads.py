"""
Lead-specific service implementation for Genius CRM sync
"""
from typing import Dict, Any, List, Optional, Tuple
from decimal import Decimal
from datetime import datetime
import logging

from ..services.base import GeniusBaseService
from ..config.leads import GeniusLeadSyncConfig
from ingestion.models import Genius_Lead


logger = logging.getLogger(__name__)


class GeniusLeadService(GeniusBaseService):
    """Service layer for Genius Lead business logic"""
    
    def __init__(self):
        self.config = GeniusLeadSyncConfig()
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Get field mappings for this entity type"""
        return self.config.FIELD_MAPPINGS
    
    def get_bulk_update_fields(self) -> List[str]:
        """Get fields that should be included in bulk updates"""
        return self.config.BULK_UPDATE_FIELDS
    
    def validate_record(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate raw lead data before processing
        
        Args:
            raw_data: Raw data from source system
            
        Returns:
            Validated data dict or None if invalid
        """
        # Skip None or empty records
        if not raw_data or not raw_data.get('lead_id'):
            return None
        
        # Apply business rules
        if self.config.SKIP_DUMMY_RECORDS:
            # Skip dummy or test records
            first_name = raw_data.get('first_name', '').lower()
            last_name = raw_data.get('last_name', '').lower()
            email = raw_data.get('email', '').lower()
            
            dummy_patterns = ['test', 'dummy', 'example', 'sample']
            if any(pattern in name for pattern in dummy_patterns 
                   for name in [first_name, last_name, email]):
                logger.debug(f"Skipping dummy record: {raw_data.get('lead_id')}")
                return None
        
        # Validate required contact info if configured
        if self.config.REQUIRE_CONTACT_INFO:
            email = raw_data.get('email')
            phone = raw_data.get('phone')
            if not email and not phone:
                logger.debug(f"Skipping record without contact info: {raw_data.get('lead_id')}")
                return None
        
        return raw_data
    
    def transform_record(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform validated data to model format
        
        Args:
            validated_data: Data that passed validation
            
        Returns:
            Transformed data ready for model creation
        """
        transformed = {}
        
        # Apply field mappings
        for source_field, dest_field in self.config.FIELD_MAPPINGS.items():
            if source_field in validated_data:
                value = validated_data[source_field]
                transformed[dest_field] = self._transform_field_value(
                    dest_field, value, source_field
                )
        
        # Add metadata
        now = datetime.now()
        if 'sync_updated_at' not in transformed:
            transformed['sync_updated_at'] = now
        
        return transformed
    
    def _transform_field_value(self, dest_field: str, value: Any, source_field: str) -> Any:
        """
        Transform individual field values
        
        Args:
            dest_field: Destination field name
            value: Raw field value
            source_field: Source field name
            
        Returns:
            Transformed value
        """
        if value is None:
            return None
        
        # Handle string fields with length limits
        if dest_field in self.config.FIELD_LIMITS:
            if isinstance(value, str):
                max_length = self.config.FIELD_LIMITS[dest_field]
                value = value[:max_length] if len(value) > max_length else value
        
        # Handle specific field transformations
        if dest_field == 'lead_id':
            # Ensure lead_id is an integer
            try:
                return int(value) if value else None
            except (ValueError, TypeError):
                logger.warning(f"Invalid lead_id format: {value}")
                return None
        
        elif dest_field in ['source', 'added_by', 'division_id', 'copied_to_id']:
            # Handle ID fields that might be empty strings
            try:
                return int(value) if value not in [None, '', '0'] else None
            except (ValueError, TypeError):
                return None
        
        elif dest_field in ['added_on', 'updated_at']:
            # Handle datetime fields
            if isinstance(value, str):
                try:
                    # Parse ISO format or other common formats
                    return datetime.fromisoformat(value.replace('Z', '+00:00'))
                except (ValueError, TypeError):
                    logger.warning(f"Invalid datetime format for {dest_field}: {value}")
                    return None
            return value
        
        # Default: return value as-is
        return value
    
    def prepare_bulk_data(self, transformed_records: List[Dict[str, Any]]) -> Tuple[List[Genius_Lead], List[Dict[str, Any]]]:
        """
        Prepare data for bulk operations
        
        Args:
            transformed_records: List of transformed record dicts
            
        Returns:
            Tuple of (objects_for_create, data_for_update)
        """
        objects_for_create = []
        data_for_update = []
        
        for record_data in transformed_records:
            try:
                # Create Lead object for bulk_create
                lead_obj = Genius_Lead(**record_data)
                objects_for_create.append(lead_obj)
                
                # Prepare data dict for bulk_update
                update_data = {
                    field: record_data.get(field)
                    for field in self.config.BULK_UPDATE_FIELDS
                    if field in record_data
                }
                update_data['lead_id'] = record_data['lead_id']  # Always include PK
                data_for_update.append(update_data)
                
            except Exception as e:
                logger.error(f"Error preparing bulk data for lead {record_data.get('lead_id')}: {e}")
                continue
        
        return objects_for_create, data_for_update
    
    def get_chunk_size(self) -> int:
        """Get optimal chunk size for this entity type"""
        return self.config.DEFAULT_CHUNK_SIZE
    
    def get_bulk_batch_size(self) -> int:
        """Get optimal bulk operation batch size"""
        return self.config.BULK_BATCH_SIZE
