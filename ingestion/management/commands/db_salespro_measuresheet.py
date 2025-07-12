"""
SalesPro Measure Sheet sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_MeasureSheet

logger = logging.getLogger(__name__)

class SalesProMeasureSheetSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Measure Sheets from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='measure_sheet',  # Simple table name
            model_class=SalesPro_MeasureSheet,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to MeasureSheet model format"""
        try:
            transformed = {
                'id': record.get('id'),
                'measure_sheet_id': record.get('measure_sheet_id'),
                'customer_id': record.get('customer_id'),
                'estimate_id': record.get('estimate_id'),
                'sheet_number': record.get('sheet_number'),
                'measurement_date': self._parse_datetime(record.get('measurement_date')),
                'measured_by': record.get('measured_by'),
                'measurements': record.get('measurements'),
                'notes': record.get('notes'),
                'status': record.get('status'),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            return {k: v for k, v in transformed.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Error transforming measure sheet record: {e}")
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
