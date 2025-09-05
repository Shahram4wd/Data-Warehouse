"""
Genius Appointments Data Client
Handles data retrieval from the Genius appointments table
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any

from ingestion.sync.genius.clients.base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusAppointmentsClient(GeniusBaseClient):
    """Client for accessing Genius appointments data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'appointment'
        self.timestamp_field = 'updated_at'  # Use updated_at for better delta sync support
    
    def execute_query_dict(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """Execute SQL query and return results as dictionaries"""
        self.connect()
        cursor = self.connection.cursor()
        try:
            cursor.execute(query, params or ())
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            cursor.close()

    def get_appointments(self, 
                        since: Optional[datetime] = None,
                        start_date: Optional[datetime] = None, 
                        end_date: Optional[datetime] = None,
                        limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Retrieve appointments from the Genius database
        
        Args:
            since: Get records modified since this datetime
            start_date: Start date filter
            end_date: End date filter  
            limit: Maximum records to return
            
        Returns:
            List of appointment records as dictionaries
        """
        
        # Build the main query with all required fields
        query = f"""
            SELECT a.id, a.prospect_id, a.prospect_source_id, a.user_id, a.type_id, 
                   a.date, a.time, a.duration, a.address1, a.address2, a.city, a.state, a.zip, 
                   a.email, a.notes, a.add_user_id, a.add_date, a.assign_date, 
                   a.confirm_user_id, a.confirm_date, a.confirm_with, a.spouses_present, 
                   a.is_complete, a.complete_outcome_id, a.complete_user_id, a.complete_date, 
                   a.updated_at, a.marketsharp_id, a.marketsharp_appt_type, a.leap_estimate_id, 
                   tps.third_party_id AS hubspot_appointment_id
            FROM {self.table_name} AS a
            LEFT JOIN third_party_source AS tps 
              ON tps.id = a.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
        """
        
        # Build WHERE clause using the base client method
        where_clause = self.build_where_clause(since, start_date, end_date)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering by primary timestamp field
        query += f" ORDER BY a.{self.timestamp_field}"
        
        # Add limit if specified
        if limit:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        
        # Execute query and return results as dictionaries
        return self.execute_query_dict(query)
    
    def get_appointments_count(self, 
                              since: Optional[datetime] = None,
                              start_date: Optional[datetime] = None,
                              end_date: Optional[datetime] = None) -> int:
        """Get count of appointments matching the criteria"""
        
        query = f"""
            SELECT COUNT(*) 
            FROM {self.table_name} AS a
            LEFT JOIN third_party_source AS tps 
              ON tps.id = a.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
        """
        
        where_clause = self.build_where_clause(since, start_date, end_date)
        if where_clause:
            query += f" {where_clause}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
    
    def build_where_clause(self, 
                          since: Optional[datetime] = None,
                          start_date: Optional[datetime] = None,
                          end_date: Optional[datetime] = None) -> str:
        """Build WHERE clause for appointments filtering"""
        conditions = []
        
        # Use updated_at for delta updates when available
        if since:
            conditions.append(f"a.updated_at >= '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        # Date range filtering
        if start_date:
            conditions.append(f"a.updated_at >= '{start_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        if end_date:
            conditions.append(f"a.updated_at <= '{end_date.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        if conditions:
            return "WHERE " + " AND ".join(conditions)
        return ""
