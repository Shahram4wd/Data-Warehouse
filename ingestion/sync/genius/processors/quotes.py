"""
Quote processor for Genius CRM data transformation and bulk operations
Following CRM sync guide with Django bulk_create operations
"""
import logging
from typing import Dict, Any, List
from decimal import Decimal
from datetime import datetime

from django.db import transaction
from django.utils import timezone

from ingestion.models import Genius_Quote

logger = logging.getLogger('quotes')


class GeniusQuoteProcessor:
    """Processor for Genius quote data transformation with bulk operations"""
    
    def __init__(self):
        pass
    
    def process_batch(self, batch_data: List[tuple], field_mapping: List[str], 
                     force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, int]:
        """Process a batch of quotes data"""
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(batch_data)} quote records")
            return {
                'total_processed': len(batch_data), 
                'created': len(batch_data), 
                'updated': 0, 
                'errors': 0
            }
        
        return self.bulk_upsert_quotes(batch_data, force_overwrite)
    def bulk_upsert_quotes(self, quotes_data: List[tuple], force_overwrite: bool = False) -> Dict[str, Any]:
        """Bulk upsert quotes using Django bulk_create with update_conflicts"""
        
        stats = {
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        if not quotes_data:
            return stats
        
        quote_objects = []
        
        for raw_quote in quotes_data:
            try:
                # Transform and validate quote data
                quote_data = self._transform_quote(raw_quote)
                
                if not quote_data:  # Skip invalid records
                    stats['errors'] += 1
                    continue
                
                # Create quote object
                quote_obj = Genius_Quote(**quote_data)
                quote_objects.append(quote_obj)
                
            except Exception as e:
                logger.error(f"Error transforming quote record: {e}")
                stats['errors'] += 1
        
        if quote_objects:
            try:
                # Use bulk_create with update_conflicts for upsert behavior
                created_quotes = Genius_Quote.objects.bulk_create(
                    quote_objects,
                    update_conflicts=True,
                    update_fields=[
                        'prospect_id', 'appointment_id', 'job_id', 'client_cid',
                        'service_id', 'label', 'description', 'amount', 'expire_date',
                        'status_id', 'contract_file_id', 'estimate_file_id', 
                        'add_user_id', 'add_date', 'updated_at'
                    ] if force_overwrite else ['updated_at'],
                    unique_fields=['id']
                )
                
                # Count actual creates vs updates
                stats['created'] = len(created_quotes)
                logger.info(f"Bulk upsert completed - Created: {stats['created']}, Updated: {stats['updated']}")
                
            except Exception as e:
                logger.error(f"Bulk operation failed: {e}")
                stats['errors'] += len(quote_objects)
        
        return stats
    
    def _transform_quote(self, raw_data: tuple) -> Dict[str, Any]:
        """Transform raw quote data to model fields"""
        
        # Map raw tuple to dictionary based on query field order
        # From client query: id, prospect_id, appointment_id, job_id, client_cid,
        # service_id, label, description, amount, expire_date, status_id,
        # contract_file_id, estimate_file_id, add_user_id, add_date, updated_at
        
        try:
            if not raw_data or len(raw_data) < 16:
                logger.error("Quote record missing required fields")
                return None
            
            # Check for required ID field
            if not raw_data[0]:
                logger.error("Quote record missing required ID field")
                return None
                
            quote_data = {
                'id': int(raw_data[0]),
                'prospect_id': int(raw_data[1]) if raw_data[1] and raw_data[1] != 0 else None,
                'appointment_id': int(raw_data[2]) if raw_data[2] and raw_data[2] != 0 else None,
                'job_id': int(raw_data[3]) if raw_data[3] and raw_data[3] != 0 else None,
                'client_cid': int(raw_data[4]) if raw_data[4] and raw_data[4] != 0 else None,
                'service_id': int(raw_data[5]) if raw_data[5] else 1,  # Default service_id
                'label': str(raw_data[6]).strip() if raw_data[6] else None,
                'description': str(raw_data[7]).strip() if raw_data[7] else None,
                'amount': Decimal(str(raw_data[8])) if raw_data[8] is not None else Decimal('0.00'),
                'expire_date': raw_data[9] if raw_data[9] else None,
                'status_id': int(raw_data[10]) if raw_data[10] else 1,  # Default status
                'contract_file_id': int(raw_data[11]) if raw_data[11] and raw_data[11] != 0 else None,
                'estimate_file_id': int(raw_data[12]) if raw_data[12] and raw_data[12] != 0 else None,
                'add_user_id': int(raw_data[13]) if raw_data[13] and raw_data[13] != 0 else 1,  # Default user
                'add_date': self._ensure_timezone_aware(raw_data[14]) if raw_data[14] else timezone.now(),
                'updated_at': self._ensure_timezone_aware(raw_data[15]) if raw_data[15] else timezone.now(),
            }
            
            # Validate required fields
            if not quote_data['prospect_id']:
                logger.error(f"Quote {quote_data['id']} missing required prospect_id")
                return None
            
            return quote_data
            
        except (ValueError, TypeError, IndexError) as e:
            logger.error(f"Error transforming quote data: {e}")
            logger.error(f"Raw data: {raw_data}")
            return None
    
    def _ensure_timezone_aware(self, dt):
        """Ensure datetime is timezone-aware"""
        if dt is None:
            return None
        
        if isinstance(dt, datetime):
            if timezone.is_aware(dt):
                return dt
            else:
                return timezone.make_aware(dt)
        
        return dt
