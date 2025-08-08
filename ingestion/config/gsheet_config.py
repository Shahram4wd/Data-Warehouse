"""
Google Sheets Configuration

Configuration management for Google Sheets sync following sync_crm_guide.md patterns.
Supports multiple authentication methods and flexible sheet configurations.
"""
import os
import logging
from typing import Dict, Any, Optional
from google.oauth2.credentials import Credentials
from google.oauth2.service_account import Credentials as ServiceAccountCredentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow

logger = logging.getLogger(__name__)


class GSheetConfig:
    """
    Google Sheets configuration manager following sync_crm_guide.md patterns
    
    Supports multiple authentication methods:
    - Service Account (recommended for production)
    - OAuth2 User Authentication (development)
    - API Key (read-only access)
    """
    
    # Google Sheets API scope
    SCOPES = ['https://www.googleapis.com/auth/spreadsheets.readonly']
    
    DEFAULT_CONFIG = {
        'api_base_url': 'https://sheets.googleapis.com/v4/spreadsheets',
        'timeout': 30,
        'max_retries': 3,
        'retry_delay': 1.0,
        'rate_limit_delay': 0.1,  # 100ms between requests
        'batch_size': 100,
        'max_concurrent_requests': 5,
        'page_size': 1000,  # Rows per API request
        
        # Sheet-specific settings
        'sheet_id': None,  # Will be set from environment or parameters
        'sheet_name': 'Sheet1',  # Default sheet name
        'header_row': 1,  # Row containing headers (1-based)
        'data_start_row': 2,  # First row of data (1-based)
        
        # Authentication settings
        'auth_method': 'service_account',  # 'service_account', 'oauth2', 'api_key'
        'service_account_file': None,
        'credentials_file': None,
        'token_file': 'token.json',
        'api_key': None,
    }
    
    @classmethod
    def get_config(cls, profile: str = 'default', **overrides) -> Dict[str, Any]:
        """
        Get configuration for Google Sheets sync
        
        Args:
            profile: Configuration profile name
            **overrides: Override specific configuration values
            
        Returns:
            Complete configuration dictionary
        """
        logger.info(f"Loading Google Sheets config for profile: {profile}")
        
        # Start with default configuration
        config = cls.DEFAULT_CONFIG.copy()
        
        # Load environment-specific settings
        env_config = cls._load_from_environment()
        config.update(env_config)
        
        # Load profile-specific settings
        profile_config = cls._load_profile_config(profile)
        config.update(profile_config)
        
        # Apply any overrides
        config.update(overrides)
        
        # Validate configuration
        cls._validate_config(config)
        
        logger.debug(f"Google Sheets configuration loaded: {list(config.keys())}")
        return config
    
    @classmethod
    def _load_from_environment(cls) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # Authentication settings
        if os.getenv('GSHEET_SERVICE_ACCOUNT_FILE'):
            env_config['service_account_file'] = os.getenv('GSHEET_SERVICE_ACCOUNT_FILE')
            env_config['auth_method'] = 'service_account'
        
        if os.getenv('GSHEET_CREDENTIALS_FILE'):
            env_config['credentials_file'] = os.getenv('GSHEET_CREDENTIALS_FILE')
            env_config['auth_method'] = 'oauth2'
        
        if os.getenv('GSHEET_API_KEY'):
            env_config['api_key'] = os.getenv('GSHEET_API_KEY')
            env_config['auth_method'] = 'api_key'
        
        # Sheet configuration
        if os.getenv('GSHEET_SHEET_ID'):
            env_config['sheet_id'] = os.getenv('GSHEET_SHEET_ID')
        
        if os.getenv('GSHEET_SHEET_NAME'):
            env_config['sheet_name'] = os.getenv('GSHEET_SHEET_NAME')
        
        # Performance settings
        if os.getenv('GSHEET_BATCH_SIZE'):
            env_config['batch_size'] = int(os.getenv('GSHEET_BATCH_SIZE'))
        
        if os.getenv('GSHEET_RATE_LIMIT_DELAY'):
            env_config['rate_limit_delay'] = float(os.getenv('GSHEET_RATE_LIMIT_DELAY'))
        
        return env_config
    
    @classmethod
    def _load_profile_config(cls, profile: str) -> Dict[str, Any]:
        """Load profile-specific configuration"""
        profiles = {
            'default': {
                'sheet_id': '17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg',
                'sheet_name': 'Sheet1',
                'header_row': 1,
                'data_start_row': 2,
            },
            'test': {
                'sheet_id': '17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg',
                'sheet_name': 'Test Sheet',
                'batch_size': 10,
                'max_records': 50,
            },
            'production': {
                'sheet_id': '17AeA4zrC4nHJrU0Z6io-9HQJITql4K-_FTMkZ5vKLqg',
                'auth_method': 'service_account',
                'rate_limit_delay': 0.2,  # More conservative rate limiting
                'batch_size': 200,
            }
        }
        
        return profiles.get(profile, {})
    
    @classmethod
    def _validate_config(cls, config: Dict[str, Any]) -> None:
        """Validate configuration completeness"""
        required_fields = ['sheet_id']
        
        for field in required_fields:
            if not config.get(field):
                raise ValueError(f"Missing required configuration: {field}")
        
        # Validate authentication method
        auth_method = config.get('auth_method')
        if auth_method == 'service_account' and not config.get('service_account_file'):
            raise ValueError("Service account authentication requires 'service_account_file'")
        
        if auth_method == 'oauth2' and not config.get('credentials_file'):
            raise ValueError("OAuth2 authentication requires 'credentials_file'")
        
        if auth_method == 'api_key' and not config.get('api_key'):
            raise ValueError("API key authentication requires 'api_key'")
        
        logger.debug("Google Sheets configuration validation passed")


