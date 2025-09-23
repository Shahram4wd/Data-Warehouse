"""
Lead client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusLeadClient(GeniusBaseClient):
    """Client for accessing Genius CRM lead data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'lead'
    
    def get_leads(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch leads from Genius database"""
        
        # Base query with all required fields
        query = """
        SELECT 
            l.lead_id,
            l.first_name,
            l.last_name,
            l.email,
            l.phone1 as phone,
            l.address1 as address,
            l.city,
            l.state,
            l.zip as zip_code,
            l.source as prospect_source_id,
            l.added_by as user_id,
            l.division as division_id,
            l.notes,
            l.status,
            l.copied_to_id as converted_to_prospect_id,
            l.added_on as created_at,
            l.updated_at
        FROM `lead` l
        """
        
        # Add WHERE clause for incremental sync - handle both updated_at and added_on
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            query += f" WHERE (l.updated_at > '{since_str}' OR (l.updated_at IS NULL AND l.added_on > '{since_str}'))"
        
        # Add ordering and limit
        query += " ORDER BY l.lead_id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_leads_chunked(self, since_date: Optional[datetime] = None, chunk_size: int = 1000):
        """Generator that yields chunks of leads to handle large datasets efficiently"""
        offset = 0
        
        while True:
            # Base query with all required fields
            query = """
            SELECT 
                l.lead_id,
                l.first_name,
                l.last_name,
                l.email,
                l.phone1 as phone,
                l.address1 as address,
                l.city,
                l.state,
                l.zip as zip_code,
                l.source as prospect_source_id,
                l.added_by as user_id,
                l.division as division_id,
                l.notes,
                l.status,
                l.copied_to_id as converted_to_prospect_id,
                l.added_on as created_at,
                l.updated_at
            FROM `lead` l
            """
            
            # Add WHERE clause for incremental sync - handle both updated_at and added_on
            if since_date:
                since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
                query += f" WHERE (l.updated_at > '{since_str}' OR (l.updated_at IS NULL AND l.added_on > '{since_str}'))"
            
            # Add ordering and pagination
            query += f" ORDER BY l.lead_id LIMIT {chunk_size} OFFSET {offset}"
            
            logger.info(f"Executing chunked query (offset: {offset}, chunk_size: {chunk_size}): {query}")
            chunk_results = self.execute_query(query)
            
            if not chunk_results:
                # No more records, break the loop
                break
            
            yield chunk_results
            
            # If we got less than chunk_size records, we've reached the end
            if len(chunk_results) < chunk_size:
                break
            
            offset += chunk_size
    
    def get_chunked_leads(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> List[tuple]:
        """Get chunked leads data"""
        # Base query with all required fields
        query = """
        SELECT 
            l.lead_id,
            l.first_name,
            l.last_name,
            l.email,
            l.phone1 as phone,
            l.address1 as address,
            l.city,
            l.state,
            l.zip as zip_code,
            l.source as prospect_source_id,
            l.added_by as user_id,
            l.division as division_id,
            l.notes,
            l.status,
            l.copied_to_id as converted_to_prospect_id,
            l.added_on as created_at,
            l.updated_at
        FROM `lead` l
        """
        
        # Add WHERE clause for incremental sync - handle both updated_at and added_on
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            query += f" WHERE (l.updated_at > '{since_str}' OR (l.updated_at IS NULL AND l.added_on > '{since_str}'))"
        
        # Add ordering and pagination
        query += f" ORDER BY l.lead_id LIMIT {chunk_size} OFFSET {offset}"
        
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> str:
        """Get the chunked query for logging purposes"""
        # Base query with all required fields
        query = """
        SELECT 
            l.lead_id,
            l.first_name,
            l.last_name,
            l.email,
            l.phone1 as phone,
            l.address1 as address,
            l.city,
            l.state,
            l.zip as zip_code,
            l.source as prospect_source_id,
            l.added_by as user_id,
            l.division as division_id,
            l.notes,
            l.status,
            l.copied_to_id as converted_to_prospect_id,
            l.added_on as created_at,
            l.updated_at
        FROM `lead` l
        """
        
        # Add WHERE clause for incremental sync - handle both updated_at and added_on
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            query += f" WHERE (l.updated_at > '{since_str}' OR (l.updated_at IS NULL AND l.added_on > '{since_str}'))"
        
        # Add ordering and pagination
        query += f" ORDER BY l.lead_id LIMIT {chunk_size} OFFSET {offset}"
        
        return query

    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation"""
        return [
            'lead_id',  # Changed from 'id' to 'lead_id'
            'first_name',
            'last_name',
            'email',
            'phone',
            'address',
            'city',
            'state',
            'zip_code',
            'prospect_source_id',
            'user_id',
            'division_id',
            'notes',
            'status',
            'converted_to_prospect_id',
            'created_at',
            'updated_at'
        ]
