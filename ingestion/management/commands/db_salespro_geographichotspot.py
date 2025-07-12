"""
SalesPro Geographic Hotspot sync from AWS Athena
Following import_refactoring.md guidelines
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.base import BaseSalesProSyncEngine
from ingestion.models.salespro import SalesPro_GeographicHotspot

logger = logging.getLogger(__name__)

class SalesProGeographicHotspotSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Geographic Hotspots from AWS Athena"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='geographic_hotspot',  # Simple table name
            model_class=SalesPro_GeographicHotspot,
            **kwargs
        )
        
    async def _transform_record(self, record: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Transform Athena record to GeographicHotspot model format"""
        try:
            transformed = {
                'id': record.get('id'),
                'hotspot_id': record.get('hotspot_id'),
                'name': record.get('name'),
                'description': record.get('description'),
                'region': record.get('region'),
                'state': record.get('state'),
                'city': record.get('city'),
                'zip_codes': record.get('zip_codes'),
                'latitude': self._parse_decimal(record.get('latitude')),
                'longitude': self._parse_decimal(record.get('longitude')),
                'radius_miles': self._parse_decimal(record.get('radius_miles')),
                'priority_level': self._parse_int(record.get('priority_level')),
                'is_active': self._parse_boolean(record.get('is_active')),
                'notes': record.get('notes'),
                'created_at': self._parse_datetime(record.get('created_at')),
                'updated_at': self._parse_datetime(record.get('updated_at')),
            }
            
            return {k: v for k, v in transformed.items() if v is not None}
            
        except Exception as e:
            logger.error(f"Error transforming geographic hotspot record: {e}")
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
            
    def _parse_int(self, value) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
            
    def _parse_boolean(self, value) -> Optional[bool]:
        if value is None:
            return None
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ('true', '1', 'yes', 'on')
        try:
            return bool(int(value))
        except (ValueError, TypeError):
            return None

class Command(BaseSalesProSyncCommand):
    """Sync geographic hotspots from SalesPro AWS Athena database"""
    
    help = "Sync geographic hotspots from SalesPro AWS Athena database"
    
    def get_sync_engine(self, **options):
        return SalesProGeographicHotspotSyncEngine(
            batch_size=options.get('batch_size', 500),
            dry_run=options.get('dry_run', False)
        )
    
    def get_sync_name(self) -> str:
        return "geographichotspot"
