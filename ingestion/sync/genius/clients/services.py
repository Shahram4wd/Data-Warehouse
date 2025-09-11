"""
Services client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)

class GeniusServicesClient(GeniusBaseClient):
    """Client for accessing Genius services data with chunked processing support"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'service'
    
    def get_field_mapping(self) -> List[str]:
        """Return the field mapping for services table"""
        return [
            'id', 'label', 'is_active', 'is_lead_required', 'order_number',
            'created_at', 'updated_at'
        ]
    
    def get_services(self, since_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[tuple]:
        """Get services data for processing (legacy method for limited records)"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE s.updated_at >= '{since_date}'" 
            
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
            SELECT
                s.id,
                s.label,
                s.is_active,
                s.is_lead_required,
                s.order_number,
                s.created_at,
                s.updated_at
            FROM {self.table_name} s
            {where_clause}
            ORDER BY s.id
            {limit_clause}
        """
        
        return self.execute_query(query)
    
    def get_chunked_services(self, offset: int, chunk_size: int, 
                            since_date: Optional[datetime] = None) -> List[tuple]:
        """Get services data in chunks for large dataset processing"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE s.updated_at >= '{since_date}'"
            
        query = f"""
            SELECT
                s.id,
                s.label,
                s.is_active,
                s.is_lead_required,
                s.order_number,
                s.created_at,
                s.updated_at
            FROM {self.table_name} s
            {where_clause}
            ORDER BY s.id LIMIT {chunk_size} OFFSET {offset}
        """
        
        return self.execute_query(query)
    
    def get_chunked_query(self, offset: int, chunk_size: int, 
                         since_date: Optional[datetime] = None) -> str:
        """Get the query string for chunked processing (for logging)"""
        
        where_clause = ""
        if since_date:
            where_clause = f" WHERE s.updated_at >= '{since_date}'"
            
        return f"""
            SELECT
                s.id,
                s.label,
                s.is_active,
                s.is_lead_required,
                s.order_number,
                s.created_at,
                s.updated_at
            FROM {self.table_name} s
            {where_clause}
         ORDER BY s.id LIMIT {chunk_size} OFFSET {offset}
        """
    
    def get_record_count(self, since_date: Optional[datetime] = None) -> int:
        """Get total count of service records for the sync"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE s.updated_at >= '{since_date}'"
            
        query = f"SELECT COUNT(*) FROM {self.table_name} s {where_clause}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
