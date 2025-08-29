"""
Lead sync engine for Genius CRM
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from .base import GeniusBaseSyncEngine
from ..clients.leads import GeniusLeadClient
from ..processors.leads import GeniusLeadProcessor
from ingestion.models import Genius_Lead, Genius_UserData, Genius_Division, Genius_Prospect

logger = logging.getLogger(__name__)


class GeniusLeadsSyncEngine(GeniusBaseSyncEngine):
    """Sync engine for Genius lead data"""
    
    def __init__(self):
        super().__init__('leads')
        self.client = GeniusLeadClient()
        self.processor = GeniusLeadProcessor(Genius_Lead)
    
    async def execute_sync(self, 
                          full: bool = False,
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None,
                          max_records: Optional[int] = None,
                          dry_run: bool = False,
                          debug: bool = False) -> Dict[str, Any]:
        """Execute the leads sync process - adapter for standard sync interface"""
        
        # Convert parameters to match existing method signature
        since_date = since
        force_overwrite = full
        
        return await self.sync_leads(
            since_date=since_date, 
            force_overwrite=force_overwrite,
            dry_run=dry_run, 
            max_records=max_records or 0
        )
    
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
            # Process leads in chunks to handle large datasets
            chunk_size = 1000
            total_processed = 0
            field_mapping = self.client.get_field_mapping()
            
            if dry_run:
                logger.info("DRY RUN: Would process leads in chunks but making no changes")
                # Still get a count for dry run
                raw_leads = await sync_to_async(self.client.get_leads)(
                    since_date=since_date,
                    limit=max_records or 10000  # Limit for dry run
                )
                stats['total_processed'] = len(raw_leads)
                logger.info(f"DRY RUN: Would process {len(raw_leads)} leads")
                return stats
            
            logger.info(f"Starting leads sync - since_date: {since_date}, force_overwrite: {force_overwrite}, max_records: {max_records}")
            
            # Process leads in chunks
            chunk_num = 0
            
            # Use a sync function to iterate through chunks
            def process_chunks():
                nonlocal chunk_num, total_processed, stats
                
                for chunk in self.client.get_leads_chunked(
                    since_date=since_date, 
                    chunk_size=min(chunk_size, max_records) if max_records else chunk_size
                ):
                    chunk_num += 1
                    
                    # Apply max_records limit if specified
                    if max_records and total_processed >= max_records:
                        logger.info(f"Reached max_records limit of {max_records}, stopping")
                        break
                        
                    # Trim chunk if it would exceed max_records
                    if max_records and total_processed + len(chunk) > max_records:
                        remaining = max_records - total_processed
                        chunk = chunk[:remaining]
                        logger.info(f"Trimming chunk to {len(chunk)} records to respect max_records limit")
                    
                    yield chunk_num, chunk
                    
                    # If we trimmed the chunk, we're done
                    if max_records and total_processed + len(chunk) >= max_records:
                        break
            
            for chunk_num, chunk in await sync_to_async(list)(process_chunks()):
                
                logger.info(f"Processing chunk {chunk_num} with {len(chunk)} records")
                
                batch_stats = await self._process_lead_chunk_bulk(
                    chunk, field_mapping, force_overwrite
                )
                
                # Update overall stats
                for key in stats:
                    stats[key] += batch_stats[key]
                
                total_processed += len(chunk)
                
                logger.info(f"Completed chunk {chunk_num}: "
                          f"{batch_stats['created']} created, "
                          f"{batch_stats['updated']} updated, "
                          f"{batch_stats['errors']} errors, "
                          f"Total processed: {total_processed}")
            
            logger.info(f"Lead sync completed. Final stats: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"Lead sync failed: {str(e)}")
            raise
        
        finally:
            self.client.disconnect()
    
    @sync_to_async
    def _process_lead_chunk_bulk(self, chunk: List[tuple], field_mapping: List[str], 
                                force_overwrite: bool = False) -> Dict[str, int]:
        """Process a chunk of lead records using bulk operations for efficiency"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        logger.info(f"Processing chunk with {len(chunk)} records, field_mapping: {field_mapping}")
        
        # Transform all records first
        processed_records = []
        existing_ids = []
        
        for raw_record in chunk:
            try:
                stats['total_processed'] += 1
                
                # Transform raw data to dict
                record_data = self.processor.transform_record(raw_record, field_mapping)
                
                # Validate record
                validated_data = self.processor.validate_record(record_data)
                
                # Skip if processor returns None (invalid/dummy record)
                if validated_data is None:
                    stats['skipped'] += 1
                    logger.debug(f"Skipped invalid/dummy record")
                    continue
                
                # Skip if required data missing
                if not validated_data.get('lead_id'):
                    logger.warning("Skipping lead with no lead_id")
                    stats['skipped'] += 1
                    continue
                
                # Add sync timestamp
                validated_data['sync_updated_at'] = timezone.now()
                
                processed_records.append(validated_data)
                existing_ids.append(validated_data['lead_id'])
                
            except Exception as e:
                stats['errors'] += 1
                logger.error(f"Error processing lead record: {e}")
                logger.error(f"Raw record: {raw_record}")
        
        if not processed_records:
            logger.warning("No valid records to process in this chunk")
            return stats
        
        logger.info(f"Successfully processed {len(processed_records)} records, attempting database operations...")
        
        try:
            with transaction.atomic():
                # Get existing records by lead_id
                existing_leads = {lead.lead_id: lead for lead in 
                                Genius_Lead.objects.filter(lead_id__in=existing_ids)}
                
                logger.info(f"Found {len(existing_leads)} existing records out of {len(processed_records)} total")
                
                # Separate into creates and updates
                creates = []
                updates = []
                
                for record_data in processed_records:
                    lead_id = record_data['lead_id']
                    
                    if lead_id in existing_leads:
                        # Update existing
                        existing_lead = existing_leads[lead_id]
                        if force_overwrite or self._should_update_lead(existing_lead, record_data):
                            for field, value in record_data.items():
                                if field != 'lead_id':  # Don't update primary key
                                    # Map and validate field values for updates
                                    if field == 'phone':
                                        setattr(existing_lead, 'phone1', str(value)[:20] if value else None)
                                    elif field == 'zip_code':
                                        setattr(existing_lead, 'zip', str(value)[:12] if value else None)
                                    elif field == 'address':
                                        setattr(existing_lead, 'address1', str(value)[:200] if value else None)
                                    elif field == 'prospect_source_id':
                                        setattr(existing_lead, 'source', value)
                                    elif field == 'user_id':
                                        setattr(existing_lead, 'added_by', value)
                                    elif field == 'created_at':
                                        setattr(existing_lead, 'added_on', value)
                                    elif field == 'converted_to_prospect_id':
                                        setattr(existing_lead, 'copied_to_id', value)
                                    elif field in ['first_name', 'last_name']:
                                        setattr(existing_lead, field, str(value)[:100] if value else None)
                                    elif field == 'email':
                                        setattr(existing_lead, field, str(value)[:100] if value else None)
                                    elif field == 'city':
                                        setattr(existing_lead, field, str(value)[:50] if value else None)
                                    elif field == 'state':
                                        setattr(existing_lead, field, str(value)[:20] if value else None)
                                    elif field == 'status':
                                        setattr(existing_lead, field, str(value)[:50] if value else None)
                                    elif field == 'notes':
                                        setattr(existing_lead, field, str(value)[:2000] if value else None)
                                    else:
                                        setattr(existing_lead, field, value)
                            updates.append(existing_lead)
                            logger.debug(f"Prepared update for lead {lead_id}")
                        else:
                            stats['skipped'] += 1
                            logger.debug(f"Skipped lead {lead_id} - no changes needed")
                    else:
                        # Create new - map fields properly and validate field lengths
                        create_data = {}
                        for field, value in record_data.items():
                            # Map field names to match model and validate lengths
                            if field == 'phone':
                                create_data['phone1'] = str(value)[:20] if value else None  # phone1 field limit
                            elif field == 'zip_code':
                                create_data['zip'] = str(value)[:12] if value else None  # zip field limit
                            elif field == 'address':
                                create_data['address1'] = str(value)[:200] if value else None
                            elif field == 'prospect_source_id':
                                create_data['source'] = value
                            elif field == 'user_id':
                                create_data['added_by'] = value
                            elif field == 'division_id':
                                create_data['division_id'] = value
                            elif field == 'created_at':
                                create_data['added_on'] = value
                            elif field == 'converted_to_prospect_id':
                                create_data['copied_to_id'] = value
                            elif field in ['first_name', 'last_name']:
                                create_data[field] = str(value)[:100] if value else None
                            elif field == 'email':
                                create_data[field] = str(value)[:100] if value else None
                            elif field == 'city':
                                create_data[field] = str(value)[:50] if value else None
                            elif field == 'state':
                                create_data[field] = str(value)[:20] if value else None
                            elif field == 'status':
                                create_data[field] = str(value)[:50] if value else None
                            elif field == 'notes':
                                create_data[field] = str(value)[:2000] if value else None
                            else:
                                create_data[field] = value
                        
                        creates.append(Genius_Lead(**create_data))
                        logger.debug(f"Prepared create for lead {lead_id}")
                
                # Perform bulk operations within this transaction
                if creates:
                    try:
                        created_leads = Genius_Lead.objects.bulk_create(
                            creates, 
                            batch_size=500, 
                            ignore_conflicts=True
                        )
                        stats['created'] = len(creates)
                        logger.info(f"Successfully bulk created {len(creates)} leads")
                    except Exception as e:
                        logger.error(f"Error in bulk_create: {e}")
                        # Don't fall back to individual creates within transaction
                        stats['errors'] += len(creates)
                
                # Bulk update
                if updates:
                    try:
                        # Define which fields to update - map to actual model fields
                        update_fields = ['first_name', 'last_name', 'email', 'phone1', 'address1', 
                                       'city', 'state', 'zip', 'status', 'notes',
                                       'source', 'added_by', 'division_id', 
                                       'copied_to_id', 'added_on', 'updated_at',
                                       'sync_updated_at']
                        
                        Genius_Lead.objects.bulk_update(updates, update_fields, batch_size=500)
                        stats['updated'] = len(updates)
                        logger.info(f"Successfully bulk updated {len(updates)} leads")
                    except Exception as e:
                        logger.error(f"Error in bulk_update: {e}")
                        # Don't fall back to individual updates within transaction
                        stats['errors'] += len(updates)
                        
        except Exception as e:
            logger.error(f"Error in database transaction: {e}")
            # Try individual operations outside of transaction if bulk fails
            stats['created'] = 0
            stats['updated'] = 0
            stats['errors'] = len(processed_records)
            
            # Attempt individual creates and updates outside atomic block
            for record_data in processed_records:
                try:
                    lead_id = record_data['lead_id']
                    
                    # Map fields for individual create/update
                    mapped_data = {}
                    for field, value in record_data.items():
                        if field == 'phone':
                            mapped_data['phone1'] = str(value)[:20] if value else None
                        elif field == 'zip_code':
                            mapped_data['zip'] = str(value)[:12] if value else None
                        elif field == 'address':
                            mapped_data['address1'] = str(value)[:200] if value else None
                        elif field == 'prospect_source_id':
                            mapped_data['source'] = value
                        elif field == 'user_id':
                            mapped_data['added_by'] = value
                        elif field == 'created_at':
                            mapped_data['added_on'] = value
                        elif field == 'converted_to_prospect_id':
                            mapped_data['copied_to_id'] = value
                        elif field in ['first_name', 'last_name']:
                            mapped_data[field] = str(value)[:100] if value else None
                        elif field == 'email':
                            mapped_data[field] = str(value)[:100] if value else None
                        elif field == 'city':
                            mapped_data[field] = str(value)[:50] if value else None
                        elif field == 'state':
                            mapped_data[field] = str(value)[:20] if value else None
                        elif field == 'status':
                            mapped_data[field] = str(value)[:50] if value else None
                        elif field == 'notes':
                            mapped_data[field] = str(value)[:2000] if value else None
                        else:
                            mapped_data[field] = value
                    
                    lead, created = Genius_Lead.objects.get_or_create(
                        lead_id=lead_id,
                        defaults=mapped_data
                    )
                    
                    if created:
                        stats['created'] += 1
                        stats['errors'] -= 1
                    else:
                        # Update if needed
                        if force_overwrite or self._should_update_lead(lead, record_data):
                            for field, value in mapped_data.items():
                                if field != 'lead_id':
                                    setattr(lead, field, value)
                            lead.save()
                            stats['updated'] += 1
                            stats['errors'] -= 1
                        else:
                            stats['skipped'] += 1
                            stats['errors'] -= 1
                            
                except Exception as individual_error:
                    logger.error(f"Error processing individual lead {record_data.get('lead_id', 'unknown')}: {individual_error}")
                    # Keep error count as is
        
        logger.info(f"Chunk processing complete: {stats}")
        return stats
    
    @sync_to_async
    def _process_lead_batch(self, batch: List[tuple], field_mapping: List[str], 
                           force_overwrite: bool = False) -> Dict[str, int]:
        """Process a batch of lead records"""
        
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0, 'skipped': 0}
        
        # Preload lookup data for FK validation
        users = {u.user_id: u for u in Genius_UserData.objects.all()}
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
