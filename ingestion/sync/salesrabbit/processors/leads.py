"""
SalesRabbit lead processor with framework-compliant validation and bulk operations
"""
import logging
from typing import Dict, Any, List
from django.db import transaction
from .base import SalesRabbitBaseProcessor
from ingestion.models.salesrabbit import SalesRabbit_Lead

logger = logging.getLogger(__name__)

class SalesRabbitLeadProcessor(SalesRabbitBaseProcessor):
    """Lead processor with framework-compliant validation and bulk operations"""
    
    def __init__(self, **kwargs):
        super().__init__(SalesRabbit_Lead, **kwargs)
    
    async def process_batch(self, leads: List[Dict], batch_size: int = 500) -> Dict[str, int]:
        """Process leads using bulk operations - FRAMEWORK STANDARD"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not leads:
            return results
        
        # Transform all records with enhanced error logging
        transformed_leads = []
        for lead_data in leads:
            try:
                # Use enhanced validation with better error logging
                context = {'id': lead_data.get('id', 'unknown')}
                transformed = self.transform_record_with_enhanced_validation(lead_data, context)
                validated = self.validate_record(transformed)
                transformed_leads.append(validated)
            except Exception as e:
                record_id = lead_data.get('id', 'unknown')
                logger.error(f"Failed to transform lead {record_id}: {e}")
                
                # Enhanced error logging with SalesRabbit URL
                if record_id != 'unknown':
                    salesrabbit_url = self.get_salesrabbit_url(record_id)
                    logger.error(f"Failed lead URL: {salesrabbit_url}")
                
                results['failed'] += 1
        
        # Process in chunks for bulk operations
        for chunk in self.chunk_data(transformed_leads, batch_size):
            chunk_results = await self.process_chunk(chunk)
            for key in results:
                results[key] += chunk_results.get(key, 0)
        
        return results
    
    @transaction.atomic
    async def process_chunk(self, chunk: List[Dict]) -> Dict[str, int]:
        """Process chunk using bulk operations"""
        if not chunk:
            return {'created': 0, 'updated': 0, 'failed': 0}
        
        try:
            # Get existing IDs to determine creates vs updates
            existing_ids = set(
                SalesRabbit_Lead.objects.filter(
                    id__in=[lead['id'] for lead in chunk]
                ).values_list('id', flat=True)
            )
            
            leads_to_create = []
            leads_to_update = []
            
            for lead_data in chunk:
                lead_obj = SalesRabbit_Lead(**lead_data)
                
                if lead_data['id'] in existing_ids:
                    leads_to_update.append(lead_obj)
                else:
                    leads_to_create.append(lead_obj)
            
            # Bulk create new leads
            created_count = 0
            if leads_to_create:
                SalesRabbit_Lead.objects.bulk_create(
                    leads_to_create, 
                    batch_size=len(chunk),
                    ignore_conflicts=True
                )
                created_count = len(leads_to_create)
                logger.info(f"Bulk created {created_count} leads")
            
            # Bulk update existing leads
            updated_count = 0
            if leads_to_update:
                SalesRabbit_Lead.objects.bulk_update(
                    leads_to_update,
                    fields=self.get_update_fields(),
                    batch_size=len(chunk)
                )
                updated_count = len(leads_to_update)
                logger.info(f"Bulk updated {updated_count} leads")
            
            return {'created': created_count, 'updated': updated_count, 'failed': 0}
            
        except Exception as e:
            # Enhanced error logging for batch processing
            logger.error(f"Error processing chunk with {len(chunk)} records: {e}")
            
            # Log batch details with enhanced context
            self.log_batch_error(e, chunk)
            
            # Try individual record processing as fallback (following HubSpot pattern)
            return await self.process_chunk_individually(chunk)
    
    def get_update_fields(self) -> List[str]:
        """Get fields that should be updated during sync"""
        return [
            'first_name', 'last_name', 'business_name',
            'email', 'phone_primary', 'phone_alternate',
            'street1', 'street2', 'city', 'state', 'zip', 'country',
            'latitude', 'longitude', 'status', 'status_modified',
            'notes', 'campaign_id', 'user_id', 'user_name',
            'date_modified', 'owner_modified', 'date_of_birth',
            'deleted_at', 'data', 'custom_fields'
        ]
    
    async def process_chunk_individually(self, chunk: List[Dict]) -> Dict[str, int]:
        """Process records individually when bulk operations fail (HubSpot pattern)"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record_data in chunk:
            try:
                record_id = record_data.get('id')
                
                # Try to get existing record
                try:
                    existing_lead = SalesRabbit_Lead.objects.get(id=record_id)
                    # Update existing record
                    for field, value in record_data.items():
                        if field != 'id':
                            setattr(existing_lead, field, value)
                    existing_lead.save()
                    results['updated'] += 1
                    logger.debug(f"Individually updated lead {record_id}")
                    
                except SalesRabbit_Lead.DoesNotExist:
                    # Create new record
                    new_lead = SalesRabbit_Lead(**record_data)
                    new_lead.save()
                    results['created'] += 1
                    logger.debug(f"Individually created lead {record_id}")
                    
            except Exception as e:
                # Enhanced individual record error logging
                record_id = record_data.get('id', 'unknown')
                logger.error(f"Failed to process individual lead {record_id}: {e}")
                
                # Use enhanced database error logging
                self.log_database_error(e, record_data, "individual_save")
                
                results['failed'] += 1
        
        logger.info(f"Individual processing results: {results}")
        return results
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform SalesRabbit lead record with enhanced field handling"""
        # Use parent transformation
        transformed = super().transform_record(record)
        
        # Add lead-specific transformations
        context = {'id': record.get('id', 'unknown')}
        
        # Handle date fields specifically
        date_fields = ['date_created', 'date_modified', 'status_modified', 'owner_modified', 'deleted_at']
        for field in date_fields:
            if field in transformed and transformed[field]:
                transformed[field] = self._parse_datetime(transformed[field])
        
        # Handle date of birth separately (date only, not datetime)
        if 'date_of_birth' in transformed and transformed['date_of_birth']:
            transformed['date_of_birth'] = self._parse_date(transformed['date_of_birth'])
        
        # Ensure numeric fields are properly typed
        numeric_fields = ['campaign_id', 'user_id', 'latitude', 'longitude']
        for field in numeric_fields:
            if field in transformed and transformed[field] is not None:
                if field in ['latitude', 'longitude']:
                    transformed[field] = self._parse_decimal(transformed[field])
                else:
                    transformed[field] = self._parse_integer(transformed[field])
        
        return transformed
    
    def _parse_datetime(self, value: Any) -> Any:
        """Parse datetime value safely"""
        if not value:
            return None
        
        try:
            from django.utils.dateparse import parse_datetime
            from django.utils import timezone
            
            if isinstance(value, str):
                # Try parsing ISO format
                parsed = parse_datetime(value)
                if parsed:
                    return parsed
                
                # Try other common formats
                import datetime
                formats = [
                    '%Y-%m-%d %H:%M:%S',
                    '%Y-%m-%dT%H:%M:%S',
                    '%Y-%m-%dT%H:%M:%SZ',
                    '%Y-%m-%dT%H:%M:%S.%fZ'
                ]
                
                for fmt in formats:
                    try:
                        dt = datetime.datetime.strptime(value, fmt)
                        return timezone.make_aware(dt)
                    except ValueError:
                        continue
            
            return value
        except Exception as e:
            logger.warning(f"Failed to parse datetime '{value}': {e}")
            return None
    
    def _parse_date(self, value: Any) -> Any:
        """Parse date value safely"""
        if not value:
            return None
        
        try:
            from django.utils.dateparse import parse_date
            import datetime
            
            if isinstance(value, str):
                # Try parsing ISO format
                parsed = parse_date(value)
                if parsed:
                    return parsed
                
                # Try other common formats
                formats = ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y']
                for fmt in formats:
                    try:
                        return datetime.datetime.strptime(value, fmt).date()
                    except ValueError:
                        continue
            
            return value
        except Exception as e:
            logger.warning(f"Failed to parse date '{value}': {e}")
            return None
    
    def _parse_decimal(self, value: Any) -> Any:
        """Parse decimal value safely"""
        if not value:
            return None
        
        try:
            from decimal import Decimal
            return Decimal(str(value))
        except Exception as e:
            logger.warning(f"Failed to parse decimal '{value}': {e}")
            return None
