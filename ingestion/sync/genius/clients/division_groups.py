"""
Division Group client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusDivisionGroupClient(GeniusBaseClient):
    """Client for accessing Genius CRM division group data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'division_group'
    
    def get_division_groups(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch division groups from Genius database"""
        
        # Base query selecting all fields from division_group table
        query = "SELECT dg.* FROM division_group dg"
        
        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY dg.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_field_mapping(self) -> List[str]:
        """Get field mapping for transformation - matches actual database columns"""
        return [
            'id',
            'group_label',
            'region',
            'default_time_zone_name',
            'intern_payroll_start',
            'painter_payroll_start',
            'is_active',
            'cc_profile_id',
            'mes_profile_id',
            'mes_profile_key',
            'docusign_acct_id',
            'paysimple_username',
            'paysimple_secret',
            'hub_account_id',
            'created_at',
            'updated_at'
        ]
