"""
Base Google Sheets Sync Engine
"""
import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.models.common import SyncHistory
from ingestion.sync.gsheet.clients.base import GoogleSheetsAPIClient

logger = logging.getLogger(__name__)


class BaseGoogleSheetsSyncEngine(BaseSyncEngine):
    """
    Base sync engine for Google Sheets following CRM sync guide architecture
    """
    
    def __init__(self, sheet_name: str, **kwargs):
        super().__init__(crm_source='gsheet', sync_type=sheet_name, **kwargs)
        
        self.sheet_name = sheet_name
        self.client = None
        self.processor = None
        
        # Configuration should be defined in subclasses as hardcoded values
        self.sheet_config = None
    
    def get_default_batch_size(self) -> int:
        """Return default batch size for Google Sheets sync"""
        return 500
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get the last successful sync timestamp using SyncHistory
        
        Returns:
            datetime: Last sync timestamp in UTC, or None if never synced
        """
        try:
            # Get most recent successful sync from SyncHistory
            sync_record = SyncHistory.objects.filter(
                crm_source='gsheet',
                sync_type=self.sheet_name,
                status='success'
            ).order_by('-end_time').first()
            
            if sync_record:
                logger.info(f"Last successful sync: {sync_record.end_time}")
                return sync_record.end_time
            
            logger.info(f"No previous sync found for sheet: {self.sheet_name}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    def get_last_sheet_modified_time(self) -> Optional[datetime]:
        """
        Get the last known sheet modification time
        
        Returns:
            datetime: Last known sheet modification time, or None
        """
        try:
            if self.sheet_config:
                return self.sheet_config.last_sheet_modified
            return None
        except Exception as e:
            logger.error(f"Error getting last sheet modified time: {e}")
            return None
    
    def should_perform_sync(self) -> Dict[str, Any]:
        """
        Determine if sync should be performed based on sheet modification time
        
        Returns:
            Dict containing sync decision and reason
        """
        try:
            # Get sheet modification time from Google
            if not self.client:
                return {
                    'should_sync': True,
                    'reason': 'No client available - assuming sync needed',
                    'sync_type': 'full'
                }
            
            current_modified = self.client.get_sheet_modification_time(
                self.client.sheet_id if hasattr(self.client, 'sheet_id') else ''
            )
            
            if not current_modified:
                return {
                    'should_sync': True,
                    'reason': 'Could not determine sheet modification time',
                    'sync_type': 'full'
                }
            
            # Get last known modification time
            last_known_modified = self.get_last_sheet_modified_time()
            
            if not last_known_modified:
                return {
                    'should_sync': True,
                    'reason': 'No previous sync - performing initial sync',
                    'sync_type': 'full',
                    'current_modified': current_modified
                }
            
            # Compare modification times
            if current_modified > last_known_modified:
                return {
                    'should_sync': True,
                    'reason': f'Sheet modified: {current_modified} > {last_known_modified}',
                    'sync_type': 'full',  # Google Sheets doesn't support delta sync
                    'current_modified': current_modified,
                    'last_modified': last_known_modified
                }
            else:
                return {
                    'should_sync': False,
                    'reason': f'Sheet not modified: {current_modified} <= {last_known_modified}',
                    'sync_type': 'none',
                    'current_modified': current_modified,
                    'last_modified': last_known_modified
                }
                
        except Exception as e:
            logger.error(f"Error determining sync necessity: {e}")
            return {
                'should_sync': True,
                'reason': f'Error checking modification time: {e}',
                'sync_type': 'full'
            }
    
    def start_sync_session(self, **kwargs) -> SyncHistory:
        """
        Start a new sync session and create SyncHistory record
        
        Returns:
            SyncHistory: Created sync history record
        """
        try:
            sync_decision = self.should_perform_sync()
            
            self.sync_history = SyncHistory.objects.create(
                crm_source='gsheet',
                sync_type=self.sheet_name,
                endpoint=f"sheets/{self.client.sheet_id if hasattr(self.client, 'sheet_id') else 'unknown'}",
                start_time=timezone.now(),
                status='running',
                configuration={
                    'sheet_name': self.sheet_name,
                    'sync_decision': sync_decision,
                    'dry_run': self.dry_run,
                    'force_overwrite': self.force_overwrite,
                    **kwargs
                }
            )
            
            logger.info(f"Started sync session {self.sync_history.id} for {self.sheet_name}")
            return self.sync_history
            
        except Exception as e:
            logger.error(f"Failed to start sync session: {e}")
            raise
    
    def complete_sync_session(self, status: str, records_processed: int = 0, 
                            records_created: int = 0, records_updated: int = 0, 
                            records_failed: int = 0, error_message: str = None):
        """
        Complete the sync session and update SyncHistory
        """
        try:
            if not self.sync_history:
                logger.warning("No sync session to complete")
                return
            
            # Update sync history
            self.sync_history.end_time = timezone.now()
            self.sync_history.status = status
            self.sync_history.records_processed = records_processed
            self.sync_history.records_created = records_created
            self.sync_history.records_updated = records_updated
            self.sync_history.records_failed = records_failed
            self.sync_history.error_message = error_message
            
            # Add performance metrics
            duration = (self.sync_history.end_time - self.sync_history.start_time).total_seconds()
            self.sync_history.performance_metrics = {
                'duration_seconds': duration,
                'records_per_second': records_processed / duration if duration > 0 else 0
            }
            
            self.sync_history.save()
            
            # Update sheet config if successful
            if status == 'success' and self.sheet_config:
                self.sheet_config.last_sync_time = self.sync_history.end_time
                
                # Update last sheet modified time from client
                if hasattr(self.client, 'get_sheet_modification_time'):
                    current_modified = self.client.get_sheet_modification_time(
                        self.client.sheet_id if hasattr(self.client, 'sheet_id') else ''
                    )
                    if current_modified:
                        self.sheet_config.last_sheet_modified = current_modified
                
                self.sheet_config.save()
            
            logger.info(f"Completed sync session {self.sync_history.id}: {status}")
            
        except Exception as e:
            logger.error(f"Failed to complete sync session: {e}")
    
    async def sync_with_retry(self, max_retries: int = 3) -> Dict[str, Any]:
        """
        Perform sync with retry logic
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict containing sync results
        """
        for attempt in range(max_retries + 1):
            try:
                result = await self.run_sync()
                return result
                
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Sync attempt {attempt + 1} failed, retrying: {e}")
                    await asyncio.sleep(2 ** attempt)  # Exponential backoff
                else:
                    logger.error(f"All sync attempts failed: {e}")
                    raise