class GSheetAuthenticator:
    """
    Handle Google Sheets authentication following best practices
    """
    
    @staticmethod
    def get_credentials(config: Dict[str, Any]) -> Optional[Credentials]:
        """
        Get authenticated credentials based on configuration
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Google API credentials object
        """
        auth_method = config.get('auth_method', 'service_account')
        
        try:
            if auth_method == 'service_account':
                return GSheetAuthenticator._get_service_account_credentials(config)
            elif auth_method == 'oauth2':
                return GSheetAuthenticator._get_oauth2_credentials(config)
            elif auth_method == 'api_key':
                # API key doesn't use credentials object
                return None
            else:
                raise ValueError(f"Unsupported authentication method: {auth_method}")
        
        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            raise
    
    @staticmethod
    def _get_service_account_credentials(config: Dict[str, Any]) -> ServiceAccountCredentials:
        """Get service account credentials"""
        service_account_file = config['service_account_file']
        
        if not os.path.exists(service_account_file):
            raise FileNotFoundError(f"Service account file not found: {service_account_file}")
        
        credentials = ServiceAccountCredentials.from_service_account_file(
            service_account_file,
            scopes=GSheetConfig.SCOPES
        )
        
        logger.info("Service account authentication successful")
        return credentials
    
    @staticmethod
    def _get_oauth2_credentials(config: Dict[str, Any]) -> Credentials:
        """Get OAuth2 user credentials"""
        credentials_file = config['credentials_file']
        token_file = config.get('token_file', 'token.json')
        
        creds = None
        
        # Load existing token
        if os.path.exists(token_file):
            creds = Credentials.from_authorized_user_file(token_file, GSheetConfig.SCOPES)
        
        # If no valid credentials, get new ones
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.exists(credentials_file):
                    raise FileNotFoundError(f"Credentials file not found: {credentials_file}")
                
                flow = InstalledAppFlow.from_client_secrets_file(
                    credentials_file,
                    GSheetConfig.SCOPES
                )
                creds = flow.run_local_server(port=0)
            
            # Save credentials for next run
            with open(token_file, 'w') as token:
                token.write(creds.to_json())
        
        logger.info("OAuth2 authentication successful")
        return creds


# Configuration class for backward compatibility
class GoogleSheetsSyncConfig(GSheetConfig):
    """Alias for backward compatibility"""
    pass
