"""
Arrivy entities (crew members) data processor
"""
import logging
from typing import Dict, Any
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class EntitiesProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy entities (crew members) data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_Entity
        super().__init__(model_class=Arrivy_Entity, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            'id': 'id',  # Primary key field
            'name': 'name', 
            'username': 'username',
            'type': 'type',
            'external_id': 'external_id',
            'external_type': 'external_type',
            'email': 'email',
            'phone': 'phone',
            'image_id': 'image_id',
            'image_path': 'image_path',
            'color': 'color',
            'url_safe_id': 'url_safe_id',
            'is_active': 'is_active',
            'is_disabled': 'is_disabled',
            'is_default': 'is_default',
            'user_type': 'user_type',
            'invite_status': 'invite_status',
            'group_id': 'group_id',
            'owner': 'owner',
            'additional_group_ids': 'additional_group_ids',
            'address_line_1': 'address_line_1',
            'address_line_2': 'address_line_2',
            'city': 'city',
            'state': 'state',
            'country': 'country',
            'zipcode': 'zipcode',
            'complete_address': 'complete_address',
            'exact_location': 'exact_location',
            'is_address_geo_coded': 'is_address_geo_coded',
            'use_lat_lng_address': 'use_lat_lng_address',
            'allow_login_in_kiosk_mode_only': 'allow_login_in_kiosk_mode_only',
            'can_turnoff_location': 'can_turnoff_location',
            'can_view_customers_of_all_groups': 'can_view_customers_of_all_groups',
            'is_status_priority_notifications_disabled': 'is_status_priority_notifications_disabled',
            'is_included_in_billing': 'is_included_in_billing',
            'force_stop_billing': 'force_stop_billing',
            # New management permissions
            'can_manage_resources': 'can_manage_resources',
            'can_manage_crews': 'can_manage_crews', 
            'can_manage_entities': 'can_manage_entities',
            'skill_ids': 'skill_ids',
            'skill_details': 'skill_details',
            'details': 'details',
            'extra_fields': 'extra_fields',
            'visible_bookings': 'visible_bookings',
            'visible_routing_forms': 'visible_routing_forms',
            'notifications': 'notifications',
            'allow_status_notifications': 'allow_status_notifications',
            'permission_groups': 'permission_groups',
            'template_id': 'template_id',
            'template_extra_fields': 'template_extra_fields',
            # Email invitation data
            'email_invitation': 'email_invitation',
            'created_by': 'created_by',
            'created_by_user': 'created_by_user',
            'updated_by': 'updated_by',
            'updated_by_user': 'updated_by_user',
            'joined_datetime': 'joined_datetime',
            # API timestamp fields
            'created': 'created',
            'updated': 'updated',
            # Last reading (API field is 'lastreading', model field is 'last_reading') 
            'lastreading': 'last_reading',
            'okta_user_id': 'okta_user_id'
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Arrivy entity record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Special handling for specific fields
                    if source_field in ['created', 'updated', 'joined_datetime']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['email']:
                        value = self.normalize_email(value)
                    elif source_field in ['phone', 'mobile_number']:
                        value = self.normalize_phone(value)
                    elif source_field in ['skills', 'extra_fields']:
                        # Ensure these are stored as JSON-serializable data
                        if not isinstance(value, (dict, list)):
                            value = str(value) if value else None
                    elif source_field == 'is_active':
                        value = bool(value) if value is not None else True
                    
                    transformed[target_field] = value
            
            # Ensure required fields
            if 'id' not in transformed:
                transformed['id'] = record.get('id')
            
            if 'name' not in transformed or not transformed['name']:
                # Try to construct name from first/last name
                first_name = record.get('first_name', '').strip()
                last_name = record.get('last_name', '').strip()
                if first_name or last_name:
                    transformed['name'] = f"{first_name} {last_name}".strip()
                else:
                    transformed['name'] = f"Entity {transformed.get('id', 'Unknown')}"
            
            # Note: crm_source and raw_data fields don't exist in model
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming entity record: {e}")
            logger.error(f"Record: {record}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed entity record"""
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
            boolean_fields = ['is_active', 'is_disabled', 'is_default']
            for field in boolean_fields:
                if field in record:
                    record[field] = bool(record[field]) if record[field] is not None else None
            
            # Validate email format if present
            if record.get('email') and '@' not in record['email']:
                logger.warning(f"Invalid email format: {record['email']}")
                record['email'] = None
            
            # Ensure string fields don't exceed reasonable lengths
            string_fields = ['name', 'address_line_1', 'address_line_2', 'city', 'state', 'country']
            for field in string_fields:
                if record.get(field) and len(str(record[field])) > 255:
                    record[field] = str(record[field])[:255]
                    logger.warning(f"Truncated {field} to 255 characters")
            
            return record
            
        except Exception as e:
            logger.error(f"Error validating entity record: {e}")
            raise
