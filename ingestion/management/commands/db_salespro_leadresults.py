"""
SalesPro Lead Result sync from AWS Athena with JSON normalization
Following import_refactoring.md guidelines and CRM sync framework standards
"""
import logging
import uuid
from typing import Dict, Any, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.management.commands.base_salespro_sync import BaseSalesProSyncCommand
from ingestion.sync.salespro.engines.base import BaseSalesProSyncEngine
from ingestion.sync.salespro.processors.lead_result import SalesProLeadResultProcessor
from ingestion.models.salespro import SalesPro_LeadResult

logger = logging.getLogger(__name__)

class SalesProLeadResultSyncEngine(BaseSalesProSyncEngine):
    """Sync engine for SalesPro Lead Results from AWS Athena with JSON normalization"""
    
    def __init__(self, **kwargs):
        super().__init__(
            table_name='lead_results',  # Try plural form like other tables
            model_class=SalesPro_LeadResult,
            **kwargs
        )
        # Initialize the lead result processor
        self.processor = SalesProLeadResultProcessor(
            dry_run=kwargs.get('dry_run', False)
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
        """Transform Athena record to LeadResult model format with JSON normalization"""
        try:
            # Convert tuple/list records to dict format for processor
            if isinstance(record, (tuple, list)) and len(record) >= 3:
                logger.info(f"Processing tuple record with {len(record)} fields")
                # Map tuple to expected field names
                record_dict = {
                    'estimate_id': record[0] or '',
                    'company_id': record[1] or '' if len(record) > 1 else '',
                    'lead_results': record[2] or '' if len(record) > 2 else '',
                    'created_at': record[3] if len(record) > 3 else None,
                    'updated_at': record[4] if len(record) > 4 else None,
                }
                record = record_dict
            
            # Use the processor to transform and normalize the record
            transformed = self.processor.transform_record(record)
            
            # Validate the transformed record
            validation_warnings = self.processor.validate_record_completeness(transformed)
            if validation_warnings:
                for warning in validation_warnings:
                    logger.warning(f"Lead result validation: {warning}")
            
            # Parse datetime fields
            if transformed.get('created_at'):
                transformed['created_at'] = self._parse_datetime(transformed['created_at'])
            if transformed.get('updated_at'):
                transformed['updated_at'] = self._parse_datetime(transformed['updated_at'])
            
            # Log transformation results
            estimate_id = transformed.get('estimate_id')
            updated_at = transformed.get('updated_at')
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
        return "leadresults"  # Match the actual sync_type used by the engine (table_name with underscores removed)
