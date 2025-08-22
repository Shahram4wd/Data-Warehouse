"""
MarketSharp Contact processor for data validation and transformation
"""
import logging
from typing import Dict, Any, List, Optional
from decimal import Decimal
from datetime import datetime, date

from ..validators import GeniusValidator

logger = logging.getLogger(__name__)


class GeniusMarketSharpContactProcessor:
    """Processor for MarketSharp contact data validation and transformation"""
    
    def __init__(self):
        self.validator = GeniusValidator()
    
    def process_marketsharp_contacts(self, raw_data: List[tuple], field_mapping: List[str]) -> List[Dict[str, Any]]:
        """Process raw MarketSharp contact data into validated dictionaries"""
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
                logger.error(f"Error processing MarketSharp contact record: {e}")
                logger.error(f"Problematic record: {row}")
                continue
        
        logger.info(f"Processed {len(processed_records)} MarketSharp contact records")
        return processed_records
    
    def _validate_and_transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate and transform a single MarketSharp contact record"""
        try:
            validated_record = {}
            
            # Required ID field
            if not self.validator.validate_id_field(record.get('id')):
                logger.error(f"Invalid ID for MarketSharp contact: {record.get('id')}")
                return None
            validated_record['id'] = record['id']
            
            # External ID (MarketSharp's ID)
            validated_record['external_id'] = self.validator.validate_string_field(
                record.get('external_id'), max_length=100
            )
            
            # Contact information
            validated_record['first_name'] = self.validator.validate_string_field(
                record.get('first_name'), max_length=100
            )
            validated_record['last_name'] = self.validator.validate_string_field(
                record.get('last_name'), max_length=100
            )
            
            # Email validation
            email = record.get('email')
            if email and '@' in str(email):
                validated_record['email'] = self.validator.validate_string_field(email, max_length=255)
            else:
                validated_record['email'] = None
            
            # Phone number
            validated_record['phone'] = self.validator.validate_string_field(
                record.get('phone'), max_length=50
            )
            
            # Address fields
            validated_record['address_1'] = self.validator.validate_string_field(
                record.get('address_1'), max_length=255
            )
            validated_record['address_2'] = self.validator.validate_string_field(
                record.get('address_2'), max_length=255
            )
            validated_record['city'] = self.validator.validate_string_field(
                record.get('city'), max_length=100
            )
            validated_record['state'] = self.validator.validate_string_field(
                record.get('state'), max_length=10
            )
            validated_record['zip'] = self.validator.validate_string_field(
                record.get('zip'), max_length=20
            )
            
            # Foreign key references
            validated_record['marketing_source_id'] = record.get('marketing_source_id')
            validated_record['prospect_source_id'] = record.get('prospect_source_id')
            
            # Lead status
            validated_record['lead_status'] = self.validator.validate_string_field(
                record.get('lead_status'), max_length=50
            )
            
            # Appointment scheduling
            validated_record['appointment_date'] = self._validate_date(record.get('appointment_date'))
            validated_record['appointment_time'] = self._validate_time(record.get('appointment_time'))
            
            # Notes
            validated_record['notes'] = self.validator.validate_string_field(
                record.get('notes'), max_length=1000
            )
            
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
            logger.error(f"Error validating MarketSharp contact record: {e}")
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
