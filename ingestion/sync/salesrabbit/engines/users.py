"""
SalesRabbit users sync engine following framework standards
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List, AsyncGenerator
from django.utils import timezone
from asgiref.sync import sync_to_async

from .base import SalesRabbitBaseSyncEngine
from ..clients.users import SalesRabbitUsersClient
from ..processors.users import SalesRabbitUsersProcessor
from ingestion.models.salesrabbit import SalesRabbit_User
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class SalesRabbitUserSyncEngine(SalesRabbitBaseSyncEngine):
    """Sync engine for SalesRabbit users using framework standards"""
    
    def __init__(self, **kwargs):
        super().__init__('users', **kwargs)
        self.client = SalesRabbitUsersClient()
        self.processor = SalesRabbitUsersProcessor()
        self.model_class = SalesRabbit_User
    
    async def initialize_client(self) -> None:
        """Initialize the API client"""
        await self.client.authenticate()
    
    async def validate_connection(self) -> bool:
        """Test API connection"""
        return await self.client.validate_connection()
    
    async def get_estimated_count(self, last_sync: Optional[datetime] = None) -> int:
        """Get estimated record count for progress tracking"""
        try:
            return await self.client.get_user_count_since(last_sync)
        except Exception as e:
            logger.warning(f"Could not get estimated user count: {e}")
            return 0
    
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch users data with incremental sync support - page by page"""
        last_sync = kwargs.get('last_sync')
        limit = kwargs.get('limit', 1000)
        max_records = kwargs.get('max_records', 0)
        
        try:
            # Initialize client for direct pagination control
            await self.client.authenticate()
            
            # Use page-by-page fetching instead of collecting all data first
            page = 0  # SalesRabbit API uses 0-indexed pages
            total_fetched = 0
            previous_data_hash = None  # Track duplicate responses
            
            async with self.client as client:
                while True:
                    # Stop if we've reached max_records
                    if max_records > 0 and total_fetched >= max_records:
                        logger.info(f"Reached max_records limit: {max_records}")
                        break
                    
                    # Calculate how many records to request this page
                    page_limit = limit
                    if max_records > 0:
                        remaining = max_records - total_fetched
                        page_limit = min(limit, remaining)
                    
                    # Prepare API parameters
                    params = {'limit': page_limit, 'page': page}
                    
                    # Add date filter if doing incremental sync
                    extra_headers = {}
                    if last_sync:
                        # Use If-Modified-Since header for server-side filtering
                        date_param = last_sync.strftime('%Y-%m-%dT%H:%M:%S+00:00')
                        extra_headers['If-Modified-Since'] = date_param
                        logger.info(f"Using If-Modified-Since: {date_param}")
                    
                    logger.info(f"Fetching page {page} with params: {params}")
                    
                    # Make API request for this page
                    try:
                        if extra_headers:
                            response = await client.make_request('GET', '/users', params=params, headers=extra_headers)
                        else:
                            response = await client.make_request('GET', '/users', params=params)
                        
                        # Handle different response formats
                        if isinstance(response, list):
                            data = response
                        elif isinstance(response, dict):
                            data = response.get('data', response.get('users', []))
                        else:
                            data = []
                        
                        # If no data, we're done
                        if not data:
                            logger.info(f"No data returned on page {page}, ending pagination")
                            break
                        
                        # Check for duplicate responses (SalesRabbit Users API returns all users on every page)
                        if len(data) > 0:
                            # Create a hash of all user IDs to detect exact duplicates
                            current_ids = set(user.get('id') for user in data if user.get('id'))
                            current_data_hash = f"{len(data)}-{min(current_ids) if current_ids else 'none'}-{max(current_ids) if current_ids else 'none'}"
                            
                            if previous_data_hash == current_data_hash and page > 1:
                                logger.warning(f"Detected identical response on page {page} (same {len(data)} users as page {page-1}). "
                                             f"SalesRabbit Users API appears to return all users on every page regardless of pagination.")
                                logger.info(f"Total unique users available: {len(data)}. Stopping pagination to avoid duplicates.")
                                break
                            previous_data_hash = current_data_hash
                        
                        # Limit data to max_records if needed
                        if max_records > 0:
                            remaining = max_records - total_fetched
                            data = data[:remaining]
                        
                        logger.info(f"Page {page}: fetched {len(data)} records")
                        total_fetched += len(data)
                        
                        # Yield this page's data for immediate processing
                        if data:
                            yield data
                        
                        # If we got less than requested, we're done
                        if len(data) < page_limit:
                            logger.info(f"Received {len(data)} < {page_limit} requested, ending pagination")
                            break
                        
                        page += 1
                        
                        # Add rate limiting delay
                        await asyncio.sleep(self.client.rate_limit_delay)
                        
                    except Exception as e:
                        logger.error(f"Error fetching page {page}: {e}")
                        raise
            
            logger.info(f"Total users fetched: {total_fetched}")
                
        except Exception as e:
            logger.error(f"Error in fetch_data: {e}")
            raise
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform and validate a batch of users"""
        transformed_batch = []
        
        for record in raw_data:
            try:
                # Transform record
                transformed = self.processor.transform_record(record)
                transformed_batch.append(transformed)
                
            except Exception as e:
                logger.error(f"Error processing user record {record.get('id', 'unknown')}: {e}")
                continue
        
        return transformed_batch
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        validated_batch = []
        
        for record in data:
            try:
                # Validate record
                validated = self.processor.validate_record(record)
                
                # Prepare for save
                clean_record = self.processor.prepare_for_save(validated)
                
                validated_batch.append(clean_record)
                
            except Exception as e:
                logger.error(f"Error validating user record {record.get('id', 'unknown')}: {e}")
                continue
        
        return validated_batch
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save a batch of users to database using bulk operations"""
        if not validated_data:
            return {'created': 0, 'updated': 0, 'failed': 0}
        
        @sync_to_async
        def _save_batch_sync():
            # Use the processor's bulk save method
            return self.processor.save_data(
                validated_data, 
                batch_size=100, 
                force_overwrite=self.force_overwrite
            )
        
        return await _save_batch_sync()
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        if self.client:
            # Close any open connections
            pass
    
    async def cleanup_old_records(self, cutoff_date: datetime) -> int:
        """Clean up old records that are no longer in the source system"""
        @sync_to_async
        def _cleanup_sync():
            deleted_count = SalesRabbit_User.objects.filter(
                sync_updated_at__lt=cutoff_date
            ).count()
            
            if deleted_count > 0:
                SalesRabbit_User.objects.filter(
                    sync_updated_at__lt=cutoff_date
                ).delete()
                logger.info(f"Cleaned up {deleted_count} old user records")
            
            return deleted_count
        
        return await _cleanup_sync()
    
    def get_sync_type_name(self) -> str:
        """Return the sync type name for SyncHistory"""
        return 'users'
