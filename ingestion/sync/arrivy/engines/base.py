"""
Base Sync Engine for Arrivy

Implements enterprise CRM sync patterns following crm_sync_guide.md.
Provides standardized sync orchestration with SyncHistory integration.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async
from django.utils import timezone
from django.db import transaction

from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.models.common import SyncHistory
from ..clients.base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyBaseSyncEngine(BaseSyncEngine):
    """Base sync engine for Arrivy API operations following enterprise patterns"""
    
    def __init__(self, entity_type: str, **kwargs):
        super().__init__('arrivy', entity_type, **kwargs)
        self.entity_type = entity_type  # Ensure entity_type is available as an attribute
        self.max_records = kwargs.get('max_records', 0)  # 0 means no limit
        self.client_class = ArrivyBaseClient
        self.client = None
        self.processor = None
    
    def get_default_batch_size(self) -> int:
        """Return default batch size for Arrivy sync operations"""
        return 100  # Arrivy API handles reasonable batch sizes
    
    async def initialize_client(self) -> ArrivyBaseClient:
        """Initialize Arrivy client with proper configuration"""
        if not self.client:
            self.client = self.client_class()
            
            # Test connection on first initialization
            success, message = await self.client.test_connection()
            if not success:
                raise SyncException(f"Failed to connect to Arrivy API: {message}")
            
            logger.info(f"Arrivy client initialized successfully for {self.entity_type}")
        
        return self.client
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get last successful sync timestamp from SyncHistory table
        
        This is the standardized way to get delta sync timestamps.
        NO custom sync tracking is allowed.
        
        Returns:
            Last successful sync end_time or None for full sync
        """
        try:
            # Correctly use sync_to_async for the query
            last_sync_queryset = SyncHistory.objects.filter(
                crm_source='arrivy',
                sync_type=self.entity_type,
                status='success'
            ).order_by('-end_time')
            
            last_sync = await sync_to_async(lambda: last_sync_queryset.first())()
            
            if last_sync:
                logger.info(f"Found last sync for {self.entity_type}: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info(f"No previous sync found for {self.entity_type}, performing full sync")
                return None
                
        except Exception as e:
            logger.warning(f"Error retrieving last sync timestamp: {e}")
            return None
    
    def determine_sync_strategy(self, force_full: bool = False, 
                              since_param: Optional[str] = None) -> Dict[str, Any]:
        """
        Determine sync strategy following crm_sync_guide.md patterns
        
        Priority order:
        1. --since parameter (manual override)
        2. --force flag (None = fetch all)  
        3. --full flag (None = fetch all)
        4. SyncHistory table last successful sync timestamp
        5. Default: None (full sync)
        
        Args:
            force_full: Force full sync (ignore timestamps)
            since_param: Manual sync start date (YYYY-MM-DD format)
            
        Returns:
            Sync strategy configuration
        """
        strategy = {
            'sync_type': 'full',
            'last_sync_time': None,
            'force_overwrite': self.force_overwrite
        }
        
        if since_param:
            # Manual override - convert string to datetime
            try:
                from django.utils.dateparse import parse_date
                since_date = parse_date(since_param)
                if since_date:
                    strategy['last_sync_time'] = timezone.make_aware(
                        datetime.combine(since_date, datetime.min.time())
                    )
                    strategy['sync_type'] = 'incremental'
                    logger.info(f"Using manual sync date: {strategy['last_sync_time']}")
            except Exception as e:
                logger.warning(f"Invalid --since parameter '{since_param}': {e}")
        
        elif force_full:
            # Force full sync
            strategy['sync_type'] = 'full'
            logger.info("Performing full sync (forced)")
            
        else:
            # Use SyncHistory for delta sync
            strategy['sync_type'] = 'incremental'
            logger.info("Using SyncHistory for incremental sync")
        
        return strategy
    
    async def create_sync_record(self, sync_strategy: Dict[str, Any]) -> SyncHistory:
        """
        Create SyncHistory record at sync start
        
        MANDATORY: All sync operations must use SyncHistory table
        
        Args:
            sync_strategy: Sync strategy configuration
            
        Returns:
            Created SyncHistory record
        """
        sync_config = {
            'sync_type': sync_strategy['sync_type'],
            'force_overwrite': sync_strategy['force_overwrite'],
            'batch_size': self.batch_size,
            'dry_run': self.dry_run
        }
        
        if sync_strategy['last_sync_time']:
            sync_config['since_timestamp'] = sync_strategy['last_sync_time'].isoformat()
        
        return await sync_to_async(SyncHistory.objects.create)(
            crm_source='arrivy',  # MANDATORY: lowercase, no underscores
            sync_type=self.entity_type,  # MANDATORY: no '_sync' suffix
            status='running',  # MANDATORY: standard status values
            start_time=timezone.now(),
            configuration=sync_config,
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_failed=0
        )
    
    async def update_sync_record(self, sync_record: SyncHistory,
                               status: str, metrics: Dict[str, Any],
                               error_message: Optional[str] = None) -> None:
        """
        Update SyncHistory record with results
        
        Args:
            sync_record: SyncHistory record to update
            status: Final status ('success', 'failed', 'partial')
            metrics: Sync metrics and performance data
            error_message: Error message if failed
        """
        update_data = {
            'status': status,
            'end_time': timezone.now(),
            'records_processed': metrics.get('processed', 0),
            'records_created': metrics.get('created', 0),
            'records_updated': metrics.get('updated', 0),
            'records_failed': metrics.get('failed', 0),
            'performance_metrics': {
                'duration_seconds': metrics.get('duration_seconds', 0),
                'records_per_second': metrics.get('records_per_second', 0),
                'api_calls': metrics.get('api_calls', 0),
                'batches_processed': metrics.get('batches_processed', 0)
            }
        }
        
        if error_message:
            update_data['error_message'] = error_message
        
        # Update using sync_to_async for database operations
        for field, value in update_data.items():
            setattr(sync_record, field, value)
        
        await sync_to_async(sync_record.save)()
    
    @abstractmethod
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch data from Arrivy API with delta sync support
        
        Must be implemented by entity-specific engines.
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of records from API
        """
        pass
    
    @abstractmethod
    def get_model_class(self):
        """
        Get Django model class for this entity type
        
        Must be implemented by entity-specific engines.
        
        Returns:
            Django model class
        """
        pass
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute complete sync workflow with enterprise error handling
        
        This is the main orchestration method that coordinates:
        1. Sync strategy determination
        2. SyncHistory record creation
        3. Data fetching and processing
        4. Bulk operations
        5. Results tracking and logging
        
        Args:
            **kwargs: Sync options (force_full, since_param, etc.)
            
        Returns:
            Sync results summary
        """
        start_time = timezone.now()
        sync_record = None
        
        try:
            # Initialize client
            await self.initialize_client()
            
            # Determine sync strategy
            sync_strategy = self.determine_sync_strategy(
                force_full=kwargs.get('force_full', False),
                since_param=kwargs.get('since_param')
            )
            
            # Create SyncHistory record
            sync_record = await self.create_sync_record(sync_strategy)
            logger.info(f"Started {self.entity_type} sync (ID: {sync_record.id})")
            
            # Get last sync timestamp if doing incremental sync
            last_sync_time = None
            if sync_strategy['sync_type'] == 'incremental':
                if sync_strategy['last_sync_time']:
                    last_sync_time = sync_strategy['last_sync_time']
                else:
                    last_sync_time = await self.get_last_sync_timestamp()
            
            # Execute data sync
            metrics = await self._execute_data_sync(last_sync_time)
            
            # Calculate final metrics
            end_time = timezone.now()
            duration_seconds = (end_time - start_time).total_seconds()
            metrics['duration_seconds'] = duration_seconds
            
            if duration_seconds > 0:
                metrics['records_per_second'] = metrics.get('processed', 0) / duration_seconds
            
            # Update sync record with success
            await self.update_sync_record(sync_record, 'success', metrics)
            
            logger.info(f"Completed {self.entity_type} sync: {metrics['processed']} processed, "
                       f"{metrics['created']} created, {metrics['updated']} updated, "
                       f"{metrics['failed']} failed in {duration_seconds:.2f}s")
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error during {self.entity_type} sync: {str(e)}", exc_info=True)
            
            # Update sync record with failure
            if sync_record:
                end_time = timezone.now()
                duration_seconds = (end_time - start_time).total_seconds()
                
                error_metrics = {
                    'processed': 0,
                    'created': 0, 
                    'updated': 0,
                    'failed': 0,
                    'duration_seconds': duration_seconds
                }
                
                await self.update_sync_record(
                    sync_record, 'failed', error_metrics, str(e)
                )
            
            raise SyncException(f"Sync failed: {str(e)}")
    
    async def _execute_data_sync(self, last_sync_time: Optional[datetime]) -> Dict[str, Any]:
        """
        Execute the data synchronization process
        
        Args:
            last_sync_time: Last sync timestamp for delta sync
            
        Returns:
            Sync metrics
        """
        metrics = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'api_calls': 0,
            'batches_processed': 0
        }
        
        batch_count = 0
        
        try:
            # Fetch and process data in batches
            async for batch in self.fetch_data(last_sync=last_sync_time):
                if not batch:
                    continue
                
                batch_count += 1
                metrics['api_calls'] += 1
                
                logger.debug(f"Processing batch {batch_count} with {len(batch)} records")
                
                # Trim batch if it would exceed max_records
                if self.max_records > 0:
                    remaining_records = self.max_records - metrics['processed']
                    if remaining_records <= 0:
                        logger.info(f"Reached max_records limit of {self.max_records}")
                        break
                    elif len(batch) > remaining_records:
                        batch = batch[:remaining_records]
                        logger.debug(f"Trimmed batch to {len(batch)} records to respect max_records limit")
                
                # Save batch using engine's process_batch method
                batch_results = await self.process_batch(batch)
                
                
                # Update metrics
                metrics['processed'] += len(batch)
                metrics['created'] += batch_results.get('created', 0)
                metrics['updated'] += batch_results.get('updated', 0) 
                metrics['failed'] += batch_results.get('failed', 0)
                metrics['batches_processed'] += 1
                
                logger.debug(f"Batch {batch_count} results: {batch_results}")
                
                # Break early if max_records limit reached after processing
                if self.max_records > 0 and metrics['processed'] >= self.max_records:
                    logger.info(f"Reached max_records limit of {self.max_records}")
                    break
        
        except Exception as e:
            logger.error(f"Error during data sync: {str(e)}")
            raise
        
        return metrics
    
    async def _save_batch(self, batch: List[Dict]) -> Dict[str, int]:
        """
        Save batch of records using bulk operations
        
        Args:
            batch: Batch of processed records
            
        Returns:
            Save results metrics
        """
        if self.dry_run:
            logger.info(f"DRY RUN: Would save {len(batch)} records")
            return {'created': len(batch), 'updated': 0, 'failed': 0}
        
        model_class = self.get_model_class()
        
        try:
            if self.force_overwrite:
                return await self._force_overwrite_records(batch, model_class)
            else:
                return await self._bulk_upsert_records(batch, model_class)
                
        except Exception as e:
            logger.error(f"Error saving batch: {str(e)}")
            return {'created': 0, 'updated': 0, 'failed': len(batch)}
    
    async def _bulk_upsert_records(self, batch: List[Dict], model_class) -> Dict[str, int]:
        """
        Perform bulk upsert with conflict resolution using Django's bulk_create with update_conflicts
        
        Args:
            batch: Batch of records to upsert
            model_class: Django model class
            
        Returns:
            Upsert results
        """
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not batch:
            return results
            
        logger.debug(f"Performing bulk upsert for {len(batch)} records")
        
        try:
            # Get unique field name for this model (usually 'id' but could be different)
            unique_field = self.processor.get_unique_field_name() if hasattr(self.processor, 'get_unique_field_name') else 'id'
            
            # Check existing records to calculate created vs updated counts
            existing_ids = set()
            unique_values = [record.get(unique_field) for record in batch if record.get(unique_field)]
            if unique_values:
                existing_ids = set(await sync_to_async(list)(
                    model_class.objects.filter(
                        **{f"{unique_field}__in": unique_values}
                    ).values_list(unique_field, flat=True)
                ))
            
            # Prepare model objects for bulk_create
            model_objects = []
            for record in batch:
                try:
                    model_objects.append(model_class(**record))
                except Exception as e:
                    logger.warning(f"Failed to create model object for record {record.get(unique_field)}: {e}")
                    results['failed'] += 1
            
            if not model_objects:
                return results
            
            # Get all updatable fields (exclude auto fields and primary key)
            update_fields = []
            for field in model_class._meta.fields:
                # Skip auto fields, primary key, and auto_now_add fields
                if (not field.auto_created and 
                    not field.primary_key and 
                    not getattr(field, 'auto_now_add', False)):
                    update_fields.append(field.name)
            
            # Perform bulk upsert
            await sync_to_async(model_class.objects.bulk_create)(
                model_objects,
                batch_size=self.batch_size,
                update_conflicts=True,
                update_fields=update_fields,
                unique_fields=[unique_field]
            )
            
            # Calculate results based on existing vs new records
            total_success = len(model_objects)
            results['updated'] = len(existing_ids.intersection(set(unique_values)))
            results['created'] = total_success - results['updated']
            
            logger.info(f"Bulk upsert completed: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            results['failed'] = len(batch)
            results['created'] = 0
            results['updated'] = 0
        
        return results
    
    async def _force_overwrite_records(self, batch: List[Dict], model_class) -> Dict[str, int]:
        """
        Force overwrite existing records (complete replacement)
        
        Args:
            batch: Batch of records to overwrite
            model_class: Django model class
            
        Returns:
            Overwrite results
        """
        logger.debug(f"Performing force overwrite for {len(batch)} records")
        
        # TODO: Implement force overwrite logic
        # This would typically delete existing records and create new ones
        
        return {'created': len(batch), 'updated': 0, 'failed': 0}
    
    # Implementation of abstract methods from BaseSyncEngine
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw data to target format"""
        # Default implementation - entity-specific engines can override
        transformed = []
        for record in raw_data:
            try:
                transformed_record = await self.transform_record(record)
                transformed.append(transformed_record)
            except Exception as e:
                logger.error(f"Error transforming record {record.get('id', 'unknown')}: {e}")
        
        return transformed
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        # Default implementation - entity-specific engines can override
        validated = []
        for record in data:
            try:
                # Basic validation - check for required fields
                if self._validate_record(record):
                    validated.append(record)
                else:
                    logger.warning(f"Record failed validation: {record.get('id', 'unknown')}")
            except Exception as e:
                logger.error(f"Error validating record {record.get('id', 'unknown')}: {e}")
        
        return validated
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data to database"""
        # Delegate to existing _save_batch method
        return await self._save_batch(validated_data)
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        if self.client:
            # Close any connections or cleanup client resources
            logger.debug("Cleaning up Arrivy client resources")
            # Most HTTP clients don't need explicit cleanup, but this is the hook
            pass
    
    def _validate_record(self, record: Dict) -> bool:
        """Basic record validation - can be overridden by entity-specific engines"""
        # Check for required ID field - use dynamic field name if processor available
        id_field = 'id'
        if hasattr(self, 'processor') and hasattr(self.processor, 'get_unique_field_name'):
            id_field = self.processor.get_unique_field_name()
            
        if not record.get(id_field):
            return False
        
        return True
    
    async def transform_record(self, record: Dict) -> Dict:
        """
        Transform a single record - should be overridden by entity-specific engines
        
        Args:
            record: Raw record from API
            
        Returns:
            Transformed record for database
        """
        # Default transformation - use dynamic field name if processor available
        id_field = 'id'
        if hasattr(self, 'processor') and hasattr(self.processor, 'get_unique_field_name'):
            id_field = self.processor.get_unique_field_name()
            
        return {
            id_field: record.get('id'),
            'raw_data': record
        }
    
    async def upsert_record(self, model_class, transformed_record: Dict):
        """
        Upsert a single record to the database
        
        Args:
            model_class: Django model class
            transformed_record: Transformed record data
            
        Returns:
            Tuple of (model_instance, created_boolean)
        """
        try:
            # Get unique field name from processor if available
            unique_field = 'id'  # default
            if hasattr(self, 'processor') and hasattr(self.processor, 'get_unique_field_name'):
                unique_field = self.processor.get_unique_field_name()
            
            # Get the record ID using the appropriate field
            record_id = transformed_record.get(unique_field)
            if not record_id:
                raise ValidationException(f"Record missing {unique_field} for upsert")
            
            # Use get_or_create pattern
            defaults = {k: v for k, v in transformed_record.items() if k != unique_field}
            
            instance, created = await sync_to_async(model_class.objects.get_or_create)(
                **{unique_field: record_id},
                defaults=defaults
            )
            
            # If not created, update with new data
            if not created and not self.force_overwrite:
                for key, value in defaults.items():
                    setattr(instance, key, value)
                await sync_to_async(instance.save)()
            
            return instance, created
            
        except Exception as e:
            # Get unique field name for error reporting
            unique_field = 'id'
            if hasattr(self, 'processor') and hasattr(self.processor, 'get_unique_field_name'):
                unique_field = self.processor.get_unique_field_name()
            
            logger.error(f"Error upserting record {transformed_record.get(unique_field)}: {e}")
            raise
