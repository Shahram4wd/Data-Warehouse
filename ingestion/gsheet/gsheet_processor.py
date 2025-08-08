"""
Google Sheets Data Processor

Data processing and transformation utilities for Google Sheets sync
following sync_crm_guide.md patterns.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime
from decimal import Decimal, InvalidOperation

from ingestion.base.processor import BaseProcessor
from ingestion.base.exceptions import ValidationError
from ingestion.models.gsheet import GSheet_Lead, GSheet_Contact


logger = logging.getLogger(__name__)


class GSheetDataProcessor(BaseProcessor):
    """
    Google Sheets data processor following sync_crm_guide.md patterns
    
    Handles:
    - Data validation and cleaning
    - Field mapping and transformation
    - Deduplication logic
    - Data quality checks
    """
    
    def __init__(self):
        """Initialize Google Sheets data processor"""
        super().__init__()
        self.field_validators = self._setup_field_validators()
        self.data_cleaners = self._setup_data_cleaners()
    
    def _setup_field_validators(self) -> Dict[str, callable]:
        """Setup field-specific validators"""
        return {
            'email': self._validate_email,
            'phone': self._validate_phone,
            'estimated_value': self._validate_decimal,
            'budget': self._validate_decimal,
            'lead_score': self._validate_integer,
            'zip_code': self._validate_zip_code,
            'created_date': self._validate_date,
            'updated_date': self._validate_date,
            'follow_up_date': self._validate_date,
        }
    
    def _setup_data_cleaners(self) -> Dict[str, callable]:
        """Setup field-specific data cleaners"""
        return {
            'email': self._clean_email,
            'phone': self._clean_phone,
            'first_name': self._clean_name,
            'last_name': self._clean_name,
            'full_name': self._clean_name,
            'company': self._clean_company_name,
            'address': self._clean_address,
            'city': self._clean_city_state,
            'state': self._clean_city_state,
            'country': self._clean_country,
            'zip_code': self._clean_zip_code,
        }
    
    def process_sheet_data(self, raw_data: List[Dict[str, str]], 
                          field_mappings: Dict[str, str],
                          model_type: str = 'lead') -> List[Dict[str, Any]]:
        """
        Process raw sheet data into model-ready format
        
        Args:
            raw_data: List of row dictionaries from sheet
            field_mappings: Mapping of sheet headers to model fields
            model_type: 'lead' or 'contact'
            
        Returns:
            List of processed data dictionaries
        """
        processed_data = []
        
        for row_index, row_data in enumerate(raw_data):
            try:
                processed_row = self._process_single_row(
                    row_data, field_mappings, model_type, row_index + 2  # +2 for header row
                )
                
                if processed_row:
                    processed_data.append(processed_row)
                    
            except Exception as e:
                logger.warning(f"Error processing row {row_index + 2}: {e}")
                continue
        
        return processed_data
    
    def _process_single_row(self, row_data: Dict[str, str], 
                           field_mappings: Dict[str, str],
                           model_type: str, row_number: int) -> Optional[Dict[str, Any]]:
        """
        Process a single row of data
        
        Args:
            row_data: Raw row data from sheet
            field_mappings: Field mappings
            model_type: Target model type
            row_number: Row number in sheet
            
        Returns:
            Processed row data or None if invalid
        """
        # Skip empty rows
        if not any(str(value).strip() for value in row_data.values()):
            return None
        
        # Start with base data
        processed_row = {
            'row_number': row_number,
            'raw_data': row_data.copy(),
            'field_mappings': field_mappings,
        }
        
        # Process mapped fields
        for header, field_name in field_mappings.items():
            if header in row_data:
                raw_value = row_data[header]
                processed_value = self._process_field_value(field_name, raw_value)
                
                if processed_value is not None:
                    processed_row[field_name] = processed_value
        
        # Handle unmapped fields
        self._process_unmapped_fields(processed_row, row_data, field_mappings)
        
        # Apply model-specific processing
        if model_type == 'lead':
            self._apply_lead_specific_processing(processed_row)
        elif model_type == 'contact':
            self._apply_contact_specific_processing(processed_row)
        
        # Validate required fields
        if not self._validate_required_fields(processed_row, model_type):
            return None
        
        return processed_row
    
    def _process_field_value(self, field_name: str, raw_value: str) -> Any:
        """
        Process a single field value
        
        Args:
            field_name: Target field name
            raw_value: Raw value from sheet
            
        Returns:
            Processed value or None if invalid
        """
        if not raw_value or not str(raw_value).strip():
            return None
        
        value = str(raw_value).strip()
        
        # Apply data cleaning
        if field_name in self.data_cleaners:
            value = self.data_cleaners[field_name](value)
        
        # Apply validation
        if field_name in self.field_validators:
            if not self.field_validators[field_name](value):
                return None
        
        # Apply field-specific transformations
        return self._transform_field_value(field_name, value)
    
    def _transform_field_value(self, field_name: str, value: str) -> Any:
        """
        Apply field-specific transformations
        
        Args:
            field_name: Field name
            value: Cleaned value
            
        Returns:
            Transformed value
        """
        # Decimal fields
        if field_name in ['estimated_value', 'budget']:
            try:
                # Remove currency symbols and convert
                clean_value = re.sub(r'[^\d.-]', '', value)
                return Decimal(clean_value) if clean_value else None
            except InvalidOperation:
                return None
        
        # Integer fields
        if field_name in ['lead_score']:
            try:
                return int(float(value))
            except ValueError:
                return None
        
        # Date fields
        if field_name.endswith('_date'):
            return self._parse_date_value(value)
        
        # Boolean fields
        if field_name in ['sync_enabled']:
            return value.lower() in ['true', '1', 'yes', 'y', 'on']
        
        # String fields with length limits
        max_lengths = {
            'first_name': 100,
            'last_name': 100,
            'full_name': 200,
            'email': 254,
            'phone': 50,
            'mobile': 50,
            'city': 100,
            'state': 50,
            'zip_code': 20,
            'country': 100,
            'company': 255,
            'title': 100,
            'industry': 100,
            'lead_status': 100,
            'lead_source': 100,
            'campaign': 255,
        }
        
        if field_name in max_lengths:
            max_len = max_lengths[field_name]
            return value[:max_len] if len(value) > max_len else value
        
        return value
    
    def _process_unmapped_fields(self, processed_row: Dict[str, Any], 
                                raw_data: Dict[str, str],
                                field_mappings: Dict[str, str]):
        """
        Process unmapped fields into custom fields
        
        Args:
            processed_row: Processed row data (modified in place)
            raw_data: Raw row data
            field_mappings: Field mappings
        """
        unmapped_headers = [h for h in raw_data.keys() if h not in field_mappings]
        custom_field_num = 1
        
        for header in unmapped_headers:
            if custom_field_num > 5:  # Max 5 custom fields
                break
            
            value = raw_data[header]
            if value and str(value).strip():
                custom_field_name = f"custom_field_{custom_field_num}"
                processed_row[custom_field_name] = f"{header}: {str(value).strip()}"
                custom_field_num += 1
    
    def _apply_lead_specific_processing(self, processed_row: Dict[str, Any]):
        """
        Apply lead-specific data processing
        
        Args:
            processed_row: Processed row data (modified in place)
        """
        # Generate full_name if not present
        if 'full_name' not in processed_row:
            first = processed_row.get('first_name', '').strip()
            last = processed_row.get('last_name', '').strip()
            if first or last:
                processed_row['full_name'] = f"{first} {last}".strip()
        
        # Standardize lead status
        if 'lead_status' in processed_row:
            processed_row['lead_status'] = self._standardize_lead_status(
                processed_row['lead_status']
            )
        
        # Parse and clean lead source
        if 'lead_source' in processed_row:
            processed_row['lead_source'] = self._standardize_lead_source(
                processed_row['lead_source']
            )
    
    def _apply_contact_specific_processing(self, processed_row: Dict[str, Any]):
        """
        Apply contact-specific data processing
        
        Args:
            processed_row: Processed row data (modified in place)
        """
        # Generate display_name
        if 'display_name' not in processed_row:
            first = processed_row.get('first_name', '').strip()
            last = processed_row.get('last_name', '').strip()
            if first or last:
                processed_row['display_name'] = f"{first} {last}".strip()
        
        # Handle multiple email/phone fields
        self._process_multiple_contact_fields(processed_row)
    
    def _process_multiple_contact_fields(self, processed_row: Dict[str, Any]):
        """
        Process multiple email/phone fields for contacts
        
        Args:
            processed_row: Processed row data (modified in place)
        """
        # Handle email fields
        if 'email' in processed_row and 'email_primary' not in processed_row:
            processed_row['email_primary'] = processed_row.pop('email')
        
        # Handle phone fields
        if 'phone' in processed_row and 'phone_primary' not in processed_row:
            processed_row['phone_primary'] = processed_row.pop('phone')
        
        if 'mobile' in processed_row and 'phone_secondary' not in processed_row:
            processed_row['phone_secondary'] = processed_row.pop('mobile')
    
    def _validate_required_fields(self, processed_row: Dict[str, Any], 
                                 model_type: str) -> bool:
        """
        Validate required fields are present
        
        Args:
            processed_row: Processed row data
            model_type: Model type
            
        Returns:
            True if valid, False otherwise
        """
        # Define minimum required fields for each model type
        required_fields = {
            'lead': ['email', 'phone', 'first_name', 'last_name', 'full_name'],
            'contact': ['email_primary', 'phone_primary', 'first_name', 'last_name']
        }
        
        model_required = required_fields.get(model_type, [])
        
        # Check if at least one required field group is present
        if model_type == 'lead':
            # For leads, require either email OR phone OR name
            has_contact = ('email' in processed_row or 'phone' in processed_row)
            has_name = ('first_name' in processed_row or 'last_name' in processed_row or 
                       'full_name' in processed_row)
            return has_contact or has_name
        
        elif model_type == 'contact':
            # For contacts, require either email OR phone AND some name
            has_contact = ('email_primary' in processed_row or 'phone_primary' in processed_row)
            has_name = ('first_name' in processed_row or 'last_name' in processed_row or
                       'display_name' in processed_row)
            return has_contact and has_name
        
        return True
    
    # Field validators
    def _validate_email(self, value: str) -> bool:
        """Validate email format"""
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return bool(re.match(email_pattern, value))
    
    def _validate_phone(self, value: str) -> bool:
        """Validate phone number"""
        # Remove all non-digits
        digits_only = re.sub(r'[^\d]', '', value)
        # Must have at least 7 digits
        return len(digits_only) >= 7
    
    def _validate_decimal(self, value: str) -> bool:
        """Validate decimal value"""
        try:
            float(re.sub(r'[^\d.-]', '', value))
            return True
        except ValueError:
            return False
    
    def _validate_integer(self, value: str) -> bool:
        """Validate integer value"""
        try:
            int(float(value))
            return True
        except ValueError:
            return False
    
    def _validate_zip_code(self, value: str) -> bool:
        """Validate ZIP code format"""
        # US ZIP codes (5 digits or 5+4)
        us_zip = r'^\d{5}(-\d{4})?$'
        # International postal codes (flexible)
        intl_postal = r'^[A-Za-z0-9\s-]{3,12}$'
        
        return bool(re.match(us_zip, value) or re.match(intl_postal, value))
    
    def _validate_date(self, value: str) -> bool:
        """Validate date format"""
        return self._parse_date_value(value) is not None
    
    # Data cleaners
    def _clean_email(self, value: str) -> str:
        """Clean email address"""
        return value.lower().strip()
    
    def _clean_phone(self, value: str) -> str:
        """Clean phone number"""
        # Keep digits, spaces, parentheses, hyphens, and + sign
        return re.sub(r'[^\d\s\(\)\-+]', '', value).strip()
    
    def _clean_name(self, value: str) -> str:
        """Clean name fields"""
        # Remove extra whitespace and title case
        cleaned = ' '.join(value.split())
        return cleaned.title()
    
    def _clean_company_name(self, value: str) -> str:
        """Clean company name"""
        # Remove extra whitespace but preserve original case
        return ' '.join(value.split())
    
    def _clean_address(self, value: str) -> str:
        """Clean address field"""
        # Remove extra whitespace and normalize
        return ' '.join(value.split())
    
    def _clean_city_state(self, value: str) -> str:
        """Clean city/state names"""
        return value.title().strip()
    
    def _clean_country(self, value: str) -> str:
        """Clean country name"""
        # Standardize common country name variations
        country_mappings = {
            'usa': 'United States',
            'us': 'United States',
            'united states of america': 'United States',
            'uk': 'United Kingdom',
            'britain': 'United Kingdom',
            'england': 'United Kingdom',
        }
        
        cleaned = value.lower().strip()
        return country_mappings.get(cleaned, value.title())
    
    def _clean_zip_code(self, value: str) -> str:
        """Clean ZIP/postal code"""
        # Remove extra spaces and standardize format
        cleaned = value.strip().upper()
        
        # Format US ZIP codes
        if re.match(r'^\d{9}$', cleaned):  # 9 digits, add hyphen
            cleaned = f"{cleaned[:5]}-{cleaned[5:]}"
        
        return cleaned
    
    # Utility methods
    def _parse_date_value(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime"""
        if not date_str or not str(date_str).strip():
            return None
        
        date_str = str(date_str).strip()
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
            '%B %d, %Y',  # January 1, 2023
            '%b %d, %Y',  # Jan 1, 2023
            '%d %B %Y',   # 1 January 2023
            '%d %b %Y',   # 1 Jan 2023
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        return None
    
    def _standardize_lead_status(self, status: str) -> str:
        """Standardize lead status values"""
        status_mappings = {
            'new': 'New',
            'open': 'Open',
            'contacted': 'Contacted',
            'qualified': 'Qualified',
            'unqualified': 'Unqualified',
            'nurture': 'Nurture',
            'hot': 'Hot',
            'warm': 'Warm',
            'cold': 'Cold',
            'converted': 'Converted',
            'closed': 'Closed',
            'lost': 'Lost',
            'won': 'Won',
        }
        
        normalized = status.lower().strip()
        return status_mappings.get(normalized, status.title())
    
    def _standardize_lead_source(self, source: str) -> str:
        """Standardize lead source values"""
        source_mappings = {
            'web': 'Website',
            'website': 'Website',
            'online': 'Website',
            'google': 'Google Ads',
            'facebook': 'Facebook',
            'linkedin': 'LinkedIn',
            'twitter': 'Twitter',
            'social': 'Social Media',
            'email': 'Email Marketing',
            'referral': 'Referral',
            'phone': 'Phone',
            'cold call': 'Cold Call',
            'trade show': 'Trade Show',
            'event': 'Event',
        }
        
        normalized = source.lower().strip()
        return source_mappings.get(normalized, source.title())
    
    def deduplicate_leads(self, leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate leads based on email/phone
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Deduplicated list of leads
        """
        seen_contacts = set()
        deduplicated = []
        
        for lead in leads:
            # Create unique key based on email and phone
            email = lead.get('email', '').lower().strip()
            phone = re.sub(r'[^\d]', '', lead.get('phone', ''))
            
            # Skip if no contact info
            if not email and not phone:
                continue
            
            contact_key = f"{email}|{phone}"
            
            if contact_key not in seen_contacts:
                seen_contacts.add(contact_key)
                deduplicated.append(lead)
        
        return deduplicated
