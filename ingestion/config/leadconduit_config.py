"""
LeadConduit Configuration

Configuration management for LeadConduit sync following
sync_crm_guide.md patterns.
"""
import os
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class LeadConduitConfig:
    """
    LeadConduit configuration management
    
    Provides configuration for LeadConduit API access and sync settings
    following sync_crm_guide architecture.
    """
    
    DEFAULT_CONFIG = {
        'api_base_url': 'https://app.leadconduit.com',  # Correct URL from reference
        'timeout': 30,
        'max_retries': 3,
        'retry_delay': 1,
        'rate_limit_delay': 1,
        'batch_size': 1000,
        'max_concurrent_requests': 5,
        'page_size': 100
    }
    
    @classmethod
    def get_config(cls, profile: str = 'default') -> Dict[str, Any]:
        """
        Get configuration for specified profile
        
        Args:
            profile: Configuration profile name
            
        Returns:
            Dict: Configuration dictionary
        """
        logger.info(f"Loading LeadConduit config for profile: {profile}")
        
        # Start with default config
        config = cls.DEFAULT_CONFIG.copy()
        
        # Load environment-specific settings
        config.update(cls._load_env_config())
        
        # Load profile-specific settings
        if profile != 'default':
            profile_config = cls._load_profile_config(profile)
            config.update(profile_config)
        
        # Validate configuration
        cls._validate_config(config)
        
        logger.debug(f"Loaded config keys: {list(config.keys())}")
        return config
    
    @classmethod
    def _load_env_config(cls) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # API credentials - match reference naming
        username = os.getenv('LEADCONDUIT_USERNAME')
        if username:
            env_config['username'] = username
            env_config['api_key'] = username  # For backward compatibility
        
        api_key = os.getenv('LEADCONDUIT_API_KEY')
        if api_key:
            env_config['api_secret'] = api_key  # Store as api_secret for the client
        
        # API settings
        base_url = os.getenv('LEADCONDUIT_API_URL')
        if base_url:
            env_config['api_base_url'] = base_url
        else:
            # Use correct base URL from reference
            env_config['api_base_url'] = 'https://app.leadconduit.com'
        
        # Numeric settings
        timeout = os.getenv('LEADCONDUIT_TIMEOUT')
        if timeout:
            try:
                env_config['timeout'] = int(timeout)
            except ValueError:
                logger.warning(f"Invalid timeout value: {timeout}")
        
        batch_size = os.getenv('LEADCONDUIT_BATCH_SIZE')
        if batch_size:
            try:
                env_config['batch_size'] = int(batch_size)
            except ValueError:
                logger.warning(f"Invalid batch_size value: {batch_size}")
        
        max_retries = os.getenv('LEADCONDUIT_MAX_RETRIES')
        if max_retries:
            try:
                env_config['max_retries'] = int(max_retries)
            except ValueError:
                logger.warning(f"Invalid max_retries value: {max_retries}")
        
        logger.debug(f"Loaded env config: {list(env_config.keys())}")
        return env_config
    
    @classmethod
    def _load_profile_config(cls, profile: str) -> Dict[str, Any]:
        """Load profile-specific configuration"""
        profile_configs = {
            'development': {
                'timeout': 60,
                'max_retries': 5,
                'batch_size': 100,  # Smaller batches for dev
                'rate_limit_delay': 2  # More conservative for dev
            },
            'production': {
                'timeout': 30,
                'max_retries': 3,
                'batch_size': 1000,
                'max_concurrent_requests': 10,  # More aggressive for prod
                'rate_limit_delay': 0.5
            },
            'testing': {
                'timeout': 10,
                'max_retries': 1,
                'batch_size': 10,
                'rate_limit_delay': 0
            }
        }
        
        config = profile_configs.get(profile, {})
        logger.debug(f"Loaded profile config for {profile}: {list(config.keys())}")
        return config
    
    @classmethod
    def _validate_config(cls, config: Dict[str, Any]) -> None:
        """
        Validate configuration
        
        Raises:
            ValueError: If configuration is invalid
        """
        # Check required fields for API access
        if not config.get('username') and not config.get('api_key'):
            logger.warning("No username/API key configured - some operations may fail")
        
        if not config.get('api_secret'):
            logger.warning("No API secret configured - some operations may fail")
        
        # Validate numeric fields
        numeric_fields = {
            'timeout': (1, 300),
            'max_retries': (0, 10),
            'batch_size': (1, 10000),
            'max_concurrent_requests': (1, 50),
            'rate_limit_delay': (0, 10)
        }
        
        for field, (min_val, max_val) in numeric_fields.items():
            value = config.get(field)
            if value is not None:
                if not isinstance(value, (int, float)) or value < min_val or value > max_val:
                    raise ValueError(f"Invalid {field}: {value} (must be between {min_val} and {max_val})")
        
        # Validate URL
        api_url = config.get('api_base_url', '')
        if not api_url.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid API URL: {api_url}")
    
    @classmethod
    def get_api_credentials(cls, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Extract API credentials from config
        
        Returns:
            Dict: API credentials in format expected by client
        """
        return {
            'api_key': config.get('username') or config.get('api_key', ''),  # username as api_key
            'api_secret': config.get('api_secret', ''),  # api_key as api_secret
            'api_base_url': config.get('api_base_url', cls.DEFAULT_CONFIG['api_base_url'])
        }
    
    @classmethod
    def get_sync_settings(cls, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extract sync settings from config
        
        Returns:
            Dict: Sync settings
        """
        return {
            'batch_size': config.get('batch_size', cls.DEFAULT_CONFIG['batch_size']),
            'timeout': config.get('timeout', cls.DEFAULT_CONFIG['timeout']),
            'max_retries': config.get('max_retries', cls.DEFAULT_CONFIG['max_retries']),
            'retry_delay': config.get('retry_delay', cls.DEFAULT_CONFIG['retry_delay']),
            'rate_limit_delay': config.get('rate_limit_delay', cls.DEFAULT_CONFIG['rate_limit_delay']),
            'max_concurrent_requests': config.get('max_concurrent_requests', cls.DEFAULT_CONFIG['max_concurrent_requests']),
            'page_size': config.get('page_size', cls.DEFAULT_CONFIG['page_size'])
        }
