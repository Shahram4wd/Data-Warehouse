"""
Arrivy Entities Sync Engine

Handles synchronization of Arrivy entities (crew members) following enterprise patterns.
Entities represent individual crew members across all divisions.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from .base import ArrivyBaseSyncEngine
from ..clients.entities import ArrivyEntitiesClient
from ..processors.entities import EntitiesProcessor
from ingestion.models.arrivy import Arrivy_Entity

logger = logging.getLogger(__name__)

class ArrivyEntitiesSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy entities (crew members)"""
    
    def __init__(self, **kwargs):
        super().__init__('entities', **kwargs)
        self.client_class = ArrivyEntitiesClient
        self.processor = EntitiesProcessor()
    
    def get_model_class(self):
        """Get Django model class for entities"""
        return Arrivy_Entity
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch entities data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of entity records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching entities with last_sync={last_sync}, batch_size={self.batch_size}")
        
        # Try direct entities endpoint first (following reference script pattern)
        use_direct_entities = True  # Use direct entities endpoint for maximum records
        
        if use_direct_entities:
            # Fetch directly from entities endpoint (may return more records)
            try:
                async for batch in client.fetch_entities(
                    last_sync=last_sync,
                    page_size=self.batch_size
                ):
                    if batch:
                        logger.debug(f"Fetched {len(batch)} entities from direct endpoint")
                        yield batch
            except Exception as e:
                logger.warning(f"Direct entities endpoint failed: {e}, falling back to crew members approach")
                use_direct_entities = False
        
        if not use_direct_entities:
            # Fallback: Fetch crew members from divisions (includes division context)
            async for batch in client.fetch_crew_members_from_divisions(
                last_sync=last_sync,
                page_size=self.batch_size
            ):
                if batch:
                    logger.debug(f"Fetched {len(batch)} crew members from divisions")
                    yield batch
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """
        Process a batch of entity records using bulk operations for better performance
        
        Args:
            batch: Batch of entity records
            
        Returns:
            Upsert results
        """
        logger.debug(f"Processing batch of {len(batch)} entities")
        
        try:
            # Process records through processor for transformation and validation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Extract entity ID (key field for upsert)
                    entity_id = record.get('id')
                    if not entity_id:
                        logger.warning(f"Entity record missing ID: {record}")
                        failed_count += 1
                        continue
                    
                    # Use processor to transform and validate the record
                    entity_data = self.processor.transform_record(record)
                    entity_data = self.processor.validate_record(entity_data)
                    
                    processed_batch.append(entity_data)
                        
                except Exception as e:
                    logger.error(f"Error processing entity {record.get('id', 'unknown')}: {str(e)}")
                    failed_count += 1
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                results = await self._save_batch(processed_batch)
                results['failed'] += failed_count
                logger.info(f"Entity batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
                return results
            else:
                logger.warning("No valid records to process in batch")
                return {'created': 0, 'updated': 0, 'failed': failed_count}
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            return {'created': 0, 'updated': 0, 'failed': len(batch)}
    
    async def get_sync_summary(self) -> Dict[str, Any]:
        """
        Get summary statistics for entity sync
        
        Returns:
            Summary statistics
        """
        try:
            client = await self.initialize_client()
            total_count = await client.get_entities_count()
            
            from asgiref.sync import sync_to_async
            local_count = await sync_to_async(self.get_model_class().objects.count)()
            
            return {
                'total_remote': total_count,
                'total_local': local_count,
                'entity_type': self.entity_type,
                'last_sync': await self.get_last_sync_timestamp()
            }
            
        except Exception as e:
            logger.error(f"Error getting sync summary: {str(e)}")
            return {
                'total_remote': 0,
                'total_local': 0,
                'entity_type': self.entity_type,
                'error': str(e)
            }
