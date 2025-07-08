"""
Base data processor for all CRM integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
import logging
from django.db import transaction
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import ValidationException

logger = logging.getLogger(__name__)

class BaseDataProcessor(ABC):
    """Base class for data processing operations"""
    
    def __init__(self, model_class, **kwargs):
        self.model_class = model_class
        self.batch_size = kwargs.get('batch_size', 500)
        self.field_mappings = self.get_field_mappings()
        
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings from source to target"""
        pass
        
    @abstractmethod
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform a single record"""
        pass
        
    @abstractmethod
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a single record"""
        pass
    
    async def process_batch(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Process a batch of records"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not records:
            return results
        
        # Transform records
        transformed_records = []
        for record in records:
            try:
                transformed = self.transform_record(record)
                validated = self.validate_record(transformed)
                transformed_records.append(validated)
            except Exception as e:
                logger.warning(f"Failed to transform/validate record: {e}")
                results['failed'] += 1
                continue
        
        # Save records
        if transformed_records:
            batch_results = await self.save_records(transformed_records)
            results['created'] += batch_results.get('created', 0)
            results['updated'] += batch_results.get('updated', 0)
            results['failed'] += batch_results.get('failed', 0)
        
        return results
    
    async def save_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save records to database with bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # Use sync_to_async for database operations
            return await self._save_records_sync(records)
                
        except Exception as e:
            logger.warning(f"Bulk save failed: {e}. Falling back to individual saves.")
            # Fallback to individual saves
            individual_results = await self.save_individual_records(records)
            results.update(individual_results)
        
        return results
    
    @sync_to_async
    def _save_records_sync(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Synchronous save operation wrapped for async"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            with transaction.atomic():
                # Get existing records
                existing_ids = set()
                if records and 'id' in records[0]:
                    existing_ids = set(
                        self.model_class.objects.filter(
                            id__in=[r.get('id') for r in records if r.get('id')]
                        ).values_list('id', flat=True)
                    )
                
                to_create = []
                to_update = []
                
                for record in records:
                    record_id = record.get('id')
                    if record_id in existing_ids:
                        to_update.append(record)
                    else:
                        to_create.append(record)
                
                # Bulk create
                if to_create:
                    objects = [self.model_class(**record) for record in to_create]
                    created_objects = self.model_class.objects.bulk_create(
                        objects, batch_size=self.batch_size, ignore_conflicts=True
                    )
                    results['created'] = len(created_objects)
                
                # Bulk update using get_or_create for simplicity
                for record in to_update:
                    try:
                        obj, created = self.model_class.objects.update_or_create(
                            id=record['id'],
                            defaults=record
                        )
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    except Exception as e:
                        logger.warning(f"Failed to update record {record.get('id')}: {e}")
                        results['failed'] += 1
                        
        except Exception as e:
            logger.error(f"Database operation failed: {e}")
            results['failed'] = len(records)
        
        return results
    
    async def save_individual_records(self, records: List[Dict[str, Any]]) -> Dict[str, int]:
        """Fallback to individual record saves"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in records:
            try:
                result = await self._save_individual_record(record)
                results[result] += 1
            except Exception as e:
                logger.warning(f"Failed to save individual record: {e}")
                results['failed'] += 1
        
        return results
    
    @sync_to_async
    def _save_individual_record(self, record: Dict[str, Any]) -> str:
        """Save individual record"""
        try:
            obj, created = self.model_class.objects.update_or_create(
                id=record.get('id'),
                defaults=record
            )
            return 'created' if created else 'updated'
        except Exception as e:
            logger.error(f"Failed to save record {record.get('id')}: {e}")
            raise
