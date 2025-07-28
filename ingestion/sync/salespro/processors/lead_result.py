"""
SalesPro Lead Result processor with JSON normalization
Following CRM sync framework standards
"""
import logging
import json
import re
from typing import Dict, Any, List
from decimal import Decimal, InvalidOperation
from ingestion.sync.salespro.processors.base import SalesProBaseProcessor
from ingestion.models.salespro import SalesPro_LeadResult

logger = logging.getLogger(__name__)


class SalesProLeadResultProcessor(SalesProBaseProcessor):
    """Processor for SalesPro Lead Results with JSON normalization"""
    
    def __init__(self, **kwargs):
        super().__init__(SalesPro_LeadResult, **kwargs)
        self.field_mappings.update(self.get_lead_result_mappings())
    
    def get_lead_result_mappings(self) -> Dict[str, str]:
        """Additional field mappings for lead result normalization"""
        return {
            'appointment_result': 'appointment_result',
            'result_reason_demo_not_sold': 'result_reason_demo_not_sold', 
            'result_reason_no_demo': 'result_reason_no_demo',
            'both_homeowners_present': 'both_homeowners_present',
            'one_year_price': 'one_year_price',
            'last_price_offered': 'last_price_offered',
            'preferred_payment': 'preferred_payment',
            'notes': 'notes',
            'lead_results_raw': 'lead_results_raw',
        }
    
    def normalize_lead_results_json(self, lead_results_json: str) -> Dict[str, Any]:
        """Convert JSON lead results to normalized field values"""
        normalized = {}
        
        try:
            if not lead_results_json:
                return normalized
                
            # Parse JSON if it's a string
            if isinstance(lead_results_json, str):
                lead_data = json.loads(lead_results_json)
            else:
                lead_data = lead_results_json
            
            # Create a mapping from titles to field names
            title_mappings = {
                "Appointment Result": "appointment_result",
                "Result Reason - Demo Not Sold (objection)": "result_reason_demo_not_sold",
                "Result Reason - No Demo (REQUIRES SALES MANGER APPROVAL)": "result_reason_no_demo",
                "Both Homeowners Present?": "both_homeowners_present",
                "One Year Price": "one_year_price",
                "Last Price Offered": "last_price_offered",
                "Preferred Payment": "preferred_payment",
                "Preferred Payment ": "preferred_payment",  # Handle extra space variant
                "Notes": "notes",
            }
            
            # Process each item in the lead results
            for item in lead_data:
                if isinstance(item, dict) and 'title' in item and 'value' in item:
                    title = item['title']
                    value = item['value']
                    
                    if title in title_mappings:
                        field_name = title_mappings[title]
                        
                        # Handle price fields that need decimal conversion
                        if field_name in ['one_year_price', 'last_price_offered']:
                            normalized[field_name] = self.parse_price_value(value)
                        else:
                            # Clean and store the value
                            cleaned_value = self.clean_text_value(value)
                            if cleaned_value:
                                normalized[field_name] = cleaned_value
            
            # Store the raw JSON for reference
            normalized['lead_results_raw'] = lead_results_json
            
        except (json.JSONDecodeError, KeyError, TypeError) as e:
            logger.warning(f"Failed to normalize lead results JSON: {e}")
            # Store the raw data even if parsing failed
            normalized['lead_results_raw'] = str(lead_results_json)
        
        return normalized
    
    def parse_price_value(self, price_str: str) -> Decimal:
        """Parse price string like '$0.00' to Decimal"""
        try:
            if not price_str:
                return None
            
            # Remove currency symbols and convert to decimal
            clean_price = re.sub(r'[^\d.-]', '', str(price_str))
            if clean_price and clean_price != '-':
                return Decimal(clean_price)
            return None
        except (ValueError, TypeError, InvalidOperation):
            logger.warning(f"Could not parse price value: {price_str}")
            return None
    
    def clean_text_value(self, value: str) -> str:
        """Clean text values, handling special cases"""
        if not value:
            return None
        
        # Convert to string and strip whitespace
        cleaned = str(value).strip()
        
        # Handle common "empty" values
        if cleaned.lower() in ['', 'null', 'none', 'n/a', '-']:
            return None
        
        # Handle values that start with dashes (like "-Undecided")
        if cleaned.startswith('-') and len(cleaned) > 1:
            cleaned = cleaned[1:].strip()
        
        return cleaned if cleaned else None
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform lead result record with JSON normalization"""
        # Start with base transformation
        transformed = super().transform_record(record)
        
        # Get the lead_results field (might be named differently in source)
        lead_results_raw = record.get('lead_results') or record.get('lead_results_raw')
        
        if lead_results_raw:
            # Normalize the JSON data into separate fields
            normalized_fields = self.normalize_lead_results_json(lead_results_raw)
            transformed.update(normalized_fields)
        
        return transformed
    
    def validate_record_completeness(self, record: Dict[str, Any]) -> List[str]:
        """Business rule validation for lead results"""
        warnings = []
        record_id = record.get('estimate_id', 'unknown')
        
        # Skip customer completeness checks for lead results - they don't have customer contact info
        # This overrides the base class method to avoid false warnings
        
        # Validate that we have either structured data or raw JSON
        has_structured_data = any([
            record.get('appointment_result'),
            record.get('notes'),
            record.get('one_year_price'),
            record.get('last_price_offered')
        ])
        
        has_raw_data = record.get('lead_results_raw')
        
        if not has_structured_data and not has_raw_data:
            warnings.append(f"Lead result {record_id} has no structured or raw lead data")
        
        # Validate price consistency
        one_year_price = record.get('one_year_price')
        last_price_offered = record.get('last_price_offered')
        
        if one_year_price and last_price_offered:
            if one_year_price > 0 and last_price_offered > 0:
                if abs(one_year_price - last_price_offered) > (one_year_price * Decimal('0.5')):
                    warnings.append(f"Lead result {record_id} has significant price variance between one year price and last offered")
        
        return warnings
