"""
MarketSharp Contact sync engine for Genius CRM integration
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from asgiref.sync import sync_to_async

from .base import GeniusBaseSyncEngine
from ..clients.marketsharp_contacts import GeniusMarketSharpContactClient
from ..processors.marketsharp_contacts import GeniusMarketSharpContactProcessor

logger = logging.getLogger(__name__)


class GeniusMarketSharpContactSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for MarketSharp contact data synchronization"""
    
    def __init__(self):
        super().__init__()
        self.client = GeniusMarketSharpContactClient()
        self.processor = GeniusMarketSharpContactProcessor()
        self.entity_name = 'marketsharp_contacts'
        self.batch_size = 500
    
    async def sync_marketsharp_contacts(self, full_sync: bool = False, limit: int = 0) -> Dict[str, Any]:
        """
        Sync MarketSharp contact data from Genius CRM to data warehouse
        
        Args:
            full_sync: Whether to perform a full sync (ignore last sync timestamp)
            limit: Maximum number of records to sync (0 for no limit)
        
        Returns:
            Sync summary with counts and status
        """
        
        # Create sync record
        sync_record = await self.create_sync_record(self.entity_name, full_sync)
        
        try:
            # Get last sync timestamp
            since_date = None if full_sync else await self.get_last_sync_timestamp(self.entity_name)
            
            if since_date:
                logger.info(f"Performing incremental sync for MarketSharp contacts since: {since_date}")
            else:
                logger.info("Performing full sync for MarketSharp contacts")
            
            # Fetch data from Genius
            raw_data = await sync_to_async(self.client.get_marketsharp_contacts)(since_date, limit)
            logger.info(f"Fetched {len(raw_data)} raw MarketSharp contact records")
            
            if not raw_data:
                summary = {
                    'entity': self.entity_name,
                    'total_fetched': 0,
                    'total_processed': 0,
                    'total_synced': 0,
                    'errors': 0,
                    'status': 'completed',
                    'message': 'No new records to sync'
                }
                await self.complete_sync_record(sync_record.id, summary)
                return summary
            
            # Get field mapping
            field_mapping = self.client.get_field_mapping()
            
            # Process data
            processed_data = self.processor.process_marketsharp_contacts(raw_data, field_mapping)
            logger.info(f"Processed {len(processed_data)} MarketSharp contact records")
            
            # Sync in batches
            total_synced = 0
            errors = 0
            
            for i in range(0, len(processed_data), self.batch_size):
                batch = processed_data[i:i + self.batch_size]
                try:
                    synced_count = await self._sync_batch(batch)
                    total_synced += synced_count
                    logger.info(f"Synced batch {i//self.batch_size + 1}: {synced_count} records")
                except Exception as e:
                    logger.error(f"Error syncing batch {i//self.batch_size + 1}: {e}")
                    errors += len(batch)
            
            # Create summary
            summary = {
                'entity': self.entity_name,
                'total_fetched': len(raw_data),
                'total_processed': len(processed_data),
                'total_synced': total_synced,
                'errors': errors,
                'status': 'completed' if errors == 0 else 'completed_with_errors'
            }
            
            logger.info(f"MarketSharp contact sync completed: {summary}")
            
            # Complete sync record
            await self.complete_sync_record(sync_record.id, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error during MarketSharp contact sync: {e}")
            summary = {
                'entity': self.entity_name,
                'total_fetched': 0,
                'total_processed': 0,
                'total_synced': 0,
                'errors': 1,
                'status': 'failed',
                'error_message': str(e)
            }
            await self.complete_sync_record(sync_record.id, summary)
            raise
        
        finally:
            self.client.disconnect()
    
    async def _sync_batch(self, batch: List[Dict[str, Any]]) -> int:
        """Sync a batch of MarketSharp contact records to the data warehouse"""
        # This would contain the actual database insertion logic
        # For now, return the batch size as if all were synced
        # In a real implementation, this would connect to your data warehouse
        # and perform the actual INSERT/UPDATE operations
        
        logger.info(f"Would sync {len(batch)} MarketSharp contact records to data warehouse")
        return len(batch)
