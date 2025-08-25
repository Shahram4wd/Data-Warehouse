"""
Five9 Contacts Sync Engine
Orchestrates the synchronization of contact records from Five9
"""
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta
import logging
from django.db import transaction
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
        """Fetch contact data from Five9 in batches"""
        try:
            # Get all contact lists
            lists_info = await sync_to_async(self.client.get_contact_lists)()
            
            for list_info in lists_info:
                list_name = list_info.get('name', '')
                logger.info(f"Fetching contacts from list: {list_name}")
                
                # Fetch contacts from this list
                result = await sync_to_async(self.client.get_contact_records)(
                    list_name=list_name,
                    max_records=kwargs.get('max_records_per_list', Five9Config.MAX_BATCH_SIZE)
                )
                
                contacts, _ = result if result else (None, None)
                
                if contacts:
                    # Add list_name to each contact
                    for contact in contacts:
                        contact['list_name'] = list_name
                    
                    # Yield contacts in batches
                    for i in range(0, len(contacts), self.batch_size):
                        batch = contacts[i:i + self.batch_size]
                        yield batch
                        
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
        """Save contacts batch to database (sync method)"""
        created_count = 0
        updated_count = 0
        skipped_count = 0
        
        # Get valid Django model field names
        valid_fields = set(field.name for field in Five9Contact._meta.get_fields())
        
        with transaction.atomic():
            for contact_data in contacts_data:
                try:
                    # Filter contact_data to only include valid model fields
                    filtered_data = {
                        k: v for k, v in contact_data.items() 
                        if k in valid_fields
                    }
                    
                    # Ensure we have required fields for composite key lookup
                    number1 = filtered_data.get('number1')
                    list_name = filtered_data.get('list_name')
                    
                    if not number1 or not list_name:
                        logger.warning(f"Contact missing required fields (number1: {number1}, list_name: {list_name})")
                        skipped_count += 1
                        continue
                    
                    # Use number1 + list_name as composite primary key
                    contact, created = Five9Contact.objects.update_or_create(
                        number1=number1,
                        list_name=list_name,
                        defaults=filtered_data
                    )
                    
                    if created:
                        created_count += 1
                        logger.debug(f"Created contact: {number1} ({list_name})")
                    else:
                        updated_count += 1
                        logger.debug(f"Updated contact: {number1} ({list_name})")
                        
                except Exception as e:
                    logger.warning(f"Failed to save contact {contact_data.get('number1')}: {e}")
                    skipped_count += 1
        
        return {
            'created': created_count, 
            'updated': updated_count, 
            'skipped': skipped_count
        }
    
    async def cleanup(self) -> None:
        """Cleanup Five9 client resources"""
        if self.client:
            await sync_to_async(self.client.close_sessions)()
    
    # Legacy sync methods for backward compatibility
    def sync_data(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """Legacy sync method - wraps async sync process"""
        import asyncio
        return asyncio.run(self.run_sync_async(force_full=force_full, **kwargs))
    
    async def run_sync_async(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
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
            await self.start_sync(**kwargs)
            
            # Initialize client
            await self.initialize_client()
            
            # Process data in batches
            async for raw_batch in self.fetch_data(**kwargs):
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
                # complete_sync is already an async method in the base class
                await self.complete_sync(results)
        
        return results
