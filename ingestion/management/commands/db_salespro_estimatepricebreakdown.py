"""
SalesPro Estimate Price Breakdown sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_EstimatePriceBreakdown

logger = logging.getLogger(__name__)

class SalesProEstimatePriceBreakdownSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Estimate Price Breakdowns from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='estimate_price_breakdown',  # Use simple table name from your working example
            model_class=SalesPro_EstimatePriceBreakdown,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to EstimatePriceBreakdown model format"""
        try:
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and ('estimate_id' in record or 'estimate_date' in record):
                estimate_id = record.get('estimate_id')
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on the model structure: estimate_date, company_name, estimate_id, trade_type, price_guide_amount
                if isinstance(record, (tuple, list)) and len(record) >= 5:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    estimate_id = record[2]
                    transformed = {
                        'estimate_date': self._parse_datetime(record[0]) if len(record) > 0 else None,
                        'company_name': record[1] or '' if len(record) > 1 else '',
                        'estimate_id': record[2] or '' if len(record) > 2 else '',
                        'trade_type': record[3] or '' if len(record) > 3 else '',
                        'price_guide_amount': record[4] or '' if len(record) > 4 else '',
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            # Map Athena columns directly to Django model fields
            transformed = {
                'estimate_date': self._parse_datetime(record.get('estimate_date')),
                'company_name': record.get('company_name') or '',
                'estimate_id': record.get('estimate_id') or '',
                'trade_type': record.get('trade_type') or '',
                'price_guide_amount': record.get('price_guide_amount') or '',
            }
            
            logger.info(f"Transformed estimate price breakdown record: estimate_id={estimate_id}, trade_type={transformed['trade_type']}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming estimate price breakdown record: {e}")
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
        """Parse decimal value"""
        if value is None:
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync estimate price breakdowns from SalesPro AWS Athena database"""
    
    help = "Sync estimate price breakdowns from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the estimate price breakdown sync engine"""
        return SalesProEstimatePriceBreakdownSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "estimatepricebreakdown"
