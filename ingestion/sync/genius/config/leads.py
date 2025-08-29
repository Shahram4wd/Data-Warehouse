"""
Configuration management for Genius CRM sync operations
"""
from typing import Dict, Any, List


class GeniusLeadSyncConfig:
    """Configuration for Genius Lead sync operations"""
    
    # Chunking and performance settings
    DEFAULT_CHUNK_SIZE = 1000
    MAX_CHUNK_SIZE = 5000
    BULK_BATCH_SIZE = 500
    
    # Field mappings from source to destination
    FIELD_MAPPINGS = {
        'lead_id': 'lead_id',
        'first_name': 'first_name', 
        'last_name': 'last_name',
        'email': 'email',
        'phone': 'phone1',  # Maps to phone1 in model
        'address': 'address1',  # Maps to address1 in model
        'city': 'city',
        'state': 'state',
        'zip_code': 'zip',  # Maps to zip in model
        'prospect_source_id': 'source',  # Maps to source in model
        'user_id': 'added_by',  # Maps to added_by in model
        'division_id': 'division_id',
        'notes': 'notes',
        'status': 'status',
        'converted_to_prospect_id': 'copied_to_id',  # Maps to copied_to_id in model
        'created_at': 'added_on',  # Maps to added_on in model
        'updated_at': 'updated_at',
        'sync_updated_at': 'sync_updated_at'
    }
    
    # Field length limits for validation
    FIELD_LIMITS = {
        'first_name': 100,
        'last_name': 100,
        'email': 100,
        'phone1': 20,
        'address1': 200,
        'city': 50,
        'state': 20,
        'zip': 12,
        'status': 50,
        'notes': 2000
    }
    
    # Fields that should be updated in bulk operations
    BULK_UPDATE_FIELDS = [
        'first_name', 'last_name', 'email', 'phone1', 'address1',
        'city', 'state', 'zip', 'status', 'notes',
        'source', 'added_by', 'division_id',
        'copied_to_id', 'added_on', 'updated_at', 'sync_updated_at'
    ]
    
    # Business rules
    SKIP_DUMMY_RECORDS = True
    REQUIRE_CONTACT_INFO = False  # Whether email or phone is required
    
    @classmethod
    def get_source_field_mapping(cls) -> List[str]:
        """Get ordered list of source fields for SQL queries"""
        return [
            'lead_id', 'first_name', 'last_name', 'email', 'phone',
            'address', 'city', 'state', 'zip_code', 'prospect_source_id',
            'user_id', 'division_id', 'notes', 'status',
            'converted_to_prospect_id', 'created_at', 'updated_at'
        ]
