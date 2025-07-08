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

# Global flag to track if connection pools are initialized
_connection_pools_initialized = False

async def ensure_connection_pools_initialized():
    """Ensure connection pools are initialized (lazy loading)"""
    global _connection_pools_initialized
    
    if not _connection_pools_initialized:
        try:
            from ingestion.base.connection_pool import initialize_connection_pools
            await initialize_connection_pools()
            _connection_pools_initialized = True
            logger.info("Connection pools initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize connection pools: {e}")
            # Don't fail the entire application if connection pools can't be initialized

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
        
        # Prepare configuration for JSON serialization
        config = kwargs.copy()
        
        # Convert datetime to string for JSON serialization
        if 'last_sync' in config and config['last_sync']:
            config['last_sync'] = config['last_sync'].isoformat()
        
        self.sync_history = await sync_to_async(SyncHistory.objects.create)(
            crm_source=self.crm_source,
            sync_type=self.sync_type,
            endpoint=kwargs.get('endpoint'),
            start_time=timezone.now(),
            status='running',
            configuration=config
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
        """Main sync execution method with progress tracking"""
        from tqdm.asyncio import tqdm
        
        history = await self.start_sync(**kwargs)
        results = {'processed': 0, 'created': 0, 'updated': 0, 'failed': 0}
        show_progress = kwargs.get('show_progress', True)
        
        try:
            await self.initialize_client()
            
            # Get estimated total count if possible
            estimated_total = kwargs.get('max_records', 0)
            if estimated_total == 0:
                estimated_total = await self.estimate_total_records(**kwargs)
            
            batch_count = 0
            progress_bar = None
            
            if estimated_total > 0 and show_progress:
                progress_bar = tqdm(
                    total=estimated_total,
                    desc=f"Syncing {self.sync_type}",
                    unit="records",
                    bar_format="{desc}: {percentage:3.0f}%|{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}]"
                )
            
            try:
                async for batch in self.fetch_data(**kwargs):
                    batch_count += 1
                    logger.info(f"Processing batch {batch_count} with {len(batch)} records")
                    
                    try:
                        # Transform data
                        transformed_batch = await self.transform_data(batch)
                        
                        # Validate data
                        validated_batch = await self.validate_data(transformed_batch)
                        
                        # Save data using bulk operations
                        if not self.dry_run:
                            batch_results = await self.save_data_bulk(validated_batch)
                            for key, value in batch_results.items():
                                if key in results:
                                    results[key] += value
                        
                        results['processed'] += len(batch)
                        
                        # Update progress bar
                        if progress_bar:
                            progress_bar.update(len(batch))
                        
                        logger.info(f"Batch {batch_count} completed: {len(batch)} processed")
                        
                    except Exception as e:
                        logger.error(f"Error processing batch {batch_count}: {e}")
                        results['failed'] += len(batch)
                        if progress_bar:
                            progress_bar.update(len(batch))
                        await self.handle_batch_error(batch, e)
                
            finally:
                if progress_bar:
                    progress_bar.close()
            
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
    
    async def estimate_total_records(self, **kwargs) -> int:
        """Estimate total number of records to be synced"""
        # Default implementation returns 0 (unknown)
        # Subclasses should override this for better progress tracking
        return 0
    
    async def save_data_bulk(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data using bulk operations - to be implemented by subclasses"""
        # Fallback to regular save_data if not implemented
        return await self.save_data(validated_data)
