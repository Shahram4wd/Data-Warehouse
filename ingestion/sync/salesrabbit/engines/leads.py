"""
SalesRabbit lead sync engine with framework-compliant orchestration
"""
import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, AsyncGenerator
from .base import SalesRabbitBaseSyncEngine
from ..clients.leads import SalesRabbitLeadsClient
from ..processors.leads import SalesRabbitLeadProcessor
from ingestion.models.salesrabbit import SalesRabbit_Lead

logger = logging.getLogger(__name__)

class SalesRabbitLeadSyncEngine(SalesRabbitBaseSyncEngine):
    """Lead sync engine with framework-compliant orchestration"""
    
    def __init__(self, **kwargs):
        super().__init__('leads', **kwargs)
        self.client = None
        self.processor = None
    
    async def initialize_client(self) -> None:
        """Initialize clients and processors - FRAMEWORK PATTERN"""
        self.client = SalesRabbitLeadsClient()
        await self.client.authenticate()
        
        self.processor = SalesRabbitLeadProcessor()
        
        logger.info("SalesRabbit lead sync components initialized")
    
    async def fetch_data(self, strategy: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch data based on sync strategy"""
        try:
            max_records = getattr(self, 'max_records', 0)
            
            if strategy['type'] == 'incremental' and strategy.get('last_sync'):
                logger.info(f"Fetching leads since {strategy['last_sync']}")
                return await self.client.fetch_leads_since(
                    strategy['last_sync'], 
                    limit=strategy['batch_size'],
                    max_records=max_records
                )
            else:
                logger.info("Fetching all leads")
                return await self.client.fetch_all_leads(
                    limit=strategy['batch_size'],
                    max_records=max_records
                )
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            # Return empty list for graceful handling - sync will continue with 0 records
            logger.warning("Returning empty list due to data fetch error - sync will complete with 0 records")
            return []
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw data using processor"""
        transformed_data = []
        for record in raw_data:
            try:
                transformed = self.processor.transform_record(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming record {record.get('id')}: {e}")
        
        return transformed_data
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        validated_data = []
        for record in data:
            try:
                validated = self.processor.validate_record(record)
                validated_data.append(validated)
            except Exception as e:
                logger.error(f"Error validating record {record.get('id')}: {e}")
        
        return validated_data
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data using bulk operations"""
        if not validated_data:
            return {'created': 0, 'updated': 0, 'failed': 0}
        
        from asgiref.sync import sync_to_async
        
        # Wrap the synchronous process_batch method with sync_to_async
        @sync_to_async
        def process_batch_sync():
            return self.processor.process_batch_sync(validated_data, self.batch_size)
        
        return await process_batch_sync()
    
    async def fetch_and_process_batches(self, strategy: Dict[str, Any]) -> AsyncGenerator[Dict[str, int], None]:
        """Fetch and process data in batches for efficient memory usage"""
        max_records = getattr(self, 'max_records', 0)
        total_processed = 0
        
        # Use the streaming pagination approach
        if strategy['type'] == 'incremental' and strategy.get('last_sync'):
            logger.info(f"Streaming leads since {strategy['last_sync']}")
            async for batch in self._fetch_leads_batches_since(strategy['last_sync'], strategy['batch_size'], max_records):
                batch_result = await self._process_batch(batch)
                total_processed += len(batch)
                yield batch_result
                
                # Check if we've reached max_records limit
                if max_records > 0 and total_processed >= max_records:
                    break
        else:
            logger.info("Streaming all leads")
            async for batch in self._fetch_all_leads_batches(strategy['batch_size'], max_records):
                batch_result = await self._process_batch(batch)
                total_processed += len(batch)
                yield batch_result
                
                # Check if we've reached max_records limit
                if max_records > 0 and total_processed >= max_records:
                    break
    
    async def _process_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """Process a single batch of records"""
        if not batch:
            return {'created': 0, 'updated': 0, 'failed': 0, 'processed': 0}
        
        try:
            # Transform data
            transformed_data = await self.transform_data(batch)
            logger.info(f"Transformed {len(transformed_data)} records in batch")
            
            # Validate data
            validated_data = await self.validate_data(transformed_data)
            logger.info(f"Validated {len(validated_data)} records in batch")
            
            # Save data
            save_results = await self.save_data(validated_data)
            save_results['processed'] = len(batch)
            
            return save_results
            
        except Exception as e:
            logger.error(f"Error processing batch: {e}")
            return {'created': 0, 'updated': 0, 'failed': len(batch), 'processed': len(batch)}
    
    async def _fetch_all_leads_batches(self, batch_size: int, max_records: int) -> AsyncGenerator[List[Dict], None]:
        """Fetch all leads in batches using pagination"""
        page = 1
        total_fetched = 0
        
        while True:
            try:
                # Fetch one page at a time
                params = {'page': page, 'limit': batch_size}
                
                async with self.client as client:
                    response = await client.make_request('GET', self.client.endpoints['leads'], params=params)
                    
                    # Handle different response formats
                    if isinstance(response, list):
                        batch = response
                    elif isinstance(response, dict):
                        batch = response.get('data', response.get('leads', []))
                    else:
                        batch = []
                
                if not batch:
                    break
                
                # Apply max_records limit
                if max_records > 0:
                    remaining = max_records - total_fetched
                    if remaining <= 0:
                        break
                    batch = batch[:remaining]
                
                total_fetched += len(batch)
                logger.info(f"Fetched page {page} with {len(batch)} records (total: {total_fetched})")
                
                yield batch
                
                # If we got less than batch_size or reached max_records, we're done
                if len(batch) < batch_size or (max_records > 0 and total_fetched >= max_records):
                    break
                
                page += 1
                
                # Add rate limiting delay
                await asyncio.sleep(self.client.rate_limit_delay)
                
            except Exception as e:
                logger.error(f"Error fetching page {page}: {e}")
                break
    
    async def _fetch_leads_batches_since(self, since_date: datetime, batch_size: int, max_records: int) -> AsyncGenerator[List[Dict], None]:
        """Fetch leads since date - using client-side filtering since API doesn't support server-side filtering"""
        try:
            # NOTE: SalesRabbit API doesn't support server-side date filtering
            # The client handles fetching all data and filtering client-side
            logger.info(f"Fetching leads modified since {since_date} using client-side filtering")
            
            # Use the client's fetch_leads_since method which does client-side filtering
            all_filtered_leads = await self.client.fetch_leads_since(since_date, limit=batch_size, max_records=max_records)
            
            # Yield the filtered results in batches
            total_fetched = 0
            for i in range(0, len(all_filtered_leads), batch_size):
                batch = all_filtered_leads[i:i + batch_size]
                if not batch:
                    break
                
                total_fetched += len(batch)
                logger.info(f"Processing batch with {len(batch)} filtered records (total: {total_fetched})")
                
                yield batch
                
                # Check if we've reached max_records limit
                if max_records > 0 and total_fetched >= max_records:
                    break
                    
        except Exception as e:
            logger.error(f"Error fetching leads since {since_date}: {e}")
            # Return empty generator for graceful handling
    
    async def run_sync(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """Main sync orchestration following framework standards"""
        # Store max_records for use in fetch_data
        self.max_records = kwargs.get('max_records', 0)
        
        # Initialize components
        await self.initialize_client()
        
        # Start sync tracking using base class framework method
        sync_history = await self.start_sync(**kwargs)
        
        try:
            # Determine strategy - handle different cases for last_sync parameter
            if 'last_sync' in kwargs:
                # last_sync was explicitly provided (could be None for full sync or a datetime for --since)
                provided_last_sync = kwargs.get('last_sync')
                use_override = True
            else:
                # last_sync not provided, use default behavior
                provided_last_sync = None
                use_override = False
                
            strategy = await self.determine_sync_strategy(force_full, last_sync_override=provided_last_sync, use_override=use_override)
            
            # Get record count for planning (optional)
            try:
                record_count = await self.client.get_lead_count_since(strategy.get('last_sync'))
                logger.info(f"Starting salesrabbit leads sync with ~{record_count} records")
            except Exception as e:
                logger.warning(f"Could not get record count: {e}")
                logger.info("Starting salesrabbit leads sync")
            
            # Fetch and process data in batches
            total_results = {'created': 0, 'updated': 0, 'failed': 0, 'processed': 0}
            
            if self.dry_run:
                logger.info("DRY RUN: Would process data but not save")
                # For dry run, still fetch data to show what would be processed
                raw_data = await self.fetch_data(strategy)
                total_results = {'created': 0, 'updated': len(raw_data), 'failed': 0, 'processed': len(raw_data)}
                logger.info(f"DRY RUN: Would process {len(raw_data)} records")
            else:
                # Process data in streaming batches
                async for batch_result in self.fetch_and_process_batches(strategy):
                    for key in total_results:
                        total_results[key] += batch_result.get(key, 0)
                    
                    logger.info(
                        f"Batch completed: {batch_result['created']} created, "
                        f"{batch_result['updated']} updated, {batch_result['failed']} failed. "
                        f"Total: {total_results['processed']} processed"
                    )
            
            # Complete sync tracking using base class framework method
            await self.complete_sync(total_results)
            
            logger.info(
                f"Completed salesrabbit leads sync: "
                f"{total_results['created']} created, {total_results['updated']} updated, "
                f"{total_results['failed']} failed"
            )
            
            return sync_history
            
        except Exception as e:
            # Use base class error handling
            await self.complete_sync({}, str(e))
            raise
        finally:
            await self.cleanup()
    
    async def get_record_count(self, strategy: Dict[str, Any]) -> int:
        """Get estimated record count for sync planning"""
        try:
            if strategy['type'] == 'incremental' and strategy.get('last_sync'):
                return await self.client.get_lead_count_since(strategy['last_sync'])
            else:
                return await self.client.get_lead_count_since()
        except Exception as e:
            logger.warning(f"Could not get record count: {e}")
            return 0
    
    async def test_connection(self) -> bool:
        """Test connection to SalesRabbit API"""
        try:
            await self.initialize_client()
            result = await self.client.test_connection()
            await self.cleanup()
            return result
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
