"""
Base client for Genius CRM database access with performance optimizations
"""
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator, Tuple
from datetime import datetime
from ingestion.utils import get_mysql_connection

logger = logging.getLogger(__name__)

# Try to import connection pooling, fall back gracefully if not available
try:
    import mysql.connector.pooling
    POOLING_AVAILABLE = True
except ImportError:
    logger.warning("MySQL connection pooling not available, using individual connections")
    POOLING_AVAILABLE = False

class GeniusBaseClient:
    """Base client for accessing Genius CRM database with connection pooling and optimized queries"""
    
    # Class-level connection pool
    _connection_pool = None
    
    def __init__(self):
        self.connection = None
        # Initialize connection pool if not already done
        if not self._connection_pool:
            self._init_connection_pool()
    
    @classmethod
    def _init_connection_pool(cls):
        """Initialize the connection pool for better performance"""
        if not POOLING_AVAILABLE:
            cls._connection_pool = None
            return
            
        try:
            import os
            db_host = os.getenv("GENIUS_DB_HOST")
            db_name = os.getenv("GENIUS_DB_NAME") 
            db_user = os.getenv("GENIUS_DB_USER")
            db_password = os.getenv("GENIUS_DB_PASSWORD")
            db_port = int(os.getenv("GENIUS_DB_PORT", 3306))
            
            pool_config = {
                'pool_name': 'genius_pool',
                'pool_size': 5,  # Number of connections in pool
                'pool_reset_session': True,
                'host': db_host,
                'database': db_name,
                'user': db_user,
                'password': db_password,
                'port': db_port,
                'connection_timeout': 10,
                'autocommit': True,
                'charset': 'utf8mb4',
                'collation': 'utf8mb4_unicode_ci'
            }
            
            cls._connection_pool = mysql.connector.pooling.MySQLConnectionPool(**pool_config)
            logger.info("Connection pool initialized successfully")
        except Exception as e:
            logger.warning(f"Failed to initialize connection pool, falling back to individual connections: {e}")
            cls._connection_pool = None
    
    def get_connection(self):
        """Get a connection from the pool or create a new one"""
        if self._connection_pool:
            try:
                return self._connection_pool.get_connection()
            except Exception as e:
                logger.warning(f"Failed to get connection from pool: {e}")
        
        # Fallback to individual connection
        return get_mysql_connection()
    
    def execute_query(self, query: str, params: tuple = None) -> List[tuple]:
        """Execute SQL query with improved connection handling"""
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            result = cursor.fetchall()
            return result
            
        except Exception as e:
            logger.error(f"Query execution failed: {e}")
            logger.debug(f"Failed query: {query}")
            raise
            
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()  # Returns to pool if using pooled connection
    
    def execute_query_with_cursor(self, query: str, params: tuple = None) -> Tuple[Any, Any]:
        """Execute query and return cursor and connection for streaming results"""
        connection = self.get_connection()
        cursor = connection.cursor()
        
        try:
            cursor.execute(query, params or ())
            return cursor, connection
        except Exception as e:
            cursor.close()
            connection.close()
            raise
    
    def get_table_count(self, table_name: str, where_clause: str = "") -> int:
        """Get total record count for a table with optional WHERE clause"""
        query = f"SELECT COUNT(*) FROM {table_name} {where_clause}"
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def get_cursor_based_chunk(self, table_name: str, chunk_size: int, 
                              last_cursor: Optional[Dict] = None, 
                              where_clause: str = "",
                              order_fields: List[str] = None) -> Tuple[List[tuple], Optional[Dict]]:
        """
        Get data chunk using cursor-based pagination for better performance
        Returns (data, next_cursor) tuple
        """
        if not order_fields:
            order_fields = ['id']  # Default ordering field
        
        # Build cursor WHERE clause
        cursor_clause = ""
        if last_cursor:
            conditions = []
            for field in order_fields:
                if field in last_cursor:
                    conditions.append(f"{field} > %({field})s")
            if conditions:
                cursor_clause = "AND (" + " OR ".join(conditions) + ")"
        
        # Combine WHERE clauses
        full_where = where_clause
        if cursor_clause:
            if full_where:
                full_where += f" {cursor_clause}"
            else:
                full_where = f"WHERE {cursor_clause[4:]}"  # Remove 'AND '
        
        # Build query
        order_by = ", ".join(order_fields)
        query = f"""
            SELECT * FROM {table_name} 
            {full_where}
            ORDER BY {order_by}
            LIMIT {chunk_size + 1}
        """
        
        # Execute with cursor parameters
        params = last_cursor if last_cursor else {}
        result = self.execute_query(query, tuple(params.values()) if params else None)
        
        # Determine if there's a next page and prepare cursor
        has_more = len(result) > chunk_size
        data = result[:chunk_size] if has_more else result
        
        next_cursor = None
        if has_more and data:
            # Create cursor from last record
            last_record = data[-1]
            next_cursor = {}
            for i, field in enumerate(order_fields):
                if i < len(last_record):
                    next_cursor[field] = last_record[i]
        
        return data, next_cursor
    
    def build_where_clause(self, since_date: Optional[datetime], table_name: str) -> str:
        """Build WHERE clause for incremental sync"""
        if not since_date:
            return ""
        
        # Map table names to their timestamp fields
        timestamp_field_map = {
            'prospect': 'updated_at',
            'division': 'updated_at', 
            'division_group': 'updated_at',
            'division_region': None,  # No timestamp field
            'user_title': 'updated_at',
            'appointment': 'updated_at',
            'user': 'updated_at',
            'job': 'updated_at',
            'job_status': None,  # Reference table, no timestamp field
            'job_financing': None,  # No timestamp field
            'lead': 'updated_at',
            'quote': 'updated_at',
            'job_change_order': 'updated_at',
            'appointment_type': None,  # Reference table, no timestamp field
            'appointment_outcome': 'updated_at',
            'appointment_outcome_type': None,  # Reference table, no timestamp field
            'marketing_source': 'updated_at',
            'marketing_source_type': None,  # Reference table, no timestamp field
            'prospect_source': 'updated_at',
            'marketsharp_sources': 'updated_at',
            'marketsharp_marketing_source_map': 'updated_at',
            'marketsharp_contacts': 'updated_at',
            'marketsharp_appointments': 'updated_at'
        }
        
        timestamp_field = timestamp_field_map.get(table_name, 'updated_at')
        
        # If table has no timestamp field, skip incremental sync
        if timestamp_field is None:
            return ""
        
        since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
        
        return f"WHERE {timestamp_field} > '{since_str}'"
