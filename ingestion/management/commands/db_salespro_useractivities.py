"""
SalesPro User Activity sync from AWS Athena
Following import_refactoring.md guidelines and CRM sync guide compliance
"""
import logging
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.engines.base import SalesProBaseSyncEngine
from ingestion.sync.salespro.processors.base import SalesProBaseProcessor
from ingestion.models.salespro import SalesPro_UserActivity

logger = logging.getLogger(__name__)

class SalesProUserActivitySyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro User Activities from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='user_activity',
            model_class=SalesPro_UserActivity,
            **kwargs
        )
        # Initialize the framework-compliant processor
        self.processor = SalesProBaseProcessor(
            model_class=SalesPro_UserActivity,
            crm_source='salespro'
        )
        
    async def run_sync(self, **kwargs) -> Dict[str, Any]:
        """Run sync with enterprise strategy determination"""
        # Check if manual since_date was provided (from --since parameter)
        manual_since_date = kwargs.get('since_date')
        
        # Determine sync strategy using enterprise patterns
        strategy = await self.determine_sync_strategy(
            force_full=kwargs.get('full_sync', False)
        )
        
        # Add strategy information to kwargs - but don't override manual since_date
        if strategy['type'] == 'incremental' and strategy['last_sync'] and not manual_since_date:
            # Only use automatic incremental sync if no manual since_date was provided
            kwargs['since_date'] = strategy['last_sync']
        
        # Run the base sync with strategy
        return await super().run_sync(**kwargs)
        
    async def _bulk_save_records(self, records: List[Dict]) -> Dict[str, int]:
        """Custom bulk save for user activity log - uses created_at, user_id, activity_note as unique key"""
        from django.db import transaction
        from django.utils import timezone
        
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not records:
            return results
        
        # For user activity log, we only create new records (no updates)
        # Build a set of existing records for fast lookup using the unique constraint fields
        unique_filters = []
        for record in records:
            created_at = record.get('created_at')
            user_id = record.get('user_id')
            activity_note = record.get('activity_note')
            
            # Only check if all required fields are present
            if created_at and user_id and activity_note:
                unique_filters.append({
                    'created_at': created_at,
                    'user_id': user_id, 
                    'activity_note': activity_note
                })
        
        # Get existing records based on unique combination
        existing_records = set()
        if unique_filters:
            from django.db.models import Q
            query = Q()
            for filter_dict in unique_filters:
                query |= Q(**filter_dict)
            
            existing_objs = await sync_to_async(list)(
                self.model_class.objects.filter(query).values('created_at', 'user_id', 'activity_note')
            )
            
            # Create a set of tuples for fast lookup
            for obj in existing_objs:
                key = (obj['created_at'], obj['user_id'], obj['activity_note'])
                existing_records.add(key)
        
        # Filter out records that already exist
        to_create = []
        for record in records:
            # Create lookup key
            lookup_key = (
                record.get('created_at'),
                record.get('user_id'), 
                record.get('activity_note')
            )
            
            # Skip records without required unique fields
            if None in lookup_key:
                logger.warning(f"Skipping record with missing unique fields: {record}")
                continue
            
            if lookup_key not in existing_records:
                # Only create if this exact log entry doesn't exist
                to_create.append(self.model_class(**record))
            else:
                logger.debug(f"Skipping duplicate user activity: {lookup_key}")
        
        # Bulk create new records only (no updates for log data)
        try:
            if to_create:
                created_objects = await sync_to_async(
                    self.model_class.objects.bulk_create
                )(to_create, batch_size=self.batch_size, ignore_conflicts=True)
                results['created'] = len(created_objects)
                logger.info(f"Created {len(created_objects)} new user activity records")
            else:
                logger.info("No new user activity records to create")
        except Exception as e:
            logger.error(f"Bulk create failed for user activity: {e}")
            # Fall back to individual saves
            return await self._save_individual_records(records)
        
        return results
        
    async def _save_individual_records(self, records: List[Dict]) -> Dict[str, int]:
        """Fallback to individual record saves for user activity (no ID-based operations)"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in records:
            try:
                # For user activity, use the unique constraint fields to check for existence
                created_at = record.get('created_at')
                user_id = record.get('user_id')
                activity_note = record.get('activity_note')
                
                if not all([created_at, user_id, activity_note]):
                    logger.warning(f"Skipping record with missing unique fields: {record}")
                    results['failed'] += 1
                    continue
                
                # Try to get existing record using unique constraint fields
                existing = await sync_to_async(
                    self.model_class.objects.filter
                )(
                    created_at=created_at,
                    user_id=user_id,
                    activity_note=activity_note
                ).afirst()
                
                if existing is None:
                    # Create new record since it doesn't exist
                    await sync_to_async(self.model_class.objects.create)(**record)
                    results['created'] += 1
                    logger.debug(f"Created user activity record: {created_at}, {user_id}")
                else:
                    # Record already exists, skip (log entries shouldn't be updated)
                    logger.debug(f"Skipping existing user activity: {created_at}, {user_id}, {activity_note}")
                    
            except Exception as e:
                logger.error(f"Error saving user activity record: {e}")
                results['failed'] += 1
                
        return results
    
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to UserActivity model format using framework processor"""
        try:
            # Handle both dict and tuple record formats from Athena
            if isinstance(record, dict):
                # Use the framework processor for validation and transformation
                try:
                    # First validate the record using the framework
                    validated_record = self.processor.validate_record(record)
                    # Then transform using the framework patterns
                    transformed = self.processor.transform_record(validated_record)
                    
                    # Ensure required fields are present for activity records
                    if not transformed.get('created_at'):
                        transformed['created_at'] = self._parse_datetime(record.get('created_at'))
                    
                    # Activity-specific fields that might not be in base mappings
                    transformed.update({
                        'user_id': record.get('user_id') or '',
                        'company_id': record.get('company_id') or '',
                        'company_name': record.get('company_name') or '',
                        'local_customer_uuid': record.get('local_customer_uuid') or '',
                        'customer_id': record.get('customer_id') or '',
                        'activity_note': record.get('activity_note') or '',
                        'key_metric': record.get('key_metric') or '',
                        'activity_identifier': record.get('activity_identifier') or '',
                        'price_type': record.get('price_type') or '',
                        'price': self._parse_decimal(record.get('price')),
                        'original_row_num': int(record.get('original_row_num')) if record.get('original_row_num') is not None else None,
                    })
                    
                    # Validate that we have the minimum required fields for uniqueness
                    if not all([transformed.get('created_at'), transformed.get('user_id'), transformed.get('activity_note')]):
                        logger.warning(f"Skipping record missing required unique fields: {record}")
                        return None
                    
                    return transformed
                    
                except Exception as framework_error:
                    # Fall back to basic transformation if framework validation fails
                    logger.warning(f"Framework validation failed, using basic validation: {framework_error}")
                    
                    # Basic transformation without framework validation
                    transformed = {
                        'created_at': self._parse_datetime(record.get('created_at')),
                        'user_id': record.get('user_id') or '',
                        'company_id': record.get('company_id') or '',
                        'company_name': record.get('company_name') or '',
                        'local_customer_uuid': record.get('local_customer_uuid') or '',
                        'customer_id': record.get('customer_id') or '',
                        'activity_note': record.get('activity_note') or '',
                        'key_metric': record.get('key_metric') or '',
                        'activity_identifier': record.get('activity_identifier') or '',
                        'price_type': record.get('price_type') or '',
                        'price': self._parse_decimal(record.get('price')),
                        'original_row_num': int(record.get('original_row_num')) if record.get('original_row_num') is not None else None,
                    }
                    
                    # Validate minimum required fields
                    if not all([transformed.get('created_at'), transformed.get('user_id'), transformed.get('activity_note')]):
                        logger.warning(f"Skipping record missing required unique fields: {record}")
                        return None
                    
                    return transformed
            else:
                logger.warning(f"Unexpected record format: {type(record)}")
                return None
            
        except Exception as e:
            logger.error(f"Error transforming user activity record: {e}")
            return None
            
    def _parse_datetime(self, value) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not value:
            return None
            
        try:
            # If it's already a datetime object (from Athena), just make it timezone-aware
            if isinstance(value, datetime):
                if value.tzinfo is None:
                    return timezone.make_aware(value)
                return value
            
            # Handle string values
            if isinstance(value, str):
                value_str = value.strip()
                
                # Try different formats based on your Athena data
                formats = [
                    '%Y-%m-%d %H:%M:%S.%f',  # "2020-02-07 14:15:20.384"
                    '%Y-%m-%d %H:%M:%S',     # "2020-02-07 14:15:20"
                    '%Y-%m-%d',              # "2020-02-07"
                    '%Y-%m-%dT%H:%M:%S',     # ISO format
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.strptime(value_str, fmt)
                        return timezone.make_aware(dt)
                    except ValueError:
                        continue
                        
            logger.warning(f"Could not parse datetime '{value}' with any known format")
            return None
            
        except Exception as e:
            logger.warning(f"Error parsing datetime '{value}': {e}")
            return None
            
    def _parse_decimal(self, value):
        """Parse decimal value"""
        if value is None or value == '':
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync user activities from SalesPro AWS Athena database"""
    
    help = "Sync user activities from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProUserActivitySyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "useractivity"
