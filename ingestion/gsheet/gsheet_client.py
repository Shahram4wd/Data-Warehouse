"""
Google Sheets API Client

Client implementation for accessing Google Sheets data following sync_crm_guide.md patterns.
Handles authentication, sheet access, and data retrieval.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
import re
from datetime import datetime
import time

# Google Sheets API imports (will be available after dependency installation)
try:
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from google.auth.exceptions import GoogleAuthError
    GOOGLE_APIS_AVAILABLE = True
except ImportError:
    GOOGLE_APIS_AVAILABLE = False
    # Mock classes for development without dependencies
    class HttpError(Exception):
        pass
    class GoogleAuthError(Exception):
        pass

from ingestion.config.gsheet_config import GSheetConfig, GSheetAuthenticator
from ingestion.base.exceptions import SyncError, AuthenticationError, ValidationError


logger = logging.getLogger(__name__)


class GSheetClient:
    """
    Google Sheets API client following sync_crm_guide.md patterns
    
    Provides methods for:
    - Authenticating with Google Sheets API
    - Reading sheet metadata and structure
    - Retrieving sheet data in various formats
    - Handling API rate limits and errors
    """
    
    def __init__(self, config: GSheetConfig = None):
        """
        Initialize Google Sheets client
        
        Args:
            config: GSheetConfig instance, creates default if None
        """
        self.config = config or GSheetConfig()
        self.authenticator = GSheetAuthenticator(self.config)
        self._service = None
        self._last_request_time = 0
        self._rate_limit_delay = 0.1  # 100ms between requests
        
    def _get_service(self):
        """Get authenticated Google Sheets service"""
        if not GOOGLE_APIS_AVAILABLE:
            raise SyncError(
                "Google APIs not available. Install: pip install google-auth google-auth-oauthlib google-api-python-client"
            )
        
        if self._service is None:
            try:
                credentials = self.authenticator.get_credentials()
                self._service = build('sheets', 'v4', credentials=credentials)
                logger.info("Google Sheets service initialized successfully")
            except GoogleAuthError as e:
                logger.error(f"Authentication failed: {e}")
                raise AuthenticationError(f"Failed to authenticate with Google Sheets: {e}")
            except Exception as e:
                logger.error(f"Failed to initialize Google Sheets service: {e}")
                raise SyncError(f"Service initialization failed: {e}")
        
        return self._service
    
    def _rate_limit(self):
        """Apply rate limiting between API requests"""
        current_time = time.time()
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self._rate_limit_delay:
            sleep_time = self._rate_limit_delay - time_since_last
            time.sleep(sleep_time)
        
        self._last_request_time = time.time()
    
    def _extract_sheet_id(self, url_or_id: str) -> str:
        """
        Extract sheet ID from Google Sheets URL or return ID if already extracted
        
        Args:
            url_or_id: Google Sheets URL or sheet ID
            
        Returns:
            str: Sheet ID
            
        Raises:
            ValidationError: If URL/ID format is invalid
        """
        # If it's already a sheet ID (44 characters, alphanumeric and some symbols)
        if re.match(r'^[a-zA-Z0-9_-]{44}$', url_or_id):
            return url_or_id
        
        # Extract from various Google Sheets URL formats
        patterns = [
            r'/spreadsheets/d/([a-zA-Z0-9_-]{44})',
            r'key=([a-zA-Z0-9_-]{44})',
            r'id=([a-zA-Z0-9_-]{44})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url_or_id)
            if match:
                return match.group(1)
        
        raise ValidationError(f"Invalid Google Sheets URL or ID: {url_or_id}")
    
    def get_sheet_metadata(self, sheet_url_or_id: str) -> Dict[str, Any]:
        """
        Get metadata about a Google Sheet
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            
        Returns:
            Dict containing sheet metadata
            
        Raises:
            SyncError: If API request fails
        """
        sheet_id = self._extract_sheet_id(sheet_url_or_id)
        service = self._get_service()
        
        try:
            self._rate_limit()
            
            # Get spreadsheet metadata
            result = service.spreadsheets().get(
                spreadsheetId=sheet_id,
                includeGridData=False
            ).execute()
            
            metadata = {
                'sheet_id': sheet_id,
                'title': result.get('properties', {}).get('title', 'Untitled'),
                'locale': result.get('properties', {}).get('locale', 'en_US'),
                'time_zone': result.get('properties', {}).get('timeZone', 'UTC'),
                'sheets': []
            }
            
            # Process sheet tabs
            for sheet in result.get('sheets', []):
                sheet_props = sheet.get('properties', {})
                metadata['sheets'].append({
                    'sheet_id': sheet_props.get('sheetId'),
                    'title': sheet_props.get('title', 'Sheet1'),
                    'index': sheet_props.get('index', 0),
                    'sheet_type': sheet_props.get('sheetType', 'GRID'),
                    'grid_properties': sheet_props.get('gridProperties', {})
                })
            
            logger.info(f"Retrieved metadata for sheet: {metadata['title']}")
            return metadata
            
        except HttpError as e:
            logger.error(f"HTTP error retrieving sheet metadata: {e}")
            if e.resp.status == 403:
                raise AuthenticationError("Access denied. Check sharing permissions.")
            elif e.resp.status == 404:
                raise ValidationError("Sheet not found. Check URL/ID.")
            else:
                raise SyncError(f"Failed to retrieve sheet metadata: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving sheet metadata: {e}")
            raise SyncError(f"Failed to retrieve sheet metadata: {e}")
    
    def get_sheet_values(self, sheet_url_or_id: str, range_name: str = None, 
                        sheet_name: str = None) -> List[List[str]]:
        """
        Get values from a Google Sheet
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            range_name: A1 notation range (e.g., 'A1:Z1000'), defaults to entire sheet
            sheet_name: Specific sheet tab name, defaults to first sheet
            
        Returns:
            List of rows, each row is a list of cell values
            
        Raises:
            SyncError: If API request fails
        """
        sheet_id = self._extract_sheet_id(sheet_url_or_id)
        service = self._get_service()
        
        # Build range string
        if not range_name:
            if sheet_name:
                range_str = sheet_name
            else:
                range_str = 'A:ZZ'  # Get all columns
        else:
            if sheet_name:
                range_str = f"{sheet_name}!{range_name}"
            else:
                range_str = range_name
        
        try:
            self._rate_limit()
            
            result = service.spreadsheets().values().get(
                spreadsheetId=sheet_id,
                range=range_str,
                valueRenderOption='UNFORMATTED_VALUE',
                dateTimeRenderOption='FORMATTED_STRING'
            ).execute()
            
            values = result.get('values', [])
            logger.info(f"Retrieved {len(values)} rows from sheet range: {range_str}")
            
            return values
            
        except HttpError as e:
            logger.error(f"HTTP error retrieving sheet values: {e}")
            if e.resp.status == 403:
                raise AuthenticationError("Access denied. Check sharing permissions.")
            elif e.resp.status == 404:
                raise ValidationError("Sheet or range not found.")
            else:
                raise SyncError(f"Failed to retrieve sheet values: {e}")
        except Exception as e:
            logger.error(f"Unexpected error retrieving sheet values: {e}")
            raise SyncError(f"Failed to retrieve sheet values: {e}")
    
    def get_sheet_structure(self, sheet_url_or_id: str, 
                           sheet_name: str = None) -> Dict[str, Any]:
        """
        Analyze sheet structure and detect headers
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            sheet_name: Specific sheet tab name
            
        Returns:
            Dict containing structure information:
            - headers: List of column headers
            - sample_data: First few data rows
            - total_rows: Total number of rows with data
            - suggested_mappings: Suggested field mappings
        """
        # Get first 10 rows to analyze structure
        values = self.get_sheet_values(
            sheet_url_or_id, 
            range_name='1:10',
            sheet_name=sheet_name
        )
        
        if not values:
            return {
                'headers': [],
                'sample_data': [],
                'total_rows': 0,
                'suggested_mappings': {}
            }
        
        # Assume first row contains headers
        headers = values[0] if values else []
        sample_data = values[1:] if len(values) > 1 else []
        
        # Get total row count by checking a large range
        all_values = self.get_sheet_values(sheet_url_or_id, sheet_name=sheet_name)
        total_rows = len(all_values)
        
        # Generate suggested field mappings
        suggested_mappings = self._suggest_field_mappings(headers)
        
        structure = {
            'headers': headers,
            'sample_data': sample_data,
            'total_rows': total_rows,
            'total_columns': len(headers),
            'suggested_mappings': suggested_mappings
        }
        
        logger.info(f"Analyzed sheet structure: {len(headers)} columns, {total_rows} rows")
        return structure
    
    def _suggest_field_mappings(self, headers: List[str]) -> Dict[str, str]:
        """
        Suggest field mappings based on header names
        
        Args:
            headers: List of column headers
            
        Returns:
            Dict mapping header names to model field names
        """
        mappings = {}
        
        # Common header patterns and their corresponding model fields
        field_patterns = {
            # Name fields
            'first_name': [r'first.?name', r'fname', r'given.?name'],
            'last_name': [r'last.?name', r'lname', r'surname', r'family.?name'],
            'full_name': [r'full.?name', r'name', r'contact.?name'],
            
            # Contact fields
            'email': [r'email', r'e.?mail', r'email.?address'],
            'phone': [r'phone', r'telephone', r'mobile', r'cell'],
            
            # Address fields
            'address': [r'address', r'street', r'addr'],
            'city': [r'city', r'town'],
            'state': [r'state', r'province', r'region'],
            'zip_code': [r'zip', r'postal', r'postcode'],
            'country': [r'country', r'nation'],
            
            # Business fields
            'company': [r'company', r'organization', r'business', r'firm'],
            'title': [r'title', r'position', r'job.?title', r'role'],
            
            # Lead fields
            'lead_status': [r'status', r'lead.?status', r'stage'],
            'lead_source': [r'source', r'lead.?source', r'origin'],
            'notes': [r'notes', r'comments', r'description', r'remarks'],
            
            # Dates
            'created_date': [r'created', r'date.?created', r'timestamp'],
            'updated_date': [r'updated', r'modified', r'date.?updated'],
        }
        
        for header in headers:
            header_lower = header.lower().strip()
            
            for field_name, patterns in field_patterns.items():
                for pattern in patterns:
                    if re.search(pattern, header_lower):
                        mappings[header] = field_name
                        break
                
                if header in mappings:
                    break
        
        return mappings
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test connection to Google Sheets API
        
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            service = self._get_service()
            
            # Try to get a simple API response
            self._rate_limit()
            
            # Create a test spreadsheet to verify write access
            test_request = {
                'properties': {
                    'title': f'API Test - {datetime.now().strftime("%Y%m%d_%H%M%S")}'
                }
            }
            
            result = service.spreadsheets().create(body=test_request).execute()
            test_sheet_id = result['spreadsheetId']
            
            # Clean up test sheet
            service.spreadsheets().batchUpdate(
                spreadsheetId=test_sheet_id,
                body={'requests': [{'deleteSheet': {'sheetId': 0}}]}
            ).execute()
            
            return True, "Successfully connected to Google Sheets API"
            
        except AuthenticationError as e:
            return False, f"Authentication failed: {e}"
        except Exception as e:
            return False, f"Connection test failed: {e}"
    
    def get_batch_data(self, sheet_url_or_id: str, batch_size: int = 1000,
                      sheet_name: str = None, start_row: int = 2) -> List[List[str]]:
        """
        Get sheet data in batches for large sheets
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            batch_size: Number of rows per batch
            sheet_name: Specific sheet tab name
            start_row: Row number to start from (1-based)
            
        Yields:
            List of row data for each batch
        """
        # First get the total number of rows
        structure = self.get_sheet_structure(sheet_url_or_id, sheet_name)
        total_rows = structure['total_rows']
        
        current_row = start_row
        
        while current_row <= total_rows:
            end_row = min(current_row + batch_size - 1, total_rows)
            
            range_name = f"{current_row}:{end_row}"
            
            batch_data = self.get_sheet_values(
                sheet_url_or_id,
                range_name=range_name,
                sheet_name=sheet_name
            )
            
            if batch_data:
                yield batch_data
            
            current_row = end_row + 1
            
            # Small delay between batches
            time.sleep(0.2)
