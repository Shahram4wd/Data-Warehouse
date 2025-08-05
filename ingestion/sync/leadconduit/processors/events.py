"""
LeadConduit Events Processor

Data processing and validation for LeadConduit events following
sync_crm_guide.md architecture.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from django.db import transaction
from asgiref.sync import sync_to_async

from ingestion.models.leadconduit import LeadConduit_Event

logger = logging.getLogger(__name__)


class LeadConduitEventsProcessor:
    """
    Processor for LeadConduit event data
    
    Handles data transformation, validation, and storage following
    sync_crm_guide patterns for data processing.
    """
    
    def __init__(self):
        self.entity_type = "events"
        logger.info("Initialized LeadConduit Events processor")
    
    async def process_batch(self, events_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of LeadConduit events
        
        Args:
            events_batch: List of processed event records
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing batch of {len(events_batch)} events")
        
        result = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            # Use sync_to_async wrapper for Django transaction
            @sync_to_async
            def process_batch_sync():
                with transaction.atomic():
                    batch_results = []
                    for event_data in events_batch:
                        try:
                            # Process single event synchronously
                            process_result = self.process_single_event_sync(event_data)
                            
                            result['processed'] += 1
                            if process_result['created']:
                                result['created'] += 1
                            elif process_result['updated']:
                                result['updated'] += 1
                                
                        except Exception as e:
                            logger.error(f"Failed to process event {event_data.get('event_id')}: {e}")
                            result['failed'] += 1
                            result['errors'].append({
                                'event_id': event_data.get('event_id'),
                                'error': str(e)
                            })
                    
                    return result
            
            # Execute the batch processing
            result = await process_batch_sync()
            
            logger.info(f"Batch processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            result['failed'] = len(events_batch)
            result['errors'].append({'batch_error': str(e)})
            return result
    
    def process_single_event_sync(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single event record (sync version)
        
        Args:
            event_data: Processed event data from client
            
        Returns:
            Dict with processing result
        """
        event_id = event_data.get('event_id')
        
        if not event_id:
            raise ValueError("Event ID is required")
        
        # Check if event already exists
        try:
            existing_event = LeadConduit_Event.objects.filter(event_id=event_id).first()
        except Exception as e:
            logger.error(f"Database query failed for event {event_id}: {e}")
            raise
        
        if existing_event:
            # Update existing event
            updated = self.update_event_sync(existing_event, event_data)
            return {'created': False, 'updated': updated}
        else:
            # Create new event
            self.create_event_sync(event_data)
            return {'created': True, 'updated': False}
    
    async def process_single_event(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single event record
        
        Args:
            event_data: Processed event data from client
            
        Returns:
            Dict with processing result
        """
        event_id = event_data.get('event_id')
        
        if not event_id:
            raise ValueError("Event ID is required")
        
        # Check if event already exists
        existing_event = await LeadConduit_Event.objects.filter(
            event_id=event_id
        ).afirst()
        
        if existing_event:
            # Update existing event
            updated = await self.update_event(existing_event, event_data)
            return {'created': False, 'updated': updated}
        else:
            # Create new event
            await self.create_event(event_data)
            return {'created': True, 'updated': False}
    
    def create_event_sync(self, event_data: Dict[str, Any]) -> LeadConduit_Event:
        """Create new LeadConduit event record (sync version)"""
        
        validated_data = self.validate_event_data(event_data)
        
        event = LeadConduit_Event.objects.create(
            event_id=validated_data['event_id'],
            event_type=validated_data.get('event_type', ''),
            start_timestamp=validated_data.get('start_timestamp'),
            end_timestamp=validated_data.get('end_timestamp'),
            submitted_utc=validated_data.get('submitted_utc'),
            outcome=validated_data.get('outcome', ''),
            outcome_combined=validated_data.get('outcome_combined', ''),
            reason=validated_data.get('reason', ''),
            flow_name=validated_data.get('flow_name', ''),
            source_name=validated_data.get('source_name', ''),
            raw_data=validated_data.get('raw_data', {}),
            processed_data=validated_data.get('processed_data', {})
        )
        
        logger.debug(f"Created event {event.event_id}")
        return event
    
    def update_event_sync(self, event: LeadConduit_Event, event_data: Dict[str, Any]) -> bool:
        """Update existing LeadConduit event record (sync version)"""
        
        validated_data = self.validate_event_data(event_data)
        updated = False
        
        # Update fields if different
        update_fields = [
            'event_type', 'start_timestamp', 'end_timestamp', 'submitted_utc',
            'outcome', 'outcome_combined', 'reason', 'flow_name', 'source_name',
            'raw_data', 'processed_data'
        ]
        
        for field in update_fields:
            new_value = validated_data.get(field)
            if new_value is not None and getattr(event, field) != new_value:
                setattr(event, field, new_value)
                updated = True
        
        if updated:
            event.updated_at = datetime.now(timezone.utc)
            event.save()
            logger.debug(f"Updated event {event.event_id}")
        
        return updated
    
    async def create_event(self, event_data: Dict[str, Any]) -> LeadConduit_Event:
        """Create new LeadConduit event record"""
        
        # Validate and prepare data
        validated_data = self.validate_event_data(event_data)
        
        # Create event record
        event = LeadConduit_Event(
            event_id=validated_data['event_id'],
            event_type=validated_data['event_type'],
            submitted_utc=validated_data['submitted_utc'],
            start_timestamp=validated_data.get('start_timestamp'),
            end_timestamp=validated_data.get('end_timestamp'),
            outcome=validated_data.get('outcome', ''),
            reason=validated_data.get('reason', ''),
            outcome_combined=validated_data.get('outcome_combined', ''),
            flow_name=validated_data.get('flow_name', ''),
            source_name=validated_data.get('source_name', ''),
            host=validated_data.get('host', ''),
            wait_ms=validated_data.get('wait_ms'),
            overhead_ms=validated_data.get('overhead_ms'),
            lag_ms=validated_data.get('lag_ms'),
            handler_version=validated_data.get('handler_version', ''),
            cap_reached=validated_data.get('cap_reached', False),
            ping_limit_reached=validated_data.get('ping_limit_reached', False),
            expires_at=validated_data.get('expires_at'),
            step_count=validated_data.get('step_count'),
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            email=validated_data.get('email', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            city=validated_data.get('city', ''),
            state=validated_data.get('state', ''),
            zip_code=validated_data.get('zip_code', ''),
            raw_data=validated_data.get('raw_data', {}),
            vars_data=validated_data.get('vars_data', {}),
            appended_data=validated_data.get('appended_data', {})
        )
        
        await event.asave()
        logger.debug(f"Created event {event.event_id}")
        return event
    
    async def update_event(self, 
                          existing_event: LeadConduit_Event, 
                          event_data: Dict[str, Any]) -> bool:
        """
        Update existing event record
        
        Returns:
            bool: True if event was updated, False if no changes
        """
        validated_data = self.validate_event_data(event_data)
        
        # Track if any changes were made
        updated = False
        
        # Update fields that might have changed
        update_fields = [
            'event_type', 'submitted_utc', 'start_timestamp', 'end_timestamp',
            'outcome', 'reason', 'outcome_combined', 'flow_name', 'source_name',
            'host', 'wait_ms', 'overhead_ms', 'lag_ms', 'handler_version',
            'cap_reached', 'ping_limit_reached', 'expires_at', 'step_count',
            'first_name', 'last_name', 'email', 'phone', 'address', 'city',
            'state', 'zip_code', 'raw_data', 'vars_data', 'appended_data'
        ]
        
        for field in update_fields:
            new_value = validated_data.get(field)
            current_value = getattr(existing_event, field)
            
            # Handle different data types
            if field in ['raw_data', 'vars_data', 'appended_data']:
                # JSON fields - compare as dicts
                if new_value != current_value:
                    setattr(existing_event, field, new_value or {})
                    updated = True
            elif field in ['cap_reached', 'ping_limit_reached']:
                # Boolean fields
                if new_value is not None and new_value != current_value:
                    setattr(existing_event, field, new_value)
                    updated = True
            elif field in ['wait_ms', 'overhead_ms', 'lag_ms', 'step_count']:
                # Integer fields
                if new_value is not None and new_value != current_value:
                    setattr(existing_event, field, new_value)
                    updated = True
            else:
                # String and datetime fields
                if new_value and new_value != current_value:
                    setattr(existing_event, field, new_value)
                    updated = True
        
        if updated:
            await existing_event.asave()
            logger.debug(f"Updated event {existing_event.event_id}")
        
        return updated
    
    def validate_event_data(self, event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean event data
        
        Args:
            event_data: Raw event data
            
        Returns:
            Dict: Validated and cleaned data
            
        Raises:
            ValueError: If validation fails
        """
        if not event_data.get('event_id'):
            raise ValueError("event_id is required")
        
        # Ensure submitted_utc is a datetime object
        submitted_utc = event_data.get('submitted_utc')
        if submitted_utc and not isinstance(submitted_utc, datetime):
            raise ValueError("submitted_utc must be a datetime object")
        
        # Validate event_type
        event_type = event_data.get('event_type', '')
        if not event_type:
            logger.warning(f"Event {event_data['event_id']} has no event_type")
        
        # Clean string fields
        string_fields = [
            'event_id', 'event_type', 'outcome', 'reason', 'outcome_combined',
            'flow_name', 'source_name', 'host', 'handler_version',
            'first_name', 'last_name', 'email', 'phone', 'address', 'city',
            'state', 'zip_code'
        ]
        
        validated_data = {}
        for field in string_fields:
            value = event_data.get(field, '')
            if value is None:
                value = ''
            validated_data[field] = str(value).strip()
        
        # Copy other fields as-is
        other_fields = [
            'submitted_utc', 'start_timestamp', 'end_timestamp', 'wait_ms',
            'overhead_ms', 'lag_ms', 'step_count', 'cap_reached',
            'ping_limit_reached', 'expires_at', 'raw_data', 'vars_data',
            'appended_data'
        ]
        
        for field in other_fields:
            if field in event_data:
                validated_data[field] = event_data[field]
        
        return validated_data
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processor_type': 'LeadConduitEventsProcessor',
            'entity_type': self.entity_type,
            'initialized_at': getattr(self, '_initialized_at', None)
        }
