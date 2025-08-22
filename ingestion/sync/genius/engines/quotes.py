"""
Quote sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.quotes import GeniusQuoteClient
from ..processors.quotes import GeniusQuoteProcessor
from ingestion.models import Genius_Quote, Genius_Prospect, Genius_User, Genius_Division, Genius_Job

logger = logging.getLogger(__name__)


class GeniusQuoteSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius quote data"""
    
    def __init__(self):
        super().__init__('quotes')
        self.client = GeniusQuoteClient()
        self.processor = GeniusQuoteProcessor(Genius_Quote)
    
    async def sync_quotes(self, since_date=None, force_overwrite=False, 
                         dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for quotes"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get quotes from source
            raw_quotes = await sync_to_async(self.client.get_quotes)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_quotes)} quotes from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process quotes but making no changes")
                return stats
            
            # Process quotes in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_quotes), batch_size):
                batch = raw_quotes[i:i + batch_size]
                batch_stats = await self._process_quote_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Quote sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Quote sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_quote_batch(self, batch: List[tuple], field_mapping: List[str], 
                            force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of quote records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Preload lookup data for FK validation
        prospects = {p.genius_id: p for p in Genius_Prospect.objects.all()}
        users = {u.genius_id: u for u in Genius_User.objects.all()}
        divisions = {d.genius_id: d for d in Genius_Division.objects.all()}
        jobs = {j.genius_id: j for j in Genius_Job.objects.all()}
        
        with transaction.atomic():
            for raw_record in batch:
                try:
                    stats['total_processed'] += 1
                    
                    # Transform raw data to dict
                    record_data = self.processor.transform_record(raw_record, field_mapping)
                    
                    # Validate record
                    validated_data = self.processor.validate_record(record_data)
                    
                    # Skip if required data missing
                    if not validated_data.get('genius_id'):
                        logger.warning("Skipping quote with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Validate required FK relationships exist
                    if validated_data.get('prospect_id') and validated_data['prospect_id'] not in prospects:
                        logger.warning(f"Quote {validated_data['genius_id']} references non-existent prospect {validated_data['prospect_id']}")
                        stats['skipped'] += 1
                        continue
                    
                    # Validate optional FK relationships
                    if validated_data.get('user_id') and validated_data['user_id'] not in users:
                        logger.warning(f"Quote {validated_data['genius_id']} references non-existent user {validated_data['user_id']}")
                        validated_data['user_id'] = None
                    
                    if validated_data.get('division_id') and validated_data['division_id'] not in divisions:
                        logger.warning(f"Quote {validated_data['genius_id']} references non-existent division {validated_data['division_id']}")
                        validated_data['division_id'] = None
                    
                    # Get or create quote
                    quote, created = Genius_Quote.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created quote {quote.genius_id}: {quote.quote_number}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_quote(quote, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(quote, field, value)
                            quote.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated quote {quote.genius_id}: {quote.quote_number}")
                        else:
                            stats['skipped'] += 1
                    
                    # Set relationships
                    if validated_data.get('prospect_id'):
                        quote.prospect = prospects[validated_data['prospect_id']]
                    
                    if validated_data.get('user_id') and validated_data['user_id'] in users:
                        quote.user = users[validated_data['user_id']]
                    
                    if validated_data.get('division_id') and validated_data['division_id'] in divisions:
                        quote.division = divisions[validated_data['division_id']]
                    
                    if validated_data.get('converted_to_job_id') and validated_data['converted_to_job_id'] in jobs:
                        quote.converted_to_job = jobs[validated_data['converted_to_job_id']]
                    
                    quote.save()
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing quote record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_quote(self, existing: Genius_Quote, new_data: Dict[str, Any]) -> bool:
        """Check if quote should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['quote_number', 'quote_date', 'total_amount', 'status', 
                          'notes', 'valid_until', 'prospect_id', 'user_id', 
                          'division_id', 'converted_to_job_id']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
