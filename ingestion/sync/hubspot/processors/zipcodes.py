"""
HubSpot zipcode processor for CSV data transformation
"""
from ingestion.sync.hubspot.processors.zipcode_processor import HubSpotZipCodeProcessor as BaseZipCodeProcessor

class HubSpotZipCodeProcessor(BaseZipCodeProcessor):
    """Processor for zipcode CSV data"""
    
    def __init__(self):
        super().__init__()
    
    def parse_csv(self, csv_content):
        """Parse CSV content - delegates to base processor"""
        return super().parse_csv(csv_content)
    
    def filter_valid(self, records):
        """Filter valid records - delegates to base processor"""
        return super().filter_valid(records)
    
    def transform_record(self, record):
        """Transform a single record"""
        return {
            'zipcode': record.get('zipcode') or record.get('zip'),
            'division': record.get('division'),
            'city': record.get('city'),
            'county': record.get('county'),
            'state': record.get('state'),
            'archived': False
        }
    
    def validate_record(self, record):
        """Validate a single record"""
        if not record.get('zipcode'):
            raise ValueError("Zipcode is required")
        return record
