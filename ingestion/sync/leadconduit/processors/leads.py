"""
LeadConduit Leads Processor

Data processing and validation for LeadConduit leads following
sync_crm_guide.md architecture.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ingestion.models.leadconduit import LeadConduit_Lead

logger = logging.getLogger(__name__)


class LeadConduitLeadsProcessor:
    """
    Processor for LeadConduit lead data (derived from events)
    
    Handles data transformation, validation, and storage following
    sync_crm_guide patterns for lead data processing.
    """
    
    def __init__(self):
        self.entity_type = "leads"
        logger.info("Initialized LeadConduit Leads processor")
    
    async def process_batch(self, leads_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process a batch of LeadConduit leads
        
        Args:
            leads_batch: List of lead records from get_all_leads_utc
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing batch of {len(leads_batch)} leads")
        
        result = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        try:
            for lead_data in leads_batch:
                try:
                    process_result = await self.process_single_lead(lead_data)
                    
                    result['processed'] += 1
                    if process_result['created']:
                        result['created'] += 1
                    elif process_result['updated']:
                        result['updated'] += 1
                        
                except Exception as e:
                    logger.error(f"Failed to process lead {lead_data.get('Lead ID')}: {e}")
                    result['failed'] += 1
                    result['errors'].append({
                        'lead_id': lead_data.get('Lead ID'),
                        'error': str(e)
                    })
            
            logger.info(f"Batch processing completed: {result}")
            return result
            
        except Exception as e:
            logger.error(f"Batch processing failed: {e}")
            result['failed'] = len(leads_batch)
            result['errors'].append({'batch_error': str(e)})
            return result
    
    async def process_single_lead(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single lead record
        
        Args:
            lead_data: Lead data from get_all_leads_utc function
            
        Returns:
            Dict with processing result
        """
        lead_id = lead_data.get('Lead ID')
        
        if not lead_id:
            raise ValueError("Lead ID is required")
        
        # Check if lead already exists using sync_to_async
        from asgiref.sync import sync_to_async
        
        get_lead = sync_to_async(
            lambda: LeadConduit_Lead.objects.filter(lead_id=lead_id).first()
        )
        
        existing_lead = await get_lead()
        
        if existing_lead:
            # Update existing lead
            updated = await self.update_lead(existing_lead, lead_data)
            return {'created': False, 'updated': updated}
        else:
            # Create new lead
            await self.create_lead(lead_data)
            return {'created': True, 'updated': False}
    
    async def create_lead(self, lead_data: Dict[str, Any]) -> LeadConduit_Lead:
        """Create new LeadConduit lead record"""
        
        # Validate and prepare data
        validated_data = self.validate_lead_data(lead_data)
        
        # Create lead record using sync_to_async
        from asgiref.sync import sync_to_async
        
        def create_lead_record():
            return LeadConduit_Lead.objects.create(
                lead_id=validated_data['lead_id'],
                event_id=validated_data.get('event_id', ''),
                submitted_utc=validated_data.get('submitted_utc'),
                outcome=validated_data.get('outcome', ''),
                reason=validated_data.get('reason', ''),
                flow_name=validated_data.get('flow_name', ''),
                source_name=validated_data.get('source_name', ''),
                first_name=validated_data.get('first_name', ''),
                last_name=validated_data.get('last_name', ''),
                email=validated_data.get('email', ''),
                phone=validated_data.get('phone', ''),
                address=validated_data.get('address', ''),
                city=validated_data.get('city', ''),
                state=validated_data.get('state', ''),
                zip_code=validated_data.get('zip_code', ''),
                country=validated_data.get('country', ''),
                lead_data=validated_data.get('lead_data', {}),
                raw_data=validated_data.get('raw_data', {})
            )
        
        create_async = sync_to_async(create_lead_record)
        lead = await create_async()
        logger.debug(f"Created lead {lead.lead_id}")
        return lead
    
    async def update_lead(self, 
                         existing_lead: LeadConduit_Lead, 
                         lead_data: Dict[str, Any]) -> bool:
        """
        Update existing lead record
        
        Returns:
            bool: True if lead was updated, False if no changes
        """
        validated_data = self.validate_lead_data(lead_data)
        
        # Track if any changes were made
        updated = False
        
        # Update fields that might have changed
        update_fields = [
            'event_id', 'submitted_utc', 'outcome', 'reason', 'flow_name',
            'source_name', 'first_name', 'last_name', 'email', 'phone', 'address',
            'city', 'state', 'zip_code', 'country', 'lead_data', 'raw_data'
        ]
        
        for field in update_fields:
            new_value = validated_data.get(field)
            current_value = getattr(existing_lead, field)
            
            # Handle different data types
            if field in ['lead_data', 'raw_data']:
                # JSON field - compare as dict
                if new_value != current_value:
                    setattr(existing_lead, field, new_value or {})
                    updated = True
            elif field == 'submitted_utc':
                # DateTime field
                if new_value is not None and new_value != current_value:
                    setattr(existing_lead, field, new_value)
                    updated = True
            else:
                # String fields
                if new_value and new_value != current_value:
                    setattr(existing_lead, field, new_value)
                    updated = True
        
        if updated:
            from asgiref.sync import sync_to_async
            save_async = sync_to_async(existing_lead.save)
            await save_async()
            logger.debug(f"Updated lead {existing_lead.lead_id}")
        
        return updated
    
    def validate_lead_data(self, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate and clean lead data
        
        Args:
            lead_data: Raw lead data from get_all_leads_utc
            
        Returns:
            Dict: Validated and cleaned data
            
        Raises:
            ValueError: If validation fails
        """
        lead_id = lead_data.get('Lead ID')
        if not lead_id:
            raise ValueError("Lead ID is required")
        
        # Parse submitted_utc from string format
        submitted_utc_str = lead_data.get('Submitted UTC', '')
        submitted_utc = None
        if submitted_utc_str:
            try:
                # Parse "2024-01-01 12:00:00 UTC" format
                if ' UTC' in submitted_utc_str:
                    dt_str = submitted_utc_str.replace(' UTC', '')
                    submitted_utc = datetime.strptime(dt_str, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
                else:
                    # Try ISO format
                    submitted_utc = datetime.fromisoformat(submitted_utc_str)
                    if submitted_utc.tzinfo is None:
                        submitted_utc = submitted_utc.replace(tzinfo=timezone.utc)
            except Exception as e:
                logger.warning(f"Failed to parse submitted_utc '{submitted_utc_str}': {e}")
        
        # Map lead data fields to model fields
        validated_data = {
            'lead_id': str(lead_id).strip(),
            'submitted_utc': submitted_utc,
            'event_timestamp': lead_data.get('Event Timestamp'),
            'outcome': lead_data.get('Outcome', ''),
            'reason': lead_data.get('Reason', ''),
            'flow': lead_data.get('Flow', ''),
            'source': lead_data.get('Source', ''),
            'raw_lead_data': lead_data  # Store complete original data
        }
        
        # Extract contact information with various possible field names
        contact_fields = {
            'first_name': ['First Name', 'Firstname', 'first_name'],
            'last_name': ['Last Name', 'Lastname', 'last_name'],
            'email': ['Email', 'email', 'Email Address'],
            'phone': ['Phone', 'phone', 'Phone Number', 'Mobile'],
            'address': ['Address', 'address', 'Street Address'],
            'city': ['City', 'city'],
            'state': ['State', 'state', 'Province'],
            'zip_code': ['Zip Code', 'zip_code', 'Postal Code', 'Zip']
        }
        
        for model_field, possible_keys in contact_fields.items():
            value = ''
            for key in possible_keys:
                if key in lead_data and lead_data[key]:
                    value = str(lead_data[key]).strip()
                    break
            validated_data[model_field] = value
        
        return validated_data
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processor_type': 'LeadConduitLeadsProcessor',
            'entity_type': self.entity_type,
            'initialized_at': getattr(self, '_initialized_at', None)
        }
