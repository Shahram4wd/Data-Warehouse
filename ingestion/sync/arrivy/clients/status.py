"""
Arrivy Status Client

Client for fetching status definitions from Arrivy API.
Handles status definitions using the working 'statuses' endpoint.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator

from .base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyStatusClient(ArrivyBaseClient):
    """Client for Arrivy status API"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
    
    async def fetch_statuses(
        self,
        page_size: int = 100,
        max_records: Optional[int] = None,
        include_inactive: bool = False
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch statuses from the working 'statuses' endpoint
        
        Args:
            page_size: Number of records per page (note: Arrivy ignores this parameter)
            max_records: Maximum total records to fetch
            include_inactive: Include inactive statuses
            
        Yields:
            Batches of status records
        """
        endpoint = "statuses"
        
        try:
            logger.info(f"Fetching statuses from '{endpoint}' endpoint")
            
            # Make the API call - statuses endpoint returns all records at once
            response = await self._make_request(endpoint)
            
            if not response:
                logger.warning(f"No data returned from {endpoint}")
                return
            
            # Handle both list and single record responses
            if isinstance(response, list):
                statuses = response
            elif isinstance(response, dict) and 'data' in response:
                statuses = response['data']
            elif isinstance(response, dict) and 'results' in response:
                statuses = response['results']
            else:
                # Assume the response itself is a list of statuses
                statuses = [response] if isinstance(response, dict) else []
            
            if not statuses:
                logger.warning("No statuses found in API response")
                return
            
            # Filter inactive statuses if requested
            if not include_inactive:
                statuses = [s for s in statuses if s.get('is_active', True)]
            
            logger.info(f"Found {len(statuses)} statuses")
            
            # Yield all statuses as a single batch (since the API returns all at once)
            if statuses:
                yield statuses
            
        except Exception as e:
            logger.error(f"Error fetching statuses from {endpoint}: {e}")
            raise
    
    async def fetch_status_definitions(
        self,
        page_size: int = 100,
        max_records: Optional[int] = None,
        status_type: str = 'all',
        include_inactive: bool = False
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch status definitions from Arrivy API
        
        NOTE: This endpoint appears to not be available in the current Arrivy API version.
        Returning empty results to maintain compatibility.
        
        Args:
            page_size: Number of records per page
            max_records: Maximum total records to fetch
            status_type: Type of statuses (all, task, crew, system)
            include_inactive: Include inactive status definitions
            
        Yields:
            Batches of status definition records (empty)
        """
        logger.warning("Task status definitions endpoint not available in current Arrivy API - returning empty results")
        # Return empty generator to avoid API errors while maintaining async generator contract
        return
        yield []  # This line will never execute due to return above
    
    async def fetch_workflow_definitions(
        self,
        page_size: int = 100,
        max_records: Optional[int] = None,
        workflow_type: str = 'all'
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch workflow definitions from Arrivy API
        
        NOTE: This endpoint appears to not be available in the current Arrivy API version.
        Returning empty results to maintain compatibility.
        
        Args:
            page_size: Number of records per page
            max_records: Maximum total records to fetch
            workflow_type: Type of workflows (all, task, crew, custom)
            
        Yields:
            Batches of workflow definition records (empty)
        """
        logger.warning("Workflow definitions endpoint not available in current Arrivy API - returning empty results")
        # Return empty generator to avoid API errors while maintaining async generator contract
        return
        yield []  # This line will never execute due to return above
    
    async def fetch_status_transitions(
        self,
        page_size: int = 100,
        max_records: Optional[int] = None,
        workflow_id: Optional[str] = None
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch status transition rules from Arrivy API
        
        NOTE: This endpoint appears to not be available in the current Arrivy API version.
        Returning empty results to maintain compatibility.
        
        Args:
            page_size: Number of records per page
            max_records: Maximum total records to fetch
            workflow_id: Filter by specific workflow ID
            
        Yields:
            Batches of status transition records (empty)
        """
        logger.warning("Status transitions endpoint not available in current Arrivy API - returning empty results")
        # Return empty generator to avoid API errors while maintaining async generator contract
        return
        yield []  # This line will never execute due to return above
    
    async def fetch_status_by_id(self, status_id: str) -> Optional[Dict]:
        """
        Fetch a specific status definition by ID
        
        Args:
            status_id: The status definition ID
            
        Returns:
            Status definition record or None if not found
        """
        endpoint = f"status_definitions/{status_id}"
        
        try:
            logger.info(f"Fetching status definition {status_id}")
            record = await self.get(endpoint)
            
            if record:
                record['type'] = 'status'
            
            return record
            
        except Exception as e:
            logger.error(f"Error fetching status definition {status_id}: {e}")
            return None
    
    async def fetch_workflow_by_id(self, workflow_id: str) -> Optional[Dict]:
        """
        Fetch a specific workflow definition by ID
        
        Args:
            workflow_id: The workflow definition ID
            
        Returns:
            Workflow definition record or None if not found
        """
        endpoint = f"workflow_definitions/{workflow_id}"
        
        try:
            logger.info(f"Fetching workflow definition {workflow_id}")
            record = await self.get(endpoint)
            
            if record:
                record['type'] = 'workflow'
            
            return record
            
        except Exception as e:
            logger.error(f"Error fetching workflow definition {workflow_id}: {e}")
            return None
    
    async def fetch_available_statuses_for_entity(
        self,
        entity_type: str,
        current_status: Optional[str] = None
    ) -> List[Dict]:
        """
        Fetch available status transitions for an entity
        
        Args:
            entity_type: The entity type (task, crew, etc.)
            current_status: Current status of the entity
            
        Returns:
            List of available status transitions
        """
        endpoint = f"entity_types/{entity_type}/available_statuses"
        params = {}
        
        if current_status:
            params["current_status"] = current_status
        
        try:
            logger.info(f"Fetching available statuses for {entity_type}")
            
            if params:
                response = await self.get(endpoint, params=params)
            else:
                response = await self.get(endpoint)
            
            # Ensure response is a list
            if not isinstance(response, list):
                response = []
            
            # Add type information to each status
            for status in response:
                status['type'] = 'available_status'
                status['entity_type'] = entity_type
            
            return response
            
        except Exception as e:
            logger.error(f"Error fetching available statuses for {entity_type}: {e}")
            return []
    
    async def fetch_status_history(
        self,
        entity_id: str,
        entity_type: str,
        page_size: int = 100
    ) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch status change history for a specific entity
        
        Args:
            entity_id: The entity ID
            entity_type: The entity type
            page_size: Number of records per page
            
        Yields:
            Batches of status history records
        """
        endpoint = f"entities/{entity_type}/{entity_id}/status_history"
        
        # Build additional parameters (not including page_size which is handled separately)
        additional_params = {}
        
        logger.info(f"Fetching status history for {entity_type}:{entity_id}")
        
        async for batch in self.fetch_paginated_data(endpoint=endpoint, last_sync=None, page_size=page_size, **additional_params):
            # Add entity context to records
            for record in batch:
                record['entity_id'] = entity_id
                record['entity_type'] = entity_type
                record['type'] = 'status_history'
            
            yield batch
    
    async def fetch_workflow_statistics(self) -> Dict[str, Any]:
        """
        Fetch workflow usage statistics
        
        Returns:
            Dictionary containing workflow statistics
        """
        endpoint = "workflow_statistics"
        
        try:
            logger.info("Fetching workflow statistics")
            stats = await self.get(endpoint)
            
            if not isinstance(stats, dict):
                stats = {}
            
            return stats
            
        except Exception as e:
            logger.error(f"Error fetching workflow statistics: {e}")
            return {}
    
    async def validate_status_transition(
        self,
        from_status: str,
        to_status: str,
        entity_type: str
    ) -> Dict[str, Any]:
        """
        Validate if a status transition is allowed
        
        Args:
            from_status: Current status
            to_status: Target status
            entity_type: Entity type
            
        Returns:
            Validation result with allowed flag and reasons
        """
        endpoint = "validate_transition"
        params = {
            "from_status": from_status,
            "to_status": to_status,
            "entity_type": entity_type
        }
        
        try:
            logger.info(f"Validating transition {from_status} -> {to_status} for {entity_type}")
            result = await self.get(endpoint, params=params)
            
            if not isinstance(result, dict):
                result = {"allowed": False, "reasons": ["Invalid response format"]}
            
            return result
            
        except Exception as e:
            logger.error(f"Error validating status transition: {e}")
            return {"allowed": False, "reasons": [str(e)]}
