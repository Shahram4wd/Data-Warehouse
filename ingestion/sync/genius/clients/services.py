"""
Genius Services Database Client
"""
from typing import Dict, List, Tuple, Any, Optional
from .base import GeniusBaseClient


class GeniusServicesClient(GeniusBaseClient):
    """Client for accessing Genius service data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = "service"
        self.timestamp_field = "updated_at"
        
    def get_query(self, where_clause: str = "", limit: Optional[int] = None) -> str:
        """Build the complete query for service data"""
        base_query = f"""
        SELECT 
            id,
            label,
            is_active,
            is_lead_required,
            order_number,
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
        """Fetch service data with optional filtering"""
        query = self.get_query(where_clause, limit)
        return self.execute_query(query)
