"""
Arrivy groups data processor
"""
import logging
from typing import Dict, Any
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class GroupsProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy groups (locations/divisions) data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_Group
        super().__init__(model_class=Arrivy_Group, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            'id': 'id',  # Primary key field
            'url_safe_id': 'url_safe_id',
            'owner': 'owner',
            'name': 'name',
            'description': 'description',
            'email': 'email',
            'phone': 'phone',
            'mobile_number': 'mobile_number',
            'website': 'website',
            'emergency': 'emergency',
            'address_line_1': 'address_line_1',
            'address_line_2': 'address_line_2',
            'complete_address': 'complete_address',
            'city': 'city',
            'state': 'state',
            'country': 'country',
            'zipcode': 'zipcode',
            'exact_location': 'exact_location',
            'use_lat_lng_address': 'use_lat_lng_address',
            'is_address_geo_coded': 'is_address_geo_coded',
            'timezone': 'timezone',
            'image_id': 'image_id',
            'image_path': 'image_path',
            'is_default': 'is_default',
            'is_disabled': 'is_disabled',
            'is_implicit': 'is_implicit',
            'social_links': 'social_links',
            'additional_addresses': 'additional_addresses',
            'territory_ids': 'territory_ids',
            'extra_fields': 'extra_fields',
            'created_by': 'created_by',
            'created': 'created',
            'updated': 'updated'
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Arrivy group record to database format"""
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
                    elif source_field in ['email']:
                        value = self.normalize_email(value)
                    elif source_field in ['phone', 'mobile_number']:
                        value = self.normalize_phone(value)
                    elif source_field in ['latitude', 'longitude']:
                        try:
                            value = float(value) if value is not None else None
                        except (ValueError, TypeError):
                            value = None
                    elif source_field in ['use_lat_lng_address', 'is_address_geo_coded']:
                        value = bool(value) if value is not None else False
                    elif source_field in ['owner', 'created_by']:
                        value = str(value) if value is not None else None
                    elif source_field == 'exact_location':
                        # Handle JSON/dict data
                        if isinstance(value, dict):
                            pass  # Keep as dict
                        elif isinstance(value, str):
                            try:
                                import json
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                value = None
                        else:
                            value = None
                    
                    transformed[target_field] = value
            
            # Ensure required fields
            if 'id' not in transformed:
                transformed['id'] = record.get('id')
            
            if 'name' not in transformed or not transformed['name']:
                transformed['name'] = f"Group {transformed.get('id', 'Unknown')}"
            
            # Note: crm_source and raw_data fields don't exist in model
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming group record: {e}")
            logger.error(f"Record: {record}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed group record"""
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
            boolean_fields = ['use_lat_lng_address', 'is_address_geo_coded', 'is_default', 'is_disabled', 'is_implicit']
            for field in boolean_fields:
                if field in record:
                    record[field] = bool(record[field]) if record[field] is not None else False
            
            # Validate coordinates
            for coord_field in ['latitude', 'longitude']:
                if record.get(coord_field) is not None:
                    try:
                        coord_value = float(record[coord_field])
                        # Basic coordinate range validation
                        if coord_field == 'latitude' and not (-90 <= coord_value <= 90):
                            logger.warning(f"Invalid latitude value: {coord_value}")
                            record[coord_field] = None
                        elif coord_field == 'longitude' and not (-180 <= coord_value <= 180):
                            logger.warning(f"Invalid longitude value: {coord_value}")
                            record[coord_field] = None
                        else:
                            record[coord_field] = coord_value
                    except (ValueError, TypeError):
                        record[coord_field] = None
            
            # Validate email format if present
            if record.get('email') and '@' not in record['email']:
                logger.warning(f"Invalid email format: {record['email']}")
                record['email'] = None
            
            # Ensure string fields don't exceed reasonable lengths
            string_fields = ['name', 'description', 'address_line_1', 'address_line_2', 'city', 'state', 'country']
            for field in string_fields:
                if record.get(field) and len(str(record[field])) > 255:
                    record[field] = str(record[field])[:255]
                    logger.warning(f"Truncated {field} to 255 characters")
            
            return record
            
        except Exception as e:
            logger.error(f"Error validating group record: {e}")
            raise
