"""
Arrivy bookings data processor
"""
import logging
from typing import Dict, Any, Optional
from dateutil import parser
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class BookingsProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy bookings data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_Booking
        super().__init__(model_class=Arrivy_Booking, **kwargs)
    
    def get_unique_field_name(self) -> str:
        """Bookings use id as the unique field (primary key)"""
        return 'id'
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            # Primary identification
            'id': 'id',  # Primary key field
            'url_safe_id': 'url_safe_id',
            'external_id': 'external_id',
            'title': 'title',
            'description': 'description',
            'details': 'details',
            
            # Audit trail
            'owner': 'owner',
            'created_by': 'created_by',
            'updated_by': 'updated_by',
            'created_by_user': 'created_by_user',
            'updated_by_user': 'updated_by_user',
            'created': 'created',
            'updated': 'updated',
            'created_time': 'created_time',
            'updated_time': 'updated_time',
            
            # Scheduling - datetime fields
            'start_datetime': 'start_datetime',
            'end_datetime': 'end_datetime',
            'start_datetime_original_iso_str': 'start_datetime_original_iso_str',
            'end_datetime_original_iso_str': 'end_datetime_original_iso_str',
            
            # Status and workflow
            'status': 'status',
            'status_id': 'status_id',
            'task_type': 'task_type',
            
            # Duration and timing
            'duration_estimate': 'duration_estimate',
            'actual_start_datetime': 'actual_start_datetime',
            'actual_end_datetime': 'actual_end_datetime',
            'timezone': 'timezone',
            
            # Boolean flags
            'is_recurring': 'is_recurring',
            'is_all_day': 'is_all_day',
            'enable_time_window_display': 'enable_time_window_display',
            'unscheduled': 'unscheduled',
            
            # Customer information
            'customer_id': 'customer_id',
            'customer_name': 'customer_name',
            'customer_first_name': 'customer_first_name',
            'customer_last_name': 'customer_last_name',
            'customer_company_name': 'customer_company_name',
            'customer_email': 'customer_email',
            'customer_phone': 'customer_phone',
            'customer_mobile_number': 'customer_mobile_number',
            'customer_notes': 'customer_notes',
            'customer_timezone': 'customer_timezone',
            
            # Address information
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
            
            # Team and resource assignment
            'assigned_team_members': 'assigned_team_members',
            'team_member_ids': 'team_member_ids',
            'entity_ids': 'entity_ids',
            'crew_ids': 'crew_ids',
            'worker_ids': 'worker_ids',
            'number_of_workers_required': 'number_of_workers_required',
            'resource_ids': 'resource_ids',
            
            # Template and configuration
            'template_id': 'template_id',
            'template': 'template',
            'template_extra_fields': 'template_extra_fields',
            'extra_fields': 'extra_fields',
            'custom_fields': 'custom_fields',
            
            # Group and organizational
            'group': 'group',
            'group_id': 'group_id',
            
            # External integration
            'external_type': 'external_type',
            'external_resource_type': 'external_resource_type',
            'linked_internal_ref': 'linked_internal_ref',
            'linked_external_ref': 'linked_external_ref',
            'is_linked': 'is_linked',
            
            # Routing and navigation
            'route_id': 'route_id',
            'route_name': 'route_name',
            'internal_route_id': 'internal_route_id',
            'routes': 'routes',
            'entity_routes': 'entity_routes',
            'additional_addresses': 'additional_addresses',
            'current_destination': 'current_destination',
            
            # Communication and notifications
            'notifications': 'notifications',
            'outbound_sms_count': 'outbound_sms_count',
            'inbound_sms_count': 'inbound_sms_count',
            'outbound_email_count': 'outbound_email_count',
            'inbound_email_count': 'inbound_email_count',
            
            # Performance and tracking
            'rating': 'rating',
            'rating_text': 'rating_text',
            'travel_time': 'travel_time',
            'wait_time': 'wait_time',
            'task_time': 'task_time',
            'total_time': 'total_time',
            'mileage': 'mileage',
            
            # Documents and files
            'document_ids': 'document_ids',
            'file_ids': 'file_ids',
            'files': 'files',
            'forms': 'forms',
            
            # Instructions and workflow
            'instructions': 'instructions',
            
            # Additional tracking
            'items': 'items',
            'entity_confirmation_statuses': 'entity_confirmation_statuses',
        }
    
    def transform_record(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single booking record from API format to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in raw_data:
                    value = raw_data[source_field]
                    
                    # Special handling for specific fields
                    if source_field in ['created', 'updated', 'created_time', 'updated_time']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['start_datetime', 'end_datetime', 'actual_start_datetime', 'actual_end_datetime']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['customer_email']:
                        value = self.normalize_email(value)
                    elif source_field in ['customer_phone', 'customer_mobile_number']:
                        value = self.normalize_phone(value)
                    elif source_field in ['duration_estimate']:
                        value = self.normalize_integer(value)
                    elif source_field in ['latitude', 'longitude', 'rating', 'mileage']:
                        value = self.normalize_float(value)
                    elif source_field in ['is_recurring', 'is_all_day', 'enable_time_window_display', 'unscheduled', 
                                         'is_address_geo_coded', 'use_lat_lng_address', 'is_linked']:
                        value = self.normalize_boolean(value)
                    
                    transformed[target_field] = value
            
            # Handle field mappings that don't exist in booking configurations but use alternatives
            # Map 'name' to 'title' if title doesn't exist
            if 'title' not in transformed and 'name' in raw_data:
                transformed['title'] = raw_data['name']
            
            # Map template to template_id if needed  
            if 'template_id' not in transformed and 'template' in raw_data:
                transformed['template_id'] = str(raw_data['template'])
                
            # Map time_zone to timezone
            if 'timezone' not in transformed and 'time_zone' in raw_data:
                transformed['timezone'] = raw_data['time_zone']
                
            # Extract derived date/time fields from datetime fields
            if 'start_datetime' in transformed and transformed['start_datetime']:
                try:
                    from dateutil import parser
                    start_dt = parser.parse(transformed['start_datetime']) if isinstance(transformed['start_datetime'], str) else transformed['start_datetime']
                    transformed['start_date'] = start_dt.date()
                    transformed['start_time'] = start_dt.time()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse start_datetime: {transformed['start_datetime']}: {e}")
                    
            if 'end_datetime' in transformed and transformed['end_datetime']:
                try:
                    from dateutil import parser
                    end_dt = parser.parse(transformed['end_datetime']) if isinstance(transformed['end_datetime'], str) else transformed['end_datetime']
                    transformed['end_date'] = end_dt.date()
                    transformed['end_time'] = end_dt.time()
                except (ValueError, TypeError) as e:
                    logger.warning(f"Failed to parse end_datetime: {transformed['end_datetime']}: {e}")
            
            # Extract latitude/longitude from exact_location
            if 'exact_location' in transformed and transformed['exact_location']:
                location = transformed['exact_location']
                if isinstance(location, dict):
                    transformed['latitude'] = location.get('lat')
                    transformed['longitude'] = location.get('lng')
                elif isinstance(location, list) and len(location) >= 2:
                    transformed['latitude'] = location[1]  # lat is usually second
                    transformed['longitude'] = location[0]  # lng is usually first
                    
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming booking record {raw_data.get('id', 'unknown')}: {str(e)}")
            logger.debug(f"Raw booking data: {raw_data}")
            raise
    
    def get_unique_value(self, record: Dict[str, Any]) -> str:
        """Get the unique identifier value for a booking record"""
        return str(record.get('id', ''))
    
    def validate_record(self, record: Dict[str, Any]) -> bool:
        """Validate that a booking record has required fields"""
        # Booking must have an ID
        if not record.get('id'):
            logger.warning("Booking record missing required 'id' field")
            return False
            
        return True
            
        return True
    
    def normalize_integer(self, value) -> Optional[int]:
        """Normalize integer values"""
        if value is None or value == '':
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
    
    def normalize_float(self, value) -> Optional[float]:
        """Normalize float values"""
        if value is None or value == '':
            return None
        try:
            return float(value)
        except (ValueError, TypeError):
            return None
    
    def normalize_boolean(self, value) -> bool:
        """Normalize boolean values"""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        if isinstance(value, (int, float)):
            return bool(value)
        return False
