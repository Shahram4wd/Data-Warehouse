"""
SalesPro Lead Result sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_LeadResult

logger = logging.getLogger(__name__)

class SalesProLeadResultSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Lead Results from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='lead_results',  # Try plural form like other tables
            model_class=SalesPro_LeadResult,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to LeadResult model format"""
        try:
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and ('estimate_id' in record or 'company_id' in record):
                estimate_id = record.get('estimate_id')
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on the model structure: estimate_id, company_id, lead_results, created_at, updated_at
                if isinstance(record, (tuple, list)) and len(record) >= 5:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    estimate_id = record[0]
                    transformed = {
                        'estimate_id': record[0] or '',
                        'company_id': record[1] or '',
                        'lead_results': record[2] or '',
                        'created_at': self._parse_datetime(record[3]) if len(record) > 3 else None,
                        'updated_at': self._parse_datetime(record[4]) if len(record) > 4 else None,
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            # Map Athena columns directly to Django model fields
            transformed = {
                'estimate_id': record.get('estimate_id') or '',
                'company_id': record.get('company_id') or '',
                'lead_results': record.get('lead_results') or '',
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            logger.info(f"Transformed lead result record: estimate_id={estimate_id}, company_id={transformed['company_id']}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming lead result record: {e}")
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
    """Sync lead results from SalesPro AWS Athena database"""
    
    help = "Sync lead results from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the lead result sync engine"""
        return SalesProLeadResultSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "leadresult"
