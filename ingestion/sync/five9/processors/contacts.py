"""
Five9 Contacts Data Processor
Transforms Five9 contact records into Django model format
"""
from typing import Dict, Any, List, Optional
import logging
from .base import BaseFive9Processor
from ....config.five9_config import (
    field_mapper, 
    Five9FieldTypes, 
    VALIDATION_RULES,
    DELTA_SYNC_CONFIG
)

logger = logging.getLogger(__name__)


class ContactsProcessor(BaseFive9Processor):
    """Processor for Five9 contact records"""
    
    def __init__(self):
        super().__init__()
        self.field_mapper = field_mapper
        self.validation_rules = VALIDATION_RULES
        # Create field mapping dictionary for faster lookups
        self.field_mapping = self._create_field_mapping()
        # Create field types mapping
        self.field_types = self._create_field_types_mapping()
    
    def _create_field_mapping(self) -> Dict[str, str]:
        """Create field mapping dictionary from field mapper"""
        mapping = {}
        for field_name in self.field_mapper.field_definitions.keys():
            django_field_name = self.field_mapper.get_django_field_name(field_name)
            mapping[field_name] = django_field_name
        return mapping
    
    def _create_field_types_mapping(self) -> Dict[str, str]:
        """Create field types mapping from field mapper"""
        types = {}
        for field_name, field_def in self.field_mapper.field_definitions.items():
            django_field_name = self.field_mapper.get_django_field_name(field_name)
            field_type = field_def.get('type', 'STRING')
            types[django_field_name] = field_type
        return types
    
    def process_contact_record(self, raw_record: Dict[str, Any], list_name: str) -> Dict[str, Any]:
        """
        Process a single Five9 contact record into Django model format
        
        Args:
            raw_record: Raw contact record from Five9 API
            list_name: Name of the source list
            
        Returns:
            Processed record ready for Django model
        """
        logger.debug(f"Processing contact record from list: {list_name}")
        
        # Start with cleaned raw record
        processed_record = self.clean_record(raw_record)
        
        # Add list_name
        processed_record['list_name'] = list_name
        
        # Transform fields using field mapping and types
        transformed_record = {}
        
        for five9_field, django_field in self.field_mapping.items():
            # Get the raw value
            raw_value = processed_record.get(five9_field)
            
            # Get the field type for processing
            field_type = self.field_types.get(django_field, 'STRING')
            
            # Process the field
            processed_value = self.process_field(django_field, raw_value, field_type)
            
            # Set the processed value
            transformed_record[django_field] = processed_value
        
        # Handle any unmapped fields (preserve with safe field names)
        for five9_field, value in processed_record.items():
            if five9_field not in self.field_mapping and five9_field != 'list_name':
                # Create safe field name
                safe_field_name = self._make_safe_field_name(five9_field)
                if safe_field_name not in transformed_record:
                    # Process as string by default
                    transformed_record[safe_field_name] = self.process_field(
                        safe_field_name, value, 'STRING'
                    )
        
        # Ensure list_name is included
        transformed_record['list_name'] = list_name
        
        logger.debug(f"Processed contact record: {len(transformed_record)} fields")
        return transformed_record
    
    def process_contact_batch(self, raw_records: List[Dict[str, Any]], list_name: str) -> List[Dict[str, Any]]:
        """
        Process a batch of Five9 contact records efficiently
        
        Args:
            raw_records: List of raw contact records from Five9 API
            list_name: Name of the source list
            
        Returns:
            List of processed records ready for Django models
        """
        if not raw_records:
            return []
        
        logger.info(f"Processing batch of {len(raw_records)} contact records from {list_name}")
        
        processed_records = []
        errors = 0
        
        # Pre-compile validation rules and field mappings for better performance
        field_mapping = self.field_mapping
        field_types = self.field_types
        
        for i, raw_record in enumerate(raw_records):
            try:
                processed_record = self._process_contact_record_optimized(raw_record, list_name, field_mapping, field_types)
                
                # Quick validation
                if processed_record.get('number1') and processed_record.get('list_name'):
                    processed_records.append(processed_record)
                else:
                    logger.warning(f"Record {i+1} missing required fields, skipping")
                    errors += 1
                    
            except Exception as e:
                logger.error(f"Error processing record {i+1}: {e}")
                errors += 1
                continue
        
        logger.info(f"Processed {len(processed_records)} records successfully, {errors} errors")
        return processed_records
    
    def _process_contact_record_optimized(self, raw_record: Dict[str, Any], list_name: str, field_mapping: Dict, field_types: Dict) -> Dict[str, Any]:
        """Optimized version of process_contact_record for batch processing"""
        processed = {}
        
        # Set list_name first
        processed['list_name'] = list_name
        
        # Process all fields efficiently using base class methods
        for field_name, value in raw_record.items():
            if field_name == 'list_name':
                continue  # Already set
            
            # Get Django field name
            django_field_name = field_mapping.get(field_name, field_name.lower())
            
            # Transform value based on field type using base class method
            if value is not None and value != '':
                field_type = field_types.get(django_field_name, 'STRING')
                processed_value = self.process_field(field_name, value, field_type)
                if processed_value is not None:
                    processed[django_field_name] = processed_value
        
        # Ensure required fields are present
        if 'number1' not in processed or not processed['number1']:
            processed['number1'] = raw_record.get('number1') or raw_record.get('phone') or ''
        
        return processed
        
        logger.info(f"Successfully processed {len(processed_records)} records, {errors} errors")
        return processed_records
    
    def _validate_contact_record(self, record: Dict[str, Any]) -> bool:
        """
        Validate a processed contact record
        
        Args:
            record: Processed contact record
            
        Returns:
            True if record is valid, False otherwise
        """
        # Must have list_name
        if not record.get('list_name'):
            logger.warning("Record missing list_name")
            return False
        
        # Should have at least one identifying field
        identifying_fields = ['contactID', 'email', 'number1', 'first_name', 'last_name']
        has_identifier = any(record.get(field) for field in identifying_fields)
        
        if not has_identifier:
            logger.warning("Record has no identifying fields")
            return False
        
        return True
    
    def _make_safe_field_name(self, field_name: str) -> str:
        """
        Convert Five9 field name to safe Django field name
        
        Args:
            field_name: Original Five9 field name
            
        Returns:
            Safe field name for Django
        """
        # Replace problematic characters
        safe_name = field_name.replace(' ', '_').replace('-', '_').replace('/', '_')
        safe_name = ''.join(char if char.isalnum() or char == '_' else '_' for char in safe_name)
        
        # Ensure it doesn't start with a digit
        if safe_name and safe_name[0].isdigit():
            safe_name = f'field_{safe_name}'
        
        # Handle empty names
        if not safe_name:
            safe_name = 'unknown_field'
        
        return safe_name
    
    def get_unique_key(self, record: Dict[str, Any]) -> Optional[str]:
        """
        Generate a unique key for a contact record
        Used for deduplication within the same list
        
        Args:
            record: Processed contact record
            
        Returns:
            Unique key string or None if can't generate
        """
        # Use contactID if available
        contact_id = record.get('contactID')
        if contact_id:
            return f"{record.get('list_name', 'unknown')}_{contact_id}"
        
        # Fallback to email
        email = record.get('email')
        if email:
            return f"{record.get('list_name', 'unknown')}_{email}"
        
        # Fallback to phone + name combination
        phone = record.get('number1')
        first_name = record.get('first_name')
        last_name = record.get('last_name')
        
        if phone and (first_name or last_name):
            name = f"{first_name or ''}_{last_name or ''}".strip('_')
            return f"{record.get('list_name', 'unknown')}_{phone}_{name}"
        
        logger.warning("Could not generate unique key for record")
        return None
    
    def deduplicate_records(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Remove duplicate records from a batch
        
        Args:
            records: List of processed records
            
        Returns:
            Deduplicated list of records
        """
        logger.info(f"Deduplicating {len(records)} records")
        
        seen_keys = set()
        deduplicated = []
        
        for record in records:
            unique_key = self.get_unique_key(record)
            if unique_key and unique_key not in seen_keys:
                seen_keys.add(unique_key)
                deduplicated.append(record)
            elif unique_key:
                logger.debug(f"Duplicate record found: {unique_key}")
            else:
                # Keep records without unique keys
                deduplicated.append(record)
        
        logger.info(f"Removed {len(records) - len(deduplicated)} duplicates")
        return deduplicated

    def validate_contact_batch(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Validate a batch of contact records and return valid ones
        
        Args:
            records: List of processed contact records
            
        Returns:
            List of valid contact records
        """
        logger.info(f"Validating batch of {len(records)} contact records")
        
        if not records:
            logger.warning("Empty batch provided for validation")
            return []
        
        valid_records = []
        for i, record in enumerate(records):
            if self._validate_contact_record(record):
                valid_records.append(record)
            else:
                logger.warning(f"Record {i+1} in batch failed validation, skipping")
        
        validation_ratio = len(valid_records) / len(records) if records else 0
        logger.info(f"Batch validation: {len(valid_records)}/{len(records)} records valid ({validation_ratio:.2%})")
        
        return valid_records
