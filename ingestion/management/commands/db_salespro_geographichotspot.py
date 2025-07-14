"""
SalesPro Geographic Hotspot sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_GeographicHotspot

logger = logging.getLogger(__name__)

class SalesProGeographicHotspotSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Geographic Hotspots from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='geographic_hotspot',  # Use simple table name from your working example
            model_class=SalesPro_GeographicHotspot,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to GeographicHotspot model format"""
        try:
            # Debug: log the raw record structure first
            logger.info(f"Raw record from Athena: {record}")
            logger.info(f"Record keys: {list(record.keys()) if record else 'None'}")
            
            # If record is a dict with proper keys, use them
            if isinstance(record, dict) and ('company_id' in record or 'state' in record):
                company_id = record.get('company_id')
            else:
                # If record is a tuple/list (raw from Athena), map by position
                # Based on the model structure: company_id, company_name, state, city, total_estimates, sales, 
                # close_rate, avg_sale_value, active_sales_reps
                if isinstance(record, (tuple, list)) and len(record) >= 9:
                    logger.info(f"Processing tuple record with {len(record)} fields")
                    company_id = record[0]
                    transformed = {
                        'company_id': record[0] or '',
                        'company_name': record[1] or '',
                        'state': record[2] or '',
                        'city': record[3] or '',
                        'total_estimates': int(record[4]) if record[4] is not None else None,
                        'sales': int(record[5]) if record[5] is not None else None,
                        'close_rate': self._parse_decimal(record[6]) if len(record) > 6 else None,
                        'avg_sale_value': self._parse_decimal(record[7]) if len(record) > 7 else None,
                        'active_sales_reps': int(record[8]) if len(record) > 8 and record[8] is not None else None,
                    }
                    
                    logger.info(f"Transformed from tuple: {transformed}")
                    return transformed
                else:
                    logger.warning(f"Unexpected record format: {type(record)}, length: {len(record) if hasattr(record, '__len__') else 'N/A'}")
                    return None
                    
            # Map Athena columns directly to Django model fields
            transformed = {
                'company_id': record.get('company_id') or '',
                'company_name': record.get('company_name') or '',
                'state': record.get('state') or '',
                'city': record.get('city') or '',
                'total_estimates': int(record.get('total_estimates')) if record.get('total_estimates') is not None else None,
                'sales': int(record.get('sales')) if record.get('sales') is not None else None,
                'close_rate': self._parse_decimal(record.get('close_rate')),
                'avg_sale_value': self._parse_decimal(record.get('avg_sale_value')),
                'active_sales_reps': int(record.get('active_sales_reps')) if record.get('active_sales_reps') is not None else None,
            }
            
            logger.info(f"Transformed geographic hotspot record: {transformed['city']}, {transformed['state']}, company={transformed['company_name']}")
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming geographic hotspot record: {e}")
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
        """Parse decimal value"""
        if value is None:
            return None
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync geographic hotspots from SalesPro AWS Athena database"""
    
    help = "Sync geographic hotspots from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        """Get the geographic hotspot sync engine"""
        return SalesProGeographicHotspotSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        """Get the sync operation name"""
        return "geographichotspot"
