"""
Base client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from ingestion.utils import get_mysql_connection

logger = logging.getLogger(__name__)

class GeniusBaseClient:
    """Base client for accessing Genius CRM database"""
    
    def __init__(self):
        self.connection = None
    
    def connect(self):
        """Establish connection to Genius database"""
        if not self.connection:
            self.connection = get_mysql_connection()
    
    def disconnect(self):
        """Close connection to Genius database"""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute SQL query and return results"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            return cursor.fetchall()
        finally:
            cursor.close()
    
    def get_table_count(self, table_name: str) -> int:
        """Get total record count for a table"""
        query = f"SELECT COUNT(*) FROM {table_name}"
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def build_where_clause(self, since_date: Optional[datetime], table_name: str) -> str:
        """Build WHERE clause for incremental sync"""
        if not since_date:
            return ""
        
        # Map table names to their timestamp fields
        timestamp_field_map = {
            'prospect': 'updated_at',
            'division': 'updated_at', 
            'user_title': 'updated_at',
            'appointment': 'updated_at',
            'user': 'updated_at'
        }
        
        timestamp_field = timestamp_field_map.get(table_name, 'updated_at')
        since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
        
        return f"WHERE {timestamp_field} > '{since_str}'"
