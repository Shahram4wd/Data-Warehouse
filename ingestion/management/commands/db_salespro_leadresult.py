"""
SalesPro Lead Result sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_LeadResult

logger = logging.getLogger(__name__)

class SalesProLeadResultSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Lead Results from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='lead_result',  # Simple table name
            model_class=SalesPro_LeadResult,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to LeadResult model format"""
        try:
            transformed = {
                'id': record.get('id'),
                'lead_id': record.get('lead_id'),
                'customer_id': record.get('customer_id'),
                'result_type': record.get('result_type'),
                'result_status': record.get('result_status'),
                'result_date': self._parse_datetime(record.get('result_date')),
                'follow_up_date': self._parse_datetime(record.get('follow_up_date')),
                'notes': record.get('notes'),
                'assigned_to': record.get('assigned_to'),
                'created_by': record.get('created_by'),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            return {k: v for k, v in transformed.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Error transforming lead result record: {e}")
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
    """Sync lead results from SalesPro AWS Athena database"""
    
    help = "Sync lead results from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProLeadResultSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "leadresult"
