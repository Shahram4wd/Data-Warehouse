"""
Base service class for Genius CRM business logic
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from abc import ABC, abstractmethod
from django.db import transaction

logger = logging.getLogger(__name__)


class GeniusBaseService(ABC):
    """Base service class for Genius CRM business operations"""
    
    @abstractmethod
    def get_field_mappings(self) -> Dict[str, str]:
        """Get field mappings from source to destination"""
        pass
    
    @abstractmethod
    def get_bulk_update_fields(self) -> List[str]:
        """Get fields that should be included in bulk updates"""
        pass
    
    @abstractmethod
    def validate_record(self, raw_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate raw record data"""
        pass
    
    @abstractmethod
    def transform_record(self, validated_data: Dict[str, Any]) -> Dict[str, Any]:
        """Transform validated data to model format"""
        pass
    
    @abstractmethod
    def prepare_bulk_data(self, transformed_records: List[Dict[str, Any]]) -> Tuple[List[Any], List[Dict[str, Any]]]:
        """Prepare data for bulk operations"""
        pass
    
    def validate_and_transform_batch(self, raw_batch: List[tuple]) -> List[Dict[str, Any]]:
        """Validate and transform a batch of raw records"""
        processed_records = []
        
        # Convert tuples to dictionaries using field mappings
        field_names = list(self.get_field_mappings().keys())
        
        for raw_record in raw_batch:
            try:
                # Convert tuple to dict
                if isinstance(raw_record, tuple):
                    record_dict = dict(zip(field_names, raw_record))
                else:
                    record_dict = raw_record
                
                # Validate record
                validated_data = self.validate_record(record_dict)
                
                # Skip if validation fails
                if validated_data is None:
                    logger.debug("Skipped invalid record")
                    continue
                
                # Transform record
                transformed_data = self.transform_record(validated_data)
                processed_records.append(transformed_data)
                
            except Exception as e:
                logger.error(f"Error processing record: {e}")
                logger.error(f"Raw record: {raw_record}")
                continue
        
        return processed_records
    
    def bulk_upsert_records(self, transformed_records: List[Dict[str, Any]], force_overwrite: bool = False) -> Dict[str, Any]:
        """Perform bulk upsert operations"""
        stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0
        }
        
        if not transformed_records:
            return stats
        
        try:
            # Prepare bulk data
            objects_for_create, data_for_update = self.prepare_bulk_data(transformed_records)
            
            # Get model class from the first object
            model_class = type(objects_for_create[0]) if objects_for_create else None
            
            if not model_class:
                logger.error("Could not determine model class for bulk operations")
                stats['errors'] = len(transformed_records)
                return stats
            
            with transaction.atomic():
                # Extract lead_ids for querying existing records
                lead_ids = [obj.lead_id for obj in objects_for_create]
                
                # Get existing records
                existing_records = {
                    record.lead_id: record 
                    for record in model_class.objects.filter(lead_id__in=lead_ids)
                }
                
                # Separate into creates and updates
                creates = []
                updates = []
                
                for i, obj in enumerate(objects_for_create):
                    if obj.lead_id in existing_records:
                        # Record exists - check if we should update
                        existing_record = existing_records[obj.lead_id]
                        if self._should_update_record(existing_record, data_for_update[i], force_overwrite):
                            updates.append(data_for_update[i])
                        else:
                            stats['skipped'] += 1
                    else:
                        # New record
                        creates.append(obj)
                
                # Perform bulk create
                if creates:
                    model_class.objects.bulk_create(creates, ignore_conflicts=True)
                    stats['created'] = len(creates)
                    logger.info(f"Created {len(creates)} new records")
                
                # Perform bulk update
                if updates:
                    # Update existing records
                    for update_data in updates:
                        lead_id = update_data.pop('lead_id')
                        model_class.objects.filter(lead_id=lead_id).update(**update_data)
                    
                    stats['updated'] = len(updates)
                    logger.info(f"Updated {len(updates)} existing records")
        
        except Exception as e:
            logger.error(f"Error in bulk_upsert_records: {e}")
            stats['errors'] = len(transformed_records)
            raise
        
        return stats
    
    def _should_update_record(self, existing_record, new_data: Dict[str, Any], force_overwrite: bool = False) -> bool:
        """Determine if a record should be updated"""
        if force_overwrite:
            return True
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and hasattr(existing_record, 'updated_at') and 
            existing_record.updated_at and new_data['updated_at'] > existing_record.updated_at):
            return True
        
        return False
