"""
Arrivy Tasks API Client

Handles task-specific operations for Arrivy API.
Tasks represent work orders, appointments, and bookings.
"""

from typing import Dict, List, Optional, AsyncGenerator, Any
from datetime import datetime
import logging

from .base import ArrivyBaseClient

logger = logging.getLogger(__name__)

class ArrivyTasksClient(ArrivyBaseClient):
    """Client for Arrivy tasks/bookings API operations"""
    
    async def fetch_tasks(self, last_sync: Optional[datetime] = None,
                         start_date: Optional[datetime] = None,
                         end_date: Optional[datetime] = None,
                         page_size: int = 100,
                         max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch tasks from Arrivy API with delta sync support
        
        Uses Arrivy's 'from' and 'to' parameters for date filtering and proper order_by handling.
        API Example: https://app.arrivy.com/api/tasks?from=2025-09-22T00:00:00%2B05:00&to=2025-09-26T23:59:59%2B05:00&items_per_page=100&page=1&unscheduled=false&order_by=CREATED
        
        Args:
            last_sync: Last sync timestamp for delta sync (uses as 'from' parameter)
            start_date: Filter tasks from this date (overrides last_sync if provided)
            end_date: Filter tasks until this date
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of task records
        """
        # Determine date range for delta sync
        from_date = start_date or last_sync
        to_date = end_date
        
        logger.info(f"Fetching tasks with page_size={page_size}, from_date={from_date}, to_date={to_date}")
        
        params = {}
        
        # Use Arrivy's 'from' and 'to' parameters for date filtering
        if from_date:
            # Format datetime in the format expected by Arrivy API (ISO with timezone)
            params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%S%z")
            if not params["from"].endswith('+00:00') and not params["from"].endswith('Z'):
                # Add UTC timezone if not present
                params["from"] = from_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        if to_date:
            params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%S%z")
            if not params["to"].endswith('+00:00') and not params["to"].endswith('Z'):
                # Add UTC timezone if not present  
                params["to"] = to_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        # Set additional parameters for proper task filtering
        params["unscheduled"] = "false"  # Focus on scheduled tasks as per user example
        params["order_by"] = "CREATED"   # Use CREATED ordering as suggested by user
        params["items_per_page"] = page_size
        
        records_fetched = 0
        
        # Pass the properly formatted parameters to the paginated data fetcher
        async for batch in self.fetch_paginated_data(
            endpoint="tasks",  # Use tasks endpoint for tasks data
            last_sync=None,    # Don't use last_sync here since we're using 'from'/'to' params
            page_size=page_size,
            **params
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
            
            # Trim batch if it would exceed max_records
            if max_records and records_fetched + len(batch) > max_records:
                remaining = max_records - records_fetched
                batch = batch[:remaining]
            
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} tasks (total: {records_fetched})")
            yield batch
    
    async def fetch_bookings(self, last_sync: Optional[datetime] = None,
                            page_size: int = 100, max_records: Optional[int] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch bookings from Arrivy API (alias for fetch_tasks using bookings endpoint)
        
        Args:
            last_sync: Last sync timestamp for delta sync
            page_size: Records per page
            max_records: Maximum records to fetch (optional)
            
        Yields:
            Batches of booking records
        """
        logger.info(f"Fetching bookings with page_size={page_size}, last_sync={last_sync}")
        
        records_fetched = 0
        
        async for batch in self.fetch_paginated_data(
            endpoint="bookings",
            last_sync=last_sync,
            page_size=page_size
        ):
            # Check max_records limit
            if max_records and records_fetched >= max_records:
                logger.info(f"Reached max_records limit of {max_records}")
                break
            
            # Trim batch if it would exceed max_records
            if max_records and records_fetched + len(batch) > max_records:
                remaining = max_records - records_fetched
                batch = batch[:remaining]
            
            records_fetched += len(batch)
            logger.debug(f"Fetched batch of {len(batch)} bookings (total: {records_fetched})")
            yield batch
    
    async def fetch_task_by_id(self, task_id: str) -> Dict[str, Any]:
        """
        Fetch a specific task by ID
        
        Args:
            task_id: Task ID to fetch
            
        Returns:
            Task data
        """
        logger.debug(f"Fetching task by ID: {task_id}")
        
        # Use tasks endpoint for individual task lookup
        result = await self._make_request(f"tasks/{task_id}")
        return result.get('data', {})
    
    async def get_tasks_count(self, start_date: Optional[datetime] = None,
                            end_date: Optional[datetime] = None) -> int:
        """
        Get total count of tasks without fetching all data
        
        Args:
            start_date: Filter tasks from this date
            end_date: Filter tasks until this date
            
        Returns:
            Total task count
        """
        params = {"page_size": 1, "page": 1, "unscheduled": "false"}
        
        # Use Arrivy's 'from' and 'to' parameters for date filtering
        if start_date:
            params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S%z")
            if not params["from"].endswith('+00:00') and not params["from"].endswith('Z'):
                params["from"] = start_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        if end_date:
            params["to"] = end_date.strftime("%Y-%m-%dT%H:%M:%S%z")
            if not params["to"].endswith('+00:00') and not params["to"].endswith('Z'):
                params["to"] = end_date.strftime("%Y-%m-%dT%H:%M:%S+00:00")
        
        result = await self._make_request("tasks", params)
        pagination = result.get('pagination')
        if pagination:
            return pagination.get('total_count', 0)
        return len(result.get('data', []))
    
    async def fetch_task_statuses(self) -> List[Dict[str, Any]]:
        """
        Fetch available task statuses from Arrivy API
        
        Returns:
            List of task status definitions
        """
        logger.info("Fetching task statuses")
        
        # Try different possible endpoints for task statuses
        possible_endpoints = [
            "task-statuses",
            "task_statuses", 
            "statuses",
            "taskstatuses"
        ]
        
        for endpoint in possible_endpoints:
            try:
                result = await self._make_request(endpoint)
                data = result.get('data', [])
                if data:
                    logger.debug(f"Found task statuses using endpoint: {endpoint}")
                    return data
            except Exception as e:
                logger.debug(f"Endpoint {endpoint} failed: {str(e)}")
                continue
        
        logger.warning("No valid task statuses endpoint found")
        return []
