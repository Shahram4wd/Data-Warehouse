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
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_Customer

logger = logging.getLogger(__name__)

class SalesProCustomerSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Customers from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='customer',  # Use simple table name from your working example
            model_class=SalesPro_Customer,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to Customer model format"""
        try:
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and 'customer_id' in record:
                customer_id = record.get('customer_id')
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
                        'created_at': record[8] if len(record) > 8 else None,  # datetime.datetime(2020, 2, 7, 14, 15, 20, 384000)
                        'updated_at': record[9] if len(record) > 9 else None,  # datetime.datetime(2025, 6, 23, 20, 41, 8, 583000)
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            if not customer_id:
                logger.warning(f"Skipping record without customer_id: {record}")
                return None
            
            # Map Athena columns directly to Django model fields
            transformed = {
                'customer_id': customer_id,
                'estimate_id': record.get('estimate_id') or '',
                'company_id': record.get('company_id') or '',
                'company_name': record.get('company_name') or '',
                'customer_first_name': record.get('customer_first_name') or '',
                'customer_last_name': record.get('customer_last_name') or '',
                'crm_source': record.get('crm_source') or '',
                'crm_source_id': record.get('crm_source_id') or '',
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            logger.info(f"Transformed customer record: ID={customer_id}, name={transformed['customer_first_name']} {transformed['customer_last_name']}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming customer record: {e}")
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
