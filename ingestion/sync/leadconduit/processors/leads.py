"""
LeadConduit Leads Processor

Data processing and validation for LeadConduit leads following
sync_crm_guide.md architecture.
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone
from django.db import transaction
from asgiref.sync import sync_to_async

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
        Process a batch of LeadConduit leads with bulk operations and individual fallback
        
        Args:
            leads_batch: List of lead records from get_all_leads_utc
            
        Returns:
            Dict with processing results
        """
        logger.info(f"Processing batch of {len(leads_batch)} leads")
        
        if not leads_batch:
            return {'processed': 0, 'created': 0, 'updated': 0, 'failed': 0, 'errors': []}
        
        try:
            # Try bulk processing first
            return await self._process_batch_bulk(leads_batch)
            
        except Exception as e:
            logger.error(f"Bulk processing failed with {len(leads_batch)} records: {e}")
            
            # Fall back to individual processing
            logger.info(f"Attempting individual processing for {len(leads_batch)} records after bulk failure")
            return await self._process_batch_individually(leads_batch)
    
    async def _process_batch_bulk(self, leads_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Internal bulk processing method with transaction support
        """
        result = {
            'processed': len(leads_batch),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        @sync_to_async
        def process_bulk():
            with transaction.atomic():
                # Validate all records first
                validated_leads = []
                for lead_data in leads_batch:
                    try:
                        validated_data = self.validate_lead_data(lead_data)
                        validated_leads.append(validated_data)
                    except Exception as e:
                        logger.error(f"Failed to validate lead {lead_data.get('Lead ID')}: {e}")
                        result['failed'] += 1
                        result['errors'].append({
                            'lead_id': lead_data.get('Lead ID'),
                            'error': str(e)
                        })
                
                if not validated_leads:
                    return result
                
                # Get existing leads in batch
                lead_ids = [lead['lead_id'] for lead in validated_leads]
                existing_leads = {
                    lead.lead_id: lead 
                    for lead in LeadConduit_Lead.objects.filter(lead_id__in=lead_ids)
                }
                
                # Separate creates and updates
                leads_to_create = []
                leads_to_update = []
                
                for validated_data in validated_leads:
                    lead_id = validated_data['lead_id']
                    existing_lead = existing_leads.get(lead_id)
                    
                    if existing_lead:
                        # Check if update is needed
                        if self._has_record_changed(existing_lead, validated_data):
                            updated_lead = self._prepare_updated_lead(existing_lead, validated_data)
                            leads_to_update.append(updated_lead)
                    else:
                        # New record
                        lead_obj = LeadConduit_Lead(**validated_data)
                        leads_to_create.append(lead_obj)
                
                # Bulk create new leads
                if leads_to_create:
                    LeadConduit_Lead.objects.bulk_create(leads_to_create, batch_size=500)
                    result['created'] = len(leads_to_create)
                    logger.info(f"Bulk created {len(leads_to_create)} leads")
                
                # Bulk update existing leads
                if leads_to_update:
                    update_fields = [
                        'event_id', 'submitted_utc', 'outcome', 'reason', 'flow_name',
                        'source_name', 'first_name', 'last_name', 'email', 'phone', 
                        'address', 'city', 'state', 'zip_code', 'country', 'lead_data', 'raw_data',
                        # HGE-specific fields
                        'note_hge', 'owner_hge', 'owneremail_hge', 'ownerid_hge', 'salesrabbit_lead_id_hge',
                        # Metadata fields
                        'phone_metadata', 'email_metadata', 'address_metadata'
                    ]
                    LeadConduit_Lead.objects.bulk_update(
                        leads_to_update, 
                        update_fields, 
                        batch_size=500
                    )
                    result['updated'] = len(leads_to_update)
                    logger.info(f"Bulk updated {len(leads_to_update)} leads")
                
                return result
        
        return await process_bulk()
    
    async def _process_batch_individually(self, leads_batch: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Process records individually when bulk operations fail
        """
        result = {
            'processed': len(leads_batch),
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        for lead_data in leads_batch:
            try:
                process_result = await self.process_single_lead(lead_data)
                
                if process_result['created']:
                    result['created'] += 1
                elif process_result['updated']:
                    result['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Failed to process individual lead {lead_data.get('Lead ID')}: {e}")
                result['failed'] += 1
                result['errors'].append({
                    'lead_id': lead_data.get('Lead ID'),
                    'error': str(e)
                })
        
        logger.info(f"Individual processing results: {result}")
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
                # HGE-specific fields
                note_hge=validated_data.get('note_hge', ''),
                owner_hge=validated_data.get('owner_hge', ''),
                owneremail_hge=validated_data.get('owneremail_hge', ''),
                ownerid_hge=validated_data.get('ownerid_hge', ''),
                salesrabbit_lead_id_hge=validated_data.get('salesrabbit_lead_id_hge', ''),
                # Metadata fields
                phone_metadata=validated_data.get('phone_metadata', {}),
                email_metadata=validated_data.get('email_metadata', {}),
                address_metadata=validated_data.get('address_metadata', {}),
                # Data storage
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
            'city', 'state', 'zip_code', 'country', 'lead_data', 'raw_data',
            # HGE-specific fields
            'note_hge', 'owner_hge', 'owneremail_hge', 'ownerid_hge', 'salesrabbit_lead_id_hge',
            # Metadata fields
            'phone_metadata', 'email_metadata', 'address_metadata'
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
            save_async = sync_to_async(existing_lead.save)
            await save_async()
            logger.debug(f"Updated lead {existing_lead.lead_id}")
        
        return updated
    
    def _has_record_changed(self, existing_lead: LeadConduit_Lead, new_data: Dict[str, Any]) -> bool:
        """Check if record has changed using delta comparison"""
        # Check key fields for changes
        change_detection_fields = [
            'first_name', 'last_name', 'email', 'phone', 
            'outcome', 'reason', 'flow_name', 'source_name'
        ]
        
        for field in change_detection_fields:
            if field in new_data:
                new_value = str(new_data[field]) if new_data[field] is not None else ""
                existing_value = str(getattr(existing_lead, field)) if getattr(existing_lead, field) is not None else ""
                
                if new_value != existing_value:
                    logger.debug(f"Field '{field}' changed for lead {existing_lead.lead_id}: '{existing_value}' -> '{new_value}'")
                    return True
        
        return False
    
    def _prepare_updated_lead(self, existing_lead: LeadConduit_Lead, new_data: Dict[str, Any]) -> LeadConduit_Lead:
        """Prepare existing lead with updated data"""
        # Update only the fields that have changed
        for field, value in new_data.items():
            if field != 'lead_id' and hasattr(existing_lead, field):
                setattr(existing_lead, field, value)
        
        return existing_lead
    
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
            'event_id': lead_data.get('Lead ID', ''),  # Use Lead ID as event_id
            'outcome': lead_data.get('Outcome', ''),
            'reason': lead_data.get('Reason', ''),
            'flow_name': lead_data.get('Flow', ''),  # Map to flow_name field
            'source_name': lead_data.get('Source', ''),  # Map to source_name field
            'lead_data': lead_data,  # Store complete original data in lead_data field
            'raw_data': lead_data  # Store complete original data in raw_data field
        }
        
        # Extract contact information with various possible field names
        contact_fields = {
            'first_name': ['First Name', 'Firstname', 'first_name'],
            'last_name': ['Last Name', 'Lastname', 'last_name'],
            'email': ['Email', 'email', 'Email Address'],
            'phone': ['Phone', 'phone', 'Phone Number', 'Mobile', 'phone_1'],
            'address': ['Address', 'address', 'Street Address', 'address_1'],
            'city': ['City', 'city'],
            'state': ['State', 'state', 'Province'],
            'zip_code': ['Zip Code', 'zip_code', 'Postal Code', 'Zip', 'postal_code'],
            # HGE-specific fields
            'note_hge': ['note_hge', 'Note Hge'],
            'owner_hge': ['owner_hge', 'Owner Hge'],
            'owneremail_hge': ['owneremail_hge', 'Owneremail Hge'],
            'ownerid_hge': ['ownerid_hge', 'Ownerid Hge'],
            'salesrabbit_lead_id_hge': ['salesrabbit_lead_id_hge', 'Salesrabbit Lead Id Hge']
        }

        # Store metadata for complex fields
        metadata_storage = {
            'phone_metadata': None,
            'email_metadata': None,
            'address_metadata': None
        }

        for model_field, possible_keys in contact_fields.items():
            value = ''
            raw_metadata = None
            for key in possible_keys:
                if key in lead_data and lead_data[key]:
                    raw_value = lead_data[key]
                    
                    # Special handling for zip_code field - it comes as a dict
                    if model_field == 'zip_code' and isinstance(raw_value, dict):
                        # Extract the actual zip code from the dict
                        value = str(raw_value.get('zip', raw_value.get('code', raw_value.get('normal', '')))).strip()
                        #logger.debug(f"Extracted zip_code from dict for lead {lead_id}: {raw_value} -> {value}")
                    # Special handling for email field - it comes as a dict with validation info
                    elif model_field == 'email' and isinstance(raw_value, dict):
                        # Extract the actual email from the dict and store metadata
                        value = str(raw_value.get('normal', raw_value.get('raw', raw_value.get('email', '')))).strip()
                        metadata_storage['email_metadata'] = raw_value
                        #logger.debug(f"Extracted email from dict for lead {lead_id}: {raw_value} -> {value}")
                    # Special handling for phone field - it comes as a dict with validation info
                    elif model_field == 'phone' and isinstance(raw_value, dict):
                        # Extract the actual phone from the dict and store metadata
                        value = str(raw_value.get('normal', raw_value.get('raw', raw_value.get('phone', '')))).strip()
                        metadata_storage['phone_metadata'] = raw_value
                        #logger.debug(f"Extracted phone from dict for lead {lead_id}: {raw_value} -> {value}")
                    # Special handling for address field - it comes as a dict with validation info
                    elif model_field == 'address' and isinstance(raw_value, dict):
                        # Extract the actual address from the dict and store metadata
                        value = str(raw_value.get('normal', raw_value.get('raw', raw_value.get('address', '')))).strip()
                        metadata_storage['address_metadata'] = raw_value
                        #logger.debug(f"Extracted address from dict for lead {lead_id}: {raw_value} -> {value}")
                    else:
                        value = str(raw_value).strip()
                    break
            validated_data[model_field] = value

        # Additional check: Handle any remaining dict-like zip codes that might have been missed
        if 'zip_code' in validated_data and validated_data['zip_code']:
            zip_value = validated_data['zip_code']
            # Check if it looks like a stringified dict (starts with { and contains 'zip':)
            if isinstance(zip_value, str) and zip_value.startswith('{') and "'zip':" in zip_value:
                try:
                    # Try to parse it back to a dict and extract the zip
                    import ast
                    zip_dict = ast.literal_eval(zip_value)
                    if isinstance(zip_dict, dict):
                        extracted_zip = str(zip_dict.get('zip', zip_dict.get('code', zip_dict.get('normal', '')))).strip()
                        validated_data['zip_code'] = extracted_zip
                        #logger.info(f"Fixed stringified zip_code dict for lead {lead_id}: extracted '{extracted_zip}'")
                except Exception as e:
                    logger.warning(f"Failed to parse zip_code dict string for lead {lead_id}: {e}")

        # Additional check: Handle any remaining dict-like emails that might have been missed
        if 'email' in validated_data and validated_data['email']:
            email_value = validated_data['email']
            # Check if it looks like a stringified dict (starts with { and contains 'normal':)
            if isinstance(email_value, str) and email_value.startswith('{') and "'normal':" in email_value:
                try:
                    # Try to parse it back to a dict and extract the email
                    import ast
                    email_dict = ast.literal_eval(email_value)
                    if isinstance(email_dict, dict):
                        extracted_email = str(email_dict.get('normal', email_dict.get('raw', email_dict.get('email', '')))).strip()
                        validated_data['email'] = extracted_email
                        #.debug(f"Fixed stringified email dict for lead {lead_id}: extracted '{extracted_email}'")
                except Exception as e:
                    logger.warning(f"Failed to parse email dict string for lead {lead_id}: {e}")

        # Add metadata storage to validated_data
        for metadata_field, metadata_value in metadata_storage.items():
            if metadata_value is not None:
                validated_data[metadata_field] = metadata_value
            else:
                validated_data[metadata_field] = {}

        # Apply field length limits to prevent database errors
        # These limits match the actual database schema constraints
        field_limits = {
            'lead_id': 100,         # Model: CharField(max_length=100), DB: varchar(255)
            'event_id': 100,        # Model: CharField(max_length=100), DB: varchar(255)
            'first_name': 200,      # Model: CharField(max_length=200)
            'last_name': 200,       # Model: CharField(max_length=200)
            'email': 254,           # Model: EmailField (default 254), DB: varchar(255)
            'phone': 50,            # Model: CharField(max_length=50), DB: varchar(255)
            'address': 500,         # Model: CharField(max_length=500)
            'city': 200,            # Model: CharField(max_length=200)
            'state': 100,           # Model: CharField(max_length=100), DB: varchar(255)
            'zip_code': 50,         # Model: CharField(max_length=50), DB: varchar(255)
            'country': 100,         # Model: CharField(max_length=100), DB: varchar(255)
            'flow_name': 100,       # Model: CharField(max_length=100), DB: varchar(255)
            'source_name': 100,     # Model: CharField(max_length=100), DB: varchar(255)
            'outcome': 255,         # Model: CharField(max_length=255), DB: varchar(255)
            # HGE-specific field limits
            'owner_hge': 100,       # Model: CharField(max_length=100)
            'owneremail_hge': 254,  # Model: EmailField (default 254)
            'ownerid_hge': 50,      # Model: CharField(max_length=50)
            'salesrabbit_lead_id_hge': 50  # Model: CharField(max_length=50)
        }
        
        for field, max_length in field_limits.items():
            if field in validated_data and validated_data[field]:
                original_value = validated_data[field]
                if len(original_value) > max_length:
                    truncated_value = original_value[:max_length]
                    validated_data[field] = truncated_value
                    logger.warning(f"Truncated {field} from {len(original_value)} to {max_length} chars for lead {lead_id}: '{original_value}' -> '{truncated_value}'")

        return validated_data
    
    def get_processing_stats(self) -> Dict[str, Any]:
        """Get processing statistics"""
        return {
            'processor_type': 'LeadConduitLeadsProcessor',
            'entity_type': self.entity_type,
            'initialized_at': getattr(self, '_initialized_at', None)
        }
