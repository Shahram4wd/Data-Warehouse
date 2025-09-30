"""
Marketing Leads Sync Engine for Google Sheets

Follows CRM sync guide architecture with SyncHistory integration.
Configuration supports multi-year sheets via environment variables.
"""
import logging
import os
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
    
    Configuration supports multi-year sheets via environment variables:
    - GSHEET_2024_MARKETING_LEADS_ID: Sheet ID for 2024 marketing leads
    - GSHEET_2025_MARKETING_LEADS_ID: Sheet ID for 2025 marketing leads
    - Tab: "Marketing Source Leads" (standard for both sheets)
    - Model: GoogleSheetMarketingLead (with year-row ID format)
    - CRM Source: 'gsheet_marketing_leads'
    """
    
    # SHEET CONFIGURATIONS (from environment variables)
    SHEET_CONFIGS = [
        {
            'year': 2024,
            'sheet_id': os.getenv('GSHEET_2024_MARKETING_LEADS_ID'),
            'tab_name': 'Marketing Source Leads',
            'header_row': 1,
            'data_start_row': 2,
        },
        {
            'year': 2025,
            'sheet_id': os.getenv('GSHEET_2025_MARKETING_LEADS_ID'),
            'tab_name': 'Marketing Source Leads',
            'header_row': 1,
            'data_start_row': 2,
        }
    ]
    
    # Common configuration
    TARGET_MODEL = GoogleSheetMarketingLead
    CRM_SOURCE = 'gsheet_marketing_leads'  # For SyncHistory table
    
    def __init__(self, batch_size: int = 500, dry_run: bool = False, force_overwrite: bool = False):
        """Initialize the marketing leads sync engine"""
        
        super().__init__(
            sheet_name='marketing_leads',
            batch_size=batch_size,
            dry_run=dry_run,
            force_overwrite=force_overwrite
        )
        
        # Validate environment variables
        valid_configs = []
        for config in self.SHEET_CONFIGS:
            if config['sheet_id']:
                valid_configs.append(config)
                logger.info(f"Found {config['year']} sheet: {config['sheet_id']}")
            else:
                logger.warning(f"Missing environment variable for {config['year']} sheet")
        
        if not valid_configs:
            raise ValueError("No valid sheet configurations found. Check GSHEET_202X_MARKETING_LEADS_ID environment variables.")
        
        self.sheet_configs = valid_configs
        self.model = self.TARGET_MODEL
        self.crm_source = self.CRM_SOURCE
        
        # Initialize processor (will be used for all sheets)
        self.processor = MarketingLeadsProcessor(model_class=GoogleSheetMarketingLead)
        
        logger.info(f"Initialized MarketingLeadsSyncEngine for {len(self.sheet_configs)} sheets")
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
                sync_type__startswith='marketing_leads',
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
    
    def get_last_sync_timestamp_for_year(self, year: int) -> Optional[datetime]:
        """
        Get last successful sync timestamp for a specific year
        
        Args:
            year: Year to get sync timestamp for
            
        Returns:
            datetime: Last sync time for the year or None if never synced
        """
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='gsheet',
                sync_type=f'marketing_leads_{year}',
                status='success'
            ).order_by('-end_time').first()
            
            if last_sync and last_sync.end_time:
                logger.info(f"Last successful {year} sync: {last_sync.end_time}")
                return last_sync.end_time
            else:
                logger.info(f"No previous successful {year} sync found")
                return None
                
        except Exception as e:
            logger.error(f"Error getting last {year} sync timestamp: {e}")
            return None
    
    def create_sync_history_record(self, sheet_config: Dict[str, Any]) -> SyncHistory:
        """
        Create new SyncHistory record for this sync operation
        
        Args:
            sheet_config: Configuration for the specific sheet being synced
        
        Returns:
            SyncHistory: New sync history record
        """
        return SyncHistory.objects.create(
            crm_source='gsheet',
            sync_type=f'marketing_leads_{sheet_config["year"]}',
            endpoint=f"sheets/{sheet_config['sheet_id']}/{sheet_config['tab_name']}",
            configuration={
                'year': sheet_config['year'],
                'sheet_id': sheet_config['sheet_id'],
                'tab_name': sheet_config['tab_name'],
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
        Execute sync with retry logic and SyncHistory tracking for all configured sheets
        
        Args:
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dict: Combined sync result with status and statistics
        """
        
        overall_stats = {
            'status': 'success',
            'records_processed': 0,
            'records_created': 0,
            'records_updated': 0,
            'records_failed': 0,
            'sheets_processed': 0,
            'sheets_failed': 0,
            'sheet_results': []
        }
        
        # Process each configured sheet
        for sheet_config in self.sheet_configs:
            try:
                logger.info(f"Starting sync for {sheet_config['year']} sheet: {sheet_config['sheet_id']}")
                
                # Create SyncHistory record for this sheet
                sync_record = self.create_sync_history_record(sheet_config)
                
                try:
                    # Check if sync is needed (unless forced)
                    if not self.force_overwrite:
                        last_sync = self.get_last_sync_timestamp_for_year(sheet_config['year'])
                        
                        # Create client for this specific sheet to check modification
                        client = MarketingLeadsClient(
                            sheet_id=sheet_config['sheet_id'],
                            tab_name=sheet_config['tab_name']
                        )
                        
                        if not client.is_sheet_modified_since_sync(last_sync):
                            stats = {'status': 'skipped', 'reason': f'Sheet {sheet_config["year"]} not modified since last sync'}
                            self.update_sync_history_record(sync_record, 'skipped', stats)
                            overall_stats['sheet_results'].append({
                                'year': sheet_config['year'],
                                'status': 'skipped',
                                'reason': stats['reason']
                            })
                            continue
                    
                    # Execute sync for this sheet
                    result = self.sync_sheet_sync(sheet_config)
                    
                    # Update SyncHistory with success
                    self.update_sync_history_record(sync_record, 'success', result)
                    
                    # Add to overall stats
                    overall_stats['records_processed'] += result.get('records_processed', 0)
                    overall_stats['records_created'] += result.get('records_created', 0)
                    overall_stats['records_updated'] += result.get('records_updated', 0)
                    overall_stats['records_failed'] += result.get('records_failed', 0)
                    overall_stats['sheets_processed'] += 1
                    
                    overall_stats['sheet_results'].append({
                        'year': sheet_config['year'],
                        'status': 'success',
                        **result
                    })
                    
                    logger.info(f"Successfully synced {sheet_config['year']} sheet")
                    
                except Exception as e:
                    logger.error(f"Sync failed for {sheet_config['year']} sheet: {e}")
                    
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
                    
                    overall_stats['sheets_failed'] += 1
                    overall_stats['sheet_results'].append({
                        'year': sheet_config['year'],
                        'status': 'failed',
                        'error': str(e)
                    })
                    
                    # Continue with other sheets instead of failing completely
                    continue
                    
            except Exception as e:
                logger.error(f"Failed to process {sheet_config['year']} sheet: {e}")
                overall_stats['sheets_failed'] += 1
                overall_stats['sheet_results'].append({
                    'year': sheet_config['year'],
                    'status': 'failed',
                    'error': str(e)
                })
                continue
        
        # Determine overall status
        if overall_stats['sheets_failed'] > 0:
            if overall_stats['sheets_processed'] == 0:
                overall_stats['status'] = 'failed'
            else:
                overall_stats['status'] = 'partial'
        
        return overall_stats
    
    def sync_sheet_sync(self, sheet_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronous version of sync for a single sheet with chunking and batching
        
        Args:
            sheet_config: Configuration for the specific sheet to sync
            
        Returns:
            Dict: Sync result with status and statistics
        """
        try:
            # Create client for this specific sheet
            client = MarketingLeadsClient(
                sheet_id=sheet_config['sheet_id'],
                tab_name=sheet_config['tab_name']
            )
            
            # Test connection
            if not client.test_connection():
                raise Exception(f"Google Sheets API connection failed for {sheet_config['year']} sheet")
            
            # Fetch data from Google Sheets
            logger.info(f"Fetching data from {sheet_config['year']} Google Sheet...")
            raw_data = client.fetch_sheet_data_sync()
            logger.info(f"Fetched {len(raw_data)} rows from {sheet_config['year']} Google Sheet")
            
            if not raw_data:
                logger.info(f"No data found in {sheet_config['year']} Google Sheet")
                return {
                    'status': 'success',
                    'records_processed': 0,
                    'records_created': 0,
                    'records_updated': 0,
                    'records_failed': 0,
                    'message': f'No data found in {sheet_config["year"]} sheet'
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
            
            logger.info(f"Processing {len(raw_data)} rows from {sheet_config['year']} sheet in {total_chunks} chunks of {chunk_size} rows each")
            
            for chunk_index in range(total_chunks):
                start_index = chunk_index * chunk_size
                end_index = min(start_index + chunk_size, len(raw_data))
                chunk_data = raw_data[start_index:end_index]
                
                logger.info(f"Processing {sheet_config['year']} chunk {chunk_index + 1}/{total_chunks} (rows {start_index + 1}-{end_index})")
                
                # Process chunk with year information
                chunk_stats = self._process_data_chunk(chunk_data, start_index, sheet_config['year'])
                
                # Update overall statistics
                stats['records_processed'] += chunk_stats['records_processed']
                stats['records_created'] += chunk_stats['records_created']
                stats['records_updated'] += chunk_stats['records_updated']
                stats['records_failed'] += chunk_stats['records_failed']
                
                # Log progress
                if (chunk_index + 1) % 10 == 0 or chunk_index + 1 == total_chunks:
                    logger.info(f"{sheet_config['year']} Progress: {chunk_index + 1}/{total_chunks} chunks completed. "
                              f"Created: {stats['records_created']}, Updated: {stats['records_updated']}, Failed: {stats['records_failed']}")
            
            logger.info(f"{sheet_config['year']} sync completed: {stats}")
            return {
                'status': 'success',
                **stats,
                'message': f'{sheet_config["year"]} sync completed: {stats["records_created"]} created, {stats["records_updated"]} updated, {stats["records_failed"]} failed'
            }
            
        except Exception as e:
            logger.error(f"{sheet_config['year']} sync failed: {e}")
            raise

    def _process_data_chunk(self, chunk_data: List[Dict[str, Any]], start_index: int, year: int) -> Dict[str, int]:
        """
        Process a chunk of data with batched database operations
        
        Args:
            chunk_data: List of raw row data
            start_index: Starting index for row numbering
            year: Year for this sheet data
            
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
                    # Add row metadata with year information
                    sheet_row_number = start_index + i + 2  # +2 for header row and 0-based index
                    row_data['sheet_row_number'] = sheet_row_number
                    row_data['year'] = year
                    
                    # Process the row using the processor
                    processed_data = self.processor.process_row_sync(row_data)
                    
                    if processed_data:
                        processed_rows.append(processed_data)
                        chunk_stats['records_processed'] += 1
                    else:
                        chunk_stats['records_failed'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process {year} row {start_index + i + 2}: {e}")
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
            logger.error(f"Error processing data chunk for {year}: {e}")
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
                # Extract all record IDs for bulk lookup (year-row format)
                record_ids = []
                for row_data in processed_rows:
                    year = row_data.get('year')
                    sheet_row_number = row_data.get('sheet_row_number')
                    if year and sheet_row_number:
                        record_id = f"{year}-{sheet_row_number}"
                        record_ids.append(record_id)
                
                # Single bulk query to check existing records by ID
                existing_ids = set(
                    GoogleSheetMarketingLead.objects.filter(
                        id__in=record_ids
                    ).values_list('id', flat=True)
                )
                
                # Separate into creates and updates based on existing check
                records_to_create = []
                records_to_update = []
                
                for row_data in processed_rows:
                    year = row_data.get('year')
                    sheet_row_number = row_data.get('sheet_row_number')
                    if year and sheet_row_number:
                        record_id = f"{year}-{sheet_row_number}"
                        # Ensure the ID is included in the processed data
                        row_data['id'] = record_id
                        
                        if record_id in existing_ids:
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
                            if self._validate_row_data(row_data):
                                # Create object using the row data
                                obj = GoogleSheetMarketingLead(**row_data)
                                create_objects.append(obj)
                            else:
                                batch_stats['failed'] += 1
                                
                        except Exception as e:
                            logger.error(f"Failed to create object for ID {row_data.get('id', 'unknown')}: {e}")
                            batch_stats['failed'] += 1
                    
                    # Bulk create
                    if create_objects:
                        try:
                            GoogleSheetMarketingLead.objects.bulk_create(
                                create_objects, 
                                batch_size=500,
                                ignore_conflicts=True  # Handle any race conditions
                            )
                            batch_stats['created'] += len(create_objects)
                            logger.info(f"Bulk created {len(create_objects)} marketing leads")
                        except Exception as e:
                            logger.error(f"Bulk create failed: {e}")
                            batch_stats['failed'] += len(create_objects)
                
                # Bulk update existing records
                if records_to_update:
                    for row_data in records_to_update:
                        try:
                            record_id = row_data.get('id')
                            if self._validate_row_data(row_data):
                                # Update using filter and update for better performance
                                GoogleSheetMarketingLead.objects.filter(
                                    id=record_id
                                ).update(**{k: v for k, v in row_data.items() if k != 'id'})
                                batch_stats['updated'] += 1
                            else:
                                batch_stats['failed'] += 1
                                
                        except Exception as e:
                            logger.error(f"Failed to update record ID {row_data.get('id', 'unknown')}: {e}")
                            batch_stats['failed'] += 1
                
                logger.info(f"Batch complete: {batch_stats['created']} created, {batch_stats['updated']} updated, {batch_stats['failed']} failed")
                
        except Exception as e:
            logger.error(f"Batch database operations failed: {e}")
            batch_stats['failed'] += len(processed_rows)
        
        return batch_stats

    def _validate_row_data(self, row_data: Dict[str, Any]) -> bool:
        """
        Validate row data before database operations
        
        Args:
            row_data: Raw row data
            
        Returns:
            bool: True if data is valid, False otherwise
        """
        try:
            # Basic validation checks
            required_fields = ['id', 'year', 'sheet_row_number']
            for field in required_fields:
                if not row_data.get(field):
                    logger.warning(f"Missing required field '{field}' for row {row_data.get('sheet_row_number')}")
                    return False
            
            # Get field constraints from model
            field_constraints = {}
            for field in GoogleSheetMarketingLead._meta.fields:
                if hasattr(field, 'max_length') and field.max_length:
                    field_constraints[field.name] = field.max_length
            
            # Validate string field lengths
            for field_name, value in row_data.items():
                if value is None:
                    continue
                    
                # Check string field lengths
                if field_name in field_constraints and isinstance(value, str):
                    max_length = field_constraints[field_name]
                    if len(value) > max_length:
                        logger.warning(f"Field '{field_name}' too long ({len(value)} > {max_length}) for row {row_data.get('sheet_row_number')}")
                        # Truncate the value in-place
                        row_data[field_name] = value[:max_length]
            
            return True
            
        except Exception as e:
            logger.error(f"Validation failed for row {row_data.get('sheet_row_number')}: {e}")
            return False
    
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
