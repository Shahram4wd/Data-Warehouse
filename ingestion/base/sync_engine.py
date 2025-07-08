"""
Universal sync engine base class for all CRM operations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, AsyncGenerator
import asyncio
import logging
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException

logger = logging.getLogger(__name__)

class BaseSyncEngine(ABC):
    """Universal base class for all CRM sync operations"""
    
    def __init__(self, crm_source: str, sync_type: str, **kwargs):
        self.crm_source = crm_source
        self.sync_type = sync_type
        self.batch_size = kwargs.get('batch_size', self.get_default_batch_size())
        self.dry_run = kwargs.get('dry_run', False)
        self.sync_history = None
        self.client = None
        self.processor = None
        
    @abstractmethod
    def get_default_batch_size(self) -> int:
        """Return default batch size for this sync type"""
        pass
        
    @abstractmethod
    async def initialize_client(self) -> None:
        """Initialize the API client or database connection"""
        pass
        
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch data from source system in batches"""
        pass
        
    @abstractmethod
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw data to target format"""
        pass
        
    @abstractmethod
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        pass
        
    @abstractmethod
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data to database"""
        pass
        
    @abstractmethod
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        pass
    
    # Common sync workflow methods
    async def start_sync(self, **kwargs):
        """Start sync operation and create history record"""
        from ingestion.models.common import SyncHistory
        
        self.sync_history = await sync_to_async(SyncHistory.objects.create)(
            crm_source=self.crm_source,
            sync_type=self.sync_type,
            endpoint=kwargs.get('endpoint'),
            start_time=timezone.now(),
            status='running',
            configuration=kwargs
        )
        return self.sync_history
    
    async def complete_sync(self, results: Dict[str, int], error: Optional[str] = None):
        """Complete sync operation and update history"""
        if self.sync_history:
            self.sync_history.end_time = timezone.now()
            self.sync_history.status = 'failed' if error else 'success'
            self.sync_history.records_processed = results.get('processed', 0)
            self.sync_history.records_created = results.get('created', 0)
            self.sync_history.records_updated = results.get('updated', 0)
            self.sync_history.records_failed = results.get('failed', 0)
            self.sync_history.error_message = error
            
            # Calculate performance metrics
            if self.sync_history.end_time and self.sync_history.start_time:
                duration = (self.sync_history.end_time - self.sync_history.start_time).total_seconds()
                records_per_second = results.get('processed', 0) / max(1, duration)
            else:
                duration = 0
                records_per_second = 0
                
            self.sync_history.performance_metrics = {
                'duration_seconds': duration,
                'records_per_second': records_per_second
            }
            
            await sync_to_async(self.sync_history.save)()
    
    async def run_sync(self, **kwargs):
        """Main sync execution method"""
        history = await self.start_sync(**kwargs)
        results = {'processed': 0, 'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            await self.initialize_client()
            
            batch_count = 0
            async for batch in self.fetch_data(**kwargs):
                batch_count += 1
                logger.info(f"Processing batch {batch_count} with {len(batch)} records")
                
                try:
                    # Transform data
                    transformed_batch = await self.transform_data(batch)
                    
                    # Validate data
                    validated_batch = await self.validate_data(transformed_batch)
                    
                    # Save data
                    if not self.dry_run:
                        batch_results = await self.save_data(validated_batch)
                        for key, value in batch_results.items():
                            if key in results:
                                results[key] += value
                    
                    results['processed'] += len(batch)
                    
                    logger.info(f"Batch {batch_count} completed: {len(batch)} processed")
                    
                except Exception as e:
                    logger.error(f"Error processing batch {batch_count}: {e}")
                    results['failed'] += len(batch)
                    await self.handle_batch_error(batch, e)
            
            await self.complete_sync(results)
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            await self.complete_sync(results, str(e))
            raise
        finally:
            await self.cleanup()
        
        return history
    
    async def handle_batch_error(self, batch: List[Dict], error: Exception):
        """Handle batch processing errors with fallback to individual processing"""
        logger.warning(f"Attempting individual record processing for failed batch: {error}")
        
        for record in batch:
            try:
                transformed = await self.transform_data([record])
                validated = await self.validate_data(transformed)
                if not self.dry_run:
                    await self.save_data(validated)
            except Exception as individual_error:
                logger.error(f"Individual record processing failed: {individual_error}")
                pass
