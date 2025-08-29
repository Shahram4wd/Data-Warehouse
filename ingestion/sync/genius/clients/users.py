"""
Genius Users Database Client
"""
from typing import Dict, List, Tuple, Any, Optional
from .base import GeniusBaseClient


class GeniusUsersClient(GeniusBaseClient):
    """Client for accessing Genius user data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = "user_data"
        self.timestamp_field = "updated_at"  # Use updated_at for better delta update support
        
    def get_query(self, where_clause: str = "", limit: Optional[int] = None) -> str:
        """Build the complete query for user data"""
        base_query = f"""
        SELECT 
            user_id,
            division_id,
            title_id,
            manager_user_id,
            first_name,
            first_name_alt,
            last_name,
            email,
            personal_email,
            birth_date,
            gender_id,
            marital_status_id,
            time_zone_name,
            hired_on,
            start_date,
            add_user_id,
            add_datetime,
            updated_at,
            is_inactive,
            inactive_on,
            inactive_reason_id,
            inactive_reason_other,
            inactive_transfer_division_id
        FROM {self.table_name}
        """
        
        if where_clause:
            base_query += f" WHERE {where_clause}"
            
        base_query += " ORDER BY user_id"
        
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
        """Fetch user data with optional filtering"""
        query = self.get_query(where_clause, limit)
        return self.execute_query(query)
