"""
Google Sheets Marketing Leads Client
"""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from .base import GoogleSheetsAPIClient

logger = logging.getLogger(__name__)


class MarketingLeadsClient(GoogleSheetsAPIClient):
    """
    Client for Marketing Source Leads Google Sheet
    
    Sheet URL: https://docs.google.com/spreadsheets/d/1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo/edit
    Tab: Marketing Source Leads
    """
    
    def __init__(self, sheet_id: str = None, tab_name: str = None):
        super().__init__()
        
        # Sheet configuration - use passed parameters or defaults
        self.sheet_id = sheet_id or "1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo"
        self.tab_name = tab_name or "Marketing Source Leads"
        self.header_row = 1
        self.data_start_row = 2
        
        logger.info(f"Initialized MarketingLeadsClient for sheet {self.sheet_id}")
    
    def get_marketing_leads_data(self) -> List[Dict[str, Any]]:
        """
        Get all marketing leads data from the Google Sheet
        
        Returns:
            List of dictionaries containing lead data
        """
        try:
            logger.info(f"Fetching marketing leads data from {self.sheet_id}/{self.tab_name}")
            
            # Get all data with headers
            data = self.get_all_data_with_headers(
                sheet_id=self.sheet_id,
                tab_name=self.tab_name,
                header_row=self.header_row,
                data_start_row=self.data_start_row
            )
            
            # Get sheet modification time
            modification_time = self.get_sheet_modification_time(self.sheet_id)
            
            # Add metadata to each row
            for row in data:
                row['_sheet_last_modified'] = modification_time
                row['_sheet_id'] = self.sheet_id
                row['_tab_name'] = self.tab_name
            
            logger.info(f"Retrieved {len(data)} marketing leads records")
            return data
            
        except Exception as e:
            logger.error(f"Failed to get marketing leads data: {e}")
            raise
    
    def get_headers(self) -> List[str]:
        """
        Get header columns from the marketing leads sheet
        
        Returns:
            List of header names
        """
        try:
            headers = super().get_headers(
                sheet_id=self.sheet_id,
                tab_name=self.tab_name,
                header_row=self.header_row
            )
            
            logger.info(f"Found {len(headers)} headers: {headers}")
            return headers
            
        except Exception as e:
            logger.error(f"Failed to get headers: {e}")
            raise
    
    def get_sheet_info(self) -> Dict[str, Any]:
        """
        Get comprehensive information about the marketing leads sheet
        
        Returns:
            Dictionary containing sheet information
        """
        try:
            # Get sheet metadata
            metadata = self.get_sheet_metadata(self.sheet_id)
            
            # Get headers
            headers = self.get_headers()
            
            # Get row count estimate
            data = self.get_worksheet_data(self.sheet_id, self.tab_name)
            row_count = len([row for row in data if any(cell.strip() for cell in row if cell)])
            
            return {
                'sheet_id': self.sheet_id,
                'tab_name': self.tab_name,
                'name': metadata.get('name'),
                'last_modified': metadata.get('modified_time'),
                'headers': headers,
                'header_count': len(headers),
                'estimated_data_rows': max(0, row_count - 1),  # Subtract header row
                'total_rows': row_count
            }
            
        except Exception as e:
            logger.error(f"Failed to get sheet info: {e}")
            raise
    
    def check_if_sheet_modified(self, last_known_modified: Optional[datetime]) -> bool:
        """
        Check if the sheet has been modified since the last known modification time
        
        Args:
            last_known_modified: Last known modification time
            
        Returns:
            True if sheet has been modified or if last_known_modified is None
        """
        try:
            current_modified = self.get_sheet_modification_time(self.sheet_id)
            
            if not current_modified:
                logger.warning("Could not determine sheet modification time")
                return True  # Assume modified if we can't tell
            
            if not last_known_modified:
                logger.info("No previous modification time - treating as modified")
                return True
            
            # Compare modification times
            is_modified = current_modified > last_known_modified
            
            if is_modified:
                logger.info(f"Sheet modified: {current_modified} > {last_known_modified}")
            else:
                logger.info(f"Sheet not modified: {current_modified} <= {last_known_modified}")
            
            return is_modified
            
        except Exception as e:
            logger.error(f"Failed to check sheet modification: {e}")
            return True  # Assume modified on error
    
    # Abstract method implementations
    
    async def authenticate(self) -> None:
        """Authenticate with Google Sheets API"""
        try:
            await self.setup_oauth_authentication()
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
