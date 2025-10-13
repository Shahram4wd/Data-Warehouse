"""
Marketing Spends Google Sheets Processor
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

from .base import BaseGoogleSheetsProcessor

logger = logging.getLogger(__name__)


class MarketingSpendsProcessor(BaseGoogleSheetsProcessor):
    """
    Processor for Marketing Spends Google Sheet data
    
    Handles transformation and validation of marketing spends data
    from Google Sheets to the database model.
    """
    
    def __init__(self, model_class, **kwargs):
        """Initialize with auto-detect disabled to use only explicit field mappings"""
        kwargs['auto_detect_fields'] = False
        super().__init__(model_class, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """
        Field mappings specific to Marketing Spends sheet
        Maps Google Sheet column names to Django model field names
        """
        return {
            # Core spend data
            'Date': 'spend_date',
            'Cost': 'cost',
            'Division': 'division',
            'Channel': 'channel',
            'Campaign': 'campaign',
            
            # Campaign Details (NEW FIELDS)
            'Campaign ID': 'campaign_id',
            'Campaign Type': 'campaign_type',
            
            # Event information
            'event_start_date': 'event_start_date',
            'event_end_date': 'event_end_date',
            
            # Event Cost Breakdown (NEW FIELDS)
            'event_fee': 'event_fee',
            'event_labor_cost': 'event_labor_cost',
            
            # Base metadata fields (inherited)
            '_sheet_row_number': 'sheet_row_number',
            '_sheet_last_modified': 'sheet_last_modified',
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw Google Sheets record for marketing spends
        
        Args:
            record: Raw record from Google Sheets client
            
        Returns:
            Transformed record ready for validation
        """
        try:
            # Start with base transformation
            transformed = super().transform_record(record)
            
            # Apply custom transformations for marketing spends
            transformed = self._apply_marketing_spends_transformations(transformed)
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming marketing spends record: {e}")
            raise
    
    def _apply_marketing_spends_transformations(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply marketing spends specific transformations
        
        Args:
            record: Partially transformed record
            
        Returns:
            Fully transformed record
        """
        # Date transformations
        if 'spend_date' in record:
            record['spend_date'] = self._parse_date(record['spend_date'])
        
        if 'event_start_date' in record:
            record['event_start_date'] = self._parse_date(record['event_start_date'])
            
        if 'event_end_date' in record:
            record['event_end_date'] = self._parse_date(record['event_end_date'])
        
        # Cost transformations
        if 'cost' in record:
            record['cost'] = self._parse_decimal(record['cost'])
        
        # Event cost transformations (NEW FIELDS)
        if 'event_fee' in record:
            record['event_fee'] = self._parse_decimal(record['event_fee'])
            
        if 'event_labor_cost' in record:
            record['event_labor_cost'] = self._parse_decimal(record['event_labor_cost'])
        
        # String field cleaning
        for field in ['division', 'channel', 'campaign', 'campaign_id', 'campaign_type']:
            if field in record:
                record[field] = self._clean_string_field(record[field])
        
        return record
    
    def _parse_date(self, date_value: Any) -> Optional[datetime.date]:
        """
        Parse various date formats to date object
        
        Args:
            date_value: Date value from sheet (could be string, datetime, etc.)
            
        Returns:
            Parsed date object or None
        """
        if not date_value:
            return None
            
        try:
            # If it's already a date object
            if hasattr(date_value, 'date'):
                return date_value.date()
            elif hasattr(date_value, 'year'):
                return date_value
            
            # If it's a string, try to parse it
            if isinstance(date_value, str):
                date_value = date_value.strip()
                if not date_value:
                    return None
                
                # Try common date formats
                date_formats = [
                    '%m/%d/%Y',     # 11/1/2024
                    '%Y-%m-%d',     # 2024-11-01
                    '%m-%d-%Y',     # 11-01-2024
                    '%d/%m/%Y',     # 01/11/2024
                    '%Y/%m/%d',     # 2024/11/01
                ]
                
                for fmt in date_formats:
                    try:
                        return datetime.strptime(date_value, fmt).date()
                    except ValueError:
                        continue
                
                # Try with timezone parsing
                try:
                    parsed = timezone.datetime.fromisoformat(date_value.replace('Z', '+00:00'))
                    return parsed.date()
                except:
                    pass
            
            # If it's a number (like Excel serial date)
            if isinstance(date_value, (int, float)):
                try:
                    # Excel dates start from 1900-01-01 (with 1900 being day 1)
                    # Adjust for Excel's leap year bug
                    if date_value > 59:
                        date_value -= 1
                    excel_epoch = datetime(1900, 1, 1).date()
                    return excel_epoch + timezone.timedelta(days=int(date_value) - 1)
                except:
                    pass
            
            logger.warning(f"Could not parse date value: {date_value} (type: {type(date_value)})")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing date '{date_value}': {e}")
            return None
    
    def _parse_decimal(self, cost_value: Any) -> Optional[float]:
        """
        Parse cost value to decimal
        
        Args:
            cost_value: Cost value from sheet
            
        Returns:
            Parsed decimal value or None
        """
        if not cost_value:
            return None
            
        try:
            # If it's already a number
            if isinstance(cost_value, (int, float)):
                return float(cost_value)
            
            # If it's a string, clean and parse
            if isinstance(cost_value, str):
                # Remove common currency symbols and whitespace
                cleaned = cost_value.strip().replace('$', '').replace(',', '')
                if not cleaned:
                    return None
                return float(cleaned)
            
            logger.warning(f"Could not parse cost value: {cost_value} (type: {type(cost_value)})")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing cost '{cost_value}': {e}")
            return None
    
    def _clean_string_field(self, value: Any) -> Optional[str]:
        """
        Clean string field value
        
        Args:
            value: String value from sheet
            
        Returns:
            Cleaned string or None
        """
        if not value:
            return None
            
        try:
            # Convert to string and clean
            cleaned = str(value).strip()
            return cleaned if cleaned else None
            
        except Exception as e:
            logger.warning(f"Error cleaning string field '{value}': {e}")
            return None
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a transformed marketing spends record
        
        Args:
            record: Transformed record
            
        Returns:
            Validated record
        """
        try:
            # Start with base validation
            validated = super().validate_record(record)
            
            # Apply marketing spends specific validations
            validated = self._apply_marketing_spends_validations(validated)
            
            return validated
            
        except Exception as e:
            logger.error(f"Error validating marketing spends record: {e}")
            raise
    
    def _apply_marketing_spends_validations(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Apply marketing spends specific validations
        
        Args:
            record: Record to validate
            
        Returns:
            Validated record
        """
        validation_errors = []
        
        # Validate required sheet row number
        if not record.get('sheet_row_number'):
            validation_errors.append("Missing sheet_row_number")
        
        # Validate cost is positive if present
        cost = record.get('cost')
        if cost is not None and cost < 0:
            validation_errors.append(f"Cost cannot be negative: {cost}")
        
        # Validate event date logic
        start_date = record.get('event_start_date')
        end_date = record.get('event_end_date')
        if start_date and end_date and start_date > end_date:
            validation_errors.append(f"Event start date ({start_date}) cannot be after end date ({end_date})")
        
        # Validate event cost values are positive if present
        for cost_field in ['event_fee', 'event_labor_cost']:
            cost_value = record.get(cost_field)
            if cost_value is not None and cost_value < 0:
                validation_errors.append(f"{cost_field} cannot be negative: {cost_value}")
        
        # Validate string field lengths
        field_limits = {
            'division': 50,
            'channel': 50,
            'campaign': 100,
            'campaign_id': 50,      # NEW FIELD
            'campaign_type': 20,    # NEW FIELD
        }
        
        for field, max_length in field_limits.items():
            value = record.get(field)
            if value and len(value) > max_length:
                logger.warning(f"Field '{field}' truncated from {len(value)} to {max_length} characters")
                record[field] = value[:max_length]
        
        # Log validation errors but don't fail the record
        if validation_errors:
            logger.warning(f"Validation warnings for row {record.get('sheet_row_number')}: {validation_errors}")
        
        return record
    
    def get_record_identifier(self, record: Dict[str, Any]) -> str:
        """
        Get a human-readable identifier for a record (for logging)
        
        Args:
            record: Record data
            
        Returns:
            String identifier
        """
        row_num = record.get('sheet_row_number', 'Unknown')
        division = record.get('division', 'Unknown Division')
        channel = record.get('channel', 'Unknown Channel')
        spend_date = record.get('spend_date', 'Unknown Date')
        cost = record.get('cost', 0)
        
        return f"Row {row_num}: {division} - {channel} - ${cost} on {spend_date}"
