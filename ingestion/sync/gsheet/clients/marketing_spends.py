"""
Google Sheets Marketing Spends Client
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import GoogleSheetsAPIClient as GoogleSheetsClient

logger = logging.getLogger(__name__)


class MarketingSpendsClient(GoogleSheetsClient):
    """
    Client for Marketing Spends Google Sheet
    
    Sheet URL: https://docs.google.com/spreadsheets/d/17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg/edit?gid=0#gid=0
    Tab: All Marketing Spend
    """
    
    def __init__(self, sheet_id: str = None, tab_name: str = None):
        super().__init__()
        
        # Sheet configuration - use passed parameters or defaults
        self.sheet_id = sheet_id or "17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg"
        self.tab_name = tab_name or "All Marketing Spend"
        self.header_row = 1
        self.data_start_row = 2
        
        logger.info(f"Initialized MarketingSpendsClient for sheet {self.sheet_id}")
    
    def is_sheet_modified_since_sync(self, last_sync_time) -> bool:
        """
        Check if the sheet has been modified since the last sync
        
        Args:
            last_sync_time: UTC datetime of last sync
            
        Returns:
            bool: True if sheet has been modified
        """
        try:
            sheet_info = self.get_sheet_info()
            last_modified = sheet_info.get('last_modified')
            
            if not last_modified or not last_sync_time:
                return True
                
            # Convert string to datetime if needed
            if isinstance(last_modified, str):
                last_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            
            return last_modified > last_sync_time
            
        except Exception as e:
            logger.error(f"Error checking sheet modification: {e}")
            # Default to True if we can't determine
            return True
    
    def get_marketing_spends_data(self) -> List[Dict[str, Any]]:
        """
        Get marketing spends data from the sheet
        
        Returns:
            List of dictionaries containing marketing spend records
        """
        try:
            logger.info("Fetching marketing spends data from Google Sheets")
            
            data = self.get_all_data_with_headers(
                sheet_id=self.sheet_id,
                tab_name=self.tab_name,
                header_row=self.header_row,
                data_start_row=self.data_start_row
            )
            
            logger.info(f"Retrieved {len(data)} marketing spend records from sheet")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get marketing spends data: {e}")
            raise
    
    def is_sheet_modified_since_sync(self, last_sync_time) -> bool:
        """
        Check if the sheet has been modified since the last sync
        
        Args:
            last_sync_time: UTC datetime of last sync
            
        Returns:
            bool: True if sheet has been modified
        """
        try:
            sheet_info = self.get_sheet_info()
            last_modified = sheet_info.get('last_modified')
            
            if not last_modified or not last_sync_time:
                return True
                
            # Convert string to datetime if needed
            if isinstance(last_modified, str):
                last_modified = datetime.fromisoformat(last_modified.replace('Z', '+00:00'))
            
            return last_modified > last_sync_time
            
        except Exception as e:
            logger.error(f"Error checking sheet modification: {e}")
            # Default to True if we can't determine
            return True
    
    def get_sheet_info(self) -> Dict[str, Any]:
        """
        Get sheet metadata information
        
        Returns:
            Dictionary containing sheet information
        """
        try:
            logger.info(f"Getting sheet info for {self.sheet_id}")
            
            # Get basic sheet metadata
            sheet_info = self.get_sheet_metadata(self.sheet_id)
            
            # Get headers for additional info
            headers = self.get_headers()
            
            # Estimate data rows (this is approximate)
            estimated_rows = self.get_estimated_row_count(
                sheet_id=self.sheet_id,
                tab_name=self.tab_name
            )
            
            result = {
                'sheet_id': self.sheet_id,
                'tab_name': self.tab_name,
                'name': sheet_info.get('name', 'Unknown'),
                'last_modified': sheet_info.get('modifiedTime'),
                'header_count': len(headers),
                'headers': headers,
                'estimated_data_rows': max(0, estimated_rows - self.header_row) if estimated_rows else 0
            }
            
            logger.info(f"Sheet info retrieved: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Failed to get sheet info: {e}")
            raise
    
    def fetch_sheet_data_sync(self) -> List[Dict[str, Any]]:
        """
        Synchronous method to fetch data from Google Sheets
        
        Returns:
            List of dictionaries containing row data
        """
        try:
            logger.info(f"Fetching data from sheet {self.sheet_id}, tab '{self.tab_name}'")
            
            # Use the existing method to get data with headers
            data = self.get_all_data_with_headers(
                sheet_id=self.sheet_id,
                tab_name=self.tab_name,
                header_row=self.header_row,
                data_start_row=self.data_start_row
            )
            
            logger.info(f"Successfully fetched {len(data)} rows from Google Sheets")
            return data
            
        except Exception as e:
            logger.error(f"Failed to fetch sheet data: {e}")
            raise
    
    def authenticate(self) -> None:
        """Authenticate with Google Sheets API"""
        try:
            self._authenticate()  # Call the base class method
            logger.info("Google Sheets authentication successful")
        except Exception as e:
            logger.error(f"Google Sheets authentication failed: {e}")
            raise
    
    def get_rate_limit_headers(self) -> Dict[str, str]:
        """Return rate limit headers for Google Sheets API"""
        return {
            'X-RateLimit-Requests-Per-100Seconds': '100',
            'X-RateLimit-Requests-Per-Day': '10000'
        }
