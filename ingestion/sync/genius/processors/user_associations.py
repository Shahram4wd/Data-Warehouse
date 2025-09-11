"""
User associations data processor for Genius CRM synchronization  
"""
import logging
from typing import Dict, Any, List, Optional
from django.utils import timezone
from django.db import transaction

from .base import GeniusBaseProcessor

logger = logging.getLogger(__name__)

class GeniusUserAssociationsProcessor(GeniusBaseProcessor):
    """Processor for transforming and upserting user associations data"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
        self.model_class = model_class
        
    def process_batch(self, batch_data: List[Dict[str, Any]], field_mapping: Dict[str, str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process batch of user associations using bulk operations for efficiency
        
        Args:
            batch_data: List of raw user associations records from database
            field_mapping: Mapping of source fields to model fields
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform dry run without database changes
            
        Returns:
            Dictionary containing processing statistics
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        # Transform all records first
        transformed_records = []
        record_ids = []
        
        for raw_record in batch_data:
            try:
                transformed_record = self.transform_record(raw_record, field_mapping)
                if transformed_record:
                    transformed_records.append(transformed_record)
                    record_ids.append(transformed_record['id'])
                    
            except Exception as e:
                logger.error(f"Error transforming user association record: {e}")
                stats['errors'] += 1
        
        if dry_run:
            stats['total_processed'] = len(transformed_records)
            logger.info(f"DRY RUN: Would process {len(transformed_records)} user associations")
            return stats
        
        # Use bulk operations for efficiency
        try:
            with transaction.atomic():
                if force_overwrite:
                    # Delete existing records and bulk create
                    self.model_class.objects.filter(id__in=record_ids).delete()
                    self.model_class.objects.bulk_create([
                        self.model_class(**record) for record in transformed_records
                    ])
                    stats['created'] = len(transformed_records)
                else:
                    # Use bulk_create with update_conflicts for upsert behavior  
                    created_objects = self.model_class.objects.bulk_create(
                        [self.model_class(**record) for record in transformed_records],
                        update_conflicts=True,
                        update_fields=[
                            'user_id', 'definition_id', 'division_id', 'field_value',
                            'created_at', 'updated_at', 'sync_updated_at'
                        ],
                        unique_fields=['id']
                    )
                    
                    # Count created vs updated based on bulk_create result
                    stats['created'] = len(created_objects)
                    stats['updated'] = len(transformed_records) - len(created_objects)
                
                stats['total_processed'] = len(transformed_records)
                
        except Exception as e:
            logger.error(f"Error in bulk user associations processing: {e}")
            stats['errors'] += len(transformed_records)
        
        return stats
    
    def transform_record(self, raw_record: tuple, field_mapping: Dict[str, str]) -> Optional[Dict[str, Any]]:
        """
        Transform raw user associations record to model format
        
        Args:
            raw_record: Raw record tuple from database (id, primary_user_id, created_at, updated_at)
            field_mapping: Field mapping configuration
            
        Returns:
            Transformed record ready for model creation
        """
        try:
            transformed = {}
            
            # Map tuple fields to dictionary based on position and field_mapping
            # raw_record structure: (id, primary_user_id, created_at, updated_at)
            field_positions = {
                'id': 0,
                'primary_user_id': 1, 
                'created_at': 2,
                'updated_at': 3
            }
            
            # Map fields based on field_mapping and positions
            for source_field, target_field in field_mapping.items():
                if source_field in field_positions:
                    position = field_positions[source_field]
                    value = raw_record[position] if len(raw_record) > position else None
                    
                    # Handle datetime fields - ensure timezone awareness  
                    if target_field in ['created_at', 'updated_at'] and value:
                        if hasattr(value, 'replace') and value.tzinfo is None:
                            value = timezone.make_aware(value, timezone.get_current_timezone())
                    
                    transformed[target_field] = value
            
            # Set default values for fields that don't exist in source table but are required by model
            if 'definition_id' not in transformed:
                transformed['definition_id'] = None
            if 'division_id' not in transformed:
                transformed['division_id'] = None
            if 'field_value' not in transformed:
                transformed['field_value'] = None
            
            # Set sync timestamps
            transformed['sync_updated_at'] = timezone.now()
            if 'sync_created_at' not in transformed:
                transformed['sync_created_at'] = timezone.now()
            
            return transformed
            
        except Exception as e:
            record_id = raw_record[0] if raw_record and len(raw_record) > 0 else 'unknown'
            logger.error(f"Error transforming user associations record {record_id}: {e}")
            return None
