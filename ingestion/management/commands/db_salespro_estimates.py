"""
SalesPro Estimate sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.engines.base import SalesProBaseSyncEngine
from ingestion.models.salespro import SalesPro_Estimate

logger = logging.getLogger(__name__)

class SalesProEstimateSyncEngine(SalesProBaseSyncEngine):
    """Sync engine for SalesPro Estimates from AWS Athena with enterprise features"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='estimate',  # Use simple table name from your working example
            model_class=SalesPro_Estimate,
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
        """Transform Athena record to Estimate model format"""
        try:
            # Debug: log the raw record structure first
            logger.debug(f"Raw record from Athena: {record}")
            logger.debug(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and 'estimate_id' in record:
                estimate_id = record.get('estimate_id')
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on the model structure: estimate_id, company_id, company_name, office_id, office_name, sales_rep_id,
                # sales_rep_first_name, sales_rep_last_name, customer_id, customer_first_name, customer_last_name,
                # street_address, city, state, zip_code, sale_amount, is_sale, job_type, finance_amount, bank_name,
                # loan_name, down_payment, has_credit_app, document_count, created_at, updated_at
                if isinstance(record, (tuple, list)) and len(record) >= 26:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    estimate_id = record[0]
                    transformed = {
                        'estimate_id': record[0],
                        'company_id': record[1] or '',
                        'company_name': record[2] or '',
                        'office_id': record[3] or '',
                        'office_name': record[4] or '',
                        'sales_rep_id': record[5] or '',
                        'sales_rep_first_name': record[6] or '',
                        'sales_rep_last_name': record[7] or '',
                        'customer_id': record[8] or '',
                        'customer_first_name': record[9] or '',
                        'customer_last_name': record[10] or '',
                        'street_address': record[11] or '',
                        'city': record[12] or '',
                        'state': record[13] or '',
                        'zip_code': record[14] or '',
                        'sale_amount': self._parse_decimal(record[15]) if len(record) > 15 else None,
                        'is_sale': bool(record[16]) if len(record) > 16 and record[16] is not None else False,
                        'job_type': record[17] or '' if len(record) > 17 else '',
                        'finance_amount': self._parse_decimal(record[18]) if len(record) > 18 else None,
                        'bank_name': record[19] or '' if len(record) > 19 else '',
                        'loan_name': record[20] or '' if len(record) > 20 else '',
                        'down_payment': self._parse_decimal(record[21]) if len(record) > 21 else None,
                        'has_credit_app': bool(record[22]) if len(record) > 22 and record[22] is not None else False,
                        'document_count': int(record[23]) if len(record) > 23 and record[23] is not None else None,
                        'sync_created_at': self._parse_datetime(record[24]) if len(record) > 24 else None,
                        'sync_updated_at': self._parse_datetime(record[25]) if len(record) > 25 else None,
                    }
                    
                    # Remove null timestamp fields to let Django model defaults apply
                    if transformed['sync_created_at'] is None:
                        transformed.pop('sync_created_at', None)
                    if transformed['sync_updated_at'] is None:
                        transformed.pop('sync_updated_at', None)
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            if not estimate_id:
                logger.warning(f"Skipping record without estimate_id: {record}")
                return None
            
            # Map Athena columns directly to Django model fields
            transformed = {
                'estimate_id': estimate_id,
                'company_id': record.get('company_id') or '',
                'company_name': record.get('company_name') or '',
                'office_id': record.get('office_id') or '',
                'office_name': record.get('office_name') or '',
                'sales_rep_id': record.get('sales_rep_id') or '',
                'sales_rep_first_name': record.get('sales_rep_first_name') or '',
                'sales_rep_last_name': record.get('sales_rep_last_name') or '',
                'customer_id': record.get('customer_id') or '',
                'customer_first_name': record.get('customer_first_name') or '',
                'customer_last_name': record.get('customer_last_name') or '',
                'street_address': record.get('street_address') or '',
                'city': record.get('city') or '',
                'state': record.get('state') or '',
                'zip_code': record.get('zip_code') or '',
                'sale_amount': self._parse_decimal(record.get('sale_amount')),
                'is_sale': bool(record.get('is_sale', False)),
                'job_type': record.get('job_type') or '',
                'finance_amount': self._parse_decimal(record.get('finance_amount')),
                'bank_name': record.get('bank_name') or '',
                'loan_name': record.get('loan_name') or '',
                'down_payment': self._parse_decimal(record.get('down_payment')),
                'has_credit_app': bool(record.get('has_credit_app', False)),
                'document_count': int(record.get('document_count')) if record.get('document_count') is not None else None,
                'sync_created_at': self._parse_datetime(record.get('created_at')),
                'sync_updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            # Remove null timestamp fields to let Django model defaults apply
            if transformed['sync_created_at'] is None:
                transformed.pop('sync_created_at', None)
            if transformed['sync_updated_at'] is None:
                transformed.pop('sync_updated_at', None)
            
            logger.debug(f"Transformed estimate record: ID={estimate_id}, customer={transformed['customer_first_name']} {transformed['customer_last_name']}, amount=${transformed['sale_amount']}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming estimate record: {e}")
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
    """Sync estimates from SalesPro AWS Athena database"""
    
    help = "Sync estimates from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the estimate sync engine"""
        return SalesProEstimateSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "estimate"
