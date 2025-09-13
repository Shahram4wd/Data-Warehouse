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
        """Get appointment services data in chunks for large-scale processing"""
        
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
