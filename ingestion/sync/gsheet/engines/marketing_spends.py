"""
Marketing Spends Sync Engine for Google Sheets

Follows CRM sync guide architecture with SyncHistory integration.
Configuration is hardcoded here, not stored in database.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from django.utils import timezone
from ingestion.models.common import SyncHistory  # Use global SyncHistory table
from ingestion.models.gsheet import GoogleSheetMarketingSpend
from ingestion.sync.gsheet.clients.marketing_spends import MarketingSpendsClient
from ingestion.sync.gsheet.processors.marketing_spends import MarketingSpendsProcessor
from ingestion.sync.gsheet.engines.base import BaseGoogleSheetsSyncEngine

logger = logging.getLogger(__name__)


class MarketingSpendsSyncEngine(BaseGoogleSheetsSyncEngine):
    """
    Sync engine for Marketing Spends from Google Sheets
    
    Configuration (hardcoded as per CRM sync guide):
    - Sheet ID: 17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg
    - Tab: "All Marketing Spend"
    - Model: GoogleSheetMarketingSpend
    - CRM Source: 'gsheet_marketing_spends'
    """
    
    # HARDCODED CONFIGURATION (as per CRM sync guide)
    SHEET_CONFIG = {
        'sheet_id': '17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg',
        'tab_name': 'All Marketing Spend',
        'header_row': 1,
        'data_start_row': 2,
        'target_model': GoogleSheetMarketingSpend,
        'crm_source': 'gsheet',
    }
    
    def __init__(self, batch_size: int = 500, dry_run: bool = False, force_overwrite: bool = False):
        """Initialize the marketing spends sync engine"""
        super().__init__(
            sheet_name='marketing_spends',
            batch_size=batch_size,
            dry_run=dry_run,
            force_overwrite=force_overwrite
        )
        
        # Set the CRM source for SyncHistory tracking
        self.crm_source = self.SHEET_CONFIG['crm_source']
        
        # Additional sync options
        self.max_records = None
        self.force_full_sync = False
        
        # Initialize client and processor
        self.client = MarketingSpendsClient(
            sheet_id=self.SHEET_CONFIG['sheet_id'],
            tab_name=self.SHEET_CONFIG['tab_name']
        )
        
        self.processor = MarketingSpendsProcessor(
            model_class=self.SHEET_CONFIG['target_model'],
            dry_run=dry_run
        )
        
        # Store configuration
        self.sheet_config = self.SHEET_CONFIG
        
        logger.info(f"Initialized MarketingSpendsSyncEngine")
        logger.info(f"Sheet ID: {self.SHEET_CONFIG['sheet_id']}")
        logger.info(f"Tab: {self.SHEET_CONFIG['tab_name']}")
        logger.info(f"CRM Source: {self.crm_source}")
    
    def create_sync_history_record(self, status: str = 'running') -> SyncHistory:
        """
        Create a new SyncHistory record for this sync operation
        
        Args:
            status: Initial status for the sync record
            
        Returns:
            SyncHistory instance
        """
        sync_record = SyncHistory.objects.create(
            crm_source=self.crm_source,
            sync_type='marketing_spends',
            status=status,
            start_time=timezone.now(),
            configuration={
                'sheet_id': self.SHEET_CONFIG['sheet_id'],
                'tab_name': self.SHEET_CONFIG['tab_name'],
                'batch_size': self.batch_size,
                'dry_run': self.dry_run,
                'force_overwrite': self.force_overwrite,
            }
        )
        
        logger.info(f"Created SyncHistory record {sync_record.id} for marketing spends sync")
        return sync_record
    
    def update_sync_history_record(self, sync_record: SyncHistory, 
                                 status: str, stats: Dict[str, Any]):
        """
        Update SyncHistory record with final results
        
        Args:
            sync_record: SyncHistory instance to update
            status: Final status ('success', 'failed', 'skipped')
            stats: Dictionary containing sync statistics
        """
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('records_processed', 0)
        sync_record.records_created = stats.get('records_created', 0)
        sync_record.records_updated = stats.get('records_updated', 0)
        sync_record.records_failed = stats.get('records_failed', 0)
        
        # Handle error details
        error_details = stats.get('error_details', {})
        if error_details and 'error_message' in error_details:
            sync_record.error_message = error_details['error_message']
        
        # Calculate duration and performance metrics
        if sync_record.start_time and sync_record.end_time:
            duration = (sync_record.end_time - sync_record.start_time).total_seconds()
            sync_record.performance_metrics = {
                'duration_seconds': duration,
                'records_per_second': sync_record.records_processed / duration if duration > 0 else 0,
                'records_deleted': stats.get('records_deleted', 0)
            }
        
        sync_record.save()
        
        logger.info(f"Updated SyncHistory record {sync_record.id} with status: {status}")
    
    def get_sync_summary(self) -> Dict[str, Any]:
        """
        Get summary information about marketing spends sync status
        
        Returns:
            Dictionary containing sync summary information
        """
        try:
            # Get last sync information
            last_sync = SyncHistory.objects.filter(
                crm_source=self.crm_source,
                sync_type='marketing_spends'
            ).order_by('-start_time').first()
            
            if not last_sync:
                return {
                    'status': 'never_synced',
                    'message': 'No previous sync found'
                }
            
            # Get current data counts
            db_count = GoogleSheetMarketingSpend.objects.count()
            
            # Try to get sheet row count
            try:
                sheet_info = self.client.get_sheet_info()
                sheet_count = sheet_info.get('estimated_data_rows', 0)
            except Exception as e:
                logger.warning(f"Could not get sheet info: {e}")
                sheet_count = 0
            
            return {
                'status': last_sync.status,
                'last_sync_time': last_sync.start_time,
                'last_sync_duration': (
                    (last_sync.end_time - last_sync.start_time).total_seconds() 
                    if last_sync.end_time else None
                ),
                'records_in_database': db_count,
                'records_in_sheet': sheet_count,
                'last_sync_stats': {
                    'processed': last_sync.records_processed,
                    'created': last_sync.records_created,
                    'updated': last_sync.records_updated,
                    'failed': last_sync.records_failed,
                },
                'sheet_info': sheet_info if 'sheet_info' in locals() else {}
            }
            
        except Exception as e:
            logger.error(f"Error getting sync summary: {e}")
            return {
                'status': 'error',
                'error': str(e)
            }
    
    def sync_sync(self) -> Dict[str, Any]:
        """
        Synchronous version of sync for management commands with chunking and batching
        Performs full refresh by clearing table first, then importing all data
        """
        # Create SyncHistory record for tracking
        sync_record = self.create_sync_history_record('running')
        sync_start_time = timezone.now()
        
        try:
            # Test connection
            if not self.client.test_connection():
                raise Exception("Google Sheets API connection failed")
            
            # Clear existing records first (full refresh)
            if not self.dry_run:
                existing_count = GoogleSheetMarketingSpend.objects.count()
                logger.info(f"🗑️  Clearing existing marketing spends records: {existing_count:,}")
                GoogleSheetMarketingSpend.objects.all().delete()
                logger.info("✅ Table cleared successfully")
            else:
                existing_count = GoogleSheetMarketingSpend.objects.count()
                logger.info(f"DRY RUN: Would clear {existing_count:,} existing marketing spends records")
            
            # Fetch data from Google Sheets
            logger.info("Fetching data from Google Sheets...")
            raw_data = self.client.fetch_sheet_data_sync()
            logger.info(f"Fetched {len(raw_data)} rows from Google Sheets")
            
            # Apply max_records limit if specified
            if self.max_records and self.max_records > 0:
                original_count = len(raw_data)
                raw_data = raw_data[:self.max_records]
                logger.info(f"Limited to {len(raw_data)} records (max_records={self.max_records}, original={original_count})")
            
            if not raw_data:
                logger.info("No data found in Google Sheet")
                return {
                    'status': 'success',
                    'records_processed': 0,
                    'records_created': 0,
                    'records_updated': 0,
                    'records_failed': 0,
                    'records_deleted': existing_count if not self.dry_run else 0,
                    'message': 'No data found in sheet'
                }
            
            # Initialize statistics
            stats = {
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0,
                'errors': []
            }
            
            # Process data in chunks for memory efficiency
            chunk_size = min(self.batch_size, 1000)
            total_chunks = (len(raw_data) + chunk_size - 1) // chunk_size
            
            logger.info(f"Processing {len(raw_data)} records in {total_chunks} chunks of {chunk_size}")
            
            for chunk_index in range(0, len(raw_data), chunk_size):
                chunk_data = raw_data[chunk_index:chunk_index + chunk_size]
                chunk_number = (chunk_index // chunk_size) + 1
                
                logger.info(f"Processing chunk {chunk_number}/{total_chunks} ({len(chunk_data)} records)")
                
                try:
                    chunk_stats = self._process_data_chunk(chunk_data, chunk_index)
                    
                    # Aggregate statistics
                    for key in ['records_processed', 'records_created', 'records_updated', 'records_failed']:
                        stats[key] += chunk_stats.get(key, 0)
                    
                    logger.info(f"Chunk {chunk_number} completed: {chunk_stats}")
                    
                except Exception as e:
                    logger.error(f"Error processing chunk {chunk_number}: {e}")
                    stats['records_failed'] += len(chunk_data)
                    stats['errors'].append(f"Chunk {chunk_number}: {str(e)}")
            
            # Get sheet info for response
            try:
                sheet_info = self.client.get_sheet_info()
            except Exception as e:
                logger.warning(f"Could not get sheet info: {e}")
                sheet_info = {}
            
            # Prepare final response
            result = {
                'status': 'success',
                'records_processed': stats['records_processed'],
                'records_created': stats['records_created'],
                'records_updated': stats['records_updated'],
                'records_failed': stats['records_failed'],
                'records_deleted': existing_count if not self.dry_run else 0,
                'sheet_info': sheet_info,
                'sync_id': sync_record.id
            }
            
            if stats['errors']:
                result['warnings'] = stats['errors']
            
            # Update SyncHistory record with success
            final_stats = {
                'records_processed': stats['records_processed'],
                'records_created': stats['records_created'],
                'records_updated': stats['records_updated'],
                'records_failed': stats['records_failed'],
                'records_deleted': existing_count if not self.dry_run else 0
            }
            self.update_sync_history_record(sync_record, 'success', final_stats)
            
            logger.info(f"Sync completed successfully: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            
            # Update SyncHistory record with failure
            error_stats = {
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0,
                'error_details': {'error_message': str(e)}
            }
            self.update_sync_history_record(sync_record, 'failed', error_stats)
            
            return {
                'status': 'failed',
                'error': str(e),
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0,
                'sync_id': sync_record.id
            }
    
    def _process_data_chunk(self, chunk_data: List[Dict[str, Any]], start_index: int) -> Dict[str, int]:
        """
        Process a chunk of data from Google Sheets
        
        Args:
            chunk_data: List of raw records from Google Sheets
            start_index: Starting index for this chunk
            
        Returns:
            Dictionary containing processing statistics
        """
        chunk_stats = {
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0
        }
        
        try:
            # Add sheet row numbers and metadata to each record
            processed_rows = []
            for i, row_data in enumerate(chunk_data):
                try:
                    # Add metadata
                    row_data['_sheet_row_number'] = start_index + i + 2  # +2 for 1-indexed and header row
                    row_data['_sheet_last_modified'] = timezone.now()
                    row_data['_sheet_id'] = self.SHEET_CONFIG['sheet_id']
                    row_data['_tab_name'] = self.SHEET_CONFIG['tab_name']
                    
                    # Transform the record
                    transformed = self.processor.transform_record(row_data)
                    processed_rows.append(transformed)
                    chunk_stats['records_processed'] += 1
                    
                except Exception as e:
                    logger.error(f"Error processing row {start_index + i + 2}: {e}")
                    chunk_stats['records_failed'] += 1
            
            # Batch database operations
            if processed_rows:
                db_stats = self._batch_database_operations(processed_rows)
                chunk_stats['records_created'] += db_stats.get('created', 0)
                chunk_stats['records_updated'] += db_stats.get('updated', 0)
                chunk_stats['records_failed'] += db_stats.get('failed', 0)
            
            return chunk_stats
            
        except Exception as e:
            logger.error(f"Error processing chunk starting at index {start_index}: {e}")
            chunk_stats['records_failed'] += len(chunk_data)
            return chunk_stats
    
    def _batch_database_operations(self, processed_rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Perform batch database operations (create/update) for processed records
        
        Args:
            processed_rows: List of processed and validated records
            
        Returns:
            Dictionary containing database operation statistics
        """
        batch_stats = {
            'created': 0,
            'updated': 0,
            'failed': 0
        }
        
        try:
            from django.db import transaction
            
            with transaction.atomic():
                # Get existing row numbers to determine creates vs updates
                row_numbers = [row.get('sheet_row_number') for row in processed_rows if row.get('sheet_row_number')]
                existing_row_numbers = set(
                    GoogleSheetMarketingSpend.objects.filter(
                        sheet_row_number__in=row_numbers
                    ).values_list('sheet_row_number', flat=True)
                )
                
                # Separate into creates and updates based on existing check
                records_to_create = []
                records_to_update = []
                
                for row_data in processed_rows:
                    row_num = row_data.get('sheet_row_number')
                    if row_num in existing_row_numbers:
                        records_to_update.append(row_data)
                    else:
                        records_to_create.append(row_data)
                
                logger.info(f"Batch operations: {len(records_to_create)} creates, {len(records_to_update)} updates")
                
                # Bulk create new records
                if records_to_create:
                    create_objects = []
                    for row_data in records_to_create:
                        try:
                            # Pre-validate before creating object
                            validated_data = self._validate_row_data(row_data)
                            if validated_data:
                                obj = GoogleSheetMarketingSpend(**validated_data)
                                create_objects.append(obj)
                            else:
                                batch_stats['failed'] += 1
                        except Exception as e:
                            logger.error(f"Error preparing create for row {row_data.get('sheet_row_number')}: {e}")
                            batch_stats['failed'] += 1
                    
                    if create_objects:
                        try:
                            GoogleSheetMarketingSpend.objects.bulk_create(
                                create_objects, 
                                batch_size=self.batch_size,
                                ignore_conflicts=True
                            )
                            batch_stats['created'] += len(create_objects)
                            logger.info(f"Bulk created {len(create_objects)} records")
                        except Exception as e:
                            logger.error(f"Bulk create failed: {e}")
                            logger.info(f"Falling back to individual creates for {len(create_objects)} records")
                            
                            # Fallback to individual creates
                            individual_stats = self._fallback_individual_creates(create_objects)
                            batch_stats['created'] += individual_stats['created']
                            batch_stats['failed'] += individual_stats['failed']
                
                # Bulk update existing records
                if records_to_update:
                    try:
                        # Get existing objects in bulk
                        update_row_numbers = [row['sheet_row_number'] for row in records_to_update]
                        existing_objects = {
                            obj.sheet_row_number: obj 
                            for obj in GoogleSheetMarketingSpend.objects.filter(
                                sheet_row_number__in=update_row_numbers
                            )
                        }
                        
                        update_objects = []
                        for row_data in records_to_update:
                            row_num = row_data.get('sheet_row_number')
                            if row_num in existing_objects:
                                try:
                                    # Pre-validate before updating
                                    validated_data = self._validate_row_data(row_data)
                                    if validated_data:
                                        obj = existing_objects[row_num]
                                        # Update fields
                                        for field, value in validated_data.items():
                                            if field != 'id':  # Don't update primary key
                                                setattr(obj, field, value)
                                        update_objects.append(obj)
                                    else:
                                        batch_stats['failed'] += 1
                                except Exception as e:
                                    logger.error(f"Error preparing update for row {row_num}: {e}")
                                    batch_stats['failed'] += 1
                            else:
                                logger.warning(f"Record not found for row {row_num}")
                                batch_stats['failed'] += 1
                        
                        if update_objects:
                            try:
                                # Get all field names except primary key and created_at
                                # Note: sheet_row_number is the primary key, not 'id'
                                update_fields = [
                                    field.name for field in GoogleSheetMarketingSpend._meta.fields 
                                    if field.name not in ['sheet_row_number', 'created_at']
                                ]
                                
                                GoogleSheetMarketingSpend.objects.bulk_update(
                                    update_objects,
                                    update_fields,
                                    batch_size=self.batch_size
                                )
                                batch_stats['updated'] += len(update_objects)
                                logger.info(f"Bulk updated {len(update_objects)} records")
                            except Exception as e:
                                logger.error(f"Bulk update failed: {e}")
                                logger.info(f"Falling back to individual updates for {len(update_objects)} records")
                                
                                # Fallback to individual updates
                                individual_stats = self._fallback_individual_updates(update_objects)
                                batch_stats['updated'] += individual_stats['updated']
                                batch_stats['failed'] += individual_stats['failed']
                    
                    except Exception as e:
                        logger.error(f"Update preparation failed: {e}")
                        batch_stats['failed'] += len(records_to_update)
                
        except Exception as e:
            logger.error(f"Database transaction failed: {e}")
            batch_stats['failed'] += len(processed_rows)
        
        return batch_stats
    
    def _validate_row_data(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate row data before database operations
        
        Args:
            row_data: Row data to validate
            
        Returns:
            Validated data dictionary
        """
        try:
            # Use processor validation
            validated = self.processor.validate_record(row_data)
            return validated
        except Exception as e:
            logger.error(f"Validation failed for row {row_data.get('sheet_row_number')}: {e}")
            return None
    
    def _fallback_individual_creates(self, create_objects: List[GoogleSheetMarketingSpend]) -> Dict[str, int]:
        """
        Fallback method for individual creates when bulk create fails
        
        Args:
            create_objects: List of model instances to create
            
        Returns:
            Dictionary with create statistics
        """
        fallback_stats = {'created': 0, 'failed': 0}
        
        for obj in create_objects:
            try:
                # Validate object before saving
                validation_errors = self._validate_field_lengths(obj)
                if validation_errors:
                    logger.error(f"Validation errors for row {obj.sheet_row_number}: {validation_errors}")
                    fallback_stats['failed'] += 1
                    continue
                
                obj.save()
                fallback_stats['created'] += 1
            except Exception as e:
                logger.error(f"Failed to create record for row {obj.sheet_row_number}: {e}")
                logger.error(f"Failed object data: {self._get_object_field_summary(obj)}")
                fallback_stats['failed'] += 1
        
        logger.info(f"Individual creates completed: {fallback_stats['created']} created, {fallback_stats['failed']} failed")
        return fallback_stats
    
    def _fallback_individual_updates(self, update_objects: List[GoogleSheetMarketingSpend]) -> Dict[str, int]:
        """
        Fallback method for individual updates when bulk update fails
        
        Args:
            update_objects: List of model instances to update
            
        Returns:
            Dictionary with update statistics
        """
        fallback_stats = {'updated': 0, 'failed': 0}
        
        for obj in update_objects:
            try:
                # Validate object before saving
                validation_errors = self._validate_field_lengths(obj)
                if validation_errors:
                    logger.error(f"Validation errors for row {obj.sheet_row_number}: {validation_errors}")
                    fallback_stats['failed'] += 1
                    continue
                
                obj.save()
                fallback_stats['updated'] += 1
            except Exception as e:
                logger.error(f"Failed to update record for row {obj.sheet_row_number}: {e}")
                logger.error(f"Failed object data: {self._get_object_field_summary(obj)}")
                fallback_stats['failed'] += 1
        
        logger.info(f"Individual updates completed: {fallback_stats['updated']} updated, {fallback_stats['failed']} failed")
        return fallback_stats
    
    def _validate_field_lengths(self, obj: GoogleSheetMarketingSpend) -> List[str]:
        """
        Validate field lengths against model constraints
        
        Args:
            obj: Model instance to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Define field length limits
        field_limits = {
            'division': 50,
            'channel': 50,
            'campaign': 100,
        }
        
        for field_name, max_length in field_limits.items():
            value = getattr(obj, field_name, None)
            if value and len(value) > max_length:
                errors.append(f"Field '{field_name}' length {len(value)} exceeds limit {max_length}")
        
        return errors
    
    def _get_object_field_summary(self, obj: GoogleSheetMarketingSpend) -> Dict[str, str]:
        """
        Get summary of object field values for debugging
        
        Args:
            obj: Model instance
            
        Returns:
            Dictionary with field value summary
        """
        return {
            'sheet_row_number': str(obj.sheet_row_number),
            'spend_date': str(obj.spend_date),
            'cost': str(obj.cost),
            'division': str(obj.division)[:50] if obj.division else None,
            'channel': str(obj.channel)[:50] if obj.channel else None,
            'campaign': str(obj.campaign)[:50] if obj.campaign else None,
        }
    
    async def sync_with_retry(self, max_retries: int = 2) -> Dict[str, Any]:
        """
        Async version with retry logic (for Celery tasks)
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sync attempt {attempt + 1}/{max_retries + 1}")
                result = self.sync_sync()  # Use sync version for now
                return result
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Sync attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    logger.error(f"All sync attempts failed. Last error: {e}")
                    return {
                        'status': 'failed',
                        'error': str(e),
                        'records_processed': 0,
                        'records_created': 0,
                        'records_updated': 0,
                        'records_failed': 0
                    }
    
    def sync_with_retry_sync(self, max_retries: int = 2) -> Dict[str, Any]:
        """
        Synchronous version with retry logic (for management commands)
        """
        for attempt in range(max_retries + 1):
            try:
                logger.info(f"Sync attempt {attempt + 1}/{max_retries + 1}")
                result = self.sync_sync()
                return result
            except Exception as e:
                if attempt < max_retries:
                    logger.warning(f"Sync attempt {attempt + 1} failed: {e}. Retrying...")
                    continue
                else:
                    logger.error(f"All sync attempts failed. Last error: {e}")
                    return {
                        'status': 'failed',
                        'error': str(e),
                        'records_processed': 0,
                        'records_created': 0,
                        'records_updated': 0,
                        'records_failed': 0
                    }
    
    # Abstract method implementations required by BaseSyncEngine
    
    async def initialize_client(self) -> None:
        """Initialize the Google Sheets API client"""
        try:
            from ingestion.sync.gsheet.clients.marketing_spends import MarketingSpendsClient
            self.client = MarketingSpendsClient(
                sheet_id=self.SHEET_CONFIG['sheet_id'],
                tab_name=self.SHEET_CONFIG['tab_name']
            )
            # Note: Google Sheets client might not have async initialize method
            # If it does, call it. If not, the constructor should handle initialization
            if hasattr(self.client, 'initialize'):
                await self.client.initialize()
            logger.info("Google Sheets client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Google Sheets client: {e}")
            raise
    
    async def fetch_data(self, **kwargs) -> List[Dict[str, Any]]:
        """Fetch data from Google Sheets"""
        if not self.client:
            await self.initialize_client()
        
        try:
            last_sync_time = kwargs.get('last_sync_time') or self.get_last_sync_timestamp()
            # Use sync method since Google Sheets client is synchronous
            data = self.client.fetch_sheet_data_sync()
            logger.info(f"Fetched {len(data)} rows from Google Sheets")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw sheet data to model format"""
        try:
            if not self.processor:
                self.processor = MarketingSpendsProcessor(
                    model_class=self.SHEET_CONFIG['target_model'],
                    dry_run=self.dry_run
                )
            
            transformed_data = []
            
            for i, row_data in enumerate(raw_data):
                try:
                    # Add metadata
                    row_data['_sheet_row_number'] = i + 2  # +2 for 1-indexed and header row
                    row_data['_sheet_last_modified'] = timezone.now()
                    row_data['_sheet_id'] = self.SHEET_CONFIG['sheet_id']
                    row_data['_tab_name'] = self.SHEET_CONFIG['tab_name']
                    
                    # Transform the record
                    transformed_row = self.processor.transform_record(row_data)
                    if transformed_row:
                        transformed_data.append(transformed_row)
                except Exception as e:
                    logger.error(f"Failed to transform row {i + 2}: {e}")
            
            logger.info(f"Transformed {len(transformed_data)} rows")
            return transformed_data
        except Exception as e:
            logger.error(f"Failed to transform data: {e}")
            raise
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        try:
            if not self.processor:
                self.processor = MarketingSpendsProcessor(
                    model_class=self.SHEET_CONFIG['target_model'],
                    dry_run=self.dry_run
                )
            
            validated_data = []
            for row_data in data:
                try:
                    validated_row = self.processor.validate_record(row_data)
                    if validated_row:
                        validated_data.append(validated_row)
                    else:
                        logger.warning(f"Validation failed for row: {row_data.get('sheet_row_number')}")
                except Exception as e:
                    logger.error(f"Validation error for row {row_data.get('sheet_row_number')}: {e}")
            
            logger.info(f"Validated {len(validated_data)} rows")
            return validated_data
        except Exception as e:
            logger.error(f"Failed to validate data: {e}")
            raise
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save validated data to database"""
        try:
            # Convert list of dicts to the format expected by _batch_database_operations
            stats = self._batch_database_operations(validated_data)
            
            result = {
                'processed': len(validated_data),
                'created': stats.get('created', 0),
                'updated': stats.get('updated', 0),
                'failed': stats.get('failed', 0)
            }
            
            logger.info(f"Saved data: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        try:
            # Google Sheets client doesn't typically need cleanup
            # But we can add any necessary cleanup here
            if hasattr(self.client, 'cleanup'):
                await self.client.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
            # Don't raise exception during cleanup
