"""
Integration Field client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusIntegrationFieldClient(GeniusBaseClient):
    """Client for accessing Genius CRM integration field data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'integration_field'
    
    def get_integration_fields(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch integration fields from Genius database"""
        
        # Base query with all available fields
        query = """
        SELECT
            integration_field.id,
            integration_field.definition_id,
            integration_field.user_id,
            integration_field.division_id,
            integration_field.field_value,
            integration_field.created_at,
            integration_field.updated_at
        FROM integration_field
        """        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY if.id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing integration fields query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'definition_id',
            'user_id',
            'division_id',
            'field_value',
            'created_at',
            'updated_at'
        ]
    
    def get_chunked_items(self, chunk_size: int = 10000, since: Optional[datetime] = None):
        """
        Generator that yields chunks of integration fields using cursor-based pagination for better performance
        
        Args:
            chunk_size: Number of records per chunk
            since: Optional datetime to filter records updated after this time
            
        Yields:
            Lists of integration field tuples in chunks
        """
        last_id = 0
        total_fetched = 0
        max_iterations = 10000  # Safety limit to prevent infinite loops
        iterations = 0
        
        while iterations < max_iterations:
            iterations += 1
            
            # Build the cursor-based query
            query = """
            SELECT
                integration_field.id,
                integration_field.definition_id,
                integration_field.user_id,
                integration_field.division_id,
                integration_field.field_value,
                integration_field.created_at,
                integration_field.updated_at
            FROM integration_field
            WHERE integration_field.id > %s
            """
            
            # Add date filter if specified
            params = [last_id]
            if since:
                query += " AND integration_field.updated_at >= %s"
                params.append(since)
            
            # Add ordering and limit
            query += " ORDER BY integration_field.id LIMIT %s"
            params.append(chunk_size)
            
            logger.debug(f"Cursor-based query iteration {iterations}: {query} with params: {params}")
            
            # Execute query
            chunk = self.execute_query(query, params)
            
            if not chunk:
                logger.debug(f"No more data found at iteration {iterations}, ending pagination")
                break
            
            # Update cursor for next iteration
            last_id = chunk[-1][0]  # ID is first field
            total_fetched += len(chunk)
            
            logger.debug(f"Fetched chunk {iterations}: {len(chunk)} records (total: {total_fetched})")
            yield chunk
            
            # If we got fewer records than requested, we've reached the end
            if len(chunk) < chunk_size:
                logger.debug(f"Received partial chunk ({len(chunk)} < {chunk_size}), ending pagination")
                break
        
        if iterations >= max_iterations:
            logger.warning(f"Reached maximum iteration limit ({max_iterations}), stopping to prevent infinite loop")
        
        logger.info(f"Completed chunked fetch: {total_fetched} total records in {iterations} iterations")

    def count_records(self, since: Optional[datetime] = None) -> int:
        """Count total records matching criteria"""
        query = "SELECT COUNT(*) FROM integration_field"
        params = []
        
        if since:
            query += " WHERE updated_at >= %s"
            params.append(since)
        
        logger.debug(f"Count query: {query} with params: {params}")
        result = self.execute_query(query, params)
        
        return result[0][0] if result else 0