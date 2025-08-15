"""
Arrivy Bookings API Client

Handles booking-specific operations for Arrivy API.
Bookings represent scheduled appointments and service bookings.
"""

from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging

from .base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyBookingsClient(ArrivyBaseClient):
    """Client for Arrivy bookings API operations"""
    
    async def fetch_bookings(self, last_sync: Optional[datetime] = None,
                            start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None,
                            page_size: int = 100,
                            max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch bookings from Arrivy API with delta sync support
        
        Args:
            last_sync: Last sync timestamp for delta sync
            start_date: Filter bookings from this date
            end_date: Filter bookings until this date
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of booking records
        """
        logger.info(f"Fetching bookings with page_size={page_size}, last_sync={last_sync}")
        
        params = {}
        
        # Add date range filters if provided
        if start_date:
            params["start_date"] = start_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        if end_date:
            params["end_date"] = end_date.strftime("%Y-%m-%dT%H:%M:%SZ")
        
        records_fetched = 0
        
        async for batch in self.fetch_paginated_data(
            endpoint="bookings",  # Use bookings endpoint for bookings data
            last_sync=last_sync,
            page_size=page_size,
            **params  # Unpack params directly
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
                
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} bookings (total: {records_fetched})")
            yield batch
            
            # If we got less than page_size, we've reached the end
            if len(batch) < page_size:
                break
    
    async def fetch_booking_by_id(self, booking_id: str) -> Optional[Dict]:
        """
        Fetch a single booking by ID
        
        Args:
            booking_id: The booking ID to fetch
            
        Returns:
            Booking data or None if not found
        """
        logger.info(f"Fetching booking by ID: {booking_id}")
        
        try:
            response = await self.fetch_paginated_data(
                endpoint=f"bookings/{booking_id}",
                last_sync=None,
                page_size=1
            )
            
            # Get first (and only) batch
            async for batch in response:
                if batch and len(batch) > 0:
                    return batch[0]
                break
            
            return None
            
        except Exception as e:
            logger.error(f"Error fetching booking {booking_id}: {str(e)}")
            return None
    
    async def fetch_bookings_for_date_range(self, start_date: datetime, end_date: datetime,
                                           page_size: int = 100) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch bookings for a specific date range
        
        Args:
            start_date: Start date for the range
            end_date: End date for the range
            page_size: Records per page
            
        Yields:
            Batches of booking records
        """
        logger.info(f"Fetching bookings for date range: {start_date} to {end_date}")
        
        async for batch in self.fetch_bookings(
            start_date=start_date,
            end_date=end_date,
            page_size=page_size
        ):
            yield batch
    
    async def fetch_bookings_delta(self, last_sync: datetime,
                                  page_size: int = 100) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch bookings that have been updated since last sync
        
        Args:
            last_sync: Last sync timestamp
            page_size: Records per page
            
        Yields:
            Batches of booking records
        """
        logger.info(f"Fetching bookings delta since: {last_sync}")
        
        async for batch in self.fetch_bookings(
            last_sync=last_sync,
            page_size=page_size
        ):
            yield batch
