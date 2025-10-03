"""
Integration Field Definition client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusIntegrationFieldDefinitionClient(GeniusBaseClient):
    """Client for accessing Genius CRM integration field definition data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'integration_field_definition'
    
    def get_integration_field_definitions(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch integration field definitions from Genius database"""
        
        # Base query with all available fields
        query = """
        SELECT 
            ifd.id,
            ifd.integration_id,
            ifd.label,
            ifd.key_name,
            ifd.is_user,
            ifd.is_division,
            ifd.hint,
            ifd.input_type
        FROM integration_field_definition ifd
        """
        
        # Add WHERE clause for incremental sync (definitions don't have timestamps, full sync only)
        # Add ordering and limit
        query += " ORDER BY ifd.id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing integration field definitions query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'integration_id',
            'label',
            'key_name',
            'is_user',
            'is_division',
            'hint',
            'input_type'
        ]
    
    def get_chunked_items(self, chunk_size: int = 10000, since: Optional[datetime] = None):
        """
        Generator that yields chunks of integration field definitions using cursor-based pagination
        
        Note: This table doesn't have timestamps, so 'since' parameter is ignored
        
        Args:
            chunk_size: Number of records per chunk
            since: Ignored for this table (no timestamp fields)
            
        Yields:
            Lists of integration field definition tuples in chunks
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
                ifd.id,
                ifd.integration_id,
                ifd.label,
                ifd.key_name,
                ifd.is_user,
                ifd.is_division,
                ifd.hint,
                ifd.input_type
            FROM integration_field_definition ifd
            WHERE ifd.id > %s
            ORDER BY ifd.id LIMIT %s
            """
            
            params = [last_id, chunk_size]
            
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
        query = "SELECT COUNT(*) FROM integration_field_definition"
        # No date filtering for this table since it has no timestamp fields
        
        logger.debug(f"Count query: {query}")
        result = self.execute_query(query)
        
        return result[0][0] if result else 0