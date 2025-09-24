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
        # Added LEFT JOIN to users_userassociations to pull primary_user_id.
        base_query = f"""
        SELECT 
            u.user_id,
            u.division_id,
            u.title_id,
            u.manager_user_id,
            u.first_name,
            u.first_name_alt,
            u.last_name,
            u.email,
            u.personal_email,
            u.birth_date,
            u.gender_id,
            u.marital_status_id,
            u.time_zone_name,
            u.hired_on,
            u.start_date,
            u.add_user_id,
            u.add_datetime,
            u.updated_at,
            u.is_inactive,
            u.inactive_on,
            u.inactive_reason_id,
            u.inactive_reason_other,
            ua.primary_user_id,
            u.inactive_transfer_division_id
        FROM {self.table_name} u
        LEFT JOIN users_userassociations ua ON ua.id = u.user_associations_id
        """
        
        if where_clause:
            base_query += f" WHERE {where_clause}"
            
        base_query += " ORDER BY user_id"
        
        if limit:
            base_query += f" LIMIT {limit}"
            
        return base_query

    def get_chunked_users(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> List[Tuple]:
        """Fetch user data in chunks for large datasets"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        query = f"""
        SELECT 
            u.user_id,
            u.division_id,
            u.title_id,
            u.manager_user_id,
            u.first_name,
            u.first_name_alt,
            u.last_name,
            u.email,
            u.personal_email,
            u.birth_date,
            u.gender_id,
            u.marital_status_id,
            u.time_zone_name,
            u.hired_on,
            u.start_date,
            u.add_user_id,
            u.add_datetime,
            u.updated_at,
            u.is_inactive,
            u.inactive_on,
            u.inactive_reason_id,
            u.inactive_reason_other,
            ua.primary_user_id,
            u.inactive_transfer_division_id
        FROM {self.table_name} u
        LEFT JOIN users_userassociations ua ON ua.id = u.user_associations_id
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY user_id LIMIT {chunk_size} OFFSET {offset}"
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        query = f"""
        SELECT 
            u.user_id,
            u.division_id,
            u.title_id,
            u.manager_user_id,
            u.first_name,
            u.first_name_alt,
            u.last_name,
            u.email,
            u.personal_email,
            u.birth_date,
            u.gender_id,
            u.marital_status_id,
            u.time_zone_name,
            u.hired_on,
            u.start_date,
            u.add_user_id,
            u.add_datetime,
            u.updated_at,
            u.is_inactive,
            u.inactive_on,
            u.inactive_reason_id,
            u.inactive_reason_other,
            ua.primary_user_id,
            u.inactive_transfer_division_id
        FROM {self.table_name} u
        LEFT JOIN users_userassociations ua ON ua.id = u.user_associations_id
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY user_id LIMIT {chunk_size} OFFSET {offset}"
        return query
    
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
    
    def get_users(self, since_date: Optional[Any] = None, limit: Optional[int] = None) -> List[Tuple]:
        """Fetch users data with optional since_date filtering"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        return self.fetch_data(where_clause, limit)
    
    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        return {
            'id': 0,  # user_id
            'division_id': 1,
            'title_id': 2,
            'manager_user_id': 3,
            'first_name': 4,
            'first_name_alt': 5,
            'last_name': 6,
            'email': 7,
            'personal_email': 8,
            'birth_date': 9,
            'gender_id': 10,
            'marital_status_id': 11,
            'time_zone_name': 12,
            'hired_on': 13,
            'start_date': 14,
            'add_user_id': 15,
            'add_datetime': 16,
            'updated_at': 17,
            'is_inactive': 18,
            'inactive_on': 19,
            'inactive_reason_id': 20,
            'inactive_reason_other': 21,
            'primary_user_id': 22,
            'inactive_transfer_division_id': 23
        }
