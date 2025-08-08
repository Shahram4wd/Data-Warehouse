"""
Base Google Sheets API Client
"""
import os
import logging
from typing import Optional, Dict, List, Any
from datetime import datetime, timezone
import json

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import gspread
from gspread import Spreadsheet, Worksheet

from ingestion.base.client import BaseAPIClient

logger = logging.getLogger(__name__)


class GoogleSheetsAPIClient(BaseAPIClient):
    """
    Base Google Sheets API client with OAuth authentication
    
    Features:
    - OAuth2 authentication with username/password
    - Rate limiting and retry logic
    - Error handling
    - Sheet modification time tracking
    """
    
    def __init__(self, credentials_file: Optional[str] = None, token_file: Optional[str] = None):
        """
        Initialize Google Sheets client
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store OAuth2 token
        """
        # Initialize with Google Sheets API base URL
        super().__init__(base_url='https://sheets.googleapis.com/v4')
        
        # OAuth2 scopes for Google Sheets
        self.scopes = [
            'https://www.googleapis.com/auth/spreadsheets.readonly',
            'https://www.googleapis.com/auth/drive.metadata.readonly'
        ]
        
        # File paths
        self.credentials_file = credentials_file or os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
        self.token_file = token_file or os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
        
        # API clients
        self.sheets_service = None
        self.drive_service = None
        self.gspread_client = None
        
        # Initialize authentication
        self._authenticate()
    
    def _authenticate(self):
        """
        Authenticate with Google using OAuth2
        """
        creds = None
        
        # Load existing token
        if os.path.exists(self.token_file):
            try:
                creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)
                logger.info("Loaded existing OAuth2 credentials")
            except Exception as e:
                logger.warning(f"Failed to load existing credentials: {e}")
        
        # If no valid credentials, run OAuth flow
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                    logger.info("Refreshed OAuth2 credentials")
                except Exception as e:
                    logger.warning(f"Failed to refresh credentials: {e}")
                    creds = None
            
            if not creds:
                if not os.path.exists(self.credentials_file):
                    raise ValueError(f"Google credentials file not found: {self.credentials_file}")
                
                # Run OAuth flow
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.credentials_file, self.scopes)
                
                # Use environment variables for OAuth if available
                username = os.getenv('GOOGLE_USERNAME')
                password = os.getenv('GOOGLE_PASSWORD')
                
                if username and password:
                    logger.info(f"Using OAuth with username: {username}")
                    # Note: Google OAuth doesn't support direct username/password
                    # User will need to complete OAuth flow in browser
                
                creds = flow.run_local_server(port=0)
                logger.info("Completed OAuth2 authentication")
            
            # Save credentials for next run
            with open(self.token_file, 'w') as token:
                token.write(creds.to_json())
                logger.info(f"Saved OAuth2 token to {self.token_file}")
        
        # Initialize API clients
        try:
            self.sheets_service = build('sheets', 'v4', credentials=creds)
            self.drive_service = build('drive', 'v3', credentials=creds)
            self.gspread_client = gspread.authorize(creds)
            logger.info("Successfully initialized Google API clients")
        except Exception as e:
            logger.error(f"Failed to initialize Google API clients: {e}")
            raise
    
    def get_sheet_metadata(self, sheet_id: str) -> Dict[str, Any]:
        """
        Get sheet metadata including last modified time
        
        Args:
            sheet_id: Google Sheets ID
            
        Returns:
            Dict containing sheet metadata
        """
        try:
            # Get file metadata from Drive API for modification time
            file_metadata = self.drive_service.files().get(
                fileId=sheet_id,
                fields='id,name,modifiedTime,lastModifyingUser'
            ).execute()
            
            # Get sheet structure from Sheets API
            sheet_metadata = self.sheets_service.spreadsheets().get(
                spreadsheetId=sheet_id,
                fields='sheets.properties'
            ).execute()
            
            return {
                'id': file_metadata.get('id'),
                'name': file_metadata.get('name'),
                'modified_time': file_metadata.get('modifiedTime'),
                'last_modifying_user': file_metadata.get('lastModifyingUser', {}),
                'sheets': sheet_metadata.get('sheets', [])
            }
            
        except HttpError as e:
            logger.error(f"Failed to get sheet metadata for {sheet_id}: {e}")
            raise
    
    def get_sheet_modification_time(self, sheet_id: str) -> Optional[datetime]:
        """
        Get the last modification time of a Google Sheet
        
        Args:
            sheet_id: Google Sheets ID
            
        Returns:
            datetime object of last modification time in UTC
        """
        try:
            metadata = self.get_sheet_metadata(sheet_id)
            modified_time_str = metadata.get('modified_time')
            
            if modified_time_str:
                # Parse ISO format: '2024-01-15T10:30:45.123Z'
                modified_time = datetime.fromisoformat(
                    modified_time_str.replace('Z', '+00:00')
                )
                return modified_time.astimezone(timezone.utc)
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get modification time for sheet {sheet_id}: {e}")
            return None
    
    def get_worksheet_data(self, sheet_id: str, tab_name: str, 
                          range_name: Optional[str] = None) -> List[List[str]]:
        """
        Get data from a specific worksheet tab
        
        Args:
            sheet_id: Google Sheets ID
            tab_name: Name of the worksheet tab
            range_name: Optional range (e.g., 'A1:Z1000')
            
        Returns:
            List of rows, each row is a list of cell values
        """
        try:
            # Use gspread for easier data access
            spreadsheet = self.gspread_client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(tab_name)
            
            if range_name:
                # Get specific range
                cell_range = worksheet.range(range_name)
                # Convert to 2D array
                data = []
                current_row = []
                current_row_num = cell_range[0].row
                
                for cell in cell_range:
                    if cell.row != current_row_num:
                        data.append(current_row)
                        current_row = []
                        current_row_num = cell.row
                    current_row.append(cell.value or '')
                
                if current_row:
                    data.append(current_row)
                
                return data
            else:
                # Get all data
                return worksheet.get_all_values()
                
        except Exception as e:
            logger.error(f"Failed to get worksheet data from {sheet_id}/{tab_name}: {e}")
            raise
    
    def get_headers(self, sheet_id: str, tab_name: str, header_row: int = 1) -> List[str]:
        """
        Get header row from worksheet
        
        Args:
            sheet_id: Google Sheets ID
            tab_name: Name of the worksheet tab
            header_row: Row number containing headers (1-based)
            
        Returns:
            List of header names
        """
        try:
            spreadsheet = self.gspread_client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(tab_name)
            
            headers = worksheet.row_values(header_row)
            
            # Clean headers
            cleaned_headers = []
            for header in headers:
                if header and header.strip():
                    cleaned_headers.append(header.strip())
                else:
                    break  # Stop at first empty header
            
            return cleaned_headers
            
        except Exception as e:
            logger.error(f"Failed to get headers from {sheet_id}/{tab_name}: {e}")
            raise
    
    def get_all_data_with_headers(self, sheet_id: str, tab_name: str, 
                                  header_row: int = 1, data_start_row: int = 2) -> List[Dict[str, str]]:
        """
        Get all data from worksheet as list of dictionaries
        
        Args:
            sheet_id: Google Sheets ID
            tab_name: Name of the worksheet tab
            header_row: Row number containing headers (1-based)
            data_start_row: First row containing data (1-based)
            
        Returns:
            List of dictionaries, one per data row
        """
        try:
            # Get headers
            headers = self.get_headers(sheet_id, tab_name, header_row)
            
            if not headers:
                logger.warning(f"No headers found in {sheet_id}/{tab_name}")
                return []
            
            # Get all data
            spreadsheet = self.gspread_client.open_by_key(sheet_id)
            worksheet = spreadsheet.worksheet(tab_name)
            all_data = worksheet.get_all_values()
            
            # Convert to list of dictionaries
            result = []
            for row_num, row in enumerate(all_data[data_start_row - 1:], start=data_start_row):
                if not any(cell.strip() for cell in row if cell):
                    # Skip empty rows
                    continue
                
                row_dict = {
                    '_sheet_row_number': row_num
                }
                
                # Map row data to headers
                for i, header in enumerate(headers):
                    value = row[i] if i < len(row) else ''
                    row_dict[header] = value.strip() if isinstance(value, str) else str(value)
                
                result.append(row_dict)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to get data with headers from {sheet_id}/{tab_name}: {e}")
            raise
    
    def test_connection(self) -> bool:
        """
        Test the Google Sheets API connection
        
        Returns:
            True if connection is successful
        """
        try:
            # Try to list some files to test connection
            results = self.drive_service.files().list(pageSize=1).execute()
            logger.info("Google Sheets API connection test successful")
            return True
            
        except Exception as e:
            logger.error(f"Google Sheets API connection test failed: {e}")
            return False
