"""
Marketing Leads Sync Engine for Google Sheets

Follows CRM sync guide architecture with SyncHistory integration.
Configuration is hardcoded here, not stored in database.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from django.utils import timezone
from ingestion.models.common import SyncHistory  # Use global SyncHistory table
from ingestion.models.gsheet import GoogleSheetMarketingLead
from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient
from ingestion.sync.gsheet.processors.marketing_leads import MarketingLeadsProcessor
from ingestion.sync.gsheet.engines.base import BaseGoogleSheetsSyncEngine

logger = logging.getLogger(__name__)


class MarketingLeadsSyncEngine(BaseGoogleSheetsSyncEngine):
    """
    Sync engine for Marketing Source Leads from Google Sheets
    
    Configuration (hardcoded as per CRM sync guide):
    - Sheet ID: 1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo
    - Tab: "Marketing Source Leads"
    - Model: GoogleSheetMarketingLead
    - CRM Source: 'gsheet_marketing_leads'
    """
    
    # HARDCODED CONFIGURATION (as per CRM sync guide)
    SHEET_CONFIG = {
        'sheet_id': '1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo',
        'tab_name': 'Marketing Source Leads',
        'header_row': 1,
        'data_start_row': 2,
        'target_model': GoogleSheetMarketingLead,
        'crm_source': 'gsheet_marketing_leads',  # For SyncHistory table
    }
    
    def __init__(self, batch_size: int = 500, dry_run: bool = False, force_overwrite: bool = False):
        """Initialize the marketing leads sync engine"""
        
        super().__init__(
            sheet_name='marketing_leads',
            batch_size=batch_size,
            dry_run=dry_run,
            force_overwrite=force_overwrite
        )
        
        # Initialize components with hardcoded config
        self.client = MarketingLeadsClient(
            sheet_id=self.SHEET_CONFIG['sheet_id'],
            tab_name=self.SHEET_CONFIG['tab_name']
        )
        
        self.processor = MarketingLeadsProcessor()
        self.model = self.SHEET_CONFIG['target_model']
        self.crm_source = self.SHEET_CONFIG['crm_source']
        
        logger.info(f"Initialized MarketingLeadsSyncEngine")
        logger.info(f"Sheet ID: {self.SHEET_CONFIG['sheet_id']}")
        logger.info(f"Tab: {self.SHEET_CONFIG['tab_name']}")
        logger.info(f"CRM Source: {self.crm_source}")
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get last successful sync timestamp from global SyncHistory table
        
        Returns:
            datetime: Last sync time or None if never synced
        """
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='gsheet',
                sync_type='marketing_leads',
                status='success'
            ).order_by('-end_time').first()
            
            if last_sync and last_sync.end_time:
                logger.info(f"Last successful sync: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info("No previous successful sync found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    def create_sync_history_record(self) -> SyncHistory:
        """
        Create new SyncHistory record for this sync operation
        
        Returns:
            SyncHistory: New sync history record
        """
        return SyncHistory.objects.create(
            crm_source='gsheet',
            sync_type='marketing_leads',
            endpoint=f"sheets/{self.SHEET_CONFIG['sheet_id']}/{self.SHEET_CONFIG['tab_name']}",
            configuration={
                'sheet_id': self.SHEET_CONFIG['sheet_id'],
                'tab_name': self.SHEET_CONFIG['tab_name'],
                'model': self.model.__name__,
                'batch_size': self.batch_size,
                'dry_run': self.dry_run,
                'force_overwrite': self.force_overwrite
            },
            status='running',
            start_time=timezone.now()
        )
    
    def update_sync_history_record(self, sync_record: SyncHistory, 
                                 status: str, stats: Dict[str, Any]):
        """
        Update SyncHistory record with completion status and statistics
        
        Args:
            sync_record: SyncHistory record to update
            status: Final status ('success', 'failed', 'partial')
            stats: Sync statistics dictionary
        """
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('records_processed', 0)
        sync_record.records_created = stats.get('records_created', 0)
        sync_record.records_updated = stats.get('records_updated', 0)
        sync_record.records_failed = stats.get('records_failed', 0)
        
        if status == 'failed' and 'error_message' in stats:
            sync_record.error_message = stats['error_message']
        
        # Add performance metrics
        duration = (sync_record.end_time - sync_record.start_time).total_seconds()
        sync_record.performance_metrics = {
            'duration_seconds': duration,
            'records_per_second': sync_record.records_processed / duration if duration > 0 else 0
        }
        
        sync_record.save()
        
        logger.info(f"Updated SyncHistory record {sync_record.id} with status: {status}")
    
    async def sync_with_retry(self, max_retries: int = 2) -> Dict[str, Any]:
        """
        Execute sync with retry logic and SyncHistory tracking
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict: Sync result with status and statistics
        """
        
        # Create SyncHistory record
        sync_record = self.create_sync_history_record()
        
        try:
            # Check if sync is needed (unless forced)
            if not self.force_overwrite:
                if not await self.client.is_sheet_modified_since(self.get_last_sync_timestamp()):
                    stats = {'status': 'skipped', 'reason': 'Sheet not modified since last sync'}
                    self.update_sync_history_record(sync_record, 'skipped', stats)
                    return stats
            
            # Execute sync
            result = await self.sync()
            
            # Update SyncHistory with success
            self.update_sync_history_record(sync_record, 'success', result)
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            
            # Update SyncHistory with failure
            error_stats = {
                'status': 'failed',
                'error_message': str(e),
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0
            }
            
            self.update_sync_history_record(sync_record, 'failed', error_stats)
            
            raise

    # Abstract method implementations required by BaseSyncEngine
    
    async def initialize_client(self) -> None:
        """Initialize the Google Sheets API client"""
        try:
            from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient
            self.client = MarketingLeadsClient(
                sheet_id=self.SHEET_CONFIG['sheet_id'],
                tab_name=self.SHEET_CONFIG['tab_name']
            )
            await self.client.initialize()
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from Google Sheets"""
        if not self.client:
            await self.initialize_client()
        
        try:
            last_sync_time = kwargs.get('last_sync_time') or self.get_last_sync_timestamp()
            data = await self.client.fetch_sheet_data(
                last_modified_since=last_sync_time,
                force_refresh=self.force_overwrite
            )
            logger.info(f"Fetched {len(data)} rows from Google Sheets")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw sheet data to model format"""
        try:
            processor = MarketingLeadsProcessor()
            transformed_data = []
            
            for row_data in raw_data:
                transformed_row = await processor.process_row(row_data)
                if transformed_row:
                    transformed_data.append(transformed_row)
            
            logger.info(f"Transformed {len(transformed_data)} rows")
            return transformed_data
        except Exception as e:
            logger.error(f"Failed to transform data: {e}")
            raise
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        try:
            from ingestion.sync.gsheet.validators.marketing_leads import MarketingLeadsValidator
            validator = MarketingLeadsValidator()
            
            validated_data = []
            for row_data in data:
                if await validator.validate_row(row_data):
                    validated_data.append(row_data)
                else:
                    logger.warning(f"Validation failed for row: {row_data}")
            
            logger.info(f"Validated {len(validated_data)} rows")
            return validated_data
        except Exception as e:
            logger.error(f"Failed to validate data: {e}")
            raise
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save validated data to database"""
        try:
            processor = MarketingLeadsProcessor()
            result = await processor.bulk_save(validated_data, batch_size=self.batch_size)
            
            logger.info(f"Saved data: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        try:
            if self.client:
                await self.client.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
            # Don't raise exception during cleanup
