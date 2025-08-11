"""
Marketing Leads Sync Engine for Google Sheets

Follows CRM sync guide architecture with SyncHistory integration.
Configuration is hardcoded here, not stored in database.
"""
import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from django.utils import timezone
from ingestion.models.common import SyncHistory  # Use global SyncHistory table
from ingestion.models.gsheet import GoogleSheetMarketingLead
from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient
from ingestion.sync.gsheet.processors.marketing_leads import MarketingLeadsProcessor
from ingestion.sync.gsheet.engines.base import BaseGoogleSheetsSyncEngine

logger = logging.getLogger(__name__)


class MarketingLeadsSyncEngine(BaseGoogleSheetsSyncEngine):
    """
    Sync engine for Marketing Source Leads from Google Sheets
    
    Configuration (hardcoded as per CRM sync guide):
    - Sheet ID: 1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo
    - Tab: "Marketing Source Leads"
    - Model: GoogleSheetMarketingLead
    - CRM Source: 'gsheet_marketing_leads'
    """
    
    # HARDCODED CONFIGURATION (as per CRM sync guide)
    SHEET_CONFIG = {
        'sheet_id': '1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo',
        'tab_name': 'Marketing Source Leads',
        'header_row': 1,
        'data_start_row': 2,
        'target_model': GoogleSheetMarketingLead,
        'crm_source': 'gsheet_marketing_leads',  # For SyncHistory table
    }
    
    def __init__(self, batch_size: int = 500, dry_run: bool = False, force_overwrite: bool = False):
        """Initialize the marketing leads sync engine"""
        
        super().__init__(
            sheet_name='marketing_leads',
            batch_size=batch_size,
            dry_run=dry_run,
            force_overwrite=force_overwrite
        )
        
        # Initialize components with hardcoded config
        self.client = MarketingLeadsClient(
            sheet_id=self.SHEET_CONFIG['sheet_id'],
            tab_name=self.SHEET_CONFIG['tab_name']
        )
        
        self.processor = MarketingLeadsProcessor(model_class=GoogleSheetMarketingLead)
        self.model = self.SHEET_CONFIG['target_model']
        self.crm_source = self.SHEET_CONFIG['crm_source']
        
        logger.info(f"Initialized MarketingLeadsSyncEngine")
        logger.info(f"Sheet ID: {self.SHEET_CONFIG['sheet_id']}")
        logger.info(f"Tab: {self.SHEET_CONFIG['tab_name']}")
        logger.info(f"CRM Source: {self.crm_source}")
    
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """
        Get last successful sync timestamp from global SyncHistory table
        
        Returns:
            datetime: Last sync time or None if never synced
        """
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='gsheet',
                sync_type='marketing_leads',
                status='success'
            ).order_by('-end_time').first()
            
            if last_sync and last_sync.end_time:
                logger.info(f"Last successful sync: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info("No previous successful sync found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    def create_sync_history_record(self) -> SyncHistory:
        """
        Create new SyncHistory record for this sync operation
        
        Returns:
            SyncHistory: New sync history record
        """
        return SyncHistory.objects.create(
            crm_source='gsheet',
            sync_type='marketing_leads',
            endpoint=f"sheets/{self.SHEET_CONFIG['sheet_id']}/{self.SHEET_CONFIG['tab_name']}",
            configuration={
                'sheet_id': self.SHEET_CONFIG['sheet_id'],
                'tab_name': self.SHEET_CONFIG['tab_name'],
                'model': self.model.__name__,
                'batch_size': self.batch_size,
                'dry_run': self.dry_run,
                'force_overwrite': self.force_overwrite
            },
            status='running',
            start_time=timezone.now()
        )
    
    def update_sync_history_record(self, sync_record: SyncHistory, 
                                 status: str, stats: Dict[str, Any]):
        """
        Update SyncHistory record with completion status and statistics
        
        Args:
            sync_record: SyncHistory record to update
            status: Final status ('success', 'failed', 'partial')
            stats: Sync statistics dictionary
        """
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = stats.get('records_processed', 0)
        sync_record.records_created = stats.get('records_created', 0)
        sync_record.records_updated = stats.get('records_updated', 0)
        sync_record.records_failed = stats.get('records_failed', 0)
        
        if status == 'failed' and 'error_message' in stats:
            sync_record.error_message = stats['error_message']
        
        # Add performance metrics
        duration = (sync_record.end_time - sync_record.start_time).total_seconds()
        sync_record.performance_metrics = {
            'duration_seconds': duration,
            'records_per_second': sync_record.records_processed / duration if duration > 0 else 0
        }
        
        sync_record.save()
        
        logger.info(f"Updated SyncHistory record {sync_record.id} with status: {status}")
    
    def sync_with_retry_sync(self, max_retries: int = 2) -> Dict[str, Any]:
        """
        Execute sync with retry logic and SyncHistory tracking (synchronous version)
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict: Sync result with status and statistics
        """
        
        # Create SyncHistory record
        sync_record = self.create_sync_history_record()
        
        try:
            # Check if sync is needed (unless forced)
            if not self.force_overwrite:
                last_sync = self.get_last_sync_timestamp()
                if not self.client.is_sheet_modified_since_sync(last_sync):
                    stats = {'status': 'skipped', 'reason': 'Sheet not modified since last sync'}
                    self.update_sync_history_record(sync_record, 'skipped', stats)
                    return stats
            
            # Execute sync
            result = self.sync_sync()
            
            # Update SyncHistory with success
            self.update_sync_history_record(sync_record, 'success', result)
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            
            # Update SyncHistory with failure
            error_stats = {
                'status': 'failed',
                'error_message': str(e),
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0
            }
            
            self.update_sync_history_record(sync_record, 'failed', error_stats)
            
            raise
    
    def sync_sync(self) -> Dict[str, Any]:
        """
        Synchronous version of sync for management commands with chunking and batching
        """
        try:
            # Test connection
            if not self.client.test_connection():
                raise Exception("Google Sheets API connection failed")
            
            # Fetch data from Google Sheets
            logger.info("Fetching data from Google Sheets...")
            raw_data = self.client.fetch_sheet_data_sync()
            logger.info(f"Fetched {len(raw_data)} rows from Google Sheets")
            
            if not raw_data:
                logger.info("No data found in Google Sheet")
                return {
                    'status': 'success',
                    'records_processed': 0,
                    'records_created': 0,
                    'records_updated': 0,
                    'records_failed': 0,
                    'message': 'No data found in sheet'
                }
            
            # Initialize statistics
            stats = {
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0
            }
            
            # Process data in chunks
            chunk_size = min(self.batch_size, 1000)  # Max 1000 rows per chunk
            total_chunks = (len(raw_data) + chunk_size - 1) // chunk_size
            
            logger.info(f"Processing {len(raw_data)} rows in {total_chunks} chunks of {chunk_size} rows each")
            
            for chunk_index in range(total_chunks):
                start_index = chunk_index * chunk_size
                end_index = min(start_index + chunk_size, len(raw_data))
                chunk_data = raw_data[start_index:end_index]
                
                logger.info(f"Processing chunk {chunk_index + 1}/{total_chunks} (rows {start_index + 1}-{end_index})")
                
                # Process chunk
                chunk_stats = self._process_data_chunk(chunk_data, start_index)
                
                # Update overall statistics
                stats['records_processed'] += chunk_stats['records_processed']
                stats['records_created'] += chunk_stats['records_created']
                stats['records_updated'] += chunk_stats['records_updated']
                stats['records_failed'] += chunk_stats['records_failed']
                
                # Log progress
                if (chunk_index + 1) % 10 == 0 or chunk_index + 1 == total_chunks:
                    logger.info(f"Progress: {chunk_index + 1}/{total_chunks} chunks completed. "
                              f"Created: {stats['records_created']}, Updated: {stats['records_updated']}, Failed: {stats['records_failed']}")
            
            logger.info(f"Sync completed: {stats}")
            return {
                'status': 'success',
                **stats,
                'message': f'Sync completed: {stats["records_created"]} created, {stats["records_updated"]} updated, {stats["records_failed"]} failed'
            }
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            raise

    def _process_data_chunk(self, chunk_data: List[Dict[str, Any]], start_index: int) -> Dict[str, int]:
        """
        Process a chunk of data with batched database operations
        
        Args:
            chunk_data: List of raw row data
            start_index: Starting index for row numbering
            
        Returns:
            Dictionary with processing statistics
        """
        chunk_stats = {
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0
        }
        
        try:
            # Process rows and collect valid data
            processed_rows = []
            
            for i, row_data in enumerate(chunk_data):
                try:
                    # Add row metadata
                    row_data['sheet_row_number'] = start_index + i + 2  # +2 for header row and 0-based index
                    
                    # Process the row using the processor
                    processed_data = self.processor.process_row_sync(row_data)
                    
                    if processed_data:
                        processed_rows.append(processed_data)
                        chunk_stats['records_processed'] += 1
                    else:
                        chunk_stats['records_failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process row {start_index + i + 2}: {e}")
                    chunk_stats['records_failed'] += 1
                    continue
            
            # Batch database operations if not dry run
            if not self.dry_run and processed_rows:
                batch_stats = self._batch_database_operations(processed_rows)
                chunk_stats['records_created'] += batch_stats['created']
                chunk_stats['records_updated'] += batch_stats['updated']
                chunk_stats['records_failed'] += batch_stats['failed']
            elif self.dry_run:
                # In dry run, count all processed rows as "would be created"
                chunk_stats['records_created'] = len(processed_rows)
                
        except Exception as e:
            logger.error(f"Error processing data chunk: {e}")
            chunk_stats['records_failed'] += len(chunk_data)
        
        return chunk_stats

    def _batch_database_operations(self, processed_rows: List[Dict[str, Any]]) -> Dict[str, int]:
        """
        Perform batched database operations for efficiency
        
        Args:
            processed_rows: List of processed row data
            
        Returns:
            Dictionary with operation statistics
        """
        from django.db import transaction
        
        batch_stats = {
            'created': 0,
            'updated': 0,
            'failed': 0
        }
        
        if not processed_rows:
            return batch_stats
        
        try:
            # Use database transaction for better performance
            with transaction.atomic():
                # Extract all row numbers for bulk lookup
                row_numbers = [row_data.get('sheet_row_number') for row_data in processed_rows 
                              if row_data.get('sheet_row_number')]
                
                # Single bulk query to check existing records
                existing_row_numbers = set(
                    GoogleSheetMarketingLead.objects.filter(
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
                                obj = GoogleSheetMarketingLead(**validated_data)
                                create_objects.append(obj)
                            else:
                                batch_stats['failed'] += 1
                        except Exception as e:
                            logger.error(f"Error preparing create for row {row_data.get('sheet_row_number')}: {e}")
                            batch_stats['failed'] += 1
                    
                    if create_objects:
                        try:
                            GoogleSheetMarketingLead.objects.bulk_create(
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
                            for obj in GoogleSheetMarketingLead.objects.filter(
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
                                # Get all field names except id and created_at
                                update_fields = [
                                    field.name for field in GoogleSheetMarketingLead._meta.fields 
                                    if field.name not in ['id', 'created_at']
                                ]
                                
                                GoogleSheetMarketingLead.objects.bulk_update(
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
        Validate and clean row data before database operations
        
        Args:
            row_data: Raw row data
            
        Returns:
            Validated row data or None if validation fails
        """
        try:
            validated_data = {}
            
            # Get field constraints from model
            field_constraints = {}
            for field in GoogleSheetMarketingLead._meta.fields:
                if hasattr(field, 'max_length') and field.max_length:
                    field_constraints[field.name] = field.max_length
            
            # Validate each field
            for field_name, value in row_data.items():
                if value is None:
                    continue
                    
                # Check string field lengths
                if field_name in field_constraints and isinstance(value, str):
                    max_length = field_constraints[field_name]
                    if len(value) > max_length:
                        logger.warning(f"Field '{field_name}' truncated from {len(value)} to {max_length} chars for row {row_data.get('sheet_row_number')}")
                        value = value[:max_length]
                
                validated_data[field_name] = value
            
            return validated_data
            
        except Exception as e:
            logger.error(f"Validation failed for row {row_data.get('sheet_row_number')}: {e}")
            return None

    def _fallback_individual_creates(self, create_objects: List[GoogleSheetMarketingLead]) -> Dict[str, int]:
        """
        Fallback to individual creates when bulk create fails
        
        Args:
            create_objects: List of model objects to create
            
        Returns:
            Dictionary with operation statistics
        """
        fallback_stats = {'created': 0, 'failed': 0}
        
        for obj in create_objects:
            try:
                # Validate field lengths before saving
                validation_errors = self._validate_field_lengths(obj)
                if validation_errors:
                    logger.error(f"Field validation failed for row {getattr(obj, 'sheet_row_number', 'unknown')}: {validation_errors}")
                    fallback_stats['failed'] += 1
                    continue
                
                obj.save()
                fallback_stats['created'] += 1
                
            except Exception as e:
                logger.error(f"Individual create failed for row {getattr(obj, 'sheet_row_number', 'unknown')}: {e}")
                # Log the problematic data for debugging
                logger.error(f"Failed object data: {self._get_object_field_summary(obj)}")
                fallback_stats['failed'] += 1
        
        logger.info(f"Individual creates completed: {fallback_stats['created']} created, {fallback_stats['failed']} failed")
        return fallback_stats

    def _fallback_individual_updates(self, update_objects: List[GoogleSheetMarketingLead]) -> Dict[str, int]:
        """
        Fallback to individual updates when bulk update fails
        
        Args:
            update_objects: List of model objects to update
            
        Returns:
            Dictionary with operation statistics
        """
        fallback_stats = {'updated': 0, 'failed': 0}
        
        for obj in update_objects:
            try:
                # Validate field lengths before saving
                validation_errors = self._validate_field_lengths(obj)
                if validation_errors:
                    logger.error(f"Field validation failed for row {getattr(obj, 'sheet_row_number', 'unknown')}: {validation_errors}")
                    fallback_stats['failed'] += 1
                    continue
                
                obj.save()
                fallback_stats['updated'] += 1
                
            except Exception as e:
                logger.error(f"Individual update failed for row {getattr(obj, 'sheet_row_number', 'unknown')}: {e}")
                # Log the problematic data for debugging
                logger.error(f"Failed object data: {self._get_object_field_summary(obj)}")
                fallback_stats['failed'] += 1
        
        logger.info(f"Individual updates completed: {fallback_stats['updated']} updated, {fallback_stats['failed']} failed")
        return fallback_stats

    def _validate_field_lengths(self, obj: GoogleSheetMarketingLead) -> List[str]:
        """
        Validate field lengths against model field constraints
        
        Args:
            obj: Model object to validate
            
        Returns:
            List of validation error messages
        """
        errors = []
        
        # Get field constraints from model
        for field in GoogleSheetMarketingLead._meta.fields:
            if hasattr(field, 'max_length') and field.max_length:
                field_name = field.name
                field_value = getattr(obj, field_name, None)
                
                if field_value and isinstance(field_value, str) and len(field_value) > field.max_length:
                    errors.append(f"Field '{field_name}' value length {len(field_value)} exceeds max_length {field.max_length}. Value: '{field_value[:100]}...'")
        
        return errors

    def _get_object_field_summary(self, obj: GoogleSheetMarketingLead) -> Dict[str, str]:
        """
        Get a summary of object field values for debugging
        
        Args:
            obj: Model object to summarize
            
        Returns:
            Dictionary with field names and truncated values
        """
        summary = {}
        
        for field in GoogleSheetMarketingLead._meta.fields:
            field_name = field.name
            field_value = getattr(obj, field_name, None)
            
            if field_value is not None:
                if isinstance(field_value, str):
                    # Truncate long strings for logging
                    summary[field_name] = f"'{field_value[:50]}...'" if len(field_value) > 50 else f"'{field_value}'"
                    if hasattr(field, 'max_length') and field.max_length and len(field_value) > field.max_length:
                        summary[field_name] += f" [LENGTH: {len(field_value)}, MAX: {field.max_length}]"
                else:
                    summary[field_name] = str(field_value)
        
        return summary
    
    async def sync_with_retry(self, max_retries: int = 2) -> Dict[str, Any]:
        """
        Execute sync with retry logic and SyncHistory tracking
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict: Sync result with status and statistics
        """
        
        # Create SyncHistory record
        sync_record = self.create_sync_history_record()
        
        try:
            # Check if sync is needed (unless forced)
            if not self.force_overwrite:
                if not await self.client.is_sheet_modified_since(self.get_last_sync_timestamp()):
                    stats = {'status': 'skipped', 'reason': 'Sheet not modified since last sync'}
                    self.update_sync_history_record(sync_record, 'skipped', stats)
                    return stats
            
            # Execute sync
            result = await self.sync()
            
            # Update SyncHistory with success
            self.update_sync_history_record(sync_record, 'success', result)
            
            return result
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            
            # Update SyncHistory with failure
            error_stats = {
                'status': 'failed',
                'error_message': str(e),
                'records_processed': 0,
                'records_created': 0,
                'records_updated': 0,
                'records_failed': 0
            }
            
            self.update_sync_history_record(sync_record, 'failed', error_stats)
            
            raise

    # Abstract method implementations required by BaseSyncEngine
    
    async def initialize_client(self) -> None:
        """Initialize the Google Sheets API client"""
        try:
            from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient
            self.client = MarketingLeadsClient(
                sheet_id=self.SHEET_CONFIG['sheet_id'],
                tab_name=self.SHEET_CONFIG['tab_name']
            )
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
            data = await self.client.fetch_sheet_data(
                last_modified_since=last_sync_time,
                force_refresh=self.force_overwrite
            )
            logger.info(f"Fetched {len(data)} rows from Google Sheets")
            return data
        except Exception as e:
            logger.error(f"Failed to fetch data: {e}")
            raise
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw sheet data to model format"""
        try:
            processor = MarketingLeadsProcessor(model_class=GoogleSheetMarketingLead)
            transformed_data = []
            
            for row_data in raw_data:
                transformed_row = await processor.process_row(row_data)
                if transformed_row:
                    transformed_data.append(transformed_row)
            
            logger.info(f"Transformed {len(transformed_data)} rows")
            return transformed_data
        except Exception as e:
            logger.error(f"Failed to transform data: {e}")
            raise
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data"""
        try:
            from ingestion.sync.gsheet.validators.marketing_leads import MarketingLeadsValidator
            validator = MarketingLeadsValidator()
            
            validated_data = []
            for row_data in data:
                if await validator.validate_row(row_data):
                    validated_data.append(row_data)
                else:
                    logger.warning(f"Validation failed for row: {row_data}")
            
            logger.info(f"Validated {len(validated_data)} rows")
            return validated_data
        except Exception as e:
            logger.error(f"Failed to validate data: {e}")
            raise
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save validated data to database"""
        try:
            processor = MarketingLeadsProcessor(model_class=GoogleSheetMarketingLead)
            result = await processor.bulk_save(validated_data, batch_size=self.batch_size)
            
            logger.info(f"Saved data: {result}")
            return result
        except Exception as e:
            logger.error(f"Failed to save data: {e}")
            raise
    
    async def cleanup(self) -> None:
        """Cleanup resources after sync"""
        try:
            if self.client:
                await self.client.cleanup()
            logger.info("Cleanup completed successfully")
        except Exception as e:
            logger.warning(f"Cleanup failed: {e}")
            # Don't raise exception during cleanup
