"""
Prospects client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List, AsyncGenerator
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)

class GeniusProspectsClient(GeniusBaseClient):
    """Client for accessing Genius prospects data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'prospect'
    
    def fetch_batch(self, offset: int, batch_size: int, since_date: Optional[datetime] = None) -> List[tuple]:
        """Fetch a batch of prospect records"""
        
        # Build the comprehensive SELECT query with all fields including user_id and year_built
        query = f"""
            SELECT p.id, p.division_id, p.user_id, p.first_name, p.last_name, p.alt_first_name, p.alt_last_name,
                   p.address1, p.address2, p.city, p.county, p.state, p.zip, p.year_built, p.phone1, p.phone2, 
                   p.email, p.notes, p.add_user_id, p.add_date, p.marketsharp_id, p.leap_customer_id, 
                   p.third_party_source_id, p.updated_at, tps.third_party_id AS hubspot_contact_id
            FROM {self.table_name} AS p
            LEFT JOIN third_party_source AS tps 
              ON tps.id = p.third_party_source_id
            LEFT JOIN third_party_source_type AS tpst 
              ON tpst.id = tps.third_party_source_type_id AND tpst.label = 'hubspot'
            {self.build_where_clause(since_date, self.table_name)}
            ORDER BY p.id
            LIMIT {batch_size} OFFSET {offset}
        """
        
        return self.execute_query(query)
    
    def get_record_count(self, since_date: Optional[datetime] = None) -> int:
        """Get total count of prospect records for the sync"""
        if since_date:
            where_clause = self.build_where_clause(since_date, self.table_name)
            query = f"SELECT COUNT(*) FROM {self.table_name} {where_clause}"
        else:
            query = f"SELECT COUNT(*) FROM {self.table_name}"
        
        result = self.execute_query(query)
        return result[0][0] if result else 0
