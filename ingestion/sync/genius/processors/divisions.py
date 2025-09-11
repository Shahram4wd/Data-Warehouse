"""
Divisions processor for Genius CRM data transformation with bulk operations
"""
import logging
from typing import Dict, Any, List, Tuple
from datetime import datetime
from django.utils.dateparse import parse_datetime
from django.db import transaction

logger = logging.getLogger(__name__)


class GeniusDivisionsProcessor:
    """Processor for Genius divisions data with bulk operations"""
    
    def __init__(self, model):
        self.model = model
    
    def process_batch(self, batch_data: List[Tuple], field_mapping: Dict[str, int], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """Process a batch of divisions using bulk operations"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not batch_data:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(batch_data)} division records")
            stats['total_processed'] = len(batch_data)
            stats['created'] = len(batch_data)  # Assume all would be created in dry run
            return stats
        
        # Transform raw data to model instances
        divisions_to_create = []
        
        for row_data in batch_data:
            try:
                # Transform tuple to dictionary using field mapping
                division_dict = self._transform_row(row_data, field_mapping)
                
                # Create model instance
                division = self.model(
                    id=division_dict.get('id'),
                    group_id=division_dict.get('group_id'),
                    region_id=division_dict.get('region_id'),
                    label=division_dict.get('label'),
                    abbreviation=division_dict.get('abbreviation'),
                    is_utility=division_dict.get('is_utility', False),
                    is_corp=division_dict.get('is_corp', False),
                    is_omniscient=division_dict.get('is_omniscient', False),
                    is_inactive=division_dict.get('is_inactive', False),
                    account_scheduler_id=division_dict.get('account_scheduler_id'),
                    created_at=division_dict.get('created_at'),
                    updated_at=division_dict.get('updated_at')
                )
                
                divisions_to_create.append(division)
                stats['total_processed'] += 1
                
            except Exception as e:
                logger.error(f"Error processing division record {row_data}: {e}")
                stats['errors'] += 1
                continue
        
        # Bulk create with conflict handling
        if divisions_to_create:
            try:
                with transaction.atomic():
                    if force_overwrite:
                        # Use bulk_create with update_conflicts for upsert behavior
                        result = self.model.objects.bulk_create(
                            divisions_to_create,
                            update_conflicts=True,
                            update_fields=['group_id', 'region_id', 'label', 'abbreviation', 
                                         'is_utility', 'is_corp', 'is_omniscient', 'is_inactive',
                                         'account_scheduler_id', 'created_at', 'updated_at'],
                            unique_fields=['id']
                        )
                        stats['created'] = len(result)
                        stats['updated'] = len(result)  # In force mode, treat as both
                    else:
                        # Use bulk_create with ignore_conflicts to skip existing
                        result = self.model.objects.bulk_create(
                            divisions_to_create,
                            ignore_conflicts=True
                        )
                        stats['created'] = len(result)
                
                # Django's bulk_create returns the created objects, but count may vary based on conflicts
                logger.info(f"Successfully bulk created {len(result)} divisions")
                
            except Exception as e:
                logger.error(f"Error in bulk_create for divisions: {e}")
                stats['errors'] += len(divisions_to_create)
        
        return stats
    
    def _transform_row(self, row_data: Tuple, field_mapping: Dict[str, int]) -> Dict[str, Any]:
        """Transform a single row of data into a dictionary"""
        result = {}
        
        for field_name, index in field_mapping.items():
            if index < len(row_data):
                value = row_data[index]
                
                # Handle datetime fields
                if field_name in ['created_at', 'updated_at'] and value:
                    if isinstance(value, str):
                        try:
                            result[field_name] = parse_datetime(value)
                        except (ValueError, TypeError):
                            result[field_name] = value
                    else:
                        result[field_name] = value
                # Handle boolean fields
                elif field_name in ['is_utility', 'is_corp', 'is_omniscient', 'is_inactive']:
                    result[field_name] = bool(value) if value is not None else False
                else:
                    result[field_name] = value
        
        return result
