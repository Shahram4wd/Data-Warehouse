"""
HubSpot associations processors
Following import_refactoring.md enterprise architecture standards
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from ingestion.base.exceptions import ValidationException
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor
from ingestion.models.hubspot import (
    Hubspot_AppointmentContactAssociation,
    Hubspot_ContactDivisionAssociation
)

logger = logging.getLogger(__name__)

class HubSpotAssociationProcessor(HubSpotBaseProcessor):
    """Base processor for HubSpot association data"""
    
    def __init__(self, model_class, **kwargs):
        super().__init__(model_class, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings for associations - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_field_mappings")
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform association record to model format"""
        try:
            # Apply field mappings
            transformed = self.apply_field_mappings(record)
            
            # Add timestamps if not present
            if 'created_at' not in transformed:
                transformed['created_at'] = timezone.now()
            
            # Clean up metadata fields that shouldn't be stored
            for field in ['association_types', 'raw_from', 'raw_to']:
                transformed.pop(field, None)
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming association record: {e}")
            raise ValidationException(f"Failed to transform association record: {e}")
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Validate association record"""
        try:
            # Basic validation for all associations
            if not record:
                raise ValidationException("Empty association record")
            
            # Ensure required fields are present (to be defined by subclasses)
            required_fields = self.get_required_fields()
            for field in required_fields:
                if not record.get(field):
                    raise ValidationException(f"Missing required field: {field}")
            
            # Apply field-specific validation
            validated = self.apply_field_validation(record)
            
            return validated
            
        except ValidationException:
            raise
        except Exception as e:
            logger.error(f"Error validating association record: {e}")
            raise ValidationException(f"Failed to validate association record: {e}")
    
    def get_required_fields(self) -> List[str]:
        """Get list of required fields - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement get_required_fields")
    
    def apply_field_validation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply field-specific validation - to be implemented by subclasses"""
        raise NotImplementedError("Subclasses must implement apply_field_validation")

class HubSpotAppointmentContactAssociationProcessor(HubSpotAssociationProcessor):
    """Processor for HubSpot appointment-contact associations"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_AppointmentContactAssociation, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings for appointment-contact associations"""
        return {
            'contact_id': 'contact_id',
            'appointment_id': 'appointment_id',
            'created_at': 'created_at'
        }
    
    def get_required_fields(self) -> List[str]:
        """Get required fields for appointment-contact associations"""
        return ['contact_id', 'appointment_id']
    
    def apply_field_validation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply appointment-contact association specific validation"""
        validated = record.copy()
        
        # Validate contact_id
        contact_id = validated.get('contact_id')
        if contact_id:
            # Basic format validation for HubSpot object IDs
            if not str(contact_id).isdigit():
                logger.warning(f"Contact ID format may be invalid: {contact_id}")
            validated['contact_id'] = str(contact_id)
        
        # Validate appointment_id
        appointment_id = validated.get('appointment_id')
        if appointment_id:
            if not str(appointment_id).isdigit():
                logger.warning(f"Appointment ID format may be invalid: {appointment_id}")
            validated['appointment_id'] = str(appointment_id)
        
        # Validate created_at
        if 'created_at' in validated and validated['created_at']:
            try:
                if isinstance(validated['created_at'], str):
                    validated['created_at'] = timezone.datetime.fromisoformat(
                        validated['created_at'].replace('Z', '+00:00')
                    )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid created_at format: {e}")
                validated['created_at'] = timezone.now()
        
        return validated
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform appointment-contact association record"""
        try:
            # Apply base transformation
            transformed = super().transform_record(record)
            
            # Ensure string format for IDs (required by model)
            if 'contact_id' in transformed:
                transformed['contact_id'] = str(transformed['contact_id'])
            if 'appointment_id' in transformed:
                transformed['appointment_id'] = str(transformed['appointment_id'])
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming appointment-contact association: {e}")
            raise ValidationException(f"Failed to transform appointment-contact association: {e}")

class HubSpotContactDivisionAssociationProcessor(HubSpotAssociationProcessor):
    """Processor for HubSpot contact-division associations"""
    
    def __init__(self, **kwargs):
        super().__init__(Hubspot_ContactDivisionAssociation, **kwargs)
    
    def get_field_mappings(self) -> Dict[str, str]:
        """Return field mappings for contact-division associations"""
        return {
            'contact_id': 'contact_id',
            'division_id': 'division_id',
            'created_at': 'created_at'
        }
    
    def get_required_fields(self) -> List[str]:
        """Get required fields for contact-division associations"""
        return ['contact_id', 'division_id']
    
    def apply_field_validation(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Apply contact-division association specific validation"""
        validated = record.copy()
        
        # Validate contact_id
        contact_id = validated.get('contact_id')
        if contact_id:
            if not str(contact_id).isdigit():
                logger.warning(f"Contact ID format may be invalid: {contact_id}")
            validated['contact_id'] = str(contact_id)
        
        # Validate division_id
        division_id = validated.get('division_id')
        if division_id:
            if not str(division_id).isdigit():
                logger.warning(f"Division ID format may be invalid: {division_id}")
            validated['division_id'] = str(division_id)
        
        # Validate created_at
        if 'created_at' in validated and validated['created_at']:
            try:
                if isinstance(validated['created_at'], str):
                    validated['created_at'] = timezone.datetime.fromisoformat(
                        validated['created_at'].replace('Z', '+00:00')
                    )
            except (ValueError, AttributeError) as e:
                logger.warning(f"Invalid created_at format: {e}")
                validated['created_at'] = timezone.now()
        
        return validated
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Transform contact-division association record"""
        try:
            # Apply base transformation
            transformed = super().transform_record(record)
            
            # Ensure string format for IDs (required by model)
            if 'contact_id' in transformed:
                transformed['contact_id'] = str(transformed['contact_id'])
            if 'division_id' in transformed:
                transformed['division_id'] = str(transformed['division_id'])
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error transforming contact-division association: {e}")
            raise ValidationException(f"Failed to transform contact-division association: {e}")
