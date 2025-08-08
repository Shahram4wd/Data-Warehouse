"""
Base Google Sheets Data Processor
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

from ingestion.base.processor import BaseDataProcessor

logger = logging.getLogger(__name__)


class BaseGoogleSheetsProcessor(BaseDataProcessor):
    """
    Base processor for Google Sheets data following CRM sync guide architecture
    """
    
    def __init__(self, model_class, **kwargs):
        super().__init__(model_class, **kwargs)
        
        # Google Sheets specific settings
        self.preserve_raw_data = kwargs.get('preserve_raw_data', True)
        self.auto_detect_fields = kwargs.get('auto_detect_fields', True)
        
    def get_field_mappings(self) -> Dict[str, str]:
        """
        Base field mappings for Google Sheets data
        
        Returns:
            Dict mapping source fields to target model fields
        """
        return {
            # Meta fields
            '_sheet_row_number': 'sheet_row_number',
            '_sheet_last_modified': 'sheet_last_modified',
            '_sheet_id': None,  # Don't map this to model field
            '_tab_name': None,  # Don't map this to model field
        }
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform a raw Google Sheets record
        
        Args:
            record: Raw record from Google Sheets client
            
        Returns:
            Transformed record ready for validation
        """
        try:
            transformed = {}
            field_mappings = self.get_field_mappings()
            
            # Apply field mappings
            for source_field, target_field in field_mappings.items():
                if target_field and source_field in record:
                    transformed[target_field] = record[source_field]
            
            # Store complete raw data if enabled
            if self.preserve_raw_data:
                # Remove internal fields from raw data
                raw_data = {
                    k: v for k, v in record.items() 
                    if not k.startswith('_')
                }
                transformed['raw_data'] = raw_data
            
            # Auto-detect and map remaining fields if enabled
            if self.auto_detect_fields:
                for field_name, field_value in record.items():
                    if field_name.startswith('_'):
                        continue  # Skip internal fields
                    
                    # Convert field name to model-friendly format
                    model_field_name = self._normalize_field_name(field_name)
                    
                    # Only add if not already mapped
                    if model_field_name not in transformed:
                        transformed[model_field_name] = self._clean_field_value(field_value)
            
            # Add metadata
            transformed['created_at'] = timezone.now()
            transformed['updated_at'] = timezone.now()
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming record: {e}")
            raise
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a transformed record
        
        Args:
            record: Transformed record
            
        Returns:
            Validated record
        """
        try:
            validated = record.copy()
            
            # Basic validation
            if not validated.get('raw_data'):
                logger.warning("Record missing raw_data")
            
            # Validate sheet metadata
            if validated.get('sheet_row_number'):
                try:
                    validated['sheet_row_number'] = int(validated['sheet_row_number'])
                except (ValueError, TypeError):
                    logger.warning(f"Invalid sheet_row_number: {validated.get('sheet_row_number')}")
                    validated['sheet_row_number'] = None
            
            # Validate and convert sheet_last_modified
            if validated.get('sheet_last_modified'):
                if isinstance(validated['sheet_last_modified'], str):
                    try:
                        validated['sheet_last_modified'] = datetime.fromisoformat(
                            validated['sheet_last_modified'].replace('Z', '+00:00')
                        )
                    except ValueError:
                        logger.warning(f"Invalid sheet_last_modified format: {validated.get('sheet_last_modified')}")
                        validated['sheet_last_modified'] = None
            
            # Truncate text fields to avoid database errors
            validated = self._truncate_text_fields(validated)
            
            return validated
            
        except Exception as e:
            logger.error(f"Error validating record: {e}")
            raise
    
    def _normalize_field_name(self, field_name: str) -> str:
        """
        Convert Google Sheets field name to Django model field name
        
        Args:
            field_name: Original field name from sheet
            
        Returns:
            Normalized field name for model
        """
        # Convert to lowercase and replace spaces/special chars with underscores
        normalized = field_name.lower()
        normalized = ''.join(c if c.isalnum() else '_' for c in normalized)
        
        # Remove multiple consecutive underscores
        while '__' in normalized:
            normalized = normalized.replace('__', '_')
        
        # Remove leading/trailing underscores
        normalized = normalized.strip('_')
        
        # Ensure it doesn't start with a number
        if normalized and normalized[0].isdigit():
            normalized = f"field_{normalized}"
        
        return normalized
    
    def _clean_field_value(self, value: Any) -> str:
        """
        Clean and convert field value to string
        
        Args:
            value: Raw field value
            
        Returns:
            Cleaned string value
        """
        if value is None:
            return ''
        
        if isinstance(value, str):
            return value.strip()
        
        return str(value)
    
    def _truncate_text_fields(self, record: Dict[str, Any], max_length: int = 255) -> Dict[str, Any]:
        """
        Truncate text fields to prevent database errors
        
        Args:
            record: Record to process
            max_length: Maximum length for text fields
            
        Returns:
            Record with truncated fields
        """
        truncated = record.copy()
        
        for field_name, field_value in truncated.items():
            if isinstance(field_value, str) and len(field_value) > max_length:
                truncated[field_name] = field_value[:max_length]
                logger.warning(f"Truncated field {field_name} from {len(field_value)} to {max_length} characters")
        
        return truncated
    
    async def process_batch(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Process a batch of Google Sheets records
        
        Args:
            records: List of raw records from Google Sheets
            
        Returns:
            Dict with processing statistics
        """
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not records:
            return results
        
        logger.info(f"Processing batch of {len(records)} records")
        
        # Transform and validate all records first
        processed_records = []
        for i, record in enumerate(records):
            try:
                transformed = self.transform_record(record)
                validated = self.validate_record(transformed)
                processed_records.append(validated)
            except Exception as e:
                logger.error(f"Failed to process record {i + 1}: {e}")
                results['failed'] += 1
        
        if not processed_records:
            logger.warning("No valid records to save")
            return results
        
        # Save to database
        try:
            from django.db import transaction
            
            with transaction.atomic():
                # For Google Sheets, we typically do full replacement
                # since we can't track individual row changes
                
                # Clear existing data (if not dry run)
                existing_count = self.model_class.objects.count()
                if existing_count > 0:
                    logger.info(f"Clearing {existing_count} existing records")
                    self.model_class.objects.all().delete()
                
                # Create new records
                new_objects = []
                for record_data in processed_records:
                    try:
                        # Remove fields that don't exist on the model
                        model_fields = [f.name for f in self.model_class._meta.fields]
                        filtered_data = {
                            k: v for k, v in record_data.items() 
                            if k in model_fields
                        }
                        
                        obj = self.model_class(**filtered_data)
                        new_objects.append(obj)
                        
                    except Exception as e:
                        logger.error(f"Failed to create model instance: {e}")
                        results['failed'] += 1
                
                # Bulk create
                if new_objects:
                    created_objects = self.model_class.objects.bulk_create(
                        new_objects, 
                        batch_size=self.batch_size
                    )
                    results['created'] = len(created_objects)
                    logger.info(f"Created {results['created']} new records")
                
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            raise
        
        return results
