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


class ContactsSyncEngine(BaseFive9SyncEngine):
    """Sync engine for Five9 contact records"""
    
    def __init__(self, **kwargs):
        super().__init__(source_name="Five9_Contacts", **kwargs)
        self.processor = ContactsProcessor()
        self.sync_type = "contacts"
    
    def create_client(self) -> ContactsClient:
        """Create Five9 Contacts API client"""
        return ContactsClient()
    
    def sync_data(self, force_full: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Sync Five9 contact data
        
        Args:
            force_full: Force full sync instead of delta
            **kwargs: Additional sync parameters
            
        Returns:
            Dictionary with sync results
        """
        # Determine sync strategy
        is_delta_sync = self.should_perform_delta_sync(self.sync_type, force_full)
        operation = 'delta_sync' if is_delta_sync else 'full_sync'
        
        # Create sync history record
        sync_history = self.create_sync_history(
            sync_type=self.sync_type,
            operation=operation,
            is_delta=is_delta_sync
        )
        
        try:
            if is_delta_sync:
                return self._perform_delta_sync(sync_history, **kwargs)
            else:
                return self._perform_full_sync(sync_history, **kwargs)
                
        except Exception as e:
            self.handle_sync_error(sync_history, e, "sync_data")
            raise
    
    def _perform_full_sync(self, sync_history: SyncHistory, **kwargs) -> Dict[str, Any]:
        """
        Perform full sync of all Five9 contact lists
        
        Args:
            sync_history: Sync history record
            **kwargs: Additional parameters
            
        Returns:
            Sync results dictionary
        """
        logger.info("Starting full sync of Five9 contacts")
        
        total_processed = 0
        total_errors = 0
        lists_processed = 0
        
        try:
            # Get all contact records from all lists
            max_records = kwargs.get('max_records_per_list', 1000)
            all_records = self.client.get_all_contact_records(max_records)
            
            if not all_records:
                logger.warning("No contact records retrieved from Five9")
                self.update_sync_history(
                    sync_history, 'SUCCESS', 0, 0, 
                    message="No records found"
                )
                return {
                    'success': True,
                    'records_processed': 0,
                    'lists_processed': 0,
                    'errors': 0
                }
            
            # Process each list
            for list_name, raw_records in all_records.items():
                try:
                    logger.info(f"Processing list: {list_name} ({len(raw_records)} records)")
                    
                    # Process records in batches
                    list_processed = 0
                    list_errors = 0
                    
                    for i in range(0, len(raw_records), self.batch_size):
                        batch = raw_records[i:i + self.batch_size]
                        batch_processed, batch_errors = self._process_contact_batch(
                            batch, list_name, sync_history
                        )
                        list_processed += batch_processed
                        list_errors += batch_errors
                    
                    logger.info(f"Completed list {list_name}: {list_processed} processed, {list_errors} errors")
                    total_processed += list_processed
                    total_errors += list_errors
                    lists_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing list {list_name}: {e}")
                    total_errors += len(raw_records)
                    continue
            
            # Update final sync status
            status = 'SUCCESS' if total_errors == 0 else 'PARTIAL'
            self.update_sync_history(
                sync_history, status, total_processed, total_errors,
                lists_processed=lists_processed
            )
            
            return {
                'success': True,
                'records_processed': total_processed,
                'lists_processed': lists_processed,
                'errors': total_errors
            }
            
        except Exception as e:
            self.handle_sync_error(sync_history, e, "_perform_full_sync")
            raise
    
    def _perform_delta_sync(self, sync_history: SyncHistory, **kwargs) -> Dict[str, Any]:
        """
        Perform delta sync of Five9 contacts (updated since last sync)
        
        Args:
            sync_history: Sync history record
            **kwargs: Additional parameters
            
        Returns:
            Sync results dictionary
        """
        logger.info("Starting delta sync of Five9 contacts")
        
        # Get last sync time
        last_sync_time = self.get_last_sync_time(self.sync_type)
        if not last_sync_time:
            logger.warning("No last sync time found, falling back to full sync")
            return self._perform_full_sync(sync_history, **kwargs)
        
        # For delta sync, we'll sync all lists but only update records that have changed
        # Five9 doesn't have native delta API, so we'll compare sys_last_disposition_time
        
        logger.info(f"Delta sync since: {last_sync_time}")
        
        total_processed = 0
        total_errors = 0
        lists_processed = 0
        
        try:
            # Get all contact records (Five9 doesn't support delta queries)
            max_records = kwargs.get('max_records_per_list', 1000)
            all_records = self.client.get_all_contact_records(max_records)
            
            if not all_records:
                logger.warning("No contact records retrieved from Five9")
                self.update_sync_history(
                    sync_history, 'SUCCESS', 0, 0, 
                    message="No records found"
                )
                return {
                    'success': True,
                    'records_processed': 0,
                    'lists_processed': 0,
                    'errors': 0
                }
            
            # Process each list, filtering for changed records
            for list_name, raw_records in all_records.items():
                try:
                    # Filter records changed since last sync
                    changed_records = self._filter_changed_records(raw_records, last_sync_time)
                    
                    if not changed_records:
                        logger.info(f"No changed records in list: {list_name}")
                        continue
                    
                    logger.info(f"Processing {len(changed_records)} changed records from {list_name}")
                    
                    # Process changed records in batches
                    list_processed = 0
                    list_errors = 0
                    
                    for i in range(0, len(changed_records), self.batch_size):
                        batch = changed_records[i:i + self.batch_size]
                        batch_processed, batch_errors = self._process_contact_batch(
                            batch, list_name, sync_history
                        )
                        list_processed += batch_processed
                        list_errors += batch_errors
                    
                    logger.info(f"Completed list {list_name}: {list_processed} processed, {list_errors} errors")
                    total_processed += list_processed
                    total_errors += list_errors
                    lists_processed += 1
                    
                except Exception as e:
                    logger.error(f"Error processing list {list_name}: {e}")
                    total_errors += len(raw_records)
                    continue
            
            # Update final sync status
            status = 'SUCCESS' if total_errors == 0 else 'PARTIAL'
            self.update_sync_history(
                sync_history, status, total_processed, total_errors,
                lists_processed=lists_processed,
                since=last_sync_time.isoformat()
            )
            
            return {
                'success': True,
                'records_processed': total_processed,
                'lists_processed': lists_processed,
                'errors': total_errors
            }
            
        except Exception as e:
            self.handle_sync_error(sync_history, e, "_perform_delta_sync")
            raise
    
    def _filter_changed_records(self, raw_records: List[Dict], since: datetime) -> List[Dict]:
        """
        Filter records that have changed since the given datetime
        
        Args:
            raw_records: List of raw contact records
            since: DateTime to filter from
            
        Returns:
            List of changed records
        """
        changed_records = []
        
        for record in raw_records:
            # Check sys_last_disposition_time field
            last_disposition_str = record.get('sys_last_disposition_time')
            if last_disposition_str:
                try:
                    # Process the datetime field
                    last_disposition = self.processor.process_field(
                        'sys_last_disposition_time', 
                        last_disposition_str, 
                        'DATE_TIME'
                    )
                    
                    if last_disposition and last_disposition > since:
                        changed_records.append(record)
                except Exception as e:
                    logger.debug(f"Could not parse disposition time, including record: {e}")
                    changed_records.append(record)
            else:
                # If no timestamp, include the record to be safe
                changed_records.append(record)
        
        return changed_records
    
    def _process_contact_batch(self, raw_records: List[Dict], list_name: str, 
                              sync_history: SyncHistory) -> tuple[int, int]:
        """
        Process a batch of contact records
        
        Args:
            raw_records: List of raw contact records
            list_name: Name of the source list
            sync_history: Current sync history record
            
        Returns:
            Tuple of (processed_count, error_count)
        """
        try:
            # Process records
            processed_records = self.processor.process_contact_batch(raw_records, list_name)
            
            if not processed_records:
                logger.warning(f"No valid records in batch from {list_name}")
                return 0, len(raw_records)
            
            # Deduplicate within batch
            deduplicated_records = self.processor.deduplicate_records(processed_records)
            
            # Save to database
            saved_count = self._save_contact_records(deduplicated_records)
            
            logger.debug(f"Batch processed: {saved_count}/{len(raw_records)} saved")
            return saved_count, len(raw_records) - saved_count
            
        except Exception as e:
            logger.error(f"Error processing contact batch from {list_name}: {e}")
            return 0, len(raw_records)
    
    def _save_contact_records(self, processed_records: List[Dict[str, Any]]) -> int:
        """
        Save processed contact records to database
        
        Args:
            processed_records: List of processed contact records
            
        Returns:
            Number of records saved
        """
        if not processed_records:
            return 0
        
        saved_count = 0
        
        try:
            with transaction.atomic():
                for record in processed_records:
                    try:
                        # Use update_or_create to handle duplicates
                        contact, created = Five9Contact.objects.update_or_create(
                            contactID=record.get('contactID'),
                            list_name=record.get('list_name'),
                            defaults=record
                        )
                        saved_count += 1
                        
                        if created:
                            logger.debug(f"Created new contact: {contact.contactID}")
                        else:
                            logger.debug(f"Updated existing contact: {contact.contactID}")
                            
                    except Exception as e:
                        logger.error(f"Error saving individual contact: {e}")
                        continue
            
            logger.info(f"Successfully saved {saved_count} contact records")
            return saved_count
            
        except Exception as e:
            logger.error(f"Database error saving contacts: {e}")
            return 0
