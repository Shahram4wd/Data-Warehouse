"""
Five9 Contacts Sync Engine
Orchestrates the synchronization of contact records from Five9
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import logging
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from asgiref.sync import sync_to_async

from ....base.sync_engine import BaseSyncEngine
from ..clients.contacts import ContactsClient
from ..processors.contacts import ContactsProcessor
from ....models.five9 import Five9Contact
from ....models.common import SyncHistory
from ....config.five9_config import Five9Config, DELTA_SYNC_CONFIG

logger = logging.getLogger(__name__)


class ContactsSyncEngine(BaseSyncEngine):
    """Sync engine for Five9 contact records"""
    
    def __init__(self, **kwargs):
        super().__init__(crm_source="Five9", sync_type="contacts", **kwargs)
        self.processor = ContactsProcessor()
    
    def get_default_batch_size(self) -> int:
        """Return default batch size for Five9 contacts"""
        return Five9Config.DEFAULT_BATCH_SIZE
    
    async def initialize_client(self) -> None:
        """Initialize Five9 API client"""
        self.client = ContactsClient()
        # Connect synchronously since Five9 client is not async
        if not await sync_to_async(self.client.connect)():
            raise Exception("Failed to connect to Five9 API")
    
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch contact data from Five9 list by list with delta and batching"""
        try:
            # Get contact lists first
            logger.info("Fetching Five9 contact lists...")
            contact_lists = await sync_to_async(self.client.get_contact_lists_dict)()
            
            if not contact_lists:
                logger.warning("No contact lists found")
                return
            
            max_records_per_list = kwargs.get('max_records_per_list', Five9Config.MAX_BATCH_SIZE)
            logger.info(f"Processing {len(contact_lists)} contact lists")
            
            # Determine delta window
            since = kwargs.get('since')
            full = kwargs.get('full', False)
            force_overwrite = kwargs.get('force_overwrite', False)

            if not full and not since:
                # Default to last successful SyncHistory end_time with lookback
                last_end = await sync_to_async(self._get_last_success_end_time)()
                if last_end:
                    lookback = DELTA_SYNC_CONFIG.get('lookback_hours', 24)
                    since = last_end - timedelta(hours=lookback)
                    logger.info(f"Delta mode: since={since.isoformat()} (lookback {lookback}h)")
                else:
                    # Initial window to avoid full blast
                    days = DELTA_SYNC_CONFIG.get('initial_sync_days', 30)
                    since = timezone.now() - timedelta(days=days)
                    logger.info(f"Initial delta window: last {days} days ({since.isoformat()})")

            if force_overwrite:
                since = None
                logger.info("Force overwrite requested; fetching all lists without delta filter")
            elif full:
                since = None
                logger.info("Full sync requested; fetching all lists without delta filter")

            # Process each list individually to avoid memory overload
            for i, (list_name, record_count) in enumerate(contact_lists.items(), 1):
                try:
                    # Skip empty lists
                    if record_count == 0:
                        logger.debug(f"Skipping empty list: {list_name}")
                        continue
                    
                    # Limit records per list if specified
                    actual_records_to_fetch = min(record_count, max_records_per_list) if max_records_per_list > 0 else record_count
                    
                    logger.info(f"Processing list {i}/{len(contact_lists)}: {list_name} ({actual_records_to_fetch} records)")
                    
                    # Fetch contacts for this specific list
                    list_contacts = await sync_to_async(self.client.get_contact_records_from_list)(list_name)
                    
                    if not list_contacts:
                        logger.warning(f"No contacts found in list: {list_name}")
                        continue
                    
                    # Add list_name to each contact
                    for contact in list_contacts:
                        contact['list_name'] = list_name
                    
                    # Optional local delta filtering by timestamp fields
                    if since:
                        ts_fields = [
                            DELTA_SYNC_CONFIG.get('timestamp_field', 'sys_last_disposition_time'),
                            *DELTA_SYNC_CONFIG.get('fallback_timestamp_fields', [])
                        ]
                        filtered = []
                        for rec in list_contacts:
                            ts_val = None
                            for f in ts_fields:
                                if f in rec and rec[f]:
                                    ts_val = rec[f]
                                    break
                            if not ts_val:
                                continue
                            try:
                                # Accept ISO or epoch-like strings
                                if isinstance(ts_val, str):
                                    try:
                                        parsed = timezone.datetime.fromisoformat(ts_val)
                                    except ValueError:
                                        parsed = None
                                elif isinstance(ts_val, datetime):
                                    parsed = ts_val
                                else:
                                    parsed = None
                                if parsed and timezone.is_naive(parsed):
                                    parsed = timezone.make_aware(parsed)
                                if parsed and parsed >= since:
                                    filtered.append(rec)
                            except Exception:
                                continue
                        logger.info(f"Delta-filtered {len(filtered)}/{len(list_contacts)} records in {list_name}")
                        list_contacts = filtered

                    # Yield contacts from this list in batches immediately
                    batch_size = min(self.batch_size, 500)
                    logger.info(f"Successfully retrieved {len(list_contacts)} records from {list_name}")
                    
                    for j in range(0, len(list_contacts), batch_size):
                        batch = list_contacts[j:j + batch_size]
                        logger.debug(f"Yielding batch from {list_name}: {len(batch)} contacts")
                        yield batch
                        
                except Exception as e:
                    logger.error(f"Error processing list {list_name}: {e}")
                    continue
                        
        except Exception as e:
            logger.error(f"Error fetching Five9 contact data: {e}")
            raise
    
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform raw Five9 contact data"""
        if not raw_data:
            return []
        
        # Extract list_name from first record (it's added in fetch_data method)
        list_name = raw_data[0].get('list_name', '')
        
        return await sync_to_async(self.processor.process_contact_batch)(raw_data, list_name)
    
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate transformed contact data"""
        return await sync_to_async(self.processor.validate_contact_batch)(data)
    
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save validated contacts to database"""
        if self.dry_run:
            return {'created': 0, 'updated': len(validated_data), 'skipped': 0}
        
        return await sync_to_async(self._save_contacts_batch)(validated_data)
    
    def _save_contacts_batch(self, contacts_data: List[Dict]) -> Dict[str, int]:
        """Save contacts batch to database using efficient bulk operations"""
        if not contacts_data:
            return {'created': 0, 'updated': 0, 'skipped': 0}
        
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Get valid Django model field names
        valid_fields = set(field.name for field in Five9Contact._meta.get_fields())
        
        logger.info(f"Processing batch of {len(contacts_data)} contacts for bulk save")
        
        with transaction.atomic():
            # Filter and prepare contact data
            valid_contacts = []
            contact_keys = []
            
            for contact_data in contacts_data:
                try:
                    # Filter contact_data to only include valid model fields
                    filtered_data = {
                        k: v for k, v in contact_data.items() 
                        if k in valid_fields
                    }
                    
                    # Ensure we have required fields
                    number1 = filtered_data.get('number1')
                    list_name = filtered_data.get('list_name')
                    
                    if not number1 or not list_name:
                        logger.warning(f"Contact missing required fields (number1: {number1}, list_name: {list_name})")
                        skipped_count += 1
                        continue
                    
                    valid_contacts.append(filtered_data)
                    contact_keys.append((number1, list_name))
                        
                except Exception as e:
                    logger.warning(f"Failed to process contact {contact_data.get('number1')}: {e}")
                    skipped_count += 1
            
            if not valid_contacts:
                return {'created': 0, 'updated': 0, 'skipped': skipped_count}
            
            # EFFICIENT APPROACH: Use bulk create with proper conflict resolution
            # Get all existing contacts in one query to avoid conflicts
            existing_contacts = {}
            existing_qs = Five9Contact.objects.filter(
                Q(*[
                    Q(number1=key[0], list_name=key[1]) 
                    for key in contact_keys
                ])
            ).values('number1', 'list_name', 'id')
            
            for contact in existing_qs:
                key = (contact['number1'], contact['list_name'])
                existing_contacts[key] = contact['id']
            
            # Separate into create and update batches
            contacts_to_create = []
            contacts_to_update = []
            
            for contact_data in valid_contacts:
                key = (contact_data['number1'], contact_data['list_name'])
                if key in existing_contacts:
                    contact_data['id'] = existing_contacts[key]
                    contacts_to_update.append(contact_data)
                else:
                    contacts_to_create.append(contact_data)
            
            # Bulk create new contacts
            if contacts_to_create:
                try:
                    new_contacts = [Five9Contact(**data) for data in contacts_to_create]
                    Five9Contact.objects.bulk_create(new_contacts, batch_size=500, ignore_conflicts=True)
                    created_count = len(new_contacts)
                    logger.info(f"Bulk created {created_count} new contacts")
                except Exception as create_error:
                    logger.error(f"Error in bulk_create: {create_error}")
                    created_count = 0
            
            # Bulk update existing contacts
            if contacts_to_update:
                try:
                    update_fields = [f for f in valid_fields if f not in ['id', 'number1', 'list_name']]
                    contacts_to_bulk_update = []
                    
                    for contact_data in contacts_to_update:
                        contact = Five9Contact(id=contact_data.pop('id'))
                        for field, value in contact_data.items():
                            if field in update_fields:
                                setattr(contact, field, value)
                        contacts_to_bulk_update.append(contact)
                    
                    Five9Contact.objects.bulk_update(contacts_to_bulk_update, update_fields, batch_size=500)
                    updated_count = len(contacts_to_bulk_update)
                    logger.info(f"Bulk updated {updated_count} existing contacts")
                    
                except Exception as update_error:
                    logger.error(f"Error in bulk_update: {update_error}")
                    updated_count = 0
            else:
                updated_count = 0
        
        logger.info(f"Batch save completed: {created_count} created, {updated_count} updated, {skipped_count} skipped")
        return {
            'created': created_count, 
            'updated': updated_count, 
            'skipped': skipped_count
        }

    def _get_last_success_end_time(self) -> Optional[datetime]:
        try:
            last = (SyncHistory.objects
                    .filter(crm_source=self.crm_source, sync_type=self.sync_type, status='success', end_time__isnull=False)
                    .order_by('-end_time').first())
            return last.end_time if last else None
        except Exception:
            return None
    
    async def cleanup(self) -> None:
        """Cleanup Five9 client resources"""
        if self.client:
            await sync_to_async(self.client.close_sessions)()
    
    # Legacy sync methods for backward compatibility
    def sync_data(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """Legacy sync method - wraps async sync process"""
        import asyncio
        # Normalize flags for run
        full = kwargs.pop('full', False) or force_full
        force_overwrite = kwargs.pop('force_overwrite', False)
        return asyncio.run(self.run_sync_async(full=full, force_overwrite=force_overwrite, **kwargs))
    
    async def run_sync_async(self, full: bool = False, force_overwrite: bool = False, **kwargs) -> Dict[str, Any]:
        """Run the complete sync process asynchronously"""
        results = {
            'success': False,
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': []
        }
        
        try:
            # Start sync and create history record
            await self.start_sync(full=full, force_overwrite=force_overwrite, **kwargs)
            
            # Initialize client
            await self.initialize_client()
            
            # Process data in batches
            async for raw_batch in self.fetch_data(full=full, force_overwrite=force_overwrite, **kwargs):
                try:
                    # Transform data
                    transformed_batch = await self.transform_data(raw_batch)
                    
                    # Validate data  
                    validated_batch = await self.validate_data(transformed_batch)
                    
                    # Save data
                    batch_results = await self.save_data(validated_batch)
                    
                    # Update totals
                    results['total_processed'] += len(validated_batch)
                    results['created'] += batch_results['created']
                    results['updated'] += batch_results['updated']
                    results['skipped'] += batch_results['skipped']
                    
                except Exception as e:
                    logger.error(f"Error processing batch: {e}")
                    results['errors'].append(str(e))
            
            results['success'] = True
            
        except Exception as e:
            logger.error(f"Five9 sync failed: {e}")
            results['errors'].append(str(e))
        
        finally:
            await self.cleanup()
            
            # Update sync history
            if hasattr(self, 'sync_history') and self.sync_history:
                # Map results to BaseSyncEngine expected keys for metrics
                mapped = {
                    'processed': results.get('total_processed', 0),
                    'created': results.get('created', 0),
                    'updated': results.get('updated', 0),
                    'failed': len(results.get('errors', []))
                }
                await self.complete_sync(mapped)
        
        return results
