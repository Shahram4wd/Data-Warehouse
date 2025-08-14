"""
Arrivy task status data processor
"""
import logging
from typing import Dict, Any
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class TaskStatusProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy task status data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_TaskStatus
        super().__init__(model_class=Arrivy_TaskStatus, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            'id': 'id',  # Primary key field
            'name': 'name',
            'description': 'description',
            'is_active': 'is_active',
            'created_time': 'created_time',
            'updated_time': 'updated_time'
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Arrivy task status record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Special handling for specific fields
                    if source_field in ['created', 'updated']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['is_active', 'is_default', 'is_final', 'allows_editing', 'auto_transition']:
                        value = bool(value) if value is not None else False
                    elif source_field in ['order']:
                        try:
                            value = int(value) if value is not None else 0
                        except (ValueError, TypeError):
                            value = 0
                    elif source_field in ['workflow_id']:
                        value = str(value) if value is not None else None
                    elif source_field in ['permissions', 'conditions', 'notifications']:
                        # Ensure these are stored as JSON-serializable data
                        if isinstance(value, (dict, list)):
                            pass  # Keep as is
                        elif isinstance(value, str):
                            try:
                                import json
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                value = [] if source_field in ['permissions', 'conditions'] else {}
                        else:
                            value = [] if source_field in ['permissions', 'conditions'] else {}
                    
                    transformed[target_field] = value
            
            # Ensure required fields
            if 'id' not in transformed:
                transformed['id'] = record.get('id')
            
            if 'name' not in transformed or not transformed['name']:
                transformed['name'] = f"Status {transformed.get('id', 'Unknown')}"
            
            # Set default values for important fields
            if 'status_type' not in transformed:
                transformed['status_type'] = record.get('type', 'task')
            
            if 'order' not in transformed:
                transformed['order'] = 0
            
            # Note: crm_source and raw_data fields don't exist in model
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming task status record: {e}")
            logger.error(f"Record: {record}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed task status record"""
        try:
            # Required field validation
            if not record.get('id'):
                raise ValueError("id is required")
                
            if not record.get('name'):
                raise ValueError("name is required")
            
            # Data type validation
            if 'id' in record:
                record['id'] = str(record['id'])
            
            # Ensure proper boolean values
            boolean_fields = ['is_active', 'is_default', 'is_final', 'allows_editing', 'auto_transition']
            for field in boolean_fields:
                if field in record:
                    record[field] = bool(record[field]) if record[field] is not None else False
            
            # Validate order field
            if record.get('order') is not None:
                try:
                    order_val = int(record['order'])
                    if order_val < 0:
                        logger.warning(f"Negative order value: {order_val}")
                        record['order'] = 0
                    else:
                        record['order'] = order_val
                except (ValueError, TypeError):
                    record['order'] = 0
            
            # Validate status_type
            valid_status_types = ['task', 'crew', 'system', 'workflow', 'custom']
            if record.get('status_type') and record['status_type'] not in valid_status_types:
                logger.warning(f"Unknown status_type: {record['status_type']}")
                # Keep the original value but log the warning
            
            # Validate datetime fields
            datetime_fields = ['created', 'updated']
            for field in datetime_fields:
                if record.get(field) and not hasattr(record[field], 'strftime'):
                    logger.warning(f"Invalid datetime for {field}: {record[field]}")
                    record[field] = None
            
            # Ensure string fields don't exceed reasonable lengths
            string_fields = ['name', 'description', 'color', 'status_type']
            for field in string_fields:
                if record.get(field) and len(str(record[field])) > 255:
                    record[field] = str(record[field])[:255]
                    logger.warning(f"Truncated {field} to 255 characters")
            
            # Validate JSON fields structure
            list_fields = ['permissions', 'conditions']
            for field in list_fields:
                if record.get(field) and not isinstance(record[field], list):
                    logger.warning(f"Converting {field} to list format")
                    record[field] = []
            
            dict_fields = ['notifications']
            for field in dict_fields:
                if record.get(field) and not isinstance(record[field], dict):
                    logger.warning(f"Converting {field} to dict format")
                    record[field] = {}
            
            return record
            
        except Exception as e:
            logger.error(f"Error validating task status record: {e}")
            raise
