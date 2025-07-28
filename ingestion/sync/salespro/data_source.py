"""
SalesPro data source implementation following CRM sync guide patterns
"""
import logging
from typing import Dict, Any, List, AsyncGenerator, Optional
from datetime import datetime
from abc import ABC, abstractmethod
from asgiref.sync import sync_to_async
from ingestion.utils import get_athena_client

logger = logging.getLogger(__name__)


class DataSourceFactory:
    """Factory for creating appropriate data source clients following CRM sync guide"""
    
    @staticmethod
    def create_client(crm_source: str, source_type: str, **kwargs):
        """Create appropriate client based on source type"""
        source_map = {
            'database': DatabaseDataSource,
            'api': None,  # Not used for SalesPro
            'csv': None,  # Not used for SalesPro
            'webhook': None  # Not used for SalesPro
        }
        
        client_class = source_map.get(source_type)
        if not client_class:
            raise ValueError(f"Unsupported source type for {crm_source}: {source_type}")
        
        return client_class(crm_source, **kwargs)


class BaseDataSource(ABC):
    """Base data source following CRM sync guide patterns"""
    
    def __init__(self, crm_source: str, **kwargs):
        self.crm_source = crm_source
        self.connection = None
        
    @abstractmethod
    async def initialize(self):
        """Initialize the data source connection"""
        pass
        
    @abstractmethod
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch data from the source"""
        pass
        
    @abstractmethod
    async def get_total_count(self, **kwargs) -> int:
        """Get total record count"""
        pass
        
    @abstractmethod
    async def cleanup(self):
        """Cleanup resources"""
        pass


class DatabaseDataSource(BaseDataSource):
    """Database data source for SalesPro AWS Athena following CRM sync guide"""
    
    def __init__(self, crm_source: str, table_name: str, **kwargs):
        super().__init__(crm_source, **kwargs)
        self.table_name = table_name
        self.batch_size = kwargs.get('batch_size', 500)
        
    async def initialize(self):
        """Initialize AWS Athena connection"""
        try:
            self.connection = await sync_to_async(get_athena_client)()
            logger.info(f"SalesPro {self.table_name} data source initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize SalesPro data source: {e}")
            raise
            
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch data from AWS Athena following CRM sync guide patterns"""
        if not self.connection:
            await self.initialize()
            
        try:
            query = self.build_query(**kwargs)
            logger.info(f"SalesPro {self.table_name} executing query: {query[:200]}...")
            
            # Execute query
            column_names, rows = await sync_to_async(
                self.connection.get_query_with_columns
            )(query, database='home_genius_db')
            
            if not rows:
                logger.info(f"SalesPro {self.table_name}: No data found")
                return
                
            logger.info(f"SalesPro {self.table_name}: Retrieved {len(rows)} rows")
            
            # Process in batches following CRM sync guide
            for i in range(0, len(rows), self.batch_size):
                batch_rows = rows[i:i + self.batch_size]
                batch = [dict(zip(column_names, row)) for row in batch_rows]
                yield batch
                
        except Exception as e:
            logger.error(f"SalesPro {self.table_name} data fetch failed: {e}")
            raise
            
    async def get_total_count(self, **kwargs) -> int:
        """Get total record count following CRM sync guide"""
        if not self.connection:
            await self.initialize()
            
        try:
            count_query = self.build_count_query(**kwargs)
            column_names, rows = await sync_to_async(
                self.connection.get_query_with_columns
            )(count_query, database='home_genius_db')
            
            if rows and len(rows) > 0:
                total_count = int(rows[0][0])
                logger.info(f"SalesPro {self.table_name}: Total records available: {total_count:,}")
                return total_count
            else:
                logger.warning(f"SalesPro {self.table_name}: Could not get record count")
                return 0
                
        except Exception as e:
            logger.warning(f"SalesPro {self.table_name} count query failed: {e}")
            return 0
            
    def build_query(self, **kwargs) -> str:
        """Build SQL query for data retrieval following CRM sync guide"""
        base_table = self.table_name
        
        if self.table_name == 'lead_results':
            query = f"""
            SELECT estimate_id, company_id, lead_results, created_at, updated_at
            FROM {base_table}
            WHERE estimate_id IS NOT NULL AND estimate_id != ''
            ORDER BY created_at
            """
        else:
            query = f"SELECT * FROM {base_table}"
            
        # Add incremental sync conditions following CRM sync guide
        conditions = []
        
        since_date = kwargs.get('since_date')
        if since_date and self.table_name != 'lead_results':
            since_date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            conditions.append(f"updated_at > timestamp '{since_date_str}'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Add limits following CRM sync guide
        max_records = kwargs.get('max_records', 0)
        if max_records > 0:
            query += f" LIMIT {max_records}"
            
        return query
        
    def build_count_query(self, **kwargs) -> str:
        """Build count query following CRM sync guide"""
        base_table = self.table_name
        
        if self.table_name == 'lead_results':
            query = f"""
            SELECT COUNT(*) as total_count
            FROM {base_table}
            WHERE estimate_id IS NOT NULL AND estimate_id != ''
            """
        else:
            query = f"SELECT COUNT(*) as total_count FROM {base_table}"
            
        # Add same conditions as main query
        conditions = []
        since_date = kwargs.get('since_date')
        if since_date and self.table_name != 'lead_results':
            since_date_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            conditions.append(f"updated_at > timestamp '{since_date_str}'")
            
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        return query
        
    async def cleanup(self):
        """Cleanup database resources following CRM sync guide"""
        try:
            if self.connection:
                # Close any open connections if needed
                self.connection = None
            logger.debug(f"SalesPro {self.table_name} data source cleanup completed")
        except Exception as e:
            logger.warning(f"SalesPro {self.table_name} cleanup warning: {e}")
