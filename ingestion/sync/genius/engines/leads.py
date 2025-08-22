"""
Lead sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List
from asgiref.sync import sync_to_async
from django.db import transaction

from .base import GeniusBaseSyncEngine
from ..clients.leads import GeniusLeadClient
from ..processors.leads import GeniusLeadProcessor
from ingestion.models import Genius_Lead, Genius_User, Genius_Division, Genius_Prospect

logger = logging.getLogger(__name__)


class GeniusLeadSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius lead data"""
    
    def __init__(self):
        super().__init__('leads')
        self.client = GeniusLeadClient()
        self.processor = GeniusLeadProcessor(Genius_Lead)
    
    async def sync_leads(self, since_date=None, force_overwrite=False, 
                        dry_run=False, max_records=0, **kwargs) -> Dict[str, Any]:
        """Main sync method for leads"""
        
        stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'errors': 0,
            'skipped': 0
        }
        
        try:
            # Get leads from source
            raw_leads = await sync_to_async(self.client.get_leads)(
                since_date=since_date,
                limit=max_records
            )
            
            logger.info(f"Fetched {len(raw_leads)} leads from Genius")
            
            if dry_run:
                logger.info("DRY RUN: Would process leads but making no changes")
                return stats
            
            # Process leads in batches
            batch_size = 500
            field_mapping = self.client.get_field_mapping()
            
            for i in range(0, len(raw_leads), batch_size):
                batch = raw_leads[i:i + batch_size]
                batch_stats = await self._process_lead_batch(
                    batch, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                logger.info(f"Processed batch {i//batch_size + 1}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors")
            
            logger.info(f"Lead sync completed. Total stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Lead sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_lead_batch(self, batch: List[tuple], field_mapping: List[str], 
                           force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of lead records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Preload lookup data for FK validation
        users = {u.genius_id: u for u in Genius_User.objects.all()}
        divisions = {d.genius_id: d for d in Genius_Division.objects.all()}
        prospects = {p.genius_id: p for p in Genius_Prospect.objects.all()}
        
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
                        logger.warning("Skipping lead with no ID")
                        stats['skipped'] += 1
                        continue
                    
                    # Validate FK relationships exist (optional for leads)
                    if validated_data.get('user_id') and validated_data['user_id'] not in users:
                        logger.warning(f"Lead {validated_data['genius_id']} references non-existent user {validated_data['user_id']}")
                        validated_data['user_id'] = None  # Allow lead without user
                    
                    if validated_data.get('division_id') and validated_data['division_id'] not in divisions:
                        logger.warning(f"Lead {validated_data['genius_id']} references non-existent division {validated_data['division_id']}")
                        validated_data['division_id'] = None  # Allow lead without division
                    
                    # Get or create lead
                    lead, created = Genius_Lead.objects.get_or_create(
                        genius_id=validated_data['genius_id'],
                        defaults=validated_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.debug(f"Created lead {lead.genius_id}: {lead.first_name} {lead.last_name}")
                    else:
                        # Update if force_overwrite or data changed
                        if force_overwrite or self._should_update_lead(lead, validated_data):
                            for field, value in validated_data.items():
                                if field != 'genius_id':  # Don't update primary key
                                    setattr(lead, field, value)
                            lead.save()
                            stats['updated'] += 1
                            logger.debug(f"Updated lead {lead.genius_id}: {lead.first_name} {lead.last_name}")
                        else:
                            stats['skipped'] += 1
                    
                    # Set relationships
                    if validated_data.get('user_id') and validated_data['user_id'] in users:
                        lead.user = users[validated_data['user_id']]
                    
                    if validated_data.get('division_id') and validated_data['division_id'] in divisions:
                        lead.division = divisions[validated_data['division_id']]
                    
                    if validated_data.get('converted_to_prospect_id') and validated_data['converted_to_prospect_id'] in prospects:
                        lead.converted_to_prospect = prospects[validated_data['converted_to_prospect_id']]
                    
                    lead.save()
                    
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error processing lead record: {e}")
                    logger.error(f"Record data: {raw_record}")
        
        return stats
    
    def _should_update_lead(self, existing: Genius_Lead, new_data: Dict[str, Any]) -> bool:
        """Check if lead should be updated based on data changes"""
        
        # Always update if updated_at is newer
        if (new_data.get('updated_at') and existing.updated_at and 
            new_data['updated_at'] > existing.updated_at):
            return True
        
        # Check for actual data changes
        fields_to_check = ['first_name', 'last_name', 'email', 'phone', 'address', 
                          'city', 'state', 'zip_code', 'status', 'notes',
                          'prospect_source_id', 'user_id', 'division_id', 'converted_to_prospect_id']
        for field in fields_to_check:
            if field in new_data and getattr(existing, field, None) != new_data[field]:
                return True
        
        return False
