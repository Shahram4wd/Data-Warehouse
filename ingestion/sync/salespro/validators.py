"""
SalesPro data validators
"""
import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

def validate_salespro_id(value: Any) -> Optional[str]:
    """Validate SalesPro record ID"""
    if not value:
        return None
    
    try:
        str_value = str(value).strip()
        if str_value and str_value != '0':
            return str_value
        return None
    except (ValueError, TypeError):
        return None

def validate_table_name(table_name: str) -> bool:
    """Validate that table name is allowed for SalesPro"""
    allowed_tables = {
        'customer',
        'estimate', 
        'credit_applications',
        'user_activity',
        'payments',
        'lead_results'
    }
    return table_name in allowed_tables

def validate_timestamp_column(table_name: str) -> str:
    """Get the correct timestamp column for incremental sync"""
    # Tables that use updated_at for filtering (from source system)
    updated_at_tables = {'credit_applications', 'customer', 'estimate'}
    
    if table_name in updated_at_tables:
        return 'updated_at'
    else:
        return 'created_at'
