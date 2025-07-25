"""
HubSpot zipcode processor for GitHub CSV data
"""
import logging
import csv
from io import StringIO
from typing import Dict, Any, List, Optional
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import Hubspot_ZipCode

logger = logging.getLogger(__name__)

class HubSpotZipCodeProcessor(HubSpotBaseProcessor):
    """Process HubSpot zipcode data from GitHub CSV"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_ZipCode, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings for CSV columns to model fields"""
        return {
            'zipcode': 'zipcode',
            'zip': 'zipcode',  # Alternative column name
            'division': 'division',
            'city': 'city',
            'county': 'county',
            'state': 'state',
        }
    
    def parse_csv(self, csv_content: str) -> List[Dict[str, Any]]:
        """Parse CSV content into records"""
        records = []
        
        try:
            csv_reader = csv.DictReader(StringIO(csv_content))
            
            for row in csv_reader:
                # Clean up the row - remove empty values and strip whitespace
                cleaned_row = {}
                for key, value in row.items():
                    if key and value:
                        cleaned_row[key.strip()] = str(value).strip()
                
                if cleaned_row:
                    records.append(cleaned_row)
            
            logger.info(f"Parsed {len(records)} records from CSV")
            return records
            
        except Exception as e:
            logger.error(f"Error parsing CSV: {e}")
            raise ValidationException(f"Failed to parse CSV: {e}")
    
    def filter_valid(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter out invalid records"""
        valid_records = []
        
        for record in records:
            # Check if we have a zipcode field
            zipcode = record.get('zipcode') or record.get('zip')
            if zipcode and len(str(zipcode).strip()) >= 5:
                valid_records.append(record)
            else:
                logger.warning(f"Skipping invalid zipcode record: {record}")
        
        logger.info(f"Filtered to {len(valid_records)} valid records from {len(records)} total")
        return valid_records
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform CSV record to model format"""
        # Apply field mappings
        transformed = {}
        field_mappings = self.get_field_mappings()
        
        for source_field, target_field in field_mappings.items():
            value = record.get(source_field)
            if value is not None:
                transformed[target_field] = str(value).strip()
        
        # Ensure we have a zipcode
        if not transformed.get('zipcode'):
            zipcode = record.get('zipcode') or record.get('zip')
            if zipcode:
                transformed['zipcode'] = str(zipcode).strip()
        
        # Set default values
        transformed['archived'] = False
        
        return transformed
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate zipcode record"""
        zipcode = record.get('zipcode')
        if not zipcode:
            raise ValidationException("Zipcode is required")
        
        # Basic zipcode validation
        zipcode_str = str(zipcode).strip()
        if len(zipcode_str) < 5:
            raise ValidationException(f"Invalid zipcode format: {zipcode}")
        
        # Ensure zipcode is properly formatted
        record['zipcode'] = zipcode_str
        
        return record
