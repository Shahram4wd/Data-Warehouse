import logging
from datetime import datetime
from typing import Optional, Dict, Any
from django.utils import timezone
from ingestion.models.salesrabbit import SalesRabbit_SyncHistory

logger = logging.getLogger(__name__)

class BaseSalesRabbitProcessor:
    """Base class for SalesRabbit data processing"""
    def __init__(self, sync_type: str):
        self.sync_type = sync_type
        self.sync_history: Optional[SalesRabbit_SyncHistory] = None

    def start_sync(self, api_endpoint: Optional[str] = None, query_params: Optional[Dict] = None) -> SalesRabbit_SyncHistory:
        self.sync_history = SalesRabbit_SyncHistory.objects.create(
            sync_type=self.sync_type,
            api_endpoint=api_endpoint,
            query_params=query_params or {},
            status='in_progress'
        )
        logger.info(f"Started {self.sync_type} sync with ID {self.sync_history.id}")
        return self.sync_history

    def complete_sync(self, records_processed: int = 0, records_created: int = 0, records_updated: int = 0):
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.records_processed = records_processed
            self.sync_history.records_created = records_created
            self.sync_history.records_updated = records_updated
            self.sync_history.status = 'completed'
            self.sync_history.save()
            logger.info(f"Completed {self.sync_type} sync: {records_processed} processed, {records_created} created, {records_updated} updated")

    def fail_sync(self, error_message: str):
        if self.sync_history:
            self.sync_history.completed_at = timezone.now()
            self.sync_history.status = 'failed'
            self.sync_history.error_message = error_message
            self.sync_history.save()
            logger.error(f"Failed {self.sync_type} sync: {error_message}")
