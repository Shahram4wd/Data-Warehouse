"""
Google Sheets API Authentication Configuration

Provides authentication methods for Google Sheets API access including
OAuth2 and Service Account authentication.
"""

import os
import json
from typing import Dict, Any, Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google.auth.exceptions import RefreshError
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsAuthManager:
    """
    Manages Google Sheets API authentication using OAuth2 or Service Account
    """
    
    # OAuth2 scopes required for Google Sheets access
    SCOPES = [
        'https://www.googleapis.com/auth/spreadsheets.readonly',
        'https://www.googleapis.com/auth/drive.readonly'
    ]
    
    def __init__(self):
        """Initialize authentication manager"""
        self.credentials = None
        self.auth_method = None
    
    def authenticate_with_service_account(self, 
                                        service_account_file: str) -> bool:
        """
        Authenticate using Service Account credentials
        
        Args:
            service_account_file: Path to service account JSON file
            
        Returns:
            bool: True if authentication successful
        """
        try:
            if not os.path.exists(service_account_file):
                logger.error(f"Service account file not found: {service_account_file}")
                return False
            
            self.credentials = ServiceAccountCredentials.from_service_account_file(
                service_account_file, 
                scopes=self.SCOPES
            )
            
            self.auth_method = 'service_account'
            logger.info("Successfully authenticated with service account")
            return True
            
        except Exception as e:
            logger.error(f"Service account authentication failed: {e}")
            return False
    
    def authenticate_with_oauth2(self, 
                                credentials_file: str,
                                token_file: str = 'token.json') -> bool:
        """
        Authenticate using OAuth2 flow
        
        Args:
            credentials_file: Path to OAuth2 credentials JSON file
            token_file: Path to store/load access token
            
        Returns:
            bool: True if authentication successful
        """
        try:
            creds = None
            
            # Load existing token if available
            if os.path.exists(token_file):
                creds = Credentials.from_authorized_user_file(token_file, self.SCOPES)
            
            # If no valid credentials available, run OAuth flow
            if not creds or not creds.valid:
                if creds and creds.expired and creds.refresh_token:
                    try:
                        creds.refresh(Request())
                        logger.info("Refreshed OAuth2 credentials")
                    except RefreshError:
                        logger.warning("Token refresh failed, running new OAuth flow")
                        creds = None
                
                if not creds:
                    if not os.path.exists(credentials_file):
                        logger.error(f"OAuth2 credentials file not found: {credentials_file}")
                        return False
                    
                    flow = InstalledAppFlow.from_client_secrets_file(
                        credentials_file, self.SCOPES
                    )
                    creds = flow.run_local_server(port=0)
                    logger.info("Completed OAuth2 authentication flow")
                
                # Save credentials for next run
                with open(token_file, 'w') as token:
                    token.write(creds.to_json())
                    logger.info(f"Saved OAuth2 token to {token_file}")
            
            self.credentials = creds
            self.auth_method = 'oauth2'
            logger.info("Successfully authenticated with OAuth2")
            return True
            
        except Exception as e:
            logger.error(f"OAuth2 authentication failed: {e}")
            return False
    
    def get_credentials(self) -> Optional[Credentials]:
        """
        Get current authentication credentials
        
        Returns:
            Credentials object or None if not authenticated
        """
        return self.credentials
    
    def is_authenticated(self) -> bool:
        """
        Check if currently authenticated
        
        Returns:
            bool: True if authenticated and credentials are valid
        """
        if not self.credentials:
            return False
        
        try:
            if hasattr(self.credentials, 'valid'):
                return self.credentials.valid
            return True
        except Exception:
            return False
    
    def get_auth_info(self) -> Dict[str, Any]:
        """
        Get information about current authentication
        
        Returns:
            Dictionary with authentication details
        """
        if not self.is_authenticated():
            return {
                'authenticated': False,
                'method': None,
                'scopes': self.SCOPES
            }
        
        info = {
            'authenticated': True,
            'method': self.auth_method,
            'scopes': self.SCOPES
        }
        
        if hasattr(self.credentials, 'service_account_email'):
            info['service_account'] = self.credentials.service_account_email
        
        if hasattr(self.credentials, 'expiry'):
            info['expires_at'] = self.credentials.expiry.isoformat() if self.credentials.expiry else None
        
        return info


def get_default_auth_manager() -> GoogleSheetsAuthManager:
    """
    Get default authentication manager with environment-based configuration
    
    Returns:
        Configured GoogleSheetsAuthManager instance
    """
    auth_manager = GoogleSheetsAuthManager()
    
    # Try service account authentication first (preferred for production)
    service_account_file = os.getenv('GOOGLE_SERVICE_ACCOUNT_FILE')
    if service_account_file:
        if auth_manager.authenticate_with_service_account(service_account_file):
            return auth_manager
        logger.warning("Service account authentication failed, trying OAuth2")
    
    # Fall back to OAuth2 authentication
    credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE', 'credentials.json')
    token_file = os.getenv('GOOGLE_TOKEN_FILE', 'token.json')
    
    if auth_manager.authenticate_with_oauth2(credentials_file, token_file):
        return auth_manager
    
    logger.error("All authentication methods failed")
    return auth_manager
