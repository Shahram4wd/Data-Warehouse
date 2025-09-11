"""
Genius User Titles Data Processor
"""
import logging
from typing import Dict, Any, List, Optional, Tuple
from django.utils import timezone
from django.db import IntegrityError

logger = logging.getLogger(__name__)


class GeniusUserTitlesProcessor:
    """Processor for Genius user title data with bulk operations"""
    
    def __init__(self, model_class):
        self.model = model_class
    
    def transform_record(self, raw_data: Tuple, field_mapping: Dict[str, int]) -> Dict[str, Any]:
        """Transform raw database tuple to model data"""
        record = {}
        
        # Map fields using field mapping
        for field_name, column_index in field_mapping.items():
            if column_index < len(raw_data):
                record[field_name] = raw_data[column_index]
        
        # Convert timezone-naive datetimes to timezone-aware
        if record.get('created_at'):
            record['created_at'] = self.convert_timezone_aware(record['created_at'])
        
        if record.get('updated_at'):
            record['updated_at'] = self.convert_timezone_aware(record['updated_at'])
        
        # Ensure boolean fields are properly converted
        record['is_active'] = bool(record.get('is_active', True))
        record['is_unique_per_division'] = bool(record.get('is_unique_per_division', False))
        
        # Ensure integer fields have defaults
        record['type_id'] = record.get('type_id') or 0
        record['sort'] = record.get('sort') or 0
        
        return record
    
    def convert_timezone_aware(self, dt):
        """Convert timezone-naive datetime to timezone-aware"""
        if dt and not timezone.is_aware(dt):
            return timezone.make_aware(dt)
        return dt
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean user title record data"""
        # Required fields validation
        if not record_data.get('id'):
            raise ValueError("User Title ID is required")
            
        # Clean string fields with length limits
        if record_data.get('title'):
            record_data['title'] = str(record_data['title']).strip()[:100]
        if record_data.get('abbreviation'):
            record_data['abbreviation'] = str(record_data['abbreviation']).strip()[:10]
        if record_data.get('roles'):
            record_data['roles'] = str(record_data['roles']).strip()[:256]
        
        # Ensure required datetime fields exist
        if not record_data.get('created_at'):
            record_data['created_at'] = timezone.now()
        if not record_data.get('updated_at'):
            record_data['updated_at'] = timezone.now()
        
        return record_data
    
    def process_batch(self, batch_data: List[Tuple], field_mapping: Dict[str, int], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of user title records using bulk operations"""
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        instances_to_create = []
        
        for raw_row in batch_data:
            try:
                # Transform raw data to record dict
                record_data = self.transform_record(raw_row, field_mapping)
                
                # Validate record
                record_data = self.validate_record(record_data)
                
                # Create model instance
                instance = self.model(
                    id=record_data['id'],
                    title=record_data.get('title'),
                    abbreviation=record_data.get('abbreviation'),
                    roles=record_data.get('roles'),
                    type_id=record_data.get('type_id', 0),
                    section_id=record_data.get('section_id'),
                    sort=record_data.get('sort', 0),
                    pay_component_group_id=record_data.get('pay_component_group_id'),
                    is_active=record_data.get('is_active', True),
                    is_unique_per_division=record_data.get('is_unique_per_division', False),
                    created_at=record_data.get('created_at'),
                    updated_at=record_data.get('updated_at')
                )
                
                instances_to_create.append(instance)
                stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing user title record {raw_row[0] if raw_row else 'unknown'}: {e}")
                stats['errors'] += 1
        
        # Save to database (unless dry run)
        if not dry_run and instances_to_create:
            try:
                if force_overwrite:
                    # Use bulk_create with update_conflicts for upsert behavior
                    result = self.model.objects.bulk_create(
                        instances_to_create,
                        update_conflicts=True,
                        update_fields=[
                            'title', 'abbreviation', 'roles', 'type_id', 'section_id', 'sort',
                            'pay_component_group_id', 'is_active', 'is_unique_per_division',
                            'created_at', 'updated_at'
                        ],
                        unique_fields=['id']
                    )
                else:
                    # Use bulk_create with ignore_conflicts to skip existing
                    result = self.model.objects.bulk_create(
                        instances_to_create,
                        ignore_conflicts=True
                    )
                
                # Django's bulk_create returns the created objects, but count may vary based on conflicts
                created_count = len(instances_to_create)
                stats['created'] = created_count
                
                if force_overwrite:
                    logger.info(f"Bulk upserted {created_count} user title records")
                else:
                    logger.info(f"Bulk created {created_count} new user title records (existing skipped)")
                    
            except IntegrityError as e:
                logger.error(f"Bulk create operation failed with integrity error: {e}")
                # Fallback to individual processing
                stats = self._process_individually(instances_to_create, force_overwrite, stats)
            except Exception as e:
                logger.error(f"Bulk create operation failed: {e}")
                stats['errors'] += len(instances_to_create)
        elif dry_run:
            logger.info(f"DRY RUN: Would process {len(instances_to_create)} user title records")
            stats['created'] = len(instances_to_create)
        
        return stats
    
    def _process_individually(self, instances: List, force_overwrite: bool, stats: Dict[str, int]) -> Dict[str, int]:
        """Fallback individual processing when bulk operations fail"""
        stats['created'] = 0  # Reset since bulk failed
        
        for instance in instances:
            try:
                if force_overwrite:
                    # Try to update existing, create if not found
                    obj, created = self.model.objects.update_or_create(
                        id=instance.id,
                        defaults={
                            'title': instance.title,
                            'abbreviation': instance.abbreviation,
                            'roles': instance.roles,
                            'type_id': instance.type_id,
                            'section_id': instance.section_id,
                            'sort': instance.sort,
                            'pay_component_group_id': instance.pay_component_group_id,
                            'is_active': instance.is_active,
                            'is_unique_per_division': instance.is_unique_per_division,
                            'created_at': instance.created_at,
                            'updated_at': instance.updated_at
                        }
                    )
                    if created:
                        stats['created'] += 1
                    else:
                        stats['updated'] += 1
                else:
                    # Try to create, skip if exists
                    try:
                        instance.save()
                        stats['created'] += 1
                    except IntegrityError:
                        # Record already exists, skip
                        pass
                        
            except Exception as e:
                logger.error(f"Failed to save user title {instance.id}: {e}")
                stats['errors'] += 1
        
        return stats
