"""
Base Five9 Sync Engine
Provides common sync workflow orchestration for Five9 integrations
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import logging
from django.db import transaction
from django.utils import timezone

from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory
from ..clients.base import BaseFive9Client
from ....config.five9_config import Five9Config

logger = logging.getLogger(__name__)


class BaseFive9SyncEngine(BaseSyncEngine, ABC):
    """Base sync engine for Five9 integrations"""
    
    def __init__(self, source_name: str = "Five9", **kwargs):
        super().__init__(source_name=source_name, **kwargs)
        self.client = None
        self.batch_size = kwargs.get('batch_size', Five9Config.DEFAULT_BATCH_SIZE)
        self.max_retries = kwargs.get('max_retries', Five9Config.DEFAULT_RETRY_ATTEMPTS)
    
    def create_client(self) -> BaseFive9Client:
        """Create Five9 API client - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement create_client method")
    
    def setup(self) -> bool:
        """Setup the sync engine"""
        logger.info(f"Setting up {self.source_name} sync engine")
        
        try:
            # Create and connect client
            self.client = self.create_client()
            if not self.client.connect():
                raise ConnectionError("Failed to connect to Five9 API")
            
            logger.info("Five9 sync engine setup completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Failed to setup Five9 sync engine: {e}")
            return False
    
    def cleanup(self):
        """Cleanup resources"""
        if self.client:
            try:
                self.client.close_sessions()
            except Exception as e:
                logger.warning(f"Error closing Five9 client: {e}")
        super().cleanup()
    
    def get_last_sync_time(self, sync_type: str) -> Optional[datetime]:
        """
        Get the last successful sync time for delta syncing
        
        Args:
            sync_type: Type of sync (e.g., 'contacts', 'deals')
            
        Returns:
            Last sync datetime or None for full sync
        """
        try:
            last_sync = SyncHistory.objects.filter(
                source=self.source_name,
                sync_type=sync_type,
                status='SUCCESS'
            ).order_by('-end_time').first()
            
            if last_sync:
                logger.info(f"Last successful {sync_type} sync: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info(f"No previous successful {sync_type} sync found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting last sync time: {e}")
            return None
    
    def create_sync_history(self, sync_type: str, operation: str, **kwargs) -> SyncHistory:
        """
        Create a new sync history record
        
        Args:
            sync_type: Type of sync (e.g., 'contacts')
            operation: Operation type (e.g., 'full_sync', 'delta_sync')
            **kwargs: Additional metadata
            
        Returns:
            SyncHistory instance
        """
        sync_history = SyncHistory.objects.create(
            source=self.source_name,
            sync_type=sync_type,
            operation=operation,
            status='RUNNING',
            start_time=timezone.now(),
            metadata=kwargs
        )
        
        logger.info(f"Created sync history: {sync_history.id} ({sync_type}/{operation})")
        return sync_history
    
    def update_sync_history(self, sync_history: SyncHistory, status: str, 
                          records_processed: int = 0, errors: int = 0, **kwargs):
        """
        Update sync history record
        
        Args:
            sync_history: SyncHistory instance to update
            status: New status ('SUCCESS', 'ERROR', 'PARTIAL')
            records_processed: Number of records processed
            errors: Number of errors encountered
            **kwargs: Additional metadata updates
        """
        sync_history.status = status
        sync_history.end_time = timezone.now()
        sync_history.records_processed = records_processed
        sync_history.errors = errors
        
        # Update metadata
        if sync_history.metadata:
            sync_history.metadata.update(kwargs)
        else:
            sync_history.metadata = kwargs
        
        sync_history.save()
        
        duration = sync_history.end_time - sync_history.start_time
        logger.info(
            f"Updated sync history {sync_history.id}: {status}, "
            f"{records_processed} records, {errors} errors, "
            f"duration: {duration}"
        )
    
    def should_perform_delta_sync(self, sync_type: str, force_full: bool = False) -> bool:
        """
        Determine if delta sync should be performed
        
        Args:
            sync_type: Type of sync
            force_full: Force full sync regardless of last sync time
            
        Returns:
            True if delta sync should be performed, False for full sync
        """
        if force_full:
            logger.info("Full sync forced")
            return False
        
        last_sync_time = self.get_last_sync_time(sync_type)
        if not last_sync_time:
            logger.info("No previous sync found, performing full sync")
            return False
        
        # Check if last sync was recent enough for delta sync
        delta_threshold = timezone.now() - timedelta(days=7)  # 7 days max for delta
        if last_sync_time < delta_threshold:
            logger.info(f"Last sync too old ({last_sync_time}), performing full sync")
            return False
        
        logger.info(f"Performing delta sync since {last_sync_time}")
        return True
    
    def handle_sync_error(self, sync_history: SyncHistory, error: Exception, 
                         context: str = "") -> bool:
        """
        Handle sync errors with retry logic
        
        Args:
            sync_history: Current sync history record
            error: Exception that occurred
            context: Additional context about the error
            
        Returns:
            True if should retry, False to abort
        """
        logger.error(f"Sync error in {context}: {error}")
        
        # Update sync history with error
        self.update_sync_history(
            sync_history, 
            'ERROR', 
            error_message=str(error),
            error_context=context
        )
        
        # For now, don't implement retry logic - let the management command handle it
        return False
    
    @abstractmethod
    def sync_data(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Perform the actual data sync - to be implemented by subclasses
        
        Args:
            force_full: Force full sync instead of delta
            **kwargs: Additional sync parameters
            
        Returns:
            Dictionary with sync results
        """
        pass
    
    def run_sync(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Main sync execution method
        
        Args:
            force_full: Force full sync instead of delta
            **kwargs: Additional sync parameters
            
        Returns:
            Dictionary with sync results
        """
        logger.info(f"Starting {self.source_name} sync")
        
        if not self.setup():
            return {
                'success': False,
                'error': 'Failed to setup sync engine'
            }
        
        try:
            # Perform the sync
            result = self.sync_data(force_full=force_full, **kwargs)
            logger.info(f"{self.source_name} sync completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            self.cleanup()
