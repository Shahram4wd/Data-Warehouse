"""
MarketSharp Appointment processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date

from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusMarketSharpAppointmentProcessor:
    """Processor for MarketSharp appointment data validation and transformation"""
    
    def __init__(self):
        self.validator = GeniusValidator()
    
    def process_marketsharp_appointments(self, raw_data: List[tuple], field_mapping: List[str]) -> List[Dict[str, Any]]:
        """Process raw MarketSharp appointment data into validated dictionaries"""
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
                logger.error(f"Error processing MarketSharp appointment record: {e}")
                logger.error(f"Problematic record: {row}")
                continue
        
        logger.info(f"Processed {len(processed_records)} MarketSharp appointment records")
        return processed_records
    
    def _validate_and_transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and transform a single MarketSharp appointment record"""
        try:
            validated_record = {}
            
            # Required ID field
            if not self.validator.validate_id_field(record.get('id')):
                logger.error(f"Invalid ID for MarketSharp appointment: {record.get('id')}")
                return None
            validated_record['id'] = record['id']
            
            # External ID (MarketSharp's ID)
            validated_record['external_id'] = self.validator.validate_string_field(
                record.get('external_id'), max_length=100
            )
            
            # Contact ID (required foreign key)
            if not self.validator.validate_id_field(record.get('contact_id')):
                logger.error(f"Invalid contact_id for MarketSharp appointment: {record.get('contact_id')}")
                return None
            validated_record['contact_id'] = record['contact_id']
            
            # Appointment scheduling (required)
            appointment_date = self._validate_date(record.get('appointment_date'))
            if not appointment_date:
                logger.error(f"Invalid appointment_date for MarketSharp appointment: {record.get('appointment_date')}")
                return None
            validated_record['appointment_date'] = appointment_date
            
            validated_record['appointment_time'] = self._validate_time(record.get('appointment_time'))
            
            # Foreign key references
            validated_record['appointment_type_id'] = record.get('appointment_type_id')
            validated_record['salesperson_id'] = record.get('salesperson_id')
            validated_record['marketing_source_id'] = record.get('marketing_source_id')
            validated_record['outcome_id'] = record.get('outcome_id')
            
            # Lead source
            validated_record['lead_source'] = self.validator.validate_string_field(
                record.get('lead_source'), max_length=100
            )
            
            # Appointment status
            validated_record['appointment_status'] = self.validator.validate_string_field(
                record.get('appointment_status'), max_length=50
            )
            
            # Notes
            validated_record['notes'] = self.validator.validate_string_field(
                record.get('notes'), max_length=1000
            )
            
            # Follow-up date
            validated_record['follow_up_date'] = self._validate_date(record.get('follow_up_date'))
            
            # Active flag
            active = record.get('active')
            if isinstance(active, (bool, int)):
                validated_record['active'] = bool(active)
            else:
                validated_record['active'] = True  # Default to active
            
            # Timestamps
            validated_record['created_at'] = self._validate_datetime(record.get('created_at'))
            validated_record['updated_at'] = self._validate_datetime(record.get('updated_at'))
            
            return validated_record
            
        except Exception as e:
            logger.error(f"Error validating MarketSharp appointment record: {e}")
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
    
    def _validate_date(self, value: Any) -> Optional[date]:
        """Validate date field"""
        if value is None:
            return None
        if isinstance(value, date):
            return value
        if isinstance(value, datetime):
            return value.date()
        try:
            # Try to parse string date
            if isinstance(value, str):
                return datetime.fromisoformat(value.replace('Z', '+00:00')).date()
        except (ValueError, AttributeError):
            pass
        return None
    
    def _validate_time(self, value: Any) -> Optional[str]:
        """Validate time field"""
        if value is None:
            return None
        if isinstance(value, str) and ':' in value:
            return value
        return None
