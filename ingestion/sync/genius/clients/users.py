"""
Genius Users Database Client
"""
from typing import Dict, List, Tuple, Any, Optional
from .base import GeniusBaseClient


class GeniusUsersClient(GeniusBaseClient):
    """Client for accessing Genius user data with performance optimizations"""
    
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
            where_clause = f"u.updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
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
        {where_clause and f'WHERE {where_clause}' or ''}
        ORDER BY u.user_id 
        LIMIT {chunk_size} OFFSET {offset}
        """
        
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[Any] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"u.updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
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
        {where_clause and f'WHERE {where_clause}' or ''}
        ORDER BY u.user_id 
        LIMIT {chunk_size} OFFSET {offset}
        """
        
        return query
    
    def get_total_count(self, since_date: Optional[Any] = None) -> int:
        """Get total count of records matching criteria"""
        if since_date:
            # For users table with JOIN, we need the full query structure
            query = f"""
            SELECT COUNT(*) 
            FROM {self.table_name} u
            LEFT JOIN users_userassociations ua ON ua.id = u.user_associations_id
            WHERE u.updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'
            """
        else:
            query = f"SELECT COUNT(*) FROM {self.table_name}"
            
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
            where_clause = f"u.updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
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
    
    def get_cursor_based_users(self, chunk_size: int, 
                              last_cursor: Optional[Dict] = None,
                              since_date: Optional[Any] = None) -> tuple:
        """
        Get users using cursor-based pagination for optimal performance.
        Returns (data, next_cursor) tuple.
        """
        where_conditions = []
        cursor_conditions = []
        params = []
        
        # Build since_date filter
        if since_date:
            where_conditions.append("u.updated_at >= %s")
            params.append(since_date)
        
        # Build cursor-based pagination
        if last_cursor and 'user_id' in last_cursor:
            cursor_conditions.append("u.user_id > %s")
            params.append(last_cursor['user_id'])
        
        # Combine all conditions
        all_conditions = where_conditions + cursor_conditions
        where_clause = ""
        if all_conditions:
            where_clause = "WHERE " + " AND ".join(all_conditions)
        
        # Build optimized query
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
        {where_clause}
        ORDER BY u.user_id
        LIMIT {chunk_size + 1}
        """
        
        result = self.execute_query(query, tuple(params) if params else None)
        
        # Check if there are more records
        has_more = len(result) > chunk_size
        data = result[:chunk_size] if has_more else result
        
        # Prepare next cursor
        next_cursor = None
        if has_more and data:
            last_record = data[-1]
            next_cursor = {
                'user_id': last_record[0]  # user_id is first column
            }
        
        return data, next_cursor
    
    def get_recommended_indexes(self) -> List[str]:
        """Return recommended database indexes for optimal performance"""
        return [
            f"CREATE INDEX idx_{self.table_name}_user_id ON {self.table_name} (user_id);",
            f"CREATE INDEX idx_{self.table_name}_updated_at ON {self.table_name} (updated_at);",
            f"-- Composite index for cursor-based pagination with time filtering:",
            f"CREATE INDEX idx_{self.table_name}_time_cursor ON {self.table_name} (updated_at, user_id);",
            f"-- Index for JOIN with users_userassociations:",
            f"CREATE INDEX idx_users_userassociations_id ON users_userassociations (id);"
        ]
    
    def log_performance_recommendations(self):
        """Log performance optimization recommendations"""
        import logging
        logger = logging.getLogger(__name__)
        logger.info("🔧 Database Performance Recommendations:")
        logger.info("   Consider adding these indexes for better performance:")
        for idx in self.get_recommended_indexes():
            logger.info(f"   {idx}")
        logger.info("   Note: Test indexes on non-production environment first!")
