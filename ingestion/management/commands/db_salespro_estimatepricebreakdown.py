"""
SalesPro Estimate Price Breakdown sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_EstimatePriceBreakdown

logger = logging.getLogger(__name__)

class SalesProEstimatePriceBreakdownSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Estimate Price Breakdowns from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='estimate_price_breakdown',  # Simple table name
            model_class=SalesPro_EstimatePriceBreakdown,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to EstimatePriceBreakdown model format"""
        try:
            transformed = {
                'id': record.get('id'),
                'breakdown_id': record.get('breakdown_id'),
                'estimate_id': record.get('estimate_id'),
                'item_name': record.get('item_name'),
                'item_description': record.get('item_description'),
                'category': record.get('category'),
                'quantity': self._parse_decimal(record.get('quantity')),
                'unit_price': self._parse_decimal(record.get('unit_price')),
                'total_price': self._parse_decimal(record.get('total_price')),
                'markup_percentage': self._parse_decimal(record.get('markup_percentage')),
                'cost_price': self._parse_decimal(record.get('cost_price')),
                'notes': record.get('notes'),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            return {k: v for k, v in transformed.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Error transforming estimate price breakdown record: {e}")
            return None
            
    def _parse_datetime(self, value) -> Optional[datetime]:
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
    """Sync estimate price breakdowns from SalesPro AWS Athena database"""
    
    help = "Sync estimate price breakdowns from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProEstimatePriceBreakdownSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "estimatepricebreakdown"
