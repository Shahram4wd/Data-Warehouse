"""
SalesRabbit-specific validators following framework standards
"""
import logging
from typing import Any
from ingestion.base.validators import BaseValidator, ValidationFramework

logger = logging.getLogger(__name__)

class SalesRabbitValidatorMixin:
    """SalesRabbit-specific validation logic"""
    
    def validate_salesrabbit_status(self, value: Any) -> str:
        """Validate SalesRabbit status values"""
        if not value:
            return None
            
        valid_statuses = ['new', 'contacted', 'qualified', 'unqualified', 'closed']
        value_str = str(value).lower().strip()
        
        if value_str not in valid_statuses:
            raise ValueError(f"Invalid SalesRabbit status: {value}")
        
        return value_str
    
    def validate_salesrabbit_id(self, value: Any) -> int:
        """Validate SalesRabbit ID format"""
        if not value:
            return None
            
        try:
            return int(value)
        except (ValueError, TypeError):
            raise ValueError(f"Invalid SalesRabbit ID: {value}")

class SalesRabbitValidationFramework(ValidationFramework, SalesRabbitValidatorMixin):
    """Extended validation framework for SalesRabbit"""
    
    def __init__(self):
        super().__init__('salesrabbit')
        self.custom_validators = {
            'salesrabbit_status': self.validate_salesrabbit_status,
            'salesrabbit_id': self.validate_salesrabbit_id
        }
    
    def validate_field(self, field_name: str, value: Any, field_type: str, context: dict = None) -> Any:
        """Validate field with SalesRabbit-specific logic"""
        if field_type in self.custom_validators:
            return self.custom_validators[field_type](value)
        
        # Fall back to base validation
        return super().validate_field(field_name, value, field_type, context)
