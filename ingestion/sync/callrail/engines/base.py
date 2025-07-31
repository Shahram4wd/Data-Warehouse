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
        Bulk save records to database with create/update logic
        
        Args:
            records: List of record dictionaries to save
            model_class: Django model class to save to
            primary_key: Primary key field name for upsert logic
            
        Returns:
            Dict with 'created', 'updated', 'errors' counts and 'error_details' list
        """
        created_count = 0
        updated_count = 0
        error_count = 0
        error_details = []
        
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
