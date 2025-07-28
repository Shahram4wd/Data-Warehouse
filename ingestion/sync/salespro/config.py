"""
SalesPro sync configuration following CRM sync guide standards
"""

# Sync Configuration following CRM sync guide patterns
SALESPRO_SYNC_CONFIG = {
    'salespro': {
        'leadresult': {
            'batch_size': 500,
            'timeout': 30,
            'retry_attempts': 3,
            'delta_sync': True,
            'source_type': 'database',
            'table_name': 'lead_results'
        },
        'customer': {
            'batch_size': 500,
            'timeout': 30,
            'retry_attempts': 3,
            'delta_sync': True,
            'source_type': 'database',
            'table_name': 'customer'
        },
        'estimate': {
            'batch_size': 500,
            'timeout': 30,
            'retry_attempts': 3,
            'delta_sync': True,
            'source_type': 'database',
            'table_name': 'estimates'
        }
    }
}

# Field Mappings following CRM sync guide patterns
SALESPRO_FIELD_MAPPINGS = {
    'leadresult': {
        'estimate_id': 'estimate_id',
        'company_id': 'company_id',
        'lead_results': 'lead_results_raw',
        'created_at': 'created_at',
        'updated_at': 'updated_at'
    },
    'customer': {
        'customer_id': 'customer_id',
        'company_id': 'company_id',
        'first_name': 'customer_first_name',
        'last_name': 'customer_last_name',
        'email': 'email',
        'phone': 'phone',
        'created_at': 'created_at',
        'updated_at': 'updated_at'
    }
}

# Performance monitoring thresholds following CRM sync guide
SALESPRO_MONITORING_CONFIG = {
    'performance_thresholds': {
        'max_sync_duration_minutes': 60,
        'min_records_per_second': 10,
        'max_error_rate_percent': 5,
        'max_memory_usage_mb': 1024
    },
    'alerting_triggers': {
        'sync_failure': True,
        'high_error_rate': True,
        'slow_performance': True,
        'zero_records_processed': True
    }
}

# Data validation rules following CRM sync guide
SALESPRO_VALIDATION_RULES = {
    'required_fields': {
        'leadresult': ['estimate_id'],
        'customer': ['customer_id'],
        'estimate': ['estimate_id']
    },
    'field_lengths': {
        'customer_first_name': 255,
        'customer_last_name': 255,
        'company_name': 255,
        'email': 254,
        'phone': 20,
        'address_1': 255,
        'city': 100,
        'state': 50,
        'zip_code': 20
    },
    'data_types': {
        'email': 'email',
        'phone': 'phone',
        'created_at': 'datetime',
        'updated_at': 'datetime',
        'zip_code': 'zip_code',
        'state': 'state'
    }
}
