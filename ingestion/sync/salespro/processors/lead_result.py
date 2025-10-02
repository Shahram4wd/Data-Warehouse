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
        """Comprehensive field mappings for lead result normalization"""
        return {
            # Core result fields
            'appointment_result': 'appointment_result',
            'result_reason_demo_not_sold': 'result_reason_demo_not_sold', 
            'result_reason_no_demo': 'result_reason_no_demo',
            
            # Presence indicators
            'both_homeowners_present': 'both_homeowners_present',
            'sales_manager_present': 'sales_manager_present',
            
            # Financial fields
            'job_size': 'job_size',
            'total_job_amount': 'total_job_amount',
            'one_year_price': 'one_year_price',
            'last_price_offered': 'last_price_offered',
            'last_payment_offered': 'last_payment_offered',
            'no_brainer_commitment': 'no_brainer_commitment',
            'deposit_type': 'deposit_type',
            'deposit_amount': 'deposit_amount',
            'balance_type': 'balance_type',
            'balance_amount': 'balance_amount',
            
            # Payment and financing
            'preferred_payment': 'preferred_payment',
            'financing': 'financing',
            'financing_approved': 'financing_approved',
            'loan_docs_signed': 'loan_docs_signed',
            
            # Job details
            'job_type': 'job_type',
            'services': 'services',
            'requested_start_month': 'requested_start_month',
            'deadline': 'deadline',
            'timing': 'timing',
            'scheduling_notes': 'scheduling_notes',
            
            # Process tracking
            'upload_estimate_sheet_company_cam': 'upload_estimate_sheet_company_cam',
            'st8_completed': 'st8_completed',
            'did_use_company_cam': 'did_use_company_cam',
            'client_most_likely_to_add_on': 'client_most_likely_to_add_on',
            
            # Sales process fields
            'warm_up_topic': 'warm_up_topic',
            'urgency_time_frame': 'urgency_time_frame',
            'additional_services_demoed_priced': 'additional_services_demoed_priced',
            'describe_rapport_hot_button': 'describe_rapport_hot_button',
            'company_story_pain_point': 'company_story_pain_point',
            'call_to_action': 'call_to_action',
            'price_conditioning_response': 'price_conditioning_response',
            'customers_final_price_commitment': 'customers_final_price_commitment',
            
            # Notes and details
            'notes': 'notes',
            'closing_notes': 'closing_notes',
            'notes_for_install_team': 'notes_for_install_team',
            'details_discussed_for_install': 'details_discussed_for_install',
            
            # Tools and preferences
            'measurement_tool': 'measurement_tool',
            'dumpster_preference': 'dumpster_preference',
            'color_selection': 'color_selection',
            
            # Other
            'has_consider_solar': 'has_consider_solar',
            'status_bucket': 'status_bucket',
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
            
            # Create comprehensive mapping from JSON titles to field names
            title_mappings = {
                # Core result fields
                "Appointment Result": "appointment_result",
                "Appointment Result ": "appointment_result",  # Handle trailing space variant
                "Result": "appointment_result",  # Alternative format
                "Result Reason - Demo Not Sold (objection)": "result_reason_demo_not_sold",
                "Result Reason - No Demo (REQUIRES SALES MANGER APPROVAL)": "result_reason_no_demo",
                
                # Presence indicators
                "Both Homeowners Present?": "both_homeowners_present",
                "Both Homeowners Present": "both_homeowners_present",
                "Sales Manager Present": "sales_manager_present",
                
                # Financial fields
                "Job Size": "job_size",
                "Total Job Amount": "total_job_amount",
                "One Year Price": "one_year_price",
                "Last Price Offered": "last_price_offered",
                "Last PAYMENT offered": "last_payment_offered",
                "Customer No Brainer Payment Commitment ($0.00 if you did not get commitment)": "no_brainer_commitment",
                "Customer's Final Price Commitment": "customers_final_price_commitment",
                
                # Deposit and balance
                "Deposit Type": "deposit_type",
                "Deposit Type-": "deposit_type",  # Variant with dash
                "Deposit Amount": "deposit_amount",
                "Balance Type": "balance_type",
                "Balance Type-": "balance_type",  # Variant with dash
                "Balance Form Of Payment": "balance_type",
                "Balance Amount": "balance_amount",
                
                # Payment preferences
                "Preferred Payment": "preferred_payment",
                "Preferred Payment ": "preferred_payment",  # Handle extra space
                "Financing": "financing",
                "Financing Approved": "financing_approved",
                "Financing Approved ": "financing_approved",
                "Loan Docs Signed": "loan_docs_signed",
                "Loan Docs Signed ": "loan_docs_signed",
                
                # Job details
                "Job Type": "job_type",
                "Services": "services",
                "Requested Start Month (If Any)": "requested_start_month",
                "Deadline (If Any)-": "deadline",
                "Timing": "timing",
                "Scheduling Notes": "scheduling_notes",
                
                # Process tracking
                "Did you Upload Estimate Sheet to Company Cam": "upload_estimate_sheet_company_cam",
                "Did you complete your ST-8 Form Before leaving house?": "st8_completed",
                "Did the homeowner complete the ST-8 Form before leaving house?": "st8_completed",
                "Did you use company cam": "did_use_company_cam",
                "Did you use company cam ": "did_use_company_cam",
                "Client most likely to add on:": "client_most_likely_to_add_on",
                "Client most likely to add on: ": "client_most_likely_to_add_on",
                
                # Sales process
                "Warm Up Topic": "warm_up_topic",
                "Urgency Time Frame": "urgency_time_frame",
                "Additional Services Demoed & Priced": "additional_services_demoed_priced",
                "Additional Services Demoed \\u0026 Priced": "additional_services_demoed_priced",
                "Describe Rapport & Hot Button": "describe_rapport_hot_button",
                "Describe Rapport \\u0026 Hot Button": "describe_rapport_hot_button",
                "Company Story - what is customer's pain point": "company_story_pain_point",
                "Call To Action - what is the urgency & main consequence": "call_to_action",
                "Call To Action - what is the urgency \\u0026 main consequence": "call_to_action",
                "Price Conditioning Response (Where do they want to fall & why)": "price_conditioning_response",
                "Price Conditioning Response (Where do they want to fall \\u0026 why)": "price_conditioning_response",
                
                # Notes
                "Notes": "notes",
                "Closing Notes (how could you have booked this job)": "closing_notes",
                "Notes for Install Team": "notes_for_install_team",
                "Project Notes": "notes_for_install_team",
                "Details Discussed With Homeowner That Installation Needs To Know": "details_discussed_for_install",
                
                # Tools and preferences
                "Measurement Tool(s) Used": "measurement_tool",
                "Dumpster Preference": "dumpster_preference",
                "Color Selection (Default Color in Parentheses) Drip Edge Color (White), Fascia Color (White) Soffit Color (White), Trim Capping Color (White), Low slope Color (Black), Chimney Color (Black), Flashing Color (Black), Siding Corner Post (White)": "color_selection",
                
                # Other
                "Has / would this customer ever consider Solar": "has_consider_solar",
            }
            
            # Line item tracking for multi-service jobs
            line_items = []
            
            # Track potential line items by looking for monetary values and service types
            job_size = None
            job_type = None
            final_price = None
            
            # Process each item in the lead results
            for item in lead_data:
                if isinstance(item, dict) and 'title' in item and 'value' in item:
                    title = item['title']
                    value = item['value']
                    
                    # Handle legacy line items (Job Type 1-6)
                    if title.startswith('Job Type ') and title.endswith(' Amount'):
                        # Extract job type number
                        try:
                            job_num = int(title.split(' ')[2])
                            if 1 <= job_num <= 6:
                                # Find corresponding job type
                                job_type_title = f"Job Type {job_num}"
                                job_type_value = None
                                for other_item in lead_data:
                                    if other_item.get('title') == job_type_title:
                                        job_type_value = other_item.get('value')
                                        break
                                
                                if job_type_value and value:
                                    line_items.append({
                                        'job_type_number': job_num,
                                        'job_type': self.clean_text_value(job_type_value),
                                        'job_type_amount': self.parse_price_value(value)
                                    })
                        except (ValueError, IndexError):
                            pass
                    
                    # Handle current data patterns for line items
                    elif title == "Job Size":
                        job_size = self.parse_price_value(value)
                    elif title == "Job Type":
                        job_type = self.clean_text_value(value)
                    elif title == "Customer's Final Price Commitment":
                        final_price = self.parse_price_value(value)
                    
                    # Handle regular field mappings
                    elif title in title_mappings:
                        field_name = title_mappings[title]
                        
                        # Handle boolean fields
                        if field_name in ['both_homeowners_present', 'sales_manager_present', 
                                          'financing_approved', 'loan_docs_signed',
                                          'upload_estimate_sheet_company_cam', 'st8_completed', 'did_use_company_cam']:
                            normalized[field_name] = self.parse_boolean_value(value)
                        
                        # Handle price/decimal fields
                        elif field_name in ['job_size', 'total_job_amount', 'one_year_price', 
                                            'last_price_offered', 'last_payment_offered', 'no_brainer_commitment',
                                            'deposit_amount', 'balance_amount', 'customers_final_price_commitment']:
                            normalized[field_name] = self.parse_price_value(value)
                        
                        # Handle text fields
                        else:
                            cleaned_value = self.clean_text_value(value)
                            if cleaned_value:
                                normalized[field_name] = cleaned_value
            
            # Create line items from current data patterns
            if job_type and (job_size or final_price):
                # Create a line item from the main job data
                amount = job_size or final_price
                if amount:
                    line_items.append({
                        'job_type_number': 1,  # Default to 1 for single-job records
                        'job_type': job_type,
                        'job_type_amount': amount
                    })
            
            # Store line items for later processing
            if line_items:
                normalized['_line_items'] = line_items
            
            # Store the raw JSON for reference
            normalized['lead_results_raw'] = lead_results_json
            
            # Extract status bucket from appointment result if available
            appointment_result = normalized.get('appointment_result')
            if appointment_result:
                # Extract status bucket (e.g., "[HRE]", "[CC]", "[MGMT]")
                import re
                match = re.match(r'(\[[A-Z]+\])', appointment_result)
                if match:
                    normalized['status_bucket'] = match.group(1)
            
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
    
    def parse_boolean_value(self, value: str) -> bool:
        """Parse boolean values from various string formats"""
        if not value:
            return None
        
        value_str = str(value).strip().lower()
        
        # Handle common boolean representations
        if value_str in ['yes', 'y', 'true', '1', 'on']:
            return True
        elif value_str in ['no', 'n', 'false', '0', 'off']:
            return False
        else:
            # For ambiguous values, return None to let the field be nullable
            logger.debug(f"Ambiguous boolean value: {value}")
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
        
        # Set sync timestamps for bulk operations (auto_now doesn't work with bulk operations)
        from django.utils import timezone
        now = timezone.now()
        if 'sync_created_at' not in transformed:
            transformed['sync_created_at'] = now
        transformed['sync_updated_at'] = now
        
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
