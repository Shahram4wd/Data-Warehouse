"""
Arrivy Bookings Sync Engine

Handles synchronization of Arrivy bookings following enterprise patterns.
Bookings represent scheduled appointments and service bookings.
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from .base import ArrivyBaseSyncEngine
from ..clients.bookings import ArrivyBookingsClient
from ..processors.bookings import BookingsProcessor
from ingestion.models.arrivy import Arrivy_Booking

logger = logging.getLogger(__name__)

class ArrivyBookingsSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy bookings"""
    
    def __init__(self, **kwargs):
        super().__init__('bookings', **kwargs)
        self.client_class = ArrivyBookingsClient
        self.processor = BookingsProcessor()
    
    def get_model_class(self):
        """Get Django model class for bookings"""
        return Arrivy_Booking
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch bookings data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of booking records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching bookings with last_sync={last_sync}, batch_size={self.batch_size}")
        
        # Use bookings endpoint
        logger.info("Using bookings endpoint")
        async for batch in client.fetch_bookings(
            last_sync=last_sync,
            page_size=self.batch_size,
            max_records=self.max_records
        ):
            if self.dry_run:
                logger.info(f"DRY RUN: Would process {len(batch)} bookings")
                continue
                
            yield batch
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute bookings sync with booking-specific options
        
        Args:
            **kwargs: Sync options including:
                - start_date: Start date for filtering
                - end_date: End date for filtering
                - booking_status: Status filter
                - booking_id: Specific booking ID
        
        Returns:
            Sync results
        """
        # Set booking-specific configuration
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        self.booking_status = kwargs.get('booking_status')
        self.booking_id = kwargs.get('booking_id')
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add booking-specific metrics
        results['endpoint_used'] = 'bookings'
        results['filters'] = {
            'start_date': str(self.start_date) if self.start_date else None,
            'end_date': str(self.end_date) if self.end_date else None,
            'booking_status': self.booking_status,
            'booking_id': self.booking_id
        }
        
        return results

    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of booking records using the base engine's bulk operations
        """
        logger.debug(f"Processing batch of {len(batch)} booking records")
        
        # Initialize results
        results = {
            'processed': len(batch),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        # Transform records
        processed_batch = []
        failed_count = 0
        
        for record in batch:
            try:
                transformed = self.processor.transform_record(record)
                processed_batch.append(transformed)
            except Exception as e:
                logger.warning(f"Failed to transform booking record {record.get('id', 'unknown')}: {e}")
                failed_count += 1
                results['errors'].append(str(e))
        
        # Use parent's bulk upsert method for actual database operations
        if processed_batch:
            bulk_results = await self._save_batch(processed_batch)
            results['created'] = bulk_results.get('created', 0)
            results['updated'] = bulk_results.get('updated', 0)
            results['failed'] += bulk_results.get('failed', 0) + failed_count
            logger.info(f"Booking batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
        else:
            results['failed'] = failed_count
            logger.warning(f"No valid records to process. {failed_count} records failed transformation.")
        
        return results
