"""
User associations client for Genius CRM data access
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import GeniusBaseClient

logger = logging.getLogger(__name__)

class GeniusUserAssociationsClient(GeniusBaseClient):
    """Client for fetching user associations data from Genius CRM database"""
    
    def __init__(self):
        super().__init__()
        self.table_name = "users_userassociations"
    
    def get_user_associations(self, since_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Fetch user associations data from Genius CRM
        
        Args:
            since_date: Optional datetime to fetch records modified since
            limit: Optional limit on number of records to fetch
            
        Returns:
            List of user associations records
        """
        base_query = self._build_base_query()
        where_clause = self._build_where_clause(since_date)
        
        query = f"{base_query} {where_clause} ORDER BY updated_at, id"
        
        if limit:
            query += f" LIMIT {limit}"
            
        logger.info(f"Executing user associations query: {query}")
        return self.execute_query(query)
    
    def get_chunked_user_associations(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
        """
        Fetch a chunk of user associations data for large dataset processing
        
        Args:
            offset: Starting offset for the chunk
            chunk_size: Number of records to fetch in this chunk
            since_date: Optional datetime to fetch records modified since
            
        Returns:
            List of user associations records for this chunk
        """
        base_query = self._build_base_query()
        where_clause = self._build_where_clause(since_date)
        
        query = f"{base_query} {where_clause} ORDER BY updated_at, id LIMIT {chunk_size} OFFSET {offset}"
        
        return self.execute_query(query)
    
    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> str:
        """Get the chunked query string for logging purposes"""
        base_query = self._build_base_query()
        where_clause = self._build_where_clause(since_date)
        
        return f"{base_query} {where_clause} ORDER BY updated_at, id LIMIT {chunk_size} OFFSET {offset}"
    
    def _build_base_query(self) -> str:
        """Build the base SELECT query for user associations"""
        return f"""
        SELECT 
            id,
            primary_user_id,
            created_at,
            updated_at
        FROM {self.table_name}
        """
    
    def _build_where_clause(self, since_date: Optional[datetime] = None) -> str:
        """Build WHERE clause based on parameters"""
        conditions = []
        
        if since_date:
            conditions.append(f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        
        return ""
    
    def get_field_mapping(self) -> Dict[str, str]:
        """Get field mapping for user associations data transformation"""
        return {
            'id': 'id',
            'primary_user_id': 'user_id',  # Map primary_user_id to user_id in our model
            'created_at': 'created_at',
            'updated_at': 'updated_at'
        }
