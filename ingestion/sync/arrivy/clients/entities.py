"""
Arrivy Entities API Client

Handles entity-specific operations for Arrivy API.
Entities represent individual crew members across all divisions.
"""

from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging

from .base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyEntitiesClient(ArrivyBaseClient):
    """Client for Arrivy entities (crew members) API operations"""
    
    async def fetch_entities(self, last_sync: Optional[datetime] = None, 
                           page_size: int = 100) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch entities from Arrivy API with delta sync support
        
        Uses proper Arrivy API delta sync pattern:
        - from/to date range parameters for time-based filtering
        - order_by=CREATED for consistent chronological ordering
        - Efficient server-side filtering instead of client-side
        
        Args:
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page
            
        Yields:
            Batches of entity records
        """
        logger.info(f"Fetching entities with page_size={page_size}, last_sync={last_sync}")
        
        # Prepare API parameters for delta sync following Arrivy's recommended pattern
        api_kwargs = {}
        
        if last_sync:
            # Use from/to range with order_by=CREATED as recommended by Arrivy API
            from django.utils import timezone
            
            # From: last sync timestamp
            # To: current time to get all updates since last sync
            current_time = timezone.now()
            
            # Format timestamps for Arrivy API (ISO format with timezone)
            from_timestamp = last_sync.strftime("%Y-%m-%dT%H:%M:%S%z")
            to_timestamp = current_time.strftime("%Y-%m-%dT%H:%M:%S%z")
            
            # URL encode the + sign in timezone offset
            from_timestamp = from_timestamp.replace('+', '%2B')
            to_timestamp = to_timestamp.replace('+', '%2B')
            
            api_kwargs['from'] = from_timestamp
            api_kwargs['to'] = to_timestamp
            api_kwargs['order_by'] = 'CREATED'  # Ensures chronological order for reliable delta sync
            
            logger.info(f"Delta sync: from={from_timestamp}, to={to_timestamp}, order_by=CREATED")
        else:
            # For full sync, use order_by=CREATED for consistent ordering
            api_kwargs['order_by'] = 'CREATED'
            logger.info("Full sync: order_by=CREATED")
        
        async for batch in self.fetch_paginated_data(
            endpoint="entities",
            last_sync=None,  # Don't pass last_sync since we're using from/to parameters
            page_size=page_size,
            **api_kwargs
        ):
            logger.debug(f"Fetched batch of {len(batch)} entities")
            yield batch
    
    async def fetch_crew_members_from_divisions(self, last_sync: Optional[datetime] = None,
                                              page_size: int = 100) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch individual crew members from entities_data across all divisions
        
        This is a composite operation that fetches divisions and extracts individual crew members.
        Each crew member gets additional context (division_id, division_name).
        
        NOTE: Arrivy API does not support delta filtering for /api/crews endpoint.
        Client-side filtering is applied when last_sync is provided.
        
        Args:
            last_sync: Last sync timestamp for delta sync (client-side filtering)
            page_size: Records per page (applies to crew members, not divisions)
            
        Yields:
            Batches of crew member records with division context
        """
        logger.info(f"Fetching crew members from divisions with last_sync={last_sync}")
        
        # Note: API doesn't support delta filtering, so we get all records
        if last_sync:
            logger.warning("Arrivy API does not support delta filtering for crews. "
                         "Fetching all records and applying client-side filtering.")
        
        crew_members_batch = []
        filtered_count = 0
        total_count = 0
        
        # Get all divisions first - don't pass last_sync since API ignores it
        async for divisions_batch in self.fetch_paginated_data(
            endpoint="crews",  # Use crews endpoint for divisions
            last_sync=None,  # API ignores this parameter anyway
            page_size=200  # Use larger batch size for better performance (max 200 recommended)
        ):
            for division in divisions_batch:
                division_name = division.get('name', 'Unknown Division')
                division_id = division.get('id')
                entities_data = division.get('entities_data', [])
                
                if isinstance(entities_data, list):
                    for crew_member in entities_data:
                        total_count += 1
                        
                        # Apply client-side filtering if last_sync is provided
                        if last_sync and self._should_skip_record_by_date(crew_member, last_sync):
                            filtered_count += 1
                            continue
                        
                        # Add division context to each crew member
                        crew_member_with_context = crew_member.copy()
                        crew_member_with_context['division_id'] = division_id
                        crew_member_with_context['division_name'] = division_name
                        crew_members_batch.append(crew_member_with_context)
                        
                        # Yield batch when it reaches desired size
                        if len(crew_members_batch) >= page_size:
                            logger.debug(f"Yielding batch of {len(crew_members_batch)} crew members")
                            yield crew_members_batch
                            crew_members_batch = []
        
        # Yield any remaining crew members
        if crew_members_batch:
            logger.debug(f"Yielding final batch of {len(crew_members_batch)} crew members")
            yield crew_members_batch
        
        # Log filtering results
        if last_sync:
            logger.info(f"Client-side filtering: {filtered_count} of {total_count} records filtered out "
                       f"(keeping {total_count - filtered_count} records updated since {last_sync})")
    
    def _should_skip_record_by_date(self, record: Dict[str, Any], last_sync: datetime) -> bool:
        """
        Check if record should be skipped based on last_sync date (client-side filtering)
        
        Args:
            record: Crew member record
            last_sync: Minimum update timestamp
            
        Returns:
            True if record should be skipped (too old)
        """
        # Check various date fields that might indicate when the record was last updated
        date_fields = ['updated_time', 'joined_datetime', 'created_time', 'last_modified']
        
        for field_name in date_fields:
            if field_name in record and record[field_name]:
                try:
                    if isinstance(record[field_name], str):
                        # Parse ISO format datetime
                        record_date = datetime.fromisoformat(record[field_name].replace('Z', '+00:00'))
                    else:
                        record_date = record[field_name]
                    
                    # If record is newer than last_sync, don't skip it
                    if record_date >= last_sync:
                        return False
                        
                except (ValueError, TypeError) as e:
                    logger.debug(f"Could not parse date field {field_name} = {record[field_name]}: {e}")
                    continue
        
        # If no valid date found or all dates are older than last_sync, skip the record
        record_id = record.get('id', 'unknown')
        logger.debug(f"Skipping record {record_id} - no valid date field newer than {last_sync}")
        return True
    
    async def fetch_entity_by_id(self, entity_id: str) -> Dict[str, Any]:
        """
        Fetch a specific entity by ID
        
        Args:
            entity_id: Entity ID to fetch
            
        Returns:
            Entity data
        """
        logger.debug(f"Fetching entity by ID: {entity_id}")
        
        result = await self._make_request(f"entities/{entity_id}")
        return result.get('data', {})
    
    async def get_entities_count(self) -> int:
        """
        Get total count of entities without fetching all data
        
        Returns:
            Total entity count
        """
        result = await self._make_request("entities", {"page_size": 1, "page": 1})
        pagination = result.get('pagination')
        if pagination:
            return pagination.get('total_count', 0)
        return len(result.get('data', []))
