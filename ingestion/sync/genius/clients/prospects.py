"""
Prospects client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)

class GeniusProspectsClient(GeniusBaseClient):
    """Client for accessing Genius prospects data with chunked processing support"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'prospect'
    
    def get_field_mapping(self) -> List[str]:
        """Return the field mapping for prospects table"""
        return [
            'id', 'division_id', 'user_id', 'first_name', 'last_name', 'alt_first_name', 'alt_last_name',
            'address1', 'address2', 'city', 'county', 'state', 'zip', 'year_built', 'phone1', 'phone2',
            'email', 'notes', 'add_user_id', 'add_date', 'marketsharp_id', 'leap_customer_id', 
            'third_party_source_id', 'updated_at', 'hubspot_contact_id'
        ]
    
    def get_prospects(self, since_date: Optional[datetime] = None, limit: Optional[int] = None) -> List[tuple]:
        """Get prospects data for processing (legacy method for limited records)"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE p.updated_at >= '{since_date}'" 
            
        limit_clause = f"LIMIT {limit}" if limit else ""
        
        query = f"""
            SELECT
                p.id,
                p.division_id,
                p.user_id,
                p.first_name,
                p.last_name,
                p.alt_first_name,
                p.alt_last_name,
                p.address1,
                p.address2,
                p.city,
                p.county,
                p.state,
                p.zip,
                p.year_built,
                p.phone1,
                p.phone2,
                p.email,
                p.notes,
                p.add_user_id,
                p.add_date,
                p.marketsharp_id,
                p.leap_customer_id,
                p.third_party_source_id,
                p.updated_at,
                tps.third_party_id AS hubspot_contact_id
            FROM {self.table_name} p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            {where_clause}
            ORDER BY p.id
            {limit_clause}
        """
        
        return self.execute_query(query)
    
    def get_chunked_prospects(self, offset: int, chunk_size: int, 
                             since_date: Optional[datetime] = None) -> List[tuple]:
        """Get prospects data in chunks for large dataset processing"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE p.updated_at >= '{since_date}'"
            
        query = f"""
            SELECT
                p.id,
                p.division_id,
                p.user_id,
                p.first_name,
                p.last_name,
                p.alt_first_name,
                p.alt_last_name,
                p.address1,
                p.address2,
                p.city,
                p.county,
                p.state,
                p.zip,
                p.year_built,
                p.phone1,
                p.phone2,
                p.email,
                p.notes,
                p.add_user_id,
                p.add_date,
                p.marketsharp_id,
                p.leap_customer_id,
                p.third_party_source_id,
                p.updated_at,
                tps.third_party_id AS hubspot_contact_id
            FROM {self.table_name} p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            {where_clause}
            ORDER BY p.id LIMIT {chunk_size} OFFSET {offset}
        """
        
        return self.execute_query(query)
    
    def get_chunked_query(self, offset: int, chunk_size: int, 
                         since_date: Optional[datetime] = None) -> str:
        """Get the query string for chunked processing (for logging)"""
        
        where_clause = ""
        if since_date:
            where_clause = f" WHERE p.updated_at >= '{since_date}'"
            
        return f"""
            SELECT
                p.id,
                p.division_id,
                p.user_id,
                p.first_name,
                p.last_name,
                p.alt_first_name,
                p.alt_last_name,
                p.address1,
                p.address2,
                p.city,
                p.county,
                p.state,
                p.zip,
                p.year_built,
                p.phone1,
                p.phone2,
                p.email,
                p.notes,
                p.add_user_id,
                p.add_date,
                p.marketsharp_id,
                p.leap_customer_id,
                p.third_party_source_id,
                p.updated_at,
                tps.third_party_id AS hubspot_contact_id
            FROM {self.table_name} p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            {where_clause}
             ORDER BY p.id LIMIT {chunk_size} OFFSET {offset}
        """
    
    def get_record_count(self, since_date: Optional[datetime] = None) -> int:
        """Get total count of prospect records for the sync"""
        
        where_clause = ""
        if since_date:
            where_clause = f"WHERE p.updated_at >= '{since_date}'"
            
        query = f"SELECT COUNT(*) FROM {self.table_name} p {where_clause}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
