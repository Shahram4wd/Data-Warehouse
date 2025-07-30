"""
SalesPro Credit Application sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_CreditApplication

logger = logging.getLogger(__name__)

class SalesProCreditApplicationSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Credit Applications from AWS Athena with enterprise features"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='credit_applications',  # Use plural form like other tables
            model_class=SalesPro_CreditApplication,
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
        """Transform Athena record to CreditApplication model format using framework patterns"""
        try:
            # Initialize processor for validation and transformation
            if not hasattr(self, '_processor'):
                from ingestion.sync.salespro.processors.base import SalesProBaseProcessor
                self._processor = SalesProBaseProcessor(self.model_class, crm_source='salespro')
            
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # Handle both dict and tuple formats from Athena
            transformed = {}
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and 'leap_credit_app_id' in record:
                leap_credit_app_id = record.get('leap_credit_app_id')
                
                # Apply field mappings with validation
                field_mappings = {
                    'leap_credit_app_id': 'leap_credit_app_id',
                    'company_id': 'company_id',
                    'company_name': 'company_name',
                    'sales_rep_id': 'sales_rep_id',
                    'customer_id': 'customer_id',
                    'credit_app_vendor': 'credit_app_vendor',
                    'credit_app_vendor_id': 'credit_app_vendor_id',
                    'credit_app_amount': 'credit_app_amount',
                    'credit_app_status': 'credit_app_status',
                    'credit_app_note': 'credit_app_note',
                    'created_at': 'created_at',
                    'updated_at': 'updated_at',
                }
                
                context = {'id': leap_credit_app_id}
                for source_field, target_field in field_mappings.items():
                    value = record.get(source_field)
                    if value is not None:
                        if target_field in ['created_at', 'updated_at']:
                            transformed[target_field] = self._processor._parse_datetime(value)
                        elif target_field == 'credit_app_amount':
                            transformed[target_field] = self._processor._parse_decimal(value)
                        else:
                            transformed[target_field] = str(value) if value else ''
                
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on the model structure: leap_credit_app_id, company_id, company_name, sales_rep_id, customer_id,
                # credit_app_vendor, credit_app_vendor_id, credit_app_amount, credit_app_status, credit_app_note, created_at, updated_at
                if isinstance(record, (tuple, list)) and len(record) >= 12:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    leap_credit_app_id = record[0]
                    
                    transformed = {
                        'leap_credit_app_id': record[0],
                        'company_id': record[1] or '',
                        'company_name': record[2] or '',
                        'sales_rep_id': record[3] or '',
                        'customer_id': record[4] or '',
                        'credit_app_vendor': record[5] or '',
                        'credit_app_vendor_id': record[6] or '',
                        'credit_app_amount': self._processor._parse_decimal(record[7]) if len(record) > 7 else None,
                        'credit_app_status': record[8] or '' if len(record) > 8 else '',
                        'credit_app_note': record[9] or '' if len(record) > 9 else '',
                        'created_at': self._processor._parse_datetime(record[10]) if len(record) > 10 else None,
                        'updated_at': self._processor._parse_datetime(record[11]) if len(record) > 11 else None,
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            if not leap_credit_app_id:
                logger.warning(f"Skipping record without leap_credit_app_id: {record}")
                return None
            
            # Validate record completeness using framework patterns
            if hasattr(self, '_processor'):
                warnings = self._processor.validate_record_completeness(transformed)
                if warnings:
                    logger.info(f"Credit application {leap_credit_app_id} completeness notes: {'; '.join(warnings)}")
            
            logger.info(f"Transformed credit application record: ID={leap_credit_app_id}, customer={transformed.get('customer_id', '')}, vendor={transformed.get('credit_app_vendor', '')}")
            return transformed
            
        except Exception as e:
            leap_credit_app_id = record.get('leap_credit_app_id', 'unknown') if isinstance(record, dict) else record[0] if isinstance(record, (list, tuple)) and len(record) > 0 else 'unknown'
            logger.error(f"Error transforming credit application record {leap_credit_app_id}: {e}")
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
    """Sync credit applications from SalesPro AWS Athena database"""
    
    help = "Sync credit applications from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the credit application sync engine"""
        return SalesProCreditApplicationSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "creditapplication"
