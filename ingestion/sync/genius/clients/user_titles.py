"""
Genius User Titles Database Client
"""
from typing import Dict, List, Tuple, Any, Optional
from .base import GeniusBaseClient


class GeniusUserTitlesClient(GeniusBaseClient):
    """Client for accessing Genius user title data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = "user_title"
        self.timestamp_field = "updated_at"
        
    def get_query(self, where_clause: str = "", limit: Optional[int] = None) -> str:
        """Build the complete query for user title data"""
        base_query = f"""
        SELECT 
            id,
            title,
            abbreviation,
            roles,
            type_id,
            section_id,
            sort,
            pay_component_group_id,
            is_active,
            is_unique_per_division,
            created_at,
            updated_at
        FROM {self.table_name}
        """
        
        if where_clause:
            base_query += f" WHERE {where_clause}"
            
        base_query += " ORDER BY id"
        
        if limit:
            base_query += f" LIMIT {limit}"
            
        return base_query
    
    def get_total_count(self, where_clause: str = "") -> int:
        """Get total count of records matching criteria"""
        query = f"SELECT COUNT(*) FROM {self.table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
            
        result = self.execute_query(query)
        return result[0][0] if result else 0
        
    def fetch_data(self, where_clause: str = "", limit: Optional[int] = None) -> List[Tuple]:
        """Fetch user title data with optional filtering"""
        query = self.get_query(where_clause, limit)
        return self.execute_query(query)
    
    def get_user_titles(self, since_date: Optional[Any] = None, limit: Optional[int] = None) -> List[Tuple]:
        """Fetch user titles data with optional since_date filtering"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        return self.fetch_data(where_clause, limit)
    
    def get_chunked_user_titles(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> List[Tuple]:
        """Fetch user titles data in chunks for large datasets"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        query = f"""
        SELECT 
            id,
            title,
            abbreviation,
            roles,
            type_id,
            section_id,
            sort,
            pay_component_group_id,
            is_active,
            is_unique_per_division,
            created_at,
            updated_at
        FROM {self.table_name}
        """
        
        if where_clause:
            query += f" WHERE {where_clause}"
            
        query += f" ORDER BY id LIMIT {chunk_size} OFFSET {offset}"
        
        return self.execute_query(query)
    
    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        query = f"""
        SELECT 
            id,
            title,
            abbreviation,
            roles,
            type_id,
            section_id,
            sort,
            pay_component_group_id,
            is_active,
            is_unique_per_division,
            created_at,
            updated_at
        FROM {self.table_name}
        """
        
        if where_clause:
            query += f" WHERE {where_clause}"
            
        query += f" ORDER BY id LIMIT {chunk_size} OFFSET {offset}"
        
        return query
    
    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        return {
            'id': 0,
            'title': 1,
            'abbreviation': 2,
            'roles': 3,
            'type_id': 4,
            'section_id': 5,
            'sort': 6,
            'pay_component_group_id': 7,
            'is_active': 8,
            'is_unique_per_division': 9,
            'created_at': 10,
            'updated_at': 11
        }
