"""
Base AWS Athena client for SalesPro data sync operations
"""
import logging
from typing import Dict, Any, List, Optional
from django.conf import settings
from ingestion.base.client import BaseAPIClient
from ingestion.base.exceptions import APIException
from ingestion.utils import get_athena_client
from ingestion.athena_client import AthenaClient

logger = logging.getLogger(__name__)

class SalesProBaseClient(BaseAPIClient):
    """Base AWS Athena client for SalesPro operations"""
    
    def __init__(self, **kwargs):
        # AWS Athena doesn't use a traditional base URL pattern
        super().__init__(base_url="", timeout=120)  # Longer timeout for Athena queries
        self.athena_client = None
        
    async def authenticate(self) -> None:
        """Initialize AWS Athena client with credentials"""
        try:
            self.athena_client = get_athena_client()
            logger.info("AWS Athena client initialized for SalesPro operations")
        except Exception as e:
            logger.error(f"Failed to initialize Athena client: {e}")
            raise APIException(f"Athena client initialization failed: {e}")
    
    async def execute_query(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Execute an Athena query and return results"""
        if not self.athena_client:
            raise APIException("Athena client not initialized")
        
        try:
            logger.debug(f"Executing Athena query: {query[:100]}...")
            results = self.athena_client.execute_query(query)
            logger.info(f"Query returned {len(results)} records")
            return results
        except Exception as e:
            logger.error(f"Athena query failed: {e}")
            raise APIException(f"Query execution failed: {e}")
    
    async def get_table_count(self, table_name: str, where_clause: str = "") -> int:
        """Get record count from a table"""
        query = f"SELECT COUNT(*) as count FROM {table_name}"
        if where_clause:
            query += f" WHERE {where_clause}"
        
        try:
            results = await self.execute_query(query)
            return results[0]['count'] if results else 0
        except Exception as e:
            logger.error(f"Failed to get table count: {e}")
            return 0
    
    async def test_connection(self) -> bool:
        """Test the Athena connection"""
        try:
            # Simple test query
            await self.execute_query("SELECT 1 as test_value")
            return True
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False
