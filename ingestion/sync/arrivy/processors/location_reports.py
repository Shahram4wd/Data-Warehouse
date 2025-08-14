"""
Arrivy location reports data processor
"""
import logging
from typing import Dict, Any
from .base import ArrivyBaseProcessor

logger = logging.getLogger(__name__)


class LocationReportsProcessor(ArrivyBaseProcessor):
    """Processor for Arrivy location reports data"""
    
    def __init__(self, **kwargs):
        from ingestion.models.arrivy import Arrivy_LocationReport
        super().__init__(model_class=Arrivy_LocationReport, **kwargs)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from Arrivy API to database fields"""
        return {
            'id': 'id',  # Primary key field
            'task_id': 'task_id',
            'entity_id': 'entity_id',
            'latitude': 'latitude',
            'longitude': 'longitude',
            'timestamp': 'timestamp'
        }
        
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform Arrivy location report record to database format"""
        try:
            # Get field mappings
            mappings = self.get_field_mappings()
            
            # Transform record using mappings
            transformed = {}
            for source_field, target_field in mappings.items():
                if source_field in record:
                    value = record[source_field]
                    
                    # Special handling for specific fields
                    if source_field in ['created', 'updated', 'timestamp']:
                        value = self.normalize_datetime(value)
                    elif source_field in ['latitude', 'longitude', 'accuracy', 'altitude', 'speed', 'heading']:
                        try:
                            value = float(value) if value is not None else None
                        except (ValueError, TypeError):
                            value = None
                    elif source_field in ['battery_level']:
                        try:
                            # Battery level could be percentage (0-100) or decimal (0-1)
                            battery = float(value) if value is not None else None
                            if battery is not None:
                                # Normalize to percentage if it's decimal
                                if 0 <= battery <= 1:
                                    battery = battery * 100
                                # Clamp to valid range
                                battery = max(0, min(100, battery))
                            value = battery
                        except (ValueError, TypeError):
                            value = None
                    elif source_field in ['entity_id']:
                        value = str(value) if value is not None else None
                    elif source_field == 'device_info':
                        # Handle JSON/dict data
                        if isinstance(value, dict):
                            pass  # Keep as dict
                        elif isinstance(value, str):
                            try:
                                import json
                                value = json.loads(value)
                            except json.JSONDecodeError:
                                value = {'raw': value}
                        else:
                            value = None
                    
                    transformed[target_field] = value
            
            # Ensure required fields
            if 'id' not in transformed:
                transformed['id'] = record.get('id')
            
            # Generate a report ID if missing
            if not transformed.get('id'):
                # Create a composite ID from entity, timestamp, and coordinates
                entity_id = transformed.get('entity_id', 'unknown')
                timestamp = transformed.get('timestamp')
                lat = transformed.get('latitude')
                lng = transformed.get('longitude')
                
                if timestamp:
                    ts_str = timestamp.strftime('%Y%m%d_%H%M%S') if hasattr(timestamp, 'strftime') else str(timestamp)
                else:
                    ts_str = 'unknown'
                
                transformed['id'] = f"{entity_id}_{ts_str}_{lat}_{lng}"
            
            # Set default entity_type if missing
            if not transformed.get('entity_type'):
                transformed['entity_type'] = 'crew_member'
            
            # Note: crm_source and raw_data fields don't exist in model
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming location report record: {e}")
            logger.error(f"Record: {record}")
            raise
            
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a transformed location report record"""
        try:
            # Required field validation
            if not record.get('id'):
                raise ValueError("id is required")
            
            # Validate coordinates (required for location reports)
            latitude = record.get('latitude')
            longitude = record.get('longitude')
            
            if latitude is not None and longitude is not None:
                try:
                    lat_val = float(latitude)
                    lng_val = float(longitude)
                    
                    # Basic coordinate range validation
                    if not (-90 <= lat_val <= 90):
                        logger.warning(f"Invalid latitude value: {lat_val}")
                        record['latitude'] = None
                    else:
                        record['latitude'] = lat_val
                    
                    if not (-180 <= lng_val <= 180):
                        logger.warning(f"Invalid longitude value: {lng_val}")
                        record['longitude'] = None
                    else:
                        record['longitude'] = lng_val
                        
                except (ValueError, TypeError):
                    logger.warning("Invalid coordinate values")
                    record['latitude'] = None
                    record['longitude'] = None
            
            # Data type validation
            if 'id' in record:
                record['id'] = str(record['id'])
            
            # Validate numeric fields
            numeric_fields = ['accuracy', 'altitude', 'speed', 'heading', 'battery_level']
            for field in numeric_fields:
                if record.get(field) is not None:
                    try:
                        value = float(record[field])
                        
                        # Field-specific validation
                        if field == 'accuracy' and value < 0:
                            logger.warning(f"Negative accuracy value: {value}")
                            record[field] = None
                        elif field == 'speed' and value < 0:
                            logger.warning(f"Negative speed value: {value}")
                            record[field] = None
                        elif field == 'heading' and not (0 <= value <= 360):
                            logger.warning(f"Invalid heading value: {value}")
                            record[field] = None
                        elif field == 'battery_level' and not (0 <= value <= 100):
                            logger.warning(f"Invalid battery level: {value}")
                            record[field] = None
                        else:
                            record[field] = value
                            
                    except (ValueError, TypeError):
                        record[field] = None
            
            # Validate datetime fields
            datetime_fields = ['timestamp', 'created', 'updated']
            for field in datetime_fields:
                if record.get(field) and not hasattr(record[field], 'strftime'):
                    logger.warning(f"Invalid datetime for {field}: {record[field]}")
                    record[field] = None
            
            # Ensure string fields don't exceed reasonable lengths
            string_fields = ['address', 'city', 'state', 'country', 'location_type', 'event_type']
            for field in string_fields:
                if record.get(field) and len(str(record[field])) > 255:
                    record[field] = str(record[field])[:255]
                    logger.warning(f"Truncated {field} to 255 characters")
            
            return record
            
        except Exception as e:
            logger.error(f"Error validating location report record: {e}")
            raise
