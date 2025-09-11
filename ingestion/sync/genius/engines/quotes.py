"""
Quotes sync engine for Genius CRM
Following CRM sync guide architecture with chunked processing and bulk operations
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from ..clients.quotes import GeniusQuoteClient
from ..processors.quotes import GeniusQuoteProcessor
from ingestion.models import SyncHistory, Genius_Quote

logger = logging.getLogger('quotes')


class GeniusQuotesSyncEngine:
    """Sync engine for Genius quote data with chunked processing"""
    
    def __init__(self):
        self.client = GeniusQuoteClient()
        self.processor = GeniusQuoteProcessor()
        
    def execute_sync(self, 
                    full: bool = False,
                    force_overwrite: bool = False, 
                    since: Optional[datetime] = None,
                    start_date: Optional[datetime] = None,
                    end_date: Optional[datetime] = None,
                    max_records: Optional[int] = None,
                    dry_run: bool = False,
                    debug: bool = False) -> Dict[str, Any]:
        """Execute quotes sync with chunked processing"""
        
        # Determine since_date for sync
        since_date = None if full else (since or self._get_last_sync_date())
        
        logger.info(f"Starting quotes sync - since_date: {since_date}, force_overwrite: {force_overwrite}, dry_run: {dry_run}, max_records: {max_records}")
        
        # Handle limited datasets for testing
        if max_records:
            logger.info(f"Processing limited dataset: {max_records} records")
            return self._sync_limited_quotes(
                max_records=max_records,
                force_overwrite=force_overwrite,
                dry_run=dry_run
            )
        
        # Process in chunks for large datasets
        return self._sync_chunked_quotes(
            since_date=since_date,
            force_overwrite=force_overwrite,
            dry_run=dry_run
        )
    
    def _sync_limited_quotes(self, max_records: int, force_overwrite: bool, dry_run: bool) -> Dict[str, Any]:
        """Sync limited number of quotes (for testing)"""
        
        try:
            # Get limited quotes
            quotes = self.client.get_quotes(limit=max_records)
            logger.info(f"Retrieved {len(quotes)} quotes")
            
            if dry_run:
                logger.info("DRY RUN: Would process quotes but making no changes")
                return {
                    'total_processed': len(quotes),
                    'created': 0,
                    'updated': 0,
                    'errors': 0,
                    'sync_history_id': None
                }
            
            # Process quotes in batches
            return self._process_quotes_batch(quotes, force_overwrite)
            
        except Exception as e:
            logger.error(f"Limited quotes sync failed: {e}")
            raise
        finally:
            self.client.disconnect()
    
    def _sync_chunked_quotes(self, since_date: Optional[datetime], force_overwrite: bool, dry_run: bool) -> Dict[str, Any]:
        """Sync quotes using chunked processing for large datasets"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        try:
            chunk_size = 100000  # Process 100K records per chunk
            chunk_number = 1
            
            while True:
                logger.info(f"Executing chunked query (offset: {(chunk_number - 1) * chunk_size}, chunk_size: {chunk_size}):")
                
                # Get chunk of quotes
                quotes_chunk = self.client.get_chunked_quotes(
                    since_date=since_date,
                    offset=(chunk_number - 1) * chunk_size,
                    chunk_size=chunk_size
                )
                
                if not quotes_chunk:
                    logger.info("No more quotes to process")
                    break
                
                logger.info(f"Processing chunk {chunk_number}: {len(quotes_chunk)} records (total processed so far: {stats['total_processed'] + len(quotes_chunk)})")
                
                if dry_run:
                    logger.info("DRY RUN: Would process chunk but making no changes")
                    stats['total_processed'] += len(quotes_chunk)
                    chunk_number += 1
                    continue
                
                # Process chunk
                chunk_stats = self._process_quotes_batch(quotes_chunk, force_overwrite)
                
                # Update running totals
                for key in ['total_processed', 'created', 'updated', 'errors']:
                    stats[key] += chunk_stats[key]
                
                logger.info(f"Chunk {chunk_number} completed - Created: {chunk_stats['created']}, Updated: {chunk_stats['updated']}, Running totals: {stats['created']} created, {stats['updated']} updated")
                
                # Break if we processed less than chunk_size (last chunk)
                if len(quotes_chunk) < chunk_size:
                    break
                    
                chunk_number += 1
            
            logger.info(f"Quotes sync completed - Stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Chunked quotes sync failed: {e}")
            raise
        finally:
            self.client.disconnect()
    
    def _process_quotes_batch(self, quotes: list, force_overwrite: bool) -> Dict[str, Any]:
        """Process a batch of quotes with bulk operations"""
        
        stats = {
            'total_processed': len(quotes),
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        if not quotes:
            return stats
        
        # Process quotes in smaller batches for bulk operations
        batch_size = 500
        logger.info(f"Processing {len(quotes)} quotes in {(len(quotes) + batch_size - 1) // batch_size} batches of {batch_size}")
        
        for i in range(0, len(quotes), batch_size):
            batch = quotes[i:i + batch_size]
            batch_num = i // batch_size + 1
            total_batches = (len(quotes) + batch_size - 1) // batch_size
            
            logger.info(f"Processing batch {batch_num}/{total_batches}: records {i + 1}-{min(i + batch_size, len(quotes))}")
            
            try:
                batch_stats = self.processor.bulk_upsert_quotes(batch, force_overwrite)
                
                # Update stats
                stats['created'] += batch_stats['created']
                stats['updated'] += batch_stats['updated']
                stats['errors'] += batch_stats['errors']
                
                logger.info(f"Batch {batch_num} completed - Created: {batch_stats['created']}, Updated: {batch_stats['updated']}, Total so far: {stats['created']} created, {stats['updated']} updated")
                
            except Exception as e:
                logger.error(f"Error processing batch {batch_num}: {e}")
                stats['errors'] += len(batch)
        
        logger.info(f"Bulk upsert completed - Created: {stats['created']}, Updated: {stats['updated']}")
        return stats
    
    def _get_last_sync_date(self) -> Optional[datetime]:
        """Get the last successful sync date for incremental sync"""
        try:
            last_sync = SyncHistory.objects.filter(
                source='genius',
                entity='quotes',
                status='completed'
            ).order_by('-sync_started_at').first()
            
            if last_sync:
                logger.info(f"Last successful sync: {last_sync.sync_started_at}")
                return last_sync.sync_started_at
            else:
                logger.info("No previous sync found - performing full sync")
                return None
        except Exception as e:
            logger.warning(f"Error getting last sync date: {e}")
            return None
