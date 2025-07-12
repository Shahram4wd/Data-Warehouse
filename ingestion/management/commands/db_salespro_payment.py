"""
SalesPro Payment sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_Payment

logger = logging.getLogger(__name__)

class SalesProPaymentSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Payments from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='payment',  # Use simple table name from your working example
            model_class=SalesPro_Payment,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to Payment model format"""
        try:
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and 'payment_id' in record:
                payment_id = record.get('payment_id')
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on payment table structure, adjust the field mapping as needed
                if isinstance(record, (tuple, list)) and len(record) >= 1:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    payment_id = record[0]
                    transformed = {
                        'payment_id': record[0],
                        'company_id': record[1] if len(record) > 1 else '',
                        'company_name': record[2] if len(record) > 2 else '',
                        'customer_id': record[3] if len(record) > 3 else '',
                        'payment_amount': self._parse_decimal(record[4]) if len(record) > 4 else None,
                        'payment_type': record[5] if len(record) > 5 else '',
                        'payment_description': record[6] if len(record) > 6 else '',
                        'payment_success': bool(record[7]) if len(record) > 7 else False,
                        'created_at': record[8] if len(record) > 8 else None,
                        'updated_at': record[9] if len(record) > 9 else None,
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            if not payment_id:
                logger.warning(f"Skipping record without payment_id: {record}")
                return None
            
            # Map Athena columns directly to Django model fields
            transformed = {
                'payment_id': payment_id,
                'company_id': record.get('company_id') or '',
                'company_name': record.get('company_name') or '',
                'customer_id': record.get('customer_id') or '',
                'payment_amount': self._parse_decimal(record.get('payment_amount')),
                'payment_type': record.get('payment_type') or '',
                'payment_description': record.get('payment_description') or '',
                'payment_success': bool(record.get('payment_success', False)),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            logger.info(f"Transformed payment record: ID={payment_id}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming payment record: {e}")
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
        if not value:
            return None
        try:
            if isinstance(value, datetime):
                return value
            for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%d', '%Y-%m-%dT%H:%M:%S']:
                try:
                    return datetime.strptime(str(value), fmt)
                except ValueError:
                    continue
            return None
        except Exception:
            return None
            
    def _parse_decimal(self, value):
        if value is None:
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync payments from SalesPro AWS Athena database"""
    
    help = "Sync payments from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProPaymentSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "payment"
