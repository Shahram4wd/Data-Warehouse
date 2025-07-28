"""
Base sync engine for SalesPro AWS Athena database operations
Following import_refactoring.md enterprise patterns
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime
from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async
from django.utils import timezone
from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.utils import get_athena_client
from ingestion.athena_client import AthenaClient
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

class BaseSalesProSyncEngine(BaseSyncEngine):
    """Base sync engine for SalesPro AWS Athena operations"""
    
    def __init__(self, table_name: str, model_class, **kwargs):
        super().__init__('salespro', table_name.lower().replace('_', ''), **kwargs)
        self.table_name = table_name
        self.model_class = model_class
        self.connection = None
        self.connection_pool = None
        self.credential_manager = None
        self.automation_engine = None
        self.alert_system = None
        
    def get_default_batch_size(self) -> int:
        """Return default batch size for SalesPro sync operations"""
        return 500  # AWS Athena can handle larger batches efficiently
    
    async def initialize_enterprise_features(self):
        """Initialize enterprise features following framework standards"""
        # Ensure connection pools are initialized
        try:
            from ingestion.base.sync_engine import ensure_connection_pools_initialized
            await ensure_connection_pools_initialized()
        except Exception as e:
            logger.warning(f"Failed to initialize connection pools: {e}")
        
        # Get connection pool from manager (for database operations)
        try:
            from ingestion.base.connection_pool import connection_manager
            self.connection_pool = connection_manager.get_pool('main_database')
        except Exception as e:
            logger.warning(f"Failed to get connection pool: {e}")
            self.connection_pool = None
        
        # Initialize enterprise features with fallback to mock implementations
        try:
            from ingestion.base.enterprise_compat import (
                get_credential_manager, 
                get_automation_engine, 
                get_alert_system
            )
            
            self.credential_manager = get_credential_manager()
            self.automation_engine = get_automation_engine('salespro')
            self.alert_system = get_alert_system()
            
            # Initialize if they support it
            if hasattr(self.credential_manager, 'initialize'):
                await self.credential_manager.initialize()
            if hasattr(self.automation_engine, 'initialize'):
                await self.automation_engine.initialize()
            if hasattr(self.alert_system, 'initialize'):
                await self.alert_system.initialize()
                
        except Exception as e:
            logger.warning(f"Failed to initialize enterprise features: {e}")
            self.credential_manager = None
            self.automation_engine = None
            self.alert_system = None
    
    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp - FRAMEWORK STANDARD"""
        try:
            # Create an async-safe wrapper for the entire database operation
            @sync_to_async
            def get_last_sync():
                last_sync = SyncHistory.objects.filter(
                    crm_source='salespro',
                    sync_type=f'{self.sync_type}_sync',
                    status='success',
                    end_time__isnull=False
                ).order_by('-end_time').first()
                
                return last_sync.end_time if last_sync else None
            
            return await get_last_sync()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None
    
    async def determine_sync_strategy(self, force_full: bool = False) -> Dict[str, Any]:
        """Determine sync strategy based on framework patterns"""
        last_sync = await self.get_last_sync_timestamp()
        
        strategy = {
            'type': 'full' if not last_sync or force_full else 'incremental',
            'last_sync': last_sync,
            'batch_size': self.batch_size,
            'force_full': force_full
        }
        
        logger.info(f"SalesPro {self.sync_type} sync strategy: {strategy['type']}")
        if strategy['type'] == 'incremental':
            logger.info(f"Last sync was at: {last_sync}")
        
        return strategy
        
    async def initialize_client(self) -> None:
        """Initialize AWS Athena client with enterprise features"""
        # Initialize enterprise features first
        await self.initialize_enterprise_features()
        
        try:
            # Get secure credentials if available
            credentials = {}
            if self.credential_manager:
                try:
                    credentials = await self.credential_manager.get_credentials('salespro')
                except Exception:
                    # Fallback if credential manager is not available
                    pass
            
            self.connection = await sync_to_async(get_athena_client)()
            logger.info(f"AWS Athena client initialized for table: {self.table_name}")
        except Exception as e:
            logger.error(f"Failed to initialize Athena client: {e}")
            # Use enterprise error handling
            if self.automation_engine:
                await self.automation_engine.handle_error(e, {
                    'operation': 'initialize_client',
                    'table': self.table_name,
                    'sync_type': self.sync_type
                })
            raise SyncException(f"Athena client initialization failed: {e}")
            
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch data from AWS Athena using boto3 client with enterprise features"""
        if not self.connection:
            raise SyncException("Athena client not initialized")
            
        try:
            # Build query
            query = self._build_query(**kwargs)
            logger.info(f"Executing Athena query: {query}")
            
            # Execute query using the new boto3-based client
            column_names, rows = await sync_to_async(
                self.connection.get_query_with_columns
            )(query, database='home_genius_db')
            
            if not rows:
                logger.info(f"No data found in {self.table_name}")
                return
                
            # Convert rows to list of dictionaries
            batch_size = kwargs.get('limit', self.batch_size)
            max_records = kwargs.get('max_records', 0)
            records_fetched = 0
            
            # Process in batches
            for i in range(0, len(rows), batch_size):
                if max_records > 0 and records_fetched >= max_records:
                    break
                    
                batch_rows = rows[i:i + batch_size]
                
                # Apply max_records limit
                if max_records > 0:
                    remaining = max_records - records_fetched
                    if len(batch_rows) > remaining:
                        batch_rows = batch_rows[:remaining]
                
                # Convert to dictionaries
                batch = [dict(zip(column_names, row)) for row in batch_rows]
                
                records_fetched += len(batch)
                logger.info(f"Fetched {len(batch)} records from {self.table_name}")
                yield batch
                
            logger.info(f"Total records fetched from {self.table_name}: {records_fetched}")
            
            # Report metrics to enterprise monitoring
            if self.automation_engine:
                await self.automation_engine.report_metrics({
                    'operation': 'fetch_data',
                    'table': self.table_name,
                    'records_fetched': records_fetched,
                    'batches_processed': i // batch_size + 1
                })
            
        except Exception as e:
            logger.error(f"Error fetching data from {self.table_name}: {e}")
            # Use enterprise error handling
            if self.automation_engine:
                await self.automation_engine.handle_error(e, {
                    'operation': 'fetch_data',
                    'table': self.table_name,
                    'query': query if 'query' in locals() else 'unknown'
                })
            raise SyncException(f"Failed to fetch data: {e}")
            
    def _build_query(self, **kwargs) -> str:
        """Build SQL query for Athena"""
        query = f"SELECT * FROM {self.table_name}"
        
        conditions = []
        
        # Filter out records with null customer_id to get real data
        if self.table_name == 'customer':
            conditions.append("customer_id IS NOT NULL AND customer_id != ''")
        
        # Add WHERE clause for incremental sync
        since_date = kwargs.get('since_date')
        if since_date:
            # Use created_at for user_activity table (it doesn't have updated_at)
            if self.table_name == 'user_activity':
                since_date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append(f"created_at > timestamp '{since_date_str}'")
            else:
                # For other tables, prefer updated_at but fall back to created_at
                timestamp_columns = ['updated_at', 'modified_date', 'last_modified', 'created_at']
                # For now, use created_at as fallback - this can be customized per table
                since_date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
                conditions.append(f"created_at > timestamp '{since_date_str}'")
        
        # Add WHERE conditions if any
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
                
        # Add ORDER BY for consistent pagination (especially for large tables)
        if self.table_name == 'user_activity':
            query += " ORDER BY created_at"
        else:
            # Default ordering for other tables
            query += " ORDER BY created_at"
                
        # Add LIMIT - always limit large tables to prevent timeouts
        max_records = kwargs.get('max_records', 0)
        if max_records > 0:
            query += f" LIMIT {max_records}"
        elif self.table_name in ['user_activity', 'measure_sheet'] and not since_date:
            # For full sync of large tables, use a reasonable default limit
            default_limit = 10000 if self.table_name == 'measure_sheet' else 50000
            query += f" LIMIT {default_limit}"
            logger.warning(f"Large table '{self.table_name}' detected. Limiting to {default_limit} records per sync. Use --max-records or incremental sync for better control.")
            
        return query
        
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw Athena data to model format"""
        transformed_data = []
        
        for record in raw_data:
            try:
                transformed = await self._transform_record(record)
                if transformed:
                    transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming record: {e}")
                # Continue processing other records
                
        return transformed_data
        
    @abstractmethod
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform a single record - must be implemented by subclasses"""
        pass
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed data using CRM sync framework patterns"""
        validated_data = []
        
        for record in data:
            try:
                # Initialize processor for validation if not already done
                if not hasattr(self, '_processor'):
                    from ingestion.sync.salespro.processors.base import SalesProBaseProcessor
                    self._processor = SalesProBaseProcessor(self.model_class, crm_source='salespro')
                
                # Use framework validation
                validated = await self._validate_record_framework(record)
                if validated:
                    validated_data.append(validated)
            except ValidationException as e:
                record_id = record.get('customer_id', record.get('id', 'unknown'))
                logger.warning(f"Validation warning for record {record_id}: {e}")
                # Continue processing other records in non-strict mode
                validated_data.append(record)  # Include with warning
            except Exception as e:
                record_id = record.get('customer_id', record.get('id', 'unknown'))
                logger.error(f"Validation error for record {record_id}: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def _validate_record_framework(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Validate a single record using framework patterns"""
        if not record:
            return None
        
        # Use the processor's validation if available
        if hasattr(self, '_processor'):
            try:
                # Apply business rule validation
                validated = self._processor.validate_record(record)
                
                # Remove None values but preserve empty strings (following CRM sync guide)
                cleaned_record = {}
                for k, v in validated.items():
                    if v is not None:
                        cleaned_record[k] = v
                    elif k in ['created_at', 'updated_at']:
                        # Keep datetime fields as None if not parseable
                        cleaned_record[k] = None
                
                return cleaned_record
            except Exception as e:
                logger.warning(f"Framework validation failed, using basic validation: {e}")
        
        # Fallback to basic validation
        # For activity records, we don't need customer_id - they're log entries
        # For customer records, we need either customer_id or id
        if self._is_activity_record(record):
            # Activity records are valid if they have activity-specific fields
            if not record.get('user_id') and not record.get('activity_identifier'):
                logger.debug(f"Activity record missing user_id and activity_identifier: {record}")
                return None
        else:
            # Customer/entity records need customer_id or id
            if not record.get('customer_id') and not record.get('id'):
                logger.debug(f"Customer record missing customer_id and id: {record}")
                return None
            
        # Remove None values but preserve empty strings
        cleaned_record = {k: v for k, v in record.items() if v is not None}
        
        return cleaned_record
        
    def _is_activity_record(self, record: Dict[str, Any]) -> bool:
        """Determine if this is an activity/log record vs customer/entity record"""
        # Activity records typically have activity_note, user_id, or activity_identifier
        activity_fields = ['activity_note', 'activity_identifier', 'key_metric']
        return any(record.get(field) for field in activity_fields)
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save data to database using bulk operations with enterprise monitoring following CRM sync guide"""
        if not validated_data:
            return {'created': 0, 'updated': 0, 'failed': 0}
            
        try:
            results = await self._bulk_save_records(validated_data)
            
            # Report metrics to enterprise monitoring following CRM sync guide pattern
            if self.automation_engine:
                await self.automation_engine.report_metrics({
                    'operation': 'save_data',
                    'table': self.table_name,
                    'records_processed': len(validated_data),
                    'records_created': results.get('created', 0),
                    'records_updated': results.get('updated', 0),
                    'records_failed': results.get('failed', 0)
                })
            
            # Log operation summary following CRM sync guide format
            logger.info(f"Completed SalesPro {self.table_name} sync: "
                       f"{results.get('created', 0)} created, "
                       f"{results.get('updated', 0)} updated, "
                       f"{results.get('failed', 0)} failed")
            
            return results
        except Exception as e:
            logger.error(f"Bulk save failed, falling back to individual saves: {e}")
            # Use enterprise error handling following CRM sync guide
            if self.automation_engine:
                await self.automation_engine.handle_error(e, {
                    'operation': 'save_data_bulk',
                    'table': self.table_name,
                    'record_count': len(validated_data)
                })
            return await self._save_individual_records(validated_data)
            
    async def _bulk_save_records(self, records: List[Dict]) -> Dict[str, int]:
        """Bulk save records using Django's bulk operations"""
        from django.db import transaction
        
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        # Get existing record IDs (assuming 'id' field exists)
        record_ids = [r.get('id') for r in records if r.get('id')]
        existing_records = {}
        
        if record_ids:
            existing_records = {
                obj.id: obj for obj in 
                await sync_to_async(list)(
                    self.model_class.objects.filter(id__in=record_ids)
                )
            }
        
        to_create = []
        to_update = []
        
        for record in records:
            record_id = record.get('id')
            if record_id and record_id in existing_records:
                # Update existing
                obj = existing_records[record_id]
                for field, value in record.items():
                    if hasattr(obj, field):
                        setattr(obj, field, value)
                to_update.append(obj)
            else:
                # Create new
                to_create.append(self.model_class(**record))
        
        # Bulk operations with proper async handling
        try:
            if to_create:
                created_objects = await sync_to_async(
                    self.model_class.objects.bulk_create
                )(to_create, batch_size=self.batch_size, ignore_conflicts=True)
                results['created'] = len(created_objects)
            
            if to_update:
                update_fields = list(records[0].keys()) if records else []
                await sync_to_async(
                    self.model_class.objects.bulk_update
                )(to_update, fields=update_fields, batch_size=self.batch_size)
                results['updated'] = len(to_update)
        except Exception as e:
            logger.error(f"Bulk save failed, falling back to individual saves: {e}")
            return await self._save_individual_records(records)
        
        return results
        
    async def _save_individual_records(self, records: List[Dict]) -> Dict[str, int]:
        """Fallback to individual record saves"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in records:
            try:
                record_id = record.get('id')
                if record_id:
                    obj, created = await sync_to_async(
                        self.model_class.objects.get_or_create
                    )(id=record_id, defaults=record)
                    
                    if not created:
                        # Update existing record
                        for field, value in record.items():
                            if hasattr(obj, field):
                                setattr(obj, field, value)
                        await sync_to_async(obj.save)()
                        results['updated'] += 1
                    else:
                        results['created'] += 1
                else:
                    # Create without ID
                    await sync_to_async(self.model_class.objects.create)(**record)
                    results['created'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving record: {e}")
                results['failed'] += 1
                
        return results
        
    async def cleanup(self) -> None:
        """Cleanup resources after sync with enterprise features"""
        # Cleanup enterprise features
        if hasattr(self, 'automation_engine') and self.automation_engine:
            try:
                await self.automation_engine.cleanup()
            except Exception as e:
                logger.warning(f"Error cleaning up automation engine: {e}")
        
        # Close connection pool if available
        if hasattr(self, 'connection_pool') and self.connection_pool:
            try:
                # Connection pools are managed by the connection manager
                # Just log the cleanup
                logger.debug(f"Connection pool cleanup handled by connection manager")
            except Exception as e:
                logger.warning(f"Error with connection pool cleanup: {e}")
        
        # Note: boto3 Athena client doesn't need explicit connection closing
        # Just log completion
        logger.info(f"Cleanup completed for {self.table_name} sync with enterprise features")
