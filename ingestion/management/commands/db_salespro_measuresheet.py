"""
SalesPro Measure Sheet sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_MeasureSheet

logger = logging.getLogger(__name__)

class SalesProMeasureSheetSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Measure Sheets from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='measure_sheet',
            model_class=SalesPro_MeasureSheet,
            **kwargs
        )
        
    async def _bulk_save_records(self, records: List[Dict]) -> Dict[str, int]:
        """Custom bulk save for measure sheet - uses created_at, updated_at, estimate_id, measure_sheet_item_name as unique key"""
        from django.db import transaction
        from django.utils import timezone
        
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not records:
            return results
        
        # For measure sheet, we only create new records (no updates for historical data)
        # Build a set of existing records for fast lookup using the unique constraint fields
        unique_filters = []
        for record in records:
            created_at = record.get('created_at')
            updated_at = record.get('updated_at')
            estimate_id = record.get('estimate_id')
            measure_sheet_item_name = record.get('measure_sheet_item_name')
            
            # Only check if all required fields are present
            if created_at and updated_at and estimate_id and measure_sheet_item_name:
                unique_filters.append({
                    'created_at': created_at,
                    'updated_at': updated_at,
                    'estimate_id': estimate_id,
                    'measure_sheet_item_name': measure_sheet_item_name
                })
        
        # Get existing records based on unique combination
        existing_records = set()
        if unique_filters:
            from django.db.models import Q
            query = Q()
            for filter_dict in unique_filters:
                query |= Q(**filter_dict)
            
            existing_objs = await sync_to_async(list)(
                self.model_class.objects.filter(query).values(
                    'created_at', 'updated_at', 'estimate_id', 'measure_sheet_item_name'
                )
            )
            
            # Create a set of tuples for fast lookup
            for obj in existing_objs:
                key = (obj['created_at'], obj['updated_at'], obj['estimate_id'], obj['measure_sheet_item_name'])
                existing_records.add(key)
        
        # Filter out records that already exist
        to_create = []
        for record in records:
            # Create lookup key
            lookup_key = (
                record.get('created_at'),
                record.get('updated_at'),
                record.get('estimate_id'),
                record.get('measure_sheet_item_name')
            )
            
            # Skip records without required unique fields
            if None in lookup_key or '' in lookup_key:
                logger.warning(f"Skipping record with missing unique fields: {record}")
                continue
            
            if lookup_key not in existing_records:
                # Only create if this exact measure sheet item doesn't exist
                to_create.append(self.model_class(**record))
            else:
                logger.debug(f"Skipping duplicate measure sheet item: {lookup_key}")
        
        # Bulk create new records only (no updates for historical data)
        try:
            if to_create:
                created_objects = await sync_to_async(
                    self.model_class.objects.bulk_create
                )(to_create, batch_size=self.batch_size, ignore_conflicts=True)
                results['created'] = len(created_objects)
                logger.info(f"Created {len(created_objects)} new measure sheet records")
            else:
                logger.info("No new measure sheet records to create")
        except Exception as e:
            logger.error(f"Bulk create failed for measure sheet: {e}")
            # Fall back to individual saves
            return await self._save_individual_records(records)
        
        return results
        
    async def _save_individual_records(self, records: List[Dict]) -> Dict[str, int]:
        """Fallback to individual record saves for measure sheet (no ID-based operations)"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in records:
            try:
                # For measure sheet, use the unique constraint fields to check for existence
                created_at = record.get('created_at')
                updated_at = record.get('updated_at')
                estimate_id = record.get('estimate_id')
                measure_sheet_item_name = record.get('measure_sheet_item_name')
                
                if not all([created_at, updated_at, estimate_id, measure_sheet_item_name]):
                    logger.warning(f"Skipping record with missing unique fields: {record}")
                    results['failed'] += 1
                    continue
                
                # Try to get existing record using unique constraint fields
                existing = await sync_to_async(
                    self.model_class.objects.filter
                )(
                    created_at=created_at,
                    updated_at=updated_at,
                    estimate_id=estimate_id,
                    measure_sheet_item_name=measure_sheet_item_name
                ).afirst()
                
                if existing is None:
                    # Create new record since it doesn't exist
                    await sync_to_async(self.model_class.objects.create)(**record)
                    results['created'] += 1
                    logger.debug(f"Created measure sheet record: {estimate_id}, {measure_sheet_item_name}")
                else:
                    # Record already exists, skip (historical data shouldn't be updated)
                    logger.debug(f"Skipping existing measure sheet: {estimate_id}, {measure_sheet_item_name}")
                    
            except Exception as e:
                logger.error(f"Error saving measure sheet record: {e}")
                results['failed'] += 1
                
        return results
    
    def _build_query(self, **kwargs) -> str:
        """Build SQL query for Athena with proper limits for measure_sheet"""
        query = f"SELECT * FROM {self.table_name}"
        
        conditions = []
        
        # Add WHERE clause for incremental sync
        since_date = kwargs.get('since_date')
        if since_date:
            since_date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            conditions.append(f"created_at > timestamp '{since_date_str}'")
        
        # Add WHERE conditions if any
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
                
        # Add ORDER BY for consistent pagination
        query += " ORDER BY created_at"
                
        # Add LIMIT - always limit large tables to prevent timeouts
        max_records = kwargs.get('max_records', 0)
        if max_records > 0:
            query += f" LIMIT {max_records}"
        else:
            # For full sync of measure_sheet, use a reasonable default limit
            default_limit = 10000  # Start with 10k records for measure_sheet
            query += f" LIMIT {default_limit}"
            logger.warning(f"Large table '{self.table_name}' detected. Limiting to {default_limit} records per sync. Use --max-records for different limit.")
            
        return query
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to MeasureSheet model format"""
        try:
            # Handle both dict and tuple record formats from Athena
            if isinstance(record, dict):
                # Process dict records - map fields directly
                transformed = {
                    'estimate_id': record.get('estimate_id') or '',
                    'office_id': record.get('office_id') or '',
                    'office_name': record.get('office_name') or '',
                    'company_id': record.get('company_id') or '',
                    'company_name': record.get('company_name') or '',
                    'measure_sheet_item_id': record.get('measure_sheet_item_id') or '',
                    'quantity': self._parse_decimal(record.get('quantity')),
                    'category': record.get('category') or '',
                    'measurement_type': record.get('measurement_type') or '',
                    'measure_sheet_item_name': record.get('measure_sheet_item_name') or '',
                    'measure_sheet_item_price': self._parse_decimal(record.get('measure_sheet_item_price')),
                    'created_at': self._parse_datetime(record.get('created_at')),
                    'updated_at': self._parse_datetime(record.get('updated_at')),
                }
                
                # Validate that we have the minimum required fields for uniqueness
                required_fields = ['created_at', 'updated_at', 'estimate_id', 'measure_sheet_item_name']
                if not all([transformed.get(field) for field in required_fields]):
                    logger.warning(f"Skipping record missing required unique fields: {record}")
                    return None
                
                return transformed
                
            elif isinstance(record, (tuple, list)) and len(record) >= 1:
                # Handle tuple/list format from Athena - map by position based on the schema
                # Schema: estimate_id, office_id, office_name, company_id, company_name, 
                #         measure_sheet_item_id, quantity, category, measurement_type, 
                #         measure_sheet_item_name, measure_sheet_item_price, created_at, updated_at
                transformed = {
                    'estimate_id': record[0] if len(record) > 0 else '',
                    'office_id': record[1] if len(record) > 1 else '',
                    'office_name': record[2] if len(record) > 2 else '',
                    'company_id': record[3] if len(record) > 3 else '',
                    'company_name': record[4] if len(record) > 4 else '',
                    'measure_sheet_item_id': record[5] if len(record) > 5 else '',
                    'quantity': self._parse_decimal(record[6]) if len(record) > 6 else None,
                    'category': record[7] if len(record) > 7 else '',
                    'measurement_type': record[8] if len(record) > 8 else '',
                    'measure_sheet_item_name': record[9] if len(record) > 9 else '',
                    'measure_sheet_item_price': self._parse_decimal(record[10]) if len(record) > 10 else None,
                    'created_at': self._parse_datetime(record[11]) if len(record) > 11 else None,
                    'updated_at': self._parse_datetime(record[12]) if len(record) > 12 else None,
                }
                
                # Validate required fields
                required_fields = ['created_at', 'updated_at', 'estimate_id', 'measure_sheet_item_name']
                if not all([transformed.get(field) for field in required_fields]):
                    logger.warning(f"Skipping record missing required unique fields: {record}")
                    return None
                
                return transformed
            else:
                logger.warning(f"Unexpected record format: {type(record)}")
                return None
            
        except Exception as e:
            logger.error(f"Error transforming measure sheet record: {e}")
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
    """Sync measure sheets from SalesPro AWS Athena database"""
    
    help = "Sync measure sheets from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProMeasureSheetSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "measuresheet"
