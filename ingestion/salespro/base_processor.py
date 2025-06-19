"""
Base processor for SalesPro data imports.
"""
import logging
from datetime import datetime
from typing import Optional
from django.utils import timezone
from ingestion.models.salespro import SalesPro_SyncHistory

logger = logging.getLogger(__name__)


class BaseSalesProProcessor:
    """Base class for SalesPro data processing"""
    
    def __init__(self, sync_type: str):
        self.sync_type = sync_type
        self.sync_history = None
        
    def start_sync(self, file_path: Optional[str] = None) -> SalesPro_SyncHistory:
        """Start a new sync process and create history record"""
        self.sync_history = SalesPro_SyncHistory.objects.create(
            sync_type=self.sync_type,
            file_path=file_path,
            status='in_progress'
        )
        logger.info(f"Started {self.sync_type} sync with ID {self.sync_history.id}")
        return self.sync_history
    
    def complete_sync(self, records_processed: int = 0, records_created: int = 0, records_updated: int = 0):
        """Complete the sync process successfully"""
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.records_processed = records_processed
            self.sync_history.records_created = records_created
            self.sync_history.records_updated = records_updated
            self.sync_history.status = 'completed'
            self.sync_history.save()
            logger.info(f"Completed {self.sync_type} sync: {records_processed} processed, "
                       f"{records_created} created, {records_updated} updated")
    
    def fail_sync(self, error_message: str):
        """Mark the sync as failed with error message"""
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.status = 'failed'
            self.sync_history.error_message = error_message
            self.sync_history.save()
            logger.error(f"Failed {self.sync_type} sync: {error_message}")
    
    def parse_datetime(self, value: str) -> Optional[datetime]:
        """Parse ISO datetime string"""
        if not value or not str(value).strip():
            return None
        try:
            # Handle ISO format like "2025-06-06T00:16:45.538Z"
            if value.endswith('Z'):
                value = value[:-1] + '+00:00'
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {value}")
            return None
    
    def parse_decimal(self, value) -> Optional[float]:
        """Parse decimal value, handling empty strings"""
        if not value or not str(value).strip():
            return None
        try:
            return float(str(value).strip())
        except (ValueError, TypeError):
            logger.warning(f"Could not parse decimal: {value}")
            return None
    
    def parse_boolean(self, value) -> bool:
        """Parse boolean value from string"""
        if not value:
            return False
        return str(value).upper() in ('TRUE', '1', 'YES', 'Y')
