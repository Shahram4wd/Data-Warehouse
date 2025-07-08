"""
Enterprise features configuration for the Data Warehouse
"""
import os
from django.conf import settings

# Enterprise Features Configuration
ENTERPRISE_FEATURES = {
    'connection_pooling': {
        'enabled': True,
        'max_connections': 100,
        'min_connections': 10,
        'idle_timeout': 300,
        'health_check_interval': 300,
        'cleanup_interval': 60
    },
    'monitoring': {
        'enabled': True,
        'dashboard_refresh_interval': 30,
        'metrics_retention_days': 30,
        'alert_threshold_success_rate': 0.95,
        'alert_threshold_response_time': 30.0,
        'alert_threshold_error_rate': 0.05
    },
    'automation': {
        'enabled': True,
        'auto_retry_enabled': True,
        'auto_scaling_enabled': True,
        'self_healing_enabled': True,
        'predictive_maintenance_enabled': True
    },
    'encryption': {
        'enabled': True,
        'key_rotation_interval_days': 90,
        'encryption_algorithm': 'AES-256-GCM',
        'key_derivation_iterations': 100000
    },
    'validation': {
        'enabled': True,
        'strict_mode': True,
        'email_validation_level': 'strict',
        'phone_validation_level': 'strict',
        'data_quality_threshold': 0.95
    },
    'performance': {
        'batch_size_optimization': True,
        'adaptive_batch_sizing': True,
        'memory_optimization': True,
        'connection_pooling': True,
        'caching_enabled': True
    }
}

# Connection Pool Configurations
CONNECTION_POOL_CONFIG = {
    'hubspot_api': {
        'base_url': 'https://api.hubapi.com',
        'max_connections': 50,
        'min_connections': 5,
        'idle_timeout': 300,
        'request_timeout': 30,
        'circuit_breaker': {
            'failure_threshold': 5,
            'recovery_timeout': 60,
            'success_threshold': 3
        }
    },
    'genius_api': {
        'base_url': getattr(settings, 'GENIUS_API_URL', 'https://api.genius.com'),
        'max_connections': 30,
        'min_connections': 3,
        'idle_timeout': 300,
        'request_timeout': 25,
        'circuit_breaker': {
            'failure_threshold': 3,
            'recovery_timeout': 45,
            'success_threshold': 2
        }
    },
    'main_database': {
        'max_connections': 20,
        'min_connections': 5,
        'idle_timeout': 600,
        'request_timeout': 60,
        'circuit_breaker': {
            'failure_threshold': 10,
            'recovery_timeout': 30,
            'success_threshold': 5
        }
    },
    'cache_redis': {
        'max_connections': 15,
        'min_connections': 3,
        'idle_timeout': 300,
        'request_timeout': 10,
        'circuit_breaker': {
            'failure_threshold': 5,
            'recovery_timeout': 30,
            'success_threshold': 3
        }
    }
}

# Monitoring Configuration
MONITORING_CONFIG = {
    'dashboard': {
        'enabled': True,
        'refresh_interval': 30,
        'auto_refresh': True,
        'show_performance_metrics': True,
        'show_connection_stats': True,
        'show_resource_usage': True
    },
    'alerts': {
        'enabled': True,
        'email_notifications': True,
        'slack_notifications': False,
        'webhook_notifications': False,
        'alert_cooldown_minutes': 15,
        'escalation_enabled': True
    },
    'metrics': {
        'collection_interval': 60,
        'retention_days': 30,
        'aggregation_enabled': True,
        'export_enabled': False
    }
}

# Alert Thresholds
ALERT_THRESHOLDS = {
    'sync_success_rate': 0.95,
    'sync_response_time': 30.0,
    'sync_error_rate': 0.05,
    'memory_usage_mb': 500,
    'cpu_usage_percent': 80,
    'disk_usage_percent': 85,
    'connection_pool_utilization': 0.90,
    'circuit_breaker_failures': 5
}

# Automation Configuration
AUTOMATION_CONFIG = {
    'auto_retry': {
        'enabled': True,
        'max_attempts': 3,
        'backoff_factor': 2,
        'initial_delay': 1
    },
    'auto_scaling': {
        'enabled': True,
        'scale_up_threshold': 0.8,
        'scale_down_threshold': 0.3,
        'min_instances': 1,
        'max_instances': 10
    },
    'self_healing': {
        'enabled': True,
        'restart_on_failure': True,
        'max_restart_attempts': 3,
        'health_check_interval': 300
    },
    'predictive_maintenance': {
        'enabled': True,
        'prediction_window_hours': 24,
        'maintenance_threshold': 0.7,
        'notification_advance_hours': 2
    }
}

# Encryption Configuration
ENCRYPTION_CONFIG = {
    'key_rotation': {
        'enabled': True,
        'interval_days': 90,
        'auto_rotation': True,
        'backup_old_keys': True
    },
    'algorithms': {
        'primary': 'AES-256-GCM',
        'secondary': 'ChaCha20-Poly1305',
        'key_derivation': 'PBKDF2'
    },
    'key_derivation': {
        'iterations': 100000,
        'salt_length': 32,
        'key_length': 32
    }
}

# Validation Configuration
VALIDATION_CONFIG = {
    'email': {
        'level': 'strict',
        'check_mx_records': True,
        'check_disposable': True,
        'check_role_based': True
    },
    'phone': {
        'level': 'strict',
        'international_support': True,
        'format_validation': True,
        'carrier_validation': False
    },
    'data_quality': {
        'threshold': 0.95,
        'automatic_correction': True,
        'flag_suspicious_data': True,
        'quarantine_invalid_data': True
    }
}

# Performance Configuration
PERFORMANCE_CONFIG = {
    'batch_optimization': {
        'enabled': True,
        'adaptive_sizing': True,
        'min_batch_size': 50,
        'max_batch_size': 1000,
        'target_batch_time': 30.0
    },
    'memory_optimization': {
        'enabled': True,
        'max_memory_mb': 500,
        'garbage_collection_threshold': 0.8,
        'streaming_enabled': True
    },
    'caching': {
        'enabled': True,
        'cache_ttl': 3600,
        'cache_size_mb': 100,
        'cache_compression': True
    }
}

# Load configuration from environment variables
def load_enterprise_config():
    """Load enterprise configuration from environment variables"""
    config = {}
    
    # Override with environment variables
    for section, settings_dict in ENTERPRISE_FEATURES.items():
        config[section] = {}
        for key, default_value in settings_dict.items():
            env_key = f'ENTERPRISE_{section.upper()}_{key.upper()}'
            if isinstance(default_value, bool):
                config[section][key] = os.getenv(env_key, str(default_value)).lower() == 'true'
            elif isinstance(default_value, int):
                config[section][key] = int(os.getenv(env_key, str(default_value)))
            elif isinstance(default_value, float):
                config[section][key] = float(os.getenv(env_key, str(default_value)))
            else:
                config[section][key] = os.getenv(env_key, default_value)
    
    return config

# Initialize enterprise configuration
ENTERPRISE_CONFIG = load_enterprise_config()

# Export configuration for use in other modules
__all__ = [
    'ENTERPRISE_FEATURES',
    'CONNECTION_POOL_CONFIG',
    'MONITORING_CONFIG',
    'ALERT_THRESHOLDS',
    'AUTOMATION_CONFIG',
    'ENCRYPTION_CONFIG',
    'VALIDATION_CONFIG',
    'PERFORMANCE_CONFIG',
    'ENTERPRISE_CONFIG'
]
