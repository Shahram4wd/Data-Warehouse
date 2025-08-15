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
        Execute bookings sync with comprehensive error handling
        
        Returns:
            Dict containing sync results and metrics
        """
        try:
            logger.info(f"Starting Arrivy bookings sync - dry_run={self.dry_run}")
            
            # Initialize sync tracking
            sync_history = await self.initialize_sync_tracking()
            start_time = datetime.now()
            
            # Get last sync timestamp
            last_sync = sync_history.last_synced_at if sync_history else None
            logger.info(f"Last sync timestamp: {last_sync}")
            
            # Initialize metrics
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_errors = 0
            batch_count = 0
            
            try:
                # Process data in batches
                async for batch in self.fetch_data(last_sync=last_sync):
                    batch_count += 1
                    logger.info(f"Processing batch {batch_count} with {len(batch)} bookings")
                    
                    # Process batch through processor
                    batch_results = await self.process_batch(batch)
                    
                    # Update metrics
                    total_processed += batch_results['processed']
                    total_created += batch_results['created']
                    total_updated += batch_results['updated']
                    total_errors += batch_results['errors']
                    
                    logger.info(f"Batch {batch_count} results: {batch_results}")
                    
                    # Optional batch delay to avoid rate limiting
                    if self.batch_delay and batch_count > 1:
                        logger.debug(f"Sleeping {self.batch_delay}s between batches")
                        await asyncio.sleep(self.batch_delay)
                
                # Calculate sync duration
                sync_duration = datetime.now() - start_time
                
                # Prepare results
                results = {
                    'sync_type': 'bookings',
                    'status': 'completed',
                    'total_processed': total_processed,
                    'total_created': total_created,
                    'total_updated': total_updated,
                    'total_errors': total_errors,
                    'batch_count': batch_count,
                    'sync_duration': sync_duration.total_seconds(),
                    'dry_run': self.dry_run,
                    'start_time': start_time,
                    'end_time': datetime.now()
                }
                
                # Update sync history if not dry run
                if not self.dry_run:
                    await self.finalize_sync_tracking(sync_history, results)
                
                logger.info(f"Bookings sync completed: {results}")
                return results
                
            except Exception as e:
                logger.error(f"Error during bookings sync: {str(e)}")
                
                # Record failure
                results = {
                    'sync_type': 'bookings',
                    'status': 'failed',
                    'error': str(e),
                    'total_processed': total_processed,
                    'total_created': total_created,
                    'total_updated': total_updated,
                    'total_errors': total_errors,
                    'batch_count': batch_count,
                    'dry_run': self.dry_run,
                    'start_time': start_time,
                    'end_time': datetime.now()
                }
                
                # Update sync history with failure if not dry run
                if not self.dry_run:
                    await self.finalize_sync_tracking(sync_history, results)
                
                raise
                
        except Exception as e:
            logger.error(f"Critical error in bookings sync: {str(e)}")
            raise
    
    async def sync_booking_by_id(self, booking_id: str) -> Dict[str, Any]:
        """
        Sync a single booking by ID
        
        Args:
            booking_id: The booking ID to sync
            
        Returns:
            Dict containing sync results
        """
        try:
            logger.info(f"Syncing individual booking: {booking_id}")
            
            client = await self.initialize_client()
            booking_data = await client.fetch_booking_by_id(booking_id)
            
            if not booking_data:
                logger.warning(f"Booking {booking_id} not found in API")
                return {
                    'status': 'not_found',
                    'booking_id': booking_id,
                    'message': 'Booking not found in API'
                }
            
            # Process single record
            batch_results = await self.process_batch([booking_data])
            
            return {
                'status': 'completed',
                'booking_id': booking_id,
                'results': batch_results
            }
            
        except Exception as e:
            logger.error(f"Error syncing booking {booking_id}: {str(e)}")
            return {
                'status': 'error',
                'booking_id': booking_id,
                'error': str(e)
            }
    
    async def sync_bookings_for_date_range(self, start_date: datetime, end_date: datetime) -> Dict[str, Any]:
        """
        Sync bookings for a specific date range
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            
        Returns:
            Dict containing sync results
        """
        try:
            logger.info(f"Syncing bookings for date range: {start_date} to {end_date}")
            
            client = await self.initialize_client()
            
            # Initialize metrics
            total_processed = 0
            total_created = 0
            total_updated = 0
            total_errors = 0
            batch_count = 0
            
            # Process bookings in date range
            async for batch in client.fetch_bookings_for_date_range(start_date, end_date, self.batch_size):
                batch_count += 1
                logger.info(f"Processing date range batch {batch_count} with {len(batch)} bookings")
                
                # Process batch
                batch_results = await self.process_batch(batch)
                
                # Update metrics
                total_processed += batch_results['processed']
                total_created += batch_results['created']
                total_updated += batch_results['updated']
                total_errors += batch_results['errors']
            
            return {
                'status': 'completed',
                'date_range': f"{start_date} to {end_date}",
                'total_processed': total_processed,
                'total_created': total_created,
                'total_updated': total_updated,
                'total_errors': total_errors,
                'batch_count': batch_count
            }
            
        except Exception as e:
            logger.error(f"Error syncing bookings for date range: {str(e)}")
            return {
                'status': 'error',
                'error': str(e),
                'date_range': f"{start_date} to {end_date}"
            }
