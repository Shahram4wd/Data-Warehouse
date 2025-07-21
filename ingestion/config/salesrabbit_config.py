"""
SalesRabbit sync configuration following framework standards
"""
import os

# SalesRabbit API Configuration
SALESRABBIT_CONFIG = {
    'api_url': os.getenv('SALESRABBIT_API_URL', 'https://api.salesrabbit.com'),
    'api_token': os.getenv('SALESRABBIT_API_TOKEN'),
    'timeout': 60,
    'rate_limit_delay': 1.0,  # Seconds between requests
    
    # Sync Configuration
    'batch_size': 500,
    'max_retries': 3,
    'retry_delay': 2,  # Seconds
    
    # Entity Configuration
    'entities': {
        'leads': {
            'endpoint': '/api/leads',
            'batch_size': 500,
            'incremental_field': 'date_modified',
            'required_fields': ['id', 'dateModified'],
        }
    },
    
    # Validation Configuration
    'validation': {
        'enabled': True,
        'strict_mode': False,
        'skip_invalid_records': True,
    },
    
    # Performance Configuration
    'performance': {
        'connection_pool_size': 10,
        'connection_timeout': 30,
        'read_timeout': 60,
    }
}

# Field Mappings
SALESRABBIT_FIELD_MAPPINGS = {
    'leads': {
        'api': {
            'id': 'id',
            'firstName': 'first_name',
            'lastName': 'last_name',
            'businessName': 'business_name',
            'email': 'email',
            'phonePrimary': 'phone_primary',
            'phoneAlternate': 'phone_alternate',
            'address.street1': 'street1',
            'address.street2': 'street2',
            'address.city': 'city',
            'address.state': 'state',
            'address.zip': 'zip',
            'address.country': 'country',
            'coordinates.latitude': 'latitude',
            'coordinates.longitude': 'longitude',
            'status': 'status',
            'statusModified': 'status_modified',
            'notes': 'notes',
            'campaignId': 'campaign_id',
            'userId': 'user_id',
            'userName': 'user_name',
            'dateCreated': 'date_created',
            'dateModified': 'date_modified',
            'ownerModified': 'owner_modified',
            'dateOfBirth': 'date_of_birth',
            'deletedAt': 'deleted_at'
        }
    }
}

# Validation Rules
SALESRABBIT_VALIDATION_RULES = {
    'leads': {
        'required_fields': ['id'],
        'field_types': {
            'id': 'salesrabbit_id',
            'email': 'email',
            'phone_primary': 'phone',
            'phone_alternate': 'phone',
            'zip': 'zip_code',
            'state': 'state',
            'latitude': 'decimal',
            'longitude': 'decimal',
            'date_created': 'datetime',
            'date_modified': 'datetime',
            'status_modified': 'datetime',
            'owner_modified': 'datetime',
            'date_of_birth': 'date',
            'deleted_at': 'datetime',
            'status': 'salesrabbit_status',
            'campaign_id': 'integer',
            'user_id': 'integer'
        },
        'valid_statuses': ['new', 'contacted', 'qualified', 'unqualified', 'closed']
    }
}

def get_salesrabbit_config():
    """Get SalesRabbit configuration"""
    return SALESRABBIT_CONFIG

def get_field_mappings(entity_type='leads', source_type='api'):
    """Get field mappings for entity type and source"""
    return SALESRABBIT_FIELD_MAPPINGS.get(entity_type, {}).get(source_type, {})

def get_validation_rules(entity_type='leads'):
    """Get validation rules for entity type"""
    return SALESRABBIT_VALIDATION_RULES.get(entity_type, {})
