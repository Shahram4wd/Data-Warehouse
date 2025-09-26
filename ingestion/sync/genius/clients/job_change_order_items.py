"""
Job Change Order Items client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderItemClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order item data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order_item'
    
    def get_job_change_order_items(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change order items from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT *
        FROM job_change_order_item jcoi
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY jcoi.Id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'change_order_id',
            'description', 
            'amount',
            'created_at',
            'updated_at'
        ]

    def get_job_change_order_items_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of job change order items to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields  
            query = """
            SELECT 
                jcoi.id,
                jcoi.change_order_id,
                jcoi.description,
                jcoi.amount,
                jcoi.created_at,
                jcoi.updated_at
            FROM job_change_order_item jcoi
            """
            
            # Add WHERE clause for incremental sync
            where_clause = self.build_where_clause(since_date, self.table_name)
            if where_clause:
                query += f" {where_clause}"
            
            # Add ordering and pagination
            query += f" ORDER BY jcoi.id LIMIT {chunk_size} OFFSET {offset}"
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size})")
            chunk_results = self.execute_query(query)
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            yield chunk_results
            offset += chunk_size
            
            # If we got less than chunk_size records, we're at the end
            if len(chunk_results) < chunk_size:
                break

    def get_chunked_items(self, chunk_size: int = 1000, since: Optional[datetime] = None):
        """
        Generator that yields chunks using cursor-based pagination for better performance
        
        Args:
            chunk_size: Number of records to fetch per page
            since: Get records modified since this datetime
            
        Yields:
            Lists of job change order item records
        """
        last_id = 0
        total_fetched = 0
        
        while True:
            # Build cursor-based query
            query = """
            SELECT 
                jcoi.id,
                jcoi.change_order_id,
                jcoi.description,
                jcoi.amount,
                jcoi.created_at,
                jcoi.updated_at
            FROM job_change_order_item jcoi
            WHERE jcoi.id > %s
            """
            
            params = [last_id]
            
            # Add since_date filter if provided
            if since:
                query += " AND jcoi.updated_at >= %s"
                params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += f" ORDER BY jcoi.id LIMIT {chunk_size}"
            
            logger.debug(f"Cursor-based query: {query} with params: {params}")
            chunk_results = self.execute_query(query, tuple(params))
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            total_fetched += len(chunk_results)
            logger.debug(f"Fetched chunk of {len(chunk_results)} items (total: {total_fetched})")
            
            yield chunk_results
            
            # Update cursor for next iteration (last record's ID)
            last_id = chunk_results[-1][0]  # Assuming ID is the first field
            
            # If we got less than chunk_size records, we're at the end
            if len(chunk_results) < chunk_size:
                break

    def get_total_count(self, since_date: Optional[datetime] = None) -> int:
        """Get total count of job change order items matching the criteria"""
        
        query = "SELECT COUNT(*) FROM job_change_order_item jcoi"
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
