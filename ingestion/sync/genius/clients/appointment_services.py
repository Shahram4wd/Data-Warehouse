"""
Appointment Services client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)

class GeniusAppointmentServicesClient(GeniusBaseClient):
    """Client for accessing Genius appointment services data with chunked processing support"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'appointment_to_service'
    
    def get_field_mapping(self) -> List[str]:
        """Return the field mapping for appointment_to_service table"""
        return [
            'appointment_id', 'service_id', 'created_at', 'updated_at'
        ]
    
    def get_appointment_services(self, since_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[tuple]:
        """Get appointment services data for processing (legacy method for limited records)"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE aps.updated_at >= '{since_date}'" 
            
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
            SELECT
                aps.appointment_id,
                aps.service_id,
                aps.created_at,
                aps.updated_at
            FROM {self.table_name} aps
            {where_clause}
            ORDER BY aps.appointment_id, aps.service_id
            {limit_clause}
        """
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_chunked_appointment_services(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> List[tuple]:
        """Get appointment services data in chunks for large-scale processing (legacy method)"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE aps.updated_at >= '{since_date}'"
        
        query = f"""
            SELECT
                aps.appointment_id,
                aps.service_id,
                aps.created_at,
                aps.updated_at
            FROM {self.table_name} aps
            {where_clause}
            ORDER BY aps.appointment_id, aps.service_id
            LIMIT {chunk_size} OFFSET {offset}
        """
        
        logger.debug(f"Executing chunked query: {query}")
        return self.execute_query(query)
    
    def get_cursor_based_appointment_services(self, chunk_size: int, 
                                            last_cursor: Optional[Dict] = None,
                                            since_date: Optional[datetime] = None) -> tuple:
        """
        Get appointment services using cursor-based pagination for optimal performance.
        Returns (data, next_cursor) tuple.
        """
        where_clause = ""
        cursor_clause = ""
        params = []
        
        # Build since_date filter
        if since_date:
            where_clause = "WHERE aps.updated_at >= %s"
            params.append(since_date)
        
        # Build cursor-based pagination
        if last_cursor:
            cursor_conditions = []
            if 'appointment_id' in last_cursor and 'service_id' in last_cursor:
                cursor_conditions.append(
                    "(aps.appointment_id > %s OR "
                    "(aps.appointment_id = %s AND aps.service_id > %s))"
                )
                params.extend([
                    last_cursor['appointment_id'],
                    last_cursor['appointment_id'], 
                    last_cursor['service_id']
                ])
            
            if cursor_conditions:
                if where_clause:
                    where_clause += " AND " + " AND ".join(cursor_conditions)
                else:
                    where_clause = "WHERE " + " AND ".join(cursor_conditions)
        
        # Build optimized query
        query = f"""
            SELECT
                aps.appointment_id,
                aps.service_id,
                aps.created_at,
                aps.updated_at
            FROM {self.table_name} aps
            {where_clause}
            ORDER BY aps.appointment_id, aps.service_id
            LIMIT {chunk_size + 1}
        """
        
        logger.debug(f"Executing cursor-based query: {query}")
        result = self.execute_query(query, tuple(params) if params else None)
        
        # Check if there are more records
        has_more = len(result) > chunk_size
        data = result[:chunk_size] if has_more else result
        
        # Prepare next cursor
        next_cursor = None
        if has_more and data:
            last_record = data[-1]
            next_cursor = {
                'appointment_id': last_record[0],  # appointment_id
                'service_id': last_record[1]       # service_id
            }
        
        return data, next_cursor
    
    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> str:
        """Return the chunked query string for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"WHERE aps.updated_at >= '{since_date}'"
        
        return f"""
            SELECT
                aps.appointment_id,
                aps.service_id,
                aps.created_at,
                aps.updated_at
            FROM {self.table_name} aps
            {where_clause}
            ORDER BY aps.appointment_id, aps.service_id
            LIMIT {chunk_size} OFFSET {offset}
        """
    
    def get_total_count(self, since_date: Optional[datetime] = None) -> int:
        """Get total count of records for progress tracking"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE aps.updated_at >= '{since_date}'"
        
        query = f"SELECT COUNT(*) FROM {self.table_name} aps {where_clause}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def get_recommended_indexes(self) -> List[str]:
        """Return recommended database indexes for optimal performance"""
        return [
            f"CREATE INDEX idx_{self.table_name}_compound ON {self.table_name} (appointment_id, service_id);",
            f"CREATE INDEX idx_{self.table_name}_updated_at ON {self.table_name} (updated_at);",
            f"CREATE INDEX idx_{self.table_name}_created_at ON {self.table_name} (created_at);",
            f"-- Composite index for cursor-based pagination with time filtering:",
            f"CREATE INDEX idx_{self.table_name}_time_cursor ON {self.table_name} (updated_at, appointment_id, service_id);"
        ]
    
    def log_performance_recommendations(self):
        """Log performance optimization recommendations"""
        logger.info("🔧 Database Performance Recommendations:")
        logger.info("   Consider adding these indexes for better performance:")
        for idx in self.get_recommended_indexes():
            logger.info(f"   {idx}")
        logger.info("   Note: Test indexes on non-production environment first!")
