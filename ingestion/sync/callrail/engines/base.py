"""
Base sync engine for CallRail CRM integration following the CRM sync guide architecture
"""
import logging
from typing import Dict, Any, List, Optional
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.base.sync_engine import BaseSyncEngine

logger = logging.getLogger(__name__)


class CallRailBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for CallRail with common functionality"""
    
    def __init__(self, **kwargs):
        """
        Initialize CallRail sync engine
        
        Args:
            **kwargs: Additional arguments passed to parent
        """
        super().__init__(crm_source='callrail', sync_type='callrail', **kwargs)
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for CallRail sync"""
        return 100
        
    async def initialize_client(self) -> None:
        """Initialize the CallRail API client"""
        # This will be implemented by subclasses
        pass
        
    async def fetch_data(self, **kwargs):
        """Fetch data from CallRail API - implemented by subclasses"""
        # This will be implemented by subclasses
        yield []
        
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform CallRail data - implemented by subclasses"""
        return raw_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate CallRail data - implemented by subclasses"""
        return data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save CallRail data - implemented by subclasses"""
        return {'created': 0, 'updated': 0}
        
    async def cleanup(self) -> None:
        """Cleanup CallRail sync resources"""
        pass
        
    def get_sync_params(self) -> Dict[str, Any]:
        """Get parameters for sync operation"""
        return {
            'dry_run': getattr(self, 'dry_run', False),
            'force': getattr(self, 'force', False),
        }
    
    @sync_to_async
    def bulk_save_records(self, records: List[Dict], model_class, primary_key: str) -> Dict[str, int]:
        """
        Efficient bulk save records to database following CRM sync guide standards
        Uses Django bulk_create and bulk_update for maximum performance
        
        Args:
            records: List of record dictionaries to save
            model_class: Django model class to save to
            primary_key: Primary key field name for upsert logic
            
        Returns:
            Dict with 'created', 'updated', 'errors' counts and 'error_details' list
        """
        if not records:
            return {'created': 0, 'updated': 0, 'errors': 0, 'error_details': []}
        
        logger.info(f"Bulk saving {len(records)} records using efficient bulk operations")
        
        # First, try efficient bulk operations following CRM sync guide
        try:
            return self._efficient_bulk_save(records, model_class, primary_key)
        except Exception as e:
            logger.warning(f"Bulk operations failed, falling back to individual saves: {e}")
            return self._individual_save_fallback(records, model_class, primary_key)
    
    def _efficient_bulk_save(self, records: List[Dict], model_class, primary_key: str) -> Dict[str, int]:
        """Efficient bulk save using Django bulk_create and bulk_update"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []
        
        # Get all primary key values to check for existing records
        record_keys = [r.get(primary_key) for r in records if r.get(primary_key)]
        if not record_keys:
            error_details.append(f"No valid records with {primary_key} found")
            return {'created': 0, 'updated': 0, 'errors': len(records), 'error_details': error_details}
        
        # Get existing records in a single query
        existing_records = {
            getattr(obj, primary_key): obj 
            for obj in model_class.objects.filter(**{f"{primary_key}__in": record_keys})
        }
        
        to_create = []
        to_update = []
        
        # Categorize records for bulk operations
        for record in records:
            key_value = record.get(primary_key)
            if not key_value:
                error_count += 1
                error_details.append(f"Missing primary key {primary_key}")
                continue
                
            try:
                if key_value in existing_records:
                    # Update existing record
                    existing_obj = existing_records[key_value]
                    for field, value in record.items():
                        if hasattr(existing_obj, field):
                            setattr(existing_obj, field, value)
                    to_update.append(existing_obj)
                else:
                    # Create new record
                    to_create.append(model_class(**record))
                    
            except Exception as e:
                error_count += 1
                error_details.append(f"Record {key_value}: {str(e)}")
                continue
        
        # Execute bulk operations following CRM sync guide patterns
        with transaction.atomic():
            # Bulk create new records
            if to_create:
                try:
                    created_objects = model_class.objects.bulk_create(
                        to_create, 
                        batch_size=100,  # Standard batch size from CRM sync guide
                        ignore_conflicts=True
                    )
                    created_count = len(created_objects)
                    logger.info(f"Bulk created {created_count} new records")
                except Exception as e:
                    logger.error(f"Bulk create failed: {e}")
                    error_count += len(to_create)
                    error_details.append(f"Bulk create failed: {str(e)}")
            
            # Bulk update existing records
            if to_update:
                try:
                    # Get all field names except the primary key for updating
                    update_fields = []
                    if records:
                        update_fields = [f for f in records[0].keys() if f != primary_key]
                    
                    if update_fields:
                        model_class.objects.bulk_update(
                            to_update, 
                            fields=update_fields,
                            batch_size=100  # Standard batch size from CRM sync guide
                        )
                        updated_count = len(to_update)
                        logger.info(f"Bulk updated {updated_count} existing records")
                    else:
                        logger.warning("No fields to update")
                        
                except Exception as e:
                    logger.error(f"Bulk update failed: {e}")
                    error_count += len(to_update)
                    error_details.append(f"Bulk update failed: {str(e)}")
        
        logger.info(f"Efficient bulk save completed: {created_count} created, {updated_count} updated, {error_count} errors")
        
        return {
            'created': created_count,
            'updated': updated_count, 
            'errors': error_count,
            'error_details': error_details
        }
    
    def _individual_save_fallback(self, records: List[Dict], model_class, primary_key: str) -> Dict[str, int]:
        """Fallback to individual saves if bulk operations fail"""
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []
        
        logger.warning(f"Using individual save fallback for {len(records)} records")
        
        with transaction.atomic():
            for record in records:
                if not record.get(primary_key):
                    error_count += 1
                    error_details.append(f"Missing primary key {primary_key}")
                    continue
                    
                try:
                    # Try to get existing record
                    existing = model_class.objects.filter(**{primary_key: record[primary_key]}).first()
                    
                    if existing:
                        # Update existing record
                        for field, value in record.items():
                            if hasattr(existing, field):
                                setattr(existing, field, value)
                        existing.save()
                        updated_count += 1
                    else:
                        # Create new record
                        model_class.objects.create(**record)
                        created_count += 1
                        
                except Exception as e:
                    logger.error(f"Error saving record {record.get(primary_key)}: {e}")
                    error_count += 1
                    error_details.append(f"Record {record.get(primary_key)}: {str(e)}")
                    continue
        
        return {
            'created': created_count, 
            'updated': updated_count,
            'errors': error_count,
            'error_details': error_details
        }
