"""
Dynamic configuration management for sync operations
"""
import logging
from typing import Dict, Any, Optional, Union, Type, Callable
from datetime import datetime, timedelta
from collections import defaultdict
from django.core.cache import cache
from django.conf import settings
from ingestion.base.exceptions import ConfigurationException

logger = logging.getLogger(__name__)

class ConfigurationManager:
    """Enterprise configuration management with hot-reload capabilities"""
    
    def __init__(self):
        self.config_cache = {}
        self.watchers = defaultdict(list)
        self.change_listeners = []
        self.environment = self._detect_environment()
        self.validation_rules = {}
        self.logger = logging.getLogger(__name__)
    
    def _detect_environment(self) -> str:
        """Detect current environment"""
        if hasattr(settings, 'ENVIRONMENT'):
            return settings.ENVIRONMENT
        elif settings.DEBUG:
            return 'development'
        else:
            return 'production'
    
    async def get_config(self, key: str, default=None):
        """Get configuration value with hierarchy support"""
        # Try environment-specific config first
        env_key = f"{self.environment}.{key}"
        if env_key in self.config_cache:
            return self.config_cache[env_key]
        
        # Fall back to general config
        if key in self.config_cache:
            return self.config_cache[key]
        
        # Try to load from database or settings
        value = await self._load_config_value(key, default)
        self.config_cache[key] = value
        return value
    
    async def update_config(self, key: str, value: Any, validate: bool = True):
        """Update configuration with validation"""
        if validate and key in self.validation_rules:
            await self._validate_config_value(key, value)
        
        old_value = self.config_cache.get(key)
        self.config_cache[key] = value
        
        # Notify listeners
        await self._notify_config_change(key, old_value, value)
    
    def watch_config(self, key: str, callback: Callable):
        """Watch for configuration changes"""
        self.watchers[key].append(callback)
    
    def is_stale(self, key: str) -> bool:
        """Check if configuration is stale"""
        # For now, always return False - can be enhanced later
        return False
    
    async def refresh_config(self, key: str):
        """Refresh specific configuration"""
        if key in self.config_cache:
            del self.config_cache[key]
        await self.get_config(key)
    
    async def save_config(self, key: str, value: Any):
        """Save configuration to persistent storage"""
        # Save to cache for now
        cache.set(f"config:{key}", value, timeout=3600)
    
    async def _load_config_value(self, key: str, default: Any) -> Any:
        """Load configuration value from various sources"""
        # Try cache first
        cached_value = cache.get(f"config:{key}")
        if cached_value is not None:
            return cached_value
        
        # Try settings
        if hasattr(settings, key.upper()):
            return getattr(settings, key.upper())
        
        return default
    
    async def _validate_config_value(self, key: str, value: Any):
        """Validate configuration value"""
        validator = self.validation_rules.get(key)
        if validator:
            await validator.validate(value)
    
    async def _notify_config_change(self, key: str, old_value: Any, new_value: Any):
        """Notify change listeners"""
        for listener in self.change_listeners:
            try:
                await listener(key, old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error notifying config change listener: {e}")
        
        # Notify key-specific watchers
        for watcher in self.watchers.get(key, []):
            try:
                await watcher(old_value, new_value)
            except Exception as e:
                self.logger.error(f"Error notifying config watcher: {e}")

class EnvironmentAwareConfig:
    """Environment-aware configuration"""
    
    ENVIRONMENT_CONFIGS = {
        'development': {
            'hubspot.batch_size': 10,
            'hubspot.rate_limit': 5,
            'hubspot.timeout': 30,
            'validation.strict_mode': False,
            'monitoring.enabled': False,
            'logging.level': 'DEBUG'
        },
        'staging': {
            'hubspot.batch_size': 50,
            'hubspot.rate_limit': 25,
            'hubspot.timeout': 60,
            'validation.strict_mode': True,
            'monitoring.enabled': True,
            'logging.level': 'INFO'
        },
        'production': {
            'hubspot.batch_size': 500,
            'hubspot.rate_limit': 100,
            'hubspot.timeout': 120,
            'validation.strict_mode': True,
            'monitoring.enabled': True,
            'logging.level': 'WARNING',
            'performance.profiling': True
        }
    }
    
    def get_environment_config(self, environment: str) -> Dict:
        """Get environment-specific configuration"""
        return self.ENVIRONMENT_CONFIGS.get(environment, {})

class SyncConfiguration:
    """Dynamic configuration manager for sync operations"""
    
    # Cache keys
    CACHE_KEY_PREFIX = 'sync_config'
    CACHE_TIMEOUT = 300  # 5 minutes
    
    # Default configurations
    DEFAULT_CONFIGS = {
        'hubspot': {
            'batch_size': 100,
            'max_retries': 3,
            'retry_delay': 1.0,
            'rate_limit_requests': 100,
            'rate_limit_window': 10,
            'timeout': 30,
            'concurrent_batches': 3,
            'memory_threshold': 0.8,
            'validation_enabled': True,
            'strict_validation': False,
            'bulk_operation_threshold': 1000,
            'progress_bar_enabled': True,
            'log_level': 'INFO',
        },
        'database': {
            'batch_size': 1000,
            'max_retries': 2,
            'retry_delay': 0.5,
            'timeout': 60,
            'connection_pool_size': 10,
            'bulk_insert_threshold': 500,
        },
        'performance': {
            'memory_monitoring': True,
            'performance_logging': True,
            'metrics_collection': True,
            'profiling_enabled': False,
        }
    }
    
    def __init__(self, service_name: str = None):
        self.service_name = service_name or 'default'
        self.logger = logging.getLogger(__name__)
        self._config_cache = {}
        self._last_refresh = None
        self._refresh_interval = timedelta(minutes=5)
    
    def get_config(self, key: str, default: Any = None, config_type: str = None) -> Any:
        """
        Get configuration value with caching and fallback
        
        Args:
            key: Configuration key (dot notation supported)
            default: Default value if key not found
            config_type: Type of configuration (hubspot, database, performance)
        """
        cache_key = f"{self.CACHE_KEY_PREFIX}:{self.service_name}:{key}"
        
        # Try cache first
        cached_value = cache.get(cache_key)
        if cached_value is not None:
            return cached_value
        
        # Try to get from database/model
        value = self._get_from_database(key, config_type)
        
        # Fall back to defaults
        if value is None:
            value = self._get_default_value(key, config_type, default)
        
        # Cache the value
        if value is not None:
            cache.set(cache_key, value, self.CACHE_TIMEOUT)
        
        return value
    
    def set_config(self, key: str, value: Any, config_type: str = None) -> None:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
            config_type: Type of configuration
        """
        cache_key = f"{self.CACHE_KEY_PREFIX}:{self.service_name}:{key}"
        
        # Update cache
        cache.set(cache_key, value, self.CACHE_TIMEOUT)
        
        # Update database (if model exists)
        self._set_in_database(key, value, config_type)
        
        self.logger.info(f"Configuration updated: {key} = {value}")
    
    def refresh_config(self) -> None:
        """Refresh configuration from database"""
        self._config_cache.clear()
        cache.delete_many([
            f"{self.CACHE_KEY_PREFIX}:{self.service_name}:*"
        ])
        self._last_refresh = datetime.now()
        self.logger.info("Configuration cache refreshed")
    
    def get_batch_size(self, operation_type: str = 'default') -> int:
        """Get batch size for specific operation type"""
        key = f"{operation_type}_batch_size" if operation_type != 'default' else 'batch_size'
        return self.get_config(key, 100, 'hubspot')
    
    def get_retry_config(self) -> Dict[str, Any]:
        """Get retry configuration"""
        return {
            'max_retries': self.get_config('max_retries', 3, 'hubspot'),
            'initial_delay': self.get_config('retry_delay', 1.0, 'hubspot'),
            'max_delay': self.get_config('max_retry_delay', 60.0, 'hubspot'),
            'backoff_factor': self.get_config('backoff_factor', 2.0, 'hubspot'),
        }
    
    def get_rate_limit_config(self) -> Dict[str, Any]:
        """Get rate limiting configuration"""
        return {
            'requests_per_window': self.get_config('rate_limit_requests', 100, 'hubspot'),
            'window_size': self.get_config('rate_limit_window', 10, 'hubspot'),
        }
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return {
            'concurrent_batches': self.get_config('concurrent_batches', 3, 'hubspot'),
            'memory_threshold': self.get_config('memory_threshold', 0.8, 'performance'),
            'memory_monitoring': self.get_config('memory_monitoring', True, 'performance'),
            'performance_logging': self.get_config('performance_logging', True, 'performance'),
        }
    
    def is_validation_enabled(self) -> bool:
        """Check if validation is enabled"""
        return self.get_config('validation_enabled', True, 'hubspot')
    
    def is_strict_validation(self) -> bool:
        """Check if strict validation is enabled"""
        return self.get_config('strict_validation', False, 'hubspot')
    
    def is_progress_bar_enabled(self) -> bool:
        """Check if progress bar is enabled"""
        return self.get_config('progress_bar_enabled', True, 'hubspot')
    
    def _get_from_database(self, key: str, config_type: str = None) -> Any:
        """Get configuration from database model"""
        try:
            # Try to import the model (if it exists)
            from ingestion.models.common import SyncConfigurationModel
            
            config_obj = SyncConfigurationModel.objects.filter(
                service_name=self.service_name,
                config_key=key,
                config_type=config_type or 'default',
                is_active=True
            ).first()
            
            if config_obj:
                return config_obj.get_value()
            
        except ImportError:
            # Model doesn't exist, use defaults
            pass
        except Exception as e:
            self.logger.warning(f"Error getting config from database: {e}")
        
        return None
    
    def _set_in_database(self, key: str, value: Any, config_type: str = None) -> None:
        """Set configuration in database model"""
        try:
            # Try to import the model (if it exists)
            from ingestion.models.common import SyncConfigurationModel
            
            config_obj, created = SyncConfigurationModel.objects.get_or_create(
                service_name=self.service_name,
                config_key=key,
                config_type=config_type or 'default',
                defaults={
                    'config_value': str(value),
                    'value_type': type(value).__name__,
                    'is_active': True
                }
            )
            
            if not created:
                config_obj.config_value = str(value)
                config_obj.value_type = type(value).__name__
                config_obj.save()
                
        except ImportError:
            # Model doesn't exist, skip database storage
            pass
        except Exception as e:
            self.logger.warning(f"Error setting config in database: {e}")
    
    def _get_default_value(self, key: str, config_type: str = None, default: Any = None) -> Any:
        """Get default value for configuration key"""
        if config_type and config_type in self.DEFAULT_CONFIGS:
            config_section = self.DEFAULT_CONFIGS[config_type]
            if key in config_section:
                return config_section[key]
        
        # Try to find in any section
        for section in self.DEFAULT_CONFIGS.values():
            if key in section:
                return section[key]
        
        return default
    
    def get_all_configs(self, config_type: str = None) -> Dict[str, Any]:
        """Get all configurations for a type"""
        if config_type and config_type in self.DEFAULT_CONFIGS:
            return self.DEFAULT_CONFIGS[config_type].copy()
        
        return self.DEFAULT_CONFIGS.copy()
    
    def validate_config(self, key: str, value: Any, config_type: str = None) -> bool:
        """Validate configuration value"""
        validators = {
            'batch_size': lambda x: isinstance(x, int) and x > 0,
            'max_retries': lambda x: isinstance(x, int) and x >= 0,
            'retry_delay': lambda x: isinstance(x, (int, float)) and x >= 0,
            'timeout': lambda x: isinstance(x, (int, float)) and x > 0,
            'memory_threshold': lambda x: isinstance(x, (int, float)) and 0 < x <= 1,
            'concurrent_batches': lambda x: isinstance(x, int) and x > 0,
        }
        
        if key in validators:
            return validators[key](value)
        
        return True

# Global configuration instance
config = SyncConfiguration()

# Configuration decorators
def with_config(config_key: str, config_type: str = None):
    """Decorator to inject configuration value"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            config_value = config.get_config(config_key, config_type=config_type)
            kwargs[config_key] = config_value
            return func(*args, **kwargs)
        return wrapper
    return decorator

def with_batch_size(operation_type: str = 'default'):
    """Decorator to inject batch size"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            kwargs['batch_size'] = config.get_batch_size(operation_type)
            return func(*args, **kwargs)
        return wrapper
    return decorator
