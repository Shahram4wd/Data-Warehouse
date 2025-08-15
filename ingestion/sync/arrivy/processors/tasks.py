"""
Arrivy tasks (bookings) data processor
"""
import logging
from typing import Dict, Any
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class TasksProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy tasks/bookings data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_Task
        super().__init__(model_class=Arrivy_Task, **kwargs)
    
    def get_unique_field_name(self) -> str:
        """Tasks use id as the unique field (primary key)"""
        return 'id'
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            # Primary identification
            'id': 'id',  # Primary key field
            'url_safe_id': 'url_safe_id',
            'title': 'title',
            'details': 'details',
            
            # Audit trail
            'owner': 'owner',
            'created_by': 'created_by',
            'updated_by': 'updated_by',
            'created_by_user': 'created_by_user',
            'updated_by_user': 'updated_by_user',
            'created': 'created',
            'updated': 'updated',
            
            # Scheduling - datetime fields
            'start_datetime': 'start_datetime',
            'start_datetime_original_iso_str': 'start_datetime_original_iso_str',
            'start_datetime_timezone': 'start_datetime_timezone',
            'end_datetime': 'end_datetime',
            'end_datetime_original_iso_str': 'end_datetime_original_iso_str',
            'end_datetime_timezone': 'end_datetime_timezone',
            'due_datetime': 'due_datetime',
            'due_datetime_original_iso_str': 'due_datetime_original_iso_str',
            
            # Status and workflow
            'status': 'status',
            'status_title': 'status_title',
            'template_type': 'template_type',
            'duration': 'duration',
            'unscheduled': 'unscheduled',
            'self_scheduling': 'self_scheduling',
            
            # Customer information
            'customer_id': 'customer_id',
            'customer_name': 'customer_name',
            'customer_first_name': 'customer_first_name',
            'customer_last_name': 'customer_last_name',
            'customer_company_name': 'customer_company_name',
            'customer_notes': 'customer_notes',
            'customer_timezone': 'customer_timezone',
            
            # Customer contact information
            'customer_email': 'customer_email',
            'customer_phone': 'customer_phone',
            'customer_mobile_number': 'customer_mobile_number',
            
            # Customer address
            'customer_address_line_1': 'customer_address_line_1',
            'customer_address_line_2': 'customer_address_line_2',
            'customer_address': 'customer_address',
            'customer_city': 'customer_city',
            'customer_state': 'customer_state',
            'customer_country': 'customer_country',
            'customer_zipcode': 'customer_zipcode',
            'customer_exact_location': 'customer_exact_location',
            'is_customer_address_geo_coded': 'is_customer_address_geo_coded',
            'use_lat_lng_address': 'use_lat_lng_address',
            
            # Assignment and resources
            'entity_ids': 'entity_ids',
            'crew_ids': 'crew_ids',
            'worker_ids': 'worker_ids',
            'number_of_workers_required': 'number_of_workers_required',
            'resource_ids': 'resource_ids',
            
            # External integration
            'external_type': 'external_type',
            'external_resource_type': 'external_resource_type',
            'linked_internal_ref': 'linked_internal_ref',
            'linked_external_ref': 'linked_external_ref',
            'is_linked': 'is_linked',
            
            # Supply and logistics
            'is_supply_provided_locked': 'is_supply_provided_locked',
            'is_supply_returned_locked': 'is_supply_returned_locked',
            
            # Routing and navigation
            'route_id': 'route_id',
            'internal_route_id': 'internal_route_id',
            'routes': 'routes',
            'entity_routes': 'entity_routes',
            'mileage': 'mileage_data',  # Map to new field name
            'additional_addresses': 'additional_addresses',
            'current_destination': 'current_destination',
            
            # Time tracking
            'travel_time': 'travel_time',
            'wait_time': 'wait_time',
            'task_time': 'task_time',
            'total_time': 'total_time',
            
            # Performance metrics
            'rating': 'rating',
            'rating_text': 'rating_text',
            
            # Communication tracking
            'outbound_sms_count': 'outbound_sms_count',
            'inbound_sms_count': 'inbound_sms_count',
            'outbound_email_count': 'outbound_email_count',
            'inbound_email_count': 'inbound_email_count',
            
            # Documents and files
            'document_ids': 'document_ids',
            'file_ids': 'file_ids',
            'files': 'files',
            'forms': 'forms',
            
            # Additional data
            'extra_fields': 'extra_fields',
            'template_extra_fields': 'template_extra_fields',
            'entity_confirmation_statuses': 'entity_confirmation_statuses',
            'items': 'items',
            'series_id': 'series_id',
            'skill_details': 'skill_details',
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Arrivy task record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Special handling for specific fields
                    if source_field in ['created', 'updated', 'start_datetime', 'end_datetime', 'due_datetime']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['email', 'customer_email']:
                        value = self.normalize_email(value)
                    elif source_field in ['phone', 'mobile_number']:
                        value = self.normalize_phone(value)
                    elif source_field == 'duration':
                        try:
                            value = int(value) if value is not None else None
                        except (ValueError, TypeError):
                            value = None
                    elif source_field in ['owner', 'created_by', 'updated_by', 'customer_id', 'linked_internal_ref']:
                        value = str(value) if value is not None else None
                    elif source_field in ['is_customer_address_geo_coded', 'use_lat_lng_address', 'is_linked', 
                                        'is_supply_provided_locked', 'is_supply_returned_locked', 'unscheduled', 'self_scheduling']:
                        value = bool(value) if value is not None else False
                    elif source_field in ['entity_ids', 'crew_ids', 'worker_ids', 'resource_ids', 'document_ids', 
                                        'file_ids', 'files', 'forms', 'routes', 'entity_routes', 'mileage', 
                                        'additional_addresses', 'current_destination', 'extra_fields', 
                                        'template_extra_fields', 'entity_confirmation_statuses', 'items', 
                                        'skill_details', 'customer_exact_location']:
                        # Handle JSON/array fields
                        if isinstance(value, (dict, list)):
                            pass  # Keep as is
                        elif isinstance(value, str):
                            try:
                                import json
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                value = None
                        else:
                            value = None
                    elif source_field == 'customer_exact_location':
                        # Extract lat/lng for legacy fields
                        if isinstance(value, dict) and 'lat' in value and 'lng' in value:
                            transformed['latitude'] = value.get('lat')
                            transformed['longitude'] = value.get('lng')
                    
                    # Avoid overwriting the same field multiple times
                    if target_field not in transformed:
                        transformed[target_field] = value
            
            # Ensure required fields
            if 'id' not in transformed:
                transformed['id'] = record.get('id')
            
            # Legacy field population for backward compatibility
            if 'task_id' not in transformed:
                transformed['task_id'] = record.get('id')
                
            if 'task_title' not in transformed:
                transformed['task_title'] = record.get('title')
            
            # Legacy customer fields
            if 'first_name' not in transformed:
                transformed['first_name'] = record.get('customer_first_name')
            if 'last_name' not in transformed:
                transformed['last_name'] = record.get('customer_last_name')
            if 'email' not in transformed:
                transformed['email'] = record.get('customer_email')
            if 'mobile_number' not in transformed:
                transformed['mobile_number'] = record.get('customer_mobile_number')
            if 'address' not in transformed:
                transformed['address'] = record.get('customer_address')
            if 'city' not in transformed:
                transformed['city'] = record.get('customer_city')
            if 'state' not in transformed:
                transformed['state'] = record.get('customer_state')
            if 'zipcode' not in transformed:
                transformed['zipcode'] = record.get('customer_zipcode')
            if 'country' not in transformed:
                transformed['country'] = record.get('customer_country')
            if 'created_on' not in transformed:
                transformed['created_on'] = self.normalize_datetime(record.get('created'))
            
            if not transformed.get('title'):
                transformed['title'] = f"Task {transformed.get('id', 'Unknown')}"
                
            if not transformed.get('task_title'):
                transformed['task_title'] = transformed.get('title', f"Task {transformed.get('id', 'Unknown')}")
            
            # Extract legacy date/time fields from datetime fields
            if transformed.get('start_datetime'):
                dt = transformed['start_datetime']
                if hasattr(dt, 'date') and hasattr(dt, 'time'):
                    transformed['start_date'] = dt.date()
                    transformed['start_time'] = dt.time()
                    
            if transformed.get('end_datetime'):
                dt = transformed['end_datetime']
                if hasattr(dt, 'date') and hasattr(dt, 'time'):
                    transformed['end_date'] = dt.date()
                    transformed['end_time'] = dt.time()
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming task record: {e}")
            logger.error(f"Record: {record}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed task record"""
        try:
            # Required field validation
            if not record.get('id'):
                raise ValueError("id is required")
                
            if not record.get('title') and not record.get('task_title'):
                raise ValueError("title is required")
            
            # Data type validation
            if 'id' in record:
                record['id'] = str(record['id'])
                
            if 'task_id' in record:
                record['task_id'] = str(record['task_id'])
            
            # Validate duration
            if record.get('duration') is not None:
                try:
                    duration = int(record['duration'])
                    if duration < 0:
                        logger.warning(f"Negative duration value: {duration}")
                        record['duration'] = None
                    else:
                        record['duration'] = duration
                except (ValueError, TypeError):
                    record['duration'] = None
            
            # Validate datetime fields
            datetime_fields = ['start_datetime', 'end_datetime', 'due_datetime', 'created', 'updated']
            for field in datetime_fields:
                if record.get(field) and not isinstance(record[field], type(None)):
                    # Ensure it's a valid datetime
                    if not hasattr(record[field], 'strftime'):
                        logger.warning(f"Invalid datetime for {field}: {record[field]}")
                        record[field] = None
            
            # Validate boolean fields
            boolean_fields = ['is_customer_address_geo_coded', 'use_lat_lng_address', 'is_linked', 
                            'is_supply_provided_locked', 'is_supply_returned_locked', 'unscheduled', 'self_scheduling']
            for field in boolean_fields:
                if field in record:
                    record[field] = bool(record[field]) if record[field] is not None else False
            
            # Validate customer location data
            if record.get('customer_exact_location'):
                location = record['customer_exact_location']
                if isinstance(location, dict):
                    # Validate lat/lng if present
                    if 'lat' in location:
                        try:
                            lat = float(location['lat'])
                            if not (-90 <= lat <= 90):
                                logger.warning(f"Invalid latitude: {lat}")
                                location['lat'] = None
                        except (ValueError, TypeError):
                            location['lat'] = None
                    
                    if 'lng' in location:
                        try:
                            lng = float(location['lng'])
                            if not (-180 <= lng <= 180):
                                logger.warning(f"Invalid longitude: {lng}")
                                location['lng'] = None
                        except (ValueError, TypeError):
                            location['lng'] = None
            
            # Ensure string fields don't exceed reasonable lengths
            string_fields = ['title', 'details', 'customer_name', 'customer_address_line_1', 
                           'customer_address_line_2', 'customer_city', 'customer_state', 'customer_country']
            for field in string_fields:
                if record.get(field) and len(str(record[field])) > 255:
                    record[field] = str(record[field])[:255]
                    logger.warning(f"Truncated {field} to 255 characters")
            
            # Validate numeric counts
            count_fields = ['outbound_sms_count', 'inbound_sms_count', 'outbound_email_count', 
                          'inbound_email_count', 'number_of_workers_required']
            for field in count_fields:
                if record.get(field) is not None:
                    try:
                        count = int(record[field])
                        if count < 0:
                            logger.warning(f"Negative {field}: {count}")
                            record[field] = 0
                        else:
                            record[field] = count
                    except (ValueError, TypeError):
                        record[field] = None
            
            return record
            
        except Exception as e:
            logger.error(f"Error validating task record: {e}")
            raise
