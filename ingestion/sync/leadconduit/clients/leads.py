"""
LeadConduit Leads Client

Specialized client for LeadConduit lead data retrieval following
sync_crm_guide architecture and optimization patterns.
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timezone, timedelta

from .base import LeadConduitBaseClient

logger = logging.getLogger(__name__)


class LeadConduitLeadsClient(LeadConduitBaseClient):
    """
    Specialized client for LeadConduit lead data with optimized retrieval
    
    Implements entity-specific logic for leads including:
    - Lead-specific API endpoints via events
    - Optimized data filtering
    - Batched processing for memory efficiency
    """
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.entity_type = "leads"
        logger.info("Initialized LeadConduit Leads client")
    
    def extract_flow_source_name(self, event: Dict[str, Any], field_type: str) -> str:
        """Extract flow or source name from event vars data"""
        vars_data = event.get('vars', {})
        if field_type in vars_data:
            field_data = vars_data[field_type]
            if isinstance(field_data, dict):
                return field_data.get('name', '')
            else:
                return str(field_data)
        return ''
    
    def parse_timestamp_to_utc(self, timestamp_value: Any) -> Optional[datetime]:
        """
        Parse timestamp value and ensure UTC timezone
        
        Following UTC-only approach for optimal performance
        """
        if not timestamp_value:
            return None
            
        try:
            if isinstance(timestamp_value, (int, float)):
                # Timestamp in milliseconds (LeadConduit format)
                return datetime.fromtimestamp(timestamp_value / 1000, tz=timezone.utc)
            elif isinstance(timestamp_value, str):
                # ISO format string
                if 'T' in timestamp_value:
                    if timestamp_value.endswith('Z'):
                        return datetime.fromisoformat(timestamp_value.replace('Z', '+00:00'))
                    else:
                        return datetime.fromisoformat(timestamp_value)
            elif isinstance(timestamp_value, datetime):
                # Ensure UTC timezone
                if timestamp_value.tzinfo is None:
                    return timestamp_value.replace(tzinfo=timezone.utc)
                else:
                    return timestamp_value.astimezone(timezone.utc)
                    
        except Exception as e:
            logger.warning(f"Failed to parse timestamp '{timestamp_value}': {e}")
            
        return None
    
    async def get_all_leads_utc(self, target_date_utc=None) -> List[Dict[str, Any]]:
        """
        Export ALL leads for a specific UTC date using optimized approach
        
        Adapted from the reference implementation's get_all_leads_utc function
        for high-performance data retrieval with UTC-only processing.
        """
        # If no date specified, use today in UTC
        if target_date_utc is None:
            target_date_utc = datetime.now(timezone.utc).date()
        
        logger.info(f"Getting ALL leads for UTC date: {target_date_utc} using optimized approach")
        
        # Create UTC date range - much simpler than timezone conversion!
        utc_start = datetime.combine(target_date_utc, datetime.min.time()).replace(tzinfo=timezone.utc)
        utc_end = datetime.combine(target_date_utc, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        logger.info(f"UTC range: {utc_start} to {utc_end}")
        
        # Format for API
        start_date = utc_start.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = utc_end.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"API query: {start_date} to {end_date}")
        
        # Get all events using ID-based pagination (much more efficient)
        async with self as client:
            all_events = await client.get_events_with_id_pagination_fast(start_date, end_date)
        
        if all_events is None:
            logger.error("Failed to retrieve events")
            return []
        
        total_events = len(all_events)
        logger.info(f"TOTAL: Retrieved {total_events} events using optimized approach")
        
        if not all_events:
            logger.info("No events found")
            return []
        
        # Remove duplicates based on event ID
        unique_events = {}
        for event in all_events:
            event_id = event.get('id')
            if event_id and event_id not in unique_events:
                unique_events[event_id] = event
        
        all_events = list(unique_events.values())
        dedupe_count = len(all_events)
        logger.info(f"After deduplication: {dedupe_count} unique events")
        
        # Show event type breakdown
        event_types = {}
        for event in all_events:
            event_type = event.get('type', 'unknown')
            event_types[event_type] = event_types.get(event_type, 0) + 1
        
        logger.info("Event type breakdown:")
        for event_type, count in sorted(event_types.items()):
            logger.info(f"  {event_type}: {count}")
        
        # Filter for source events (actual leads)
        source_events = [e for e in all_events if e.get('type') == 'source']
        
        if not source_events:
            logger.warning("No source events found - using all events")
            source_events = all_events
        
        logger.info(f"Using {len(source_events)} source events for processing")
        
        # Process events to extract leads and filter by UTC date
        leads_data = []
        seen_lead_ids = set()
        
        for event in source_events:
            # Extract timestamp - keep in UTC (no conversion needed!)
            event_timestamp = event.get('start_timestamp')
            if not event_timestamp:
                continue
                
            event_utc = datetime.fromtimestamp(event_timestamp / 1000, tz=timezone.utc)
            
            # Simple UTC date comparison - no timezone conversion needed!
            if event_utc.date() != target_date_utc:
                continue
            
            # Extract lead data from vars.lead
            vars_data = event.get('vars', {})
            lead_data = vars_data.get('lead', {})
            
            if not lead_data:
                continue
                
            lead_id = event.get('id', '')
            if not lead_id or lead_id in seen_lead_ids:
                continue
                
            seen_lead_ids.add(lead_id)
            
            # Format timestamp in UTC (simple and unambiguous)
            formatted_time = event_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
            
            # Extract outcome data
            outcome_state = event.get('outcome', '')
            outcome_reason = event.get('reason', '')
            outcome_combined = f"{outcome_state} {outcome_reason}".strip() if outcome_reason else outcome_state
            
            # Extract flow and source
            flow_name = self.extract_flow_source_name(event, 'flow')
            source_name = self.extract_flow_source_name(event, 'source')
            
            # Extract ALL data from the complete event
            try:
                lead_record = {}
                
                # Add basic event information
                lead_record['Lead ID'] = lead_id
                lead_record['Submitted UTC'] = formatted_time  # Clear UTC labeling
                lead_record['Event Timestamp'] = event_timestamp  # Raw timestamp for sorting
                lead_record['Outcome'] = outcome_combined
                lead_record['Reason'] = event.get('reason', '—')
                lead_record['Flow'] = flow_name
                lead_record['Source'] = source_name
                
                # Add all lead data fields (from vars.lead)
                if lead_data:
                    for field_name, field_value in lead_data.items():
                        clean_field_name = field_name.replace('_', ' ').title()
                        lead_record[clean_field_name] = self.extract_value(field_value, [field_name, 'value'])
                
                # Add all other vars data (excluding lead which we already processed)
                for var_name, var_value in vars_data.items():
                    if var_name != 'lead':
                        clean_var_name = f"Vars {var_name.replace('_', ' ').title()}"
                        if isinstance(var_value, dict):
                            if 'name' in var_value:
                                lead_record[clean_var_name] = var_value.get('name', '')
                            elif 'value' in var_value:
                                lead_record[clean_var_name] = var_value.get('value', '')
                            else:
                                lead_record[clean_var_name] = str(var_value)
                        else:
                            lead_record[clean_var_name] = str(var_value) if var_value is not None else ''
                
                leads_data.append(lead_record)
                
            except Exception as e:
                logger.warning(f"Error processing lead {lead_id}: {e}")
                continue
        
        final_count = len(leads_data)
        logger.info(f"Processed {final_count} unique leads for UTC date {target_date_utc}")
        
        return leads_data

    async def get_leads_in_batches_utc(self, target_date_utc=None, batch_size=100) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """
        Get leads for a specific UTC date in batches for memory-efficient processing
        
        This method processes events in pages and yields batches of leads as soon as
        enough are accumulated, rather than loading all events into memory first.
        
        Args:
            target_date_utc: The target date in UTC
            batch_size: Number of leads to accumulate before yielding a batch
            
        Yields:
            List of lead dictionaries in batches
        """
        # If no date specified, use today in UTC
        if target_date_utc is None:
            target_date_utc = datetime.now(timezone.utc).date()
        
        logger.info(f"Getting leads in batches for UTC date: {target_date_utc} (batch_size={batch_size})")
        
        # Create UTC date range
        utc_start = datetime.combine(target_date_utc, datetime.min.time()).replace(tzinfo=timezone.utc)
        utc_end = datetime.combine(target_date_utc, datetime.max.time()).replace(tzinfo=timezone.utc)
        
        # Format for API
        start_date = utc_start.strftime('%Y-%m-%dT%H:%M:%SZ')
        end_date = utc_end.strftime('%Y-%m-%dT%H:%M:%SZ')
        
        logger.info(f"API query: {start_date} to {end_date}")
        
        # Process events in pages and accumulate leads
        leads_batch = []
        seen_lead_ids = set()
        total_events_processed = 0
        total_leads_yielded = 0
        
        async with self as client:
            # Get paginated events
            all_events = []
            after_id = None
            page = 0
            url = f"{client.base_url}/events"
            
            # Headers exactly like reference
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json'
            }
            
            while True:
                page += 1
                params = {
                    'start': start_date,
                    'end': end_date,
                    'limit': 1000,
                    'sort': 'asc'
                }
                
                if after_id:
                    params['after_id'] = after_id
                
                try:
                    # Apply rate limiting
                    await client._apply_rate_limit()
                    
                    # Make async request
                    async with client.session.get(url, params=params) as response:
                        if response.status != 200:
                            logger.error(f"API request failed with status {response.status}")
                            return
                        
                        events_page = await response.json()
                    
                    if not events_page:
                        logger.info(f"Page {page}: No more events - pagination complete")
                        break
                    
                    page_count = len(events_page)
                    total_events_processed += page_count
                    logger.info(f"Page {page}: Retrieved {page_count} events (total so far: {total_events_processed})")
                    
                    # Process events from this page immediately
                    for event in events_page:
                        # Only process source events (actual leads)
                        if event.get('type') != 'source':
                            continue
                            
                        # Extract timestamp and check date
                        event_timestamp = event.get('start_timestamp')
                        if not event_timestamp:
                            continue
                            
                        event_utc = datetime.fromtimestamp(event_timestamp / 1000, tz=timezone.utc)
                        if event_utc.date() != target_date_utc:
                            continue
                        
                        # Extract lead data
                        vars_data = event.get('vars', {})
                        lead_data = vars_data.get('lead', {})
                        
                        if not lead_data:
                            continue
                            
                        lead_id = event.get('id', '')
                        if not lead_id or lead_id in seen_lead_ids:
                            continue
                            
                        seen_lead_ids.add(lead_id)
                        
                        # Build lead record (same logic as original method)
                        try:
                            formatted_time = event_utc.strftime('%Y-%m-%d %H:%M:%S UTC')
                            outcome_state = event.get('outcome', '')
                            outcome_reason = event.get('reason', '')
                            outcome_combined = f"{outcome_state} {outcome_reason}".strip() if outcome_reason else outcome_state
                            flow_name = self.extract_flow_source_name(event, 'flow')
                            source_name = self.extract_flow_source_name(event, 'source')
                            
                            lead_record = {}
                            lead_record['Lead ID'] = lead_id
                            lead_record['Submitted UTC'] = formatted_time
                            lead_record['Event Timestamp'] = event_timestamp
                            lead_record['Outcome'] = outcome_combined
                            lead_record['Reason'] = event.get('reason', '—')
                            lead_record['Flow'] = flow_name
                            lead_record['Source'] = source_name
                            
                            # Add all lead data fields
                            if lead_data:
                                for field_name, field_value in lead_data.items():
                                    clean_field_name = field_name.replace('_', ' ').title()
                                    lead_record[clean_field_name] = self.extract_value(field_value, [field_name, 'value'])
                            
                            # Add all other vars data
                            for var_name, var_value in vars_data.items():
                                if var_name != 'lead':
                                    clean_var_name = f"Vars {var_name.replace('_', ' ').title()}"
                                    if isinstance(var_value, dict):
                                        if 'name' in var_value:
                                            lead_record[clean_var_name] = var_value.get('name', '')
                                        elif 'value' in var_value:
                                            lead_record[clean_var_name] = var_value.get('value', '')
                                        else:
                                            lead_record[clean_var_name] = str(var_value)
                                    else:
                                        lead_record[clean_var_name] = str(var_value) if var_value is not None else ''
                            
                            leads_batch.append(lead_record)
                            
                            # Yield batch when we have enough leads
                            if len(leads_batch) >= batch_size:
                                total_leads_yielded += len(leads_batch)
                                logger.info(f"Yielding batch of {len(leads_batch)} leads (total yielded: {total_leads_yielded})")
                                yield leads_batch
                                leads_batch = []
                        
                        except Exception as e:
                            logger.warning(f"Error processing lead {lead_id}: {e}")
                            continue
                    
                    # Set up for next page
                    if page_count < 1000:  # Last page
                        break
                    
                    # Get last event ID for next page
                    if events_page:
                        after_id = events_page[-1].get('id')
                        if not after_id:
                            logger.warning("No ID found in last event - stopping pagination")
                            break
                
                except Exception as e:
                    logger.error(f"Error fetching events page {page}: {e}")
                    break
        
        # Yield any remaining leads in the final batch
        if leads_batch:
            total_leads_yielded += len(leads_batch)
            logger.info(f"Yielding final batch of {len(leads_batch)} leads (total yielded: {total_leads_yielded})")
            yield leads_batch
        
        logger.info(f"Completed batch processing: {total_events_processed} events processed, {total_leads_yielded} leads yielded")
