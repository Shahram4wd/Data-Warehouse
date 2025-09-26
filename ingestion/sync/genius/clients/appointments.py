"""
Genius Appointments Data Client
Handles data retrieval from the Genius appointments table
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Generator

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
        connection = None
        cursor = None
        
        try:
            connection = self.get_connection()
            cursor = connection.cursor()
            cursor.execute(query, params or ())
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        finally:
            if cursor:
                cursor.close()
            if connection:
                connection.close()  # Returns to pool if using pooled connection

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

    def get_cursor_based_appointments(self, 
                                     chunk_size: int = 1000,
                                     last_cursor: Optional[Dict] = None,
                                     since: Optional[datetime] = None) -> tuple:
        """
        Get appointments using cursor-based pagination for better performance
        
        Args:
            chunk_size: Number of records to fetch per page
            last_cursor: Cursor from previous page (contains updated_at and id)
            since: Get records modified since this datetime
            
        Returns:
            Tuple of (records_list, next_cursor_dict)
        """
        # Build WHERE clause for incremental sync
        conditions = []
        
        if since:
            conditions.append(f"a.updated_at >= '{since.strftime('%Y-%m-%d %H:%M:%S')}'")
        
        # Add cursor conditions for pagination
        if last_cursor and 'updated_at' in last_cursor:
            cursor_conditions = []
            cursor_conditions.append(f"a.updated_at > '{last_cursor['updated_at']}'")
            if 'id' in last_cursor:
                cursor_conditions.append(f"(a.updated_at = '{last_cursor['updated_at']}' AND a.id > {last_cursor['id']})")
            conditions.append(f"({' OR '.join(cursor_conditions)})")
        
        where_clause = "WHERE " + " AND ".join(conditions) if conditions else ""
        
        # Build the query with cursor-based pagination
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
            {where_clause}
            ORDER BY a.updated_at, a.id
            LIMIT {chunk_size + 1}
        """
        
        logger.debug(f"Cursor-based query: {query}")
        
        # Execute query
        records = self.execute_query_dict(query)
        
        # Determine if there are more records and prepare next cursor
        has_more = len(records) > chunk_size
        data = records[:chunk_size] if has_more else records
        
        next_cursor = None
        if has_more and data:
            # Create cursor from last record
            last_record = data[-1]
            next_cursor = {
                'updated_at': last_record['updated_at'],
                'id': last_record['id']
            }
        
        return data, next_cursor

    def get_chunked_appointments(self, 
                                chunk_size: int = 1000,
                                since: Optional[datetime] = None) -> Generator[List[Dict[str, Any]], None, None]:
        """
        Generator method to yield appointment chunks using cursor-based pagination
        
        Args:
            chunk_size: Size of each chunk
            since: Get records modified since this datetime
            
        Yields:
            Lists of appointment records
        """
        cursor = None
        total_fetched = 0
        
        while True:
            # Get next chunk
            chunk_data, next_cursor = self.get_cursor_based_appointments(
                chunk_size=chunk_size,
                last_cursor=cursor,
                since=since
            )
            
            if not chunk_data:
                break
                
            total_fetched += len(chunk_data)
            logger.debug(f"Fetched chunk of {len(chunk_data)} appointments (total: {total_fetched})")
            
            yield chunk_data
            
            # Update cursor for next iteration
            cursor = next_cursor
            if not cursor:
                break  # No more data

    def get_recommended_indexes(self) -> List[str]:
        """Return recommended database indexes for optimal appointments sync performance"""
        return [
            "CREATE INDEX IF NOT EXISTS idx_appointment_updated_at ON appointment (updated_at)",
            "CREATE INDEX IF NOT EXISTS idx_appointment_updated_at_id ON appointment (updated_at, id)",
            "CREATE INDEX IF NOT EXISTS idx_appointment_prospect_id ON appointment (prospect_id)",
            "CREATE INDEX IF NOT EXISTS idx_appointment_user_id ON appointment (user_id)",
            "CREATE INDEX IF NOT EXISTS idx_appointment_type_id ON appointment (type_id)",
            "CREATE INDEX IF NOT EXISTS idx_third_party_source_id ON appointment (third_party_source_id)",
            "CREATE INDEX IF NOT EXISTS idx_third_party_source_type_label ON third_party_source_type (label)",
        ]
    
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

    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        # Based on the query SELECT fields from get_appointments()
        return {
            'id': 0,
            'prospect_id': 1,
            'prospect_source_id': 2, 
            'user_id': 3,
            'type_id': 4,
            'date': 5,
            'time': 6,
            'duration': 7,
            'address1': 8,
            'address2': 9,
            'city': 10,
            'state': 11,
            'zip': 12,
            'email': 13,
            'notes': 14,
            'add_user_id': 15,
            'add_date': 16,
            'assign_date': 17,
            'confirm_user_id': 18,
            'confirm_date': 19,
            'confirm_with': 20,
            'spouses_present': 21,
            'is_complete': 22,
            'complete_outcome_id': 23,
            'complete_user_id': 24,
            'complete_date': 25,
            'updated_at': 26,
            'marketsharp_id': 27,
            'marketsharp_appt_type': 28,
            'leap_estimate_id': 29,
            'hubspot_appointment_id': 30
        }
