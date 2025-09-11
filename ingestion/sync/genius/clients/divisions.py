"""
Divisions client for Genius CRM database access with chunked processing support
"""
import logging
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusDivisionsClient(GeniusBaseClient):
    """Client for accessing Genius divisions data with chunked processing"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'division'
    
    def get_query(self, where_clause: str = "", limit: Optional[int] = None) -> str:
        """Build the base query for divisions"""
        base_query = """
        SELECT 
            d.id,
            d.group_id,
            d.region_id,
            d.label,
            d.abbreviation,
            d.is_utility,
            d.is_corp,
            d.is_omniscient,
            d.is_inactive,
            d.account_scheduler_id,
            d.created_at,
            d.updated_at
        FROM division d
        """
        
        if where_clause:
            base_query += f" WHERE {where_clause}"
            
        base_query += " ORDER BY d.id"
        
        if limit:
            base_query += f" LIMIT {limit}"
            
        return base_query

    def get_chunked_divisions(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> List[Tuple]:
        """Fetch divisions data in chunks for large datasets"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        query = f"""
        SELECT 
            d.id,
            d.group_id,
            d.region_id,
            d.label,
            d.abbreviation,
            d.is_utility,
            d.is_corp,
            d.is_omniscient,
            d.is_inactive,
            d.account_scheduler_id,
            d.created_at,
            d.updated_at
        FROM division d
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY d.id LIMIT {chunk_size} OFFSET {offset}"
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        query = f"""
        SELECT 
            d.id,
            d.group_id,
            d.region_id,
            d.label,
            d.abbreviation,
            d.is_utility,
            d.is_corp,
            d.is_omniscient,
            d.is_inactive,
            d.account_scheduler_id,
            d.created_at,
            d.updated_at
        FROM division d
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY d.id LIMIT {chunk_size} OFFSET {offset}"
        return query
    
    def get_total_count(self, where_clause: str = "") -> int:
        """Get total count of records matching criteria"""
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
            
        result = self.execute_query(query)
        return result[0][0] if result else 0
        
    def fetch_data(self, where_clause: str = "", limit: Optional[int] = None) -> List[Tuple]:
        """Fetch divisions data with optional filtering"""
        query = self.get_query(where_clause, limit)
        return self.execute_query(query)
    
    def get_divisions(self, since_date: Optional[Any] = None, limit: Optional[int] = None) -> List[Tuple]:
        """Fetch divisions data with optional since_date filtering"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        return self.fetch_data(where_clause, limit)
    
    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        return {
            'id': 0,
            'group_id': 1,
            'region_id': 2,
            'label': 3,
            'abbreviation': 4,
            'is_utility': 5,
            'is_corp': 6,
            'is_omniscient': 7,
            'is_inactive': 8,
            'account_scheduler_id': 9,
            'created_at': 10,
            'updated_at': 11
        }
