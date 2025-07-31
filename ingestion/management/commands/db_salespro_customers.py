"""
SalesPro Customer sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.engines.base import SalesProBaseSyncEngine
from ingestion.models.salespro import SalesPro_Customer

logger = logging.getLogger(__name__)

class SalesProCustomerSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro Customers from AWS Athena with enterprise features"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='customer',  # Use simple table name from your working example
            model_class=SalesPro_Customer,
            **kwargs
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
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to Customer model format using framework patterns"""
        try:
            # Initialize processor for validation and transformation
            if not hasattr(self, '_processor'):
                from ingestion.sync.salespro.processors.base import SalesProBaseProcessor
                self._processor = SalesProBaseProcessor(self.model_class, crm_source='salespro')
            
            # Debug: log the raw record structure first
            logger.debug(f"Raw record from Athena: {record}")
            logger.debug(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # Handle both dict and tuple formats from Athena
            transformed = {}
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and 'customer_id' in record:
                customer_id = record.get('customer_id')
                
                # Apply field mappings with validation
                field_mappings = {
                    'customer_id': 'customer_id',
                    'estimate_id': 'estimate_id',
                    'company_id': 'company_id',
                    'company_name': 'company_name',
                    'customer_first_name': 'customer_first_name',
                    'customer_last_name': 'customer_last_name',
                    'crm_source': 'crm_source',
                    'crm_source_id': 'crm_source_id',
                    'created_at': 'created_at',
                    'updated_at': 'updated_at',
                }
                
                context = {'id': customer_id}
                for source_field, target_field in field_mappings.items():
                    value = record.get(source_field)
                    if value is not None:
                        if target_field in ['created_at', 'updated_at']:
                            transformed[target_field] = self._processor._parse_datetime(value)
                        else:
                            transformed[target_field] = str(value) if value else ''
                
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on your query result structure:
                # (customer_id, estimate_id, company_id, company_name, customer_first_name, customer_last_name, crm_source, crm_source_id, created_at, updated_at)
                if isinstance(record, (tuple, list)) and len(record) >= 10:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    customer_id = record[0]
                    
                    transformed = {
                        'customer_id': record[0],  # 'TFduILj66d'
                        'estimate_id': record[1] or '',  # '3GgGCcY96x' 
                        'company_id': record[2] or '',   # '5uMv0xne1g'
                        'company_name': record[3] or '', # 'Home Genius Exteriors Corporate'
                        'customer_first_name': record[4] or '', # 'Stanley and Rebecca (new with porch)'
                        'customer_last_name': record[5] or '',  # 'Klick'
                        'crm_source': record[6] or '',   # ''
                        'crm_source_id': record[7] or '', # ''
                        'created_at': self._processor._parse_datetime(record[8]) if len(record) > 8 else None,
                        'updated_at': self._processor._parse_datetime(record[9]) if len(record) > 9 else None,
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            if not customer_id:
                logger.warning(f"Skipping record without customer_id: {record}")
                return None
            
            # Validate record completeness using framework patterns
            if hasattr(self, '_processor'):
                warnings = self._processor.validate_record_completeness(transformed)
                if warnings:
                    logger.debug(f"Customer {customer_id} completeness notes: {'; '.join(warnings)}")
            
            logger.debug(f"Transformed customer record: ID={customer_id}, name={transformed.get('customer_first_name', '')} {transformed.get('customer_last_name', '')}")
            return transformed
            
        except Exception as e:
            customer_id = record.get('customer_id', 'unknown') if isinstance(record, dict) else record[0] if isinstance(record, (list, tuple)) and len(record) > 0 else 'unknown'
            logger.error(f"Error transforming customer record {customer_id}: {e}")
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
        if value is None:
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync customers from SalesPro AWS Athena database"""
    
    help = "Sync customers from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the customer sync engine"""
        return SalesProCustomerSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "customer"
