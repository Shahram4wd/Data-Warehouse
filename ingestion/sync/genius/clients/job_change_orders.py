"""
Job Change Order client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobChangeOrderClient(GeniusBaseClient):
    """Client for accessing Genius CRM job change order data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job_change_order'
    
    def get_job_change_orders(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch job change orders from Genius database"""
        
        # Base query with all available fields
        query = """
        SELECT 
            jco.id,
            jco.job_id,
            jco.number,
            jco.status_id,
            jco.type_id,
            jco.adjustment_change_order_id,
            jco.effective_date,
            jco.total_amount,
            jco.add_user_id,
            jco.add_date,
            jco.sold_user_id,
            jco.sold_date,
            jco.cancel_user_id,
            jco.cancel_date,
            jco.reason_id,
            jco.envelope_id,
            jco.total_contract_amount,
            jco.total_pre_change_orders_amount,
            jco.signer_name,
            jco.signer_email,
            jco.financing_note,
            jco.updated_at
        FROM job_change_order jco
        """
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY jco.id"
        if limit and limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'id',
            'job_id',
            'number',
            'status_id',
            'type_id',
            'adjustment_change_order_id',
            'effective_date',
            'total_amount',
            'add_user_id',
            'add_date',
            'sold_user_id',
            'sold_date',
            'cancel_user_id',
            'cancel_date',
            'reason_id',
            'envelope_id',
            'total_contract_amount',
            'total_pre_change_orders_amount',
            'signer_name',
            'signer_email',
            'financing_note',
            'updated_at'
        ]
    
    def get_chunked_items(self, chunk_size: int = 10000, since: Optional[datetime] = None):
        """
        Generator that yields chunks of job change orders using cursor-based pagination for better performance
        
        Args:
            chunk_size: Number of records per chunk
            since: Optional datetime to filter records updated after this time
            
        Yields:
            Lists of job change order tuples in chunks
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
                jco.id,
                jco.job_id,
                jco.number,
                jco.status_id,
                jco.type_id,
                jco.adjustment_change_order_id,
                jco.effective_date,
                jco.total_amount,
                jco.add_user_id,
                jco.add_date,
                jco.sold_user_id,
                jco.sold_date,
                jco.cancel_user_id,
                jco.cancel_date,
                jco.reason_id,
                jco.envelope_id,
                jco.total_contract_amount,
                jco.total_pre_change_orders_amount,
                jco.signer_name,
                jco.signer_email,
                jco.financing_note,
                jco.updated_at
            FROM job_change_order jco
            WHERE jco.id > %s
            """
            
            params = [last_id]
            
            # Add date filter if provided
            if since:
                query += " AND jco.updated_at >= %s"
                params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += " ORDER BY jco.id LIMIT %s"
            params.append(chunk_size)
            
            logger.debug(f"Cursor-based query iteration {iterations}: {query} with params: {params}")
            
            try:
                # Execute query with timeout protection
                chunk = self.execute_query(query, tuple(params))
            except Exception as e:
                logger.error(f"Query failed at iteration {iterations}: {e}")
                break
            
            if not chunk:
                logger.debug(f"No more data found at iteration {iterations}, ending pagination")
                break
            
            # Safety check: ensure we're making progress
            new_last_id = chunk[-1][0]  # First field is ID
            if new_last_id <= last_id:
                logger.error(f"Cursor not advancing! last_id={last_id}, new_last_id={new_last_id}")
                break
                
            last_id = new_last_id
            total_fetched += len(chunk)
            
            logger.debug(f"Fetched chunk of {len(chunk)} items (total: {total_fetched}, last_id: {last_id})")
            
            yield chunk
            
        if iterations >= max_iterations:
            logger.warning(f"Reached maximum iterations ({max_iterations}) in chunked fetch")
            
        logger.info(f"Completed chunked fetch: {total_fetched} total records in {iterations} iterations")
    
    def get_total_count(self, since: Optional[datetime] = None) -> int:
        """
        Get total count of job change orders matching the criteria
        
        Args:
            since: Optional datetime to filter records updated after this time
            
        Returns:
            Total count of matching records
        """
        query = "SELECT COUNT(*) FROM job_change_order jco"
        params = []
        
        if since:
            query += " WHERE jco.updated_at >= %s"
            params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
        
        result = self.execute_query(query, tuple(params))
        return result[0][0] if result else 0
