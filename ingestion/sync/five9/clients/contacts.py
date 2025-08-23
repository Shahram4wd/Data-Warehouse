"""
Five9 Contacts API Client
Handles contact list retrieval and contact record extraction
"""
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import logging
from .base import BaseFive9Client
from ....config.five9_config import Five9Config, DELTA_SYNC_CONFIG

logger = logging.getLogger(__name__)


class ContactsClient(BaseFive9Client):
    """Five9 Contacts API Client"""
    
    def get_contact_lists(self) -> List[Dict[str, Any]]:
        """Get all available contact lists"""
        try:
            logger.info("Fetching Five9 contact lists...")
            lists_info = self.admin_service.getListsInfo()
            clean_lists = self.clean_zeep_object(lists_info)
            
            if isinstance(clean_lists, list):
                logger.info(f"Found {len(clean_lists)} contact lists")
                for contact_list in clean_lists:
                    list_name = contact_list.get('name', 'Unknown')
                    list_size = contact_list.get('size', 0)
                    logger.debug(f"List: {list_name} ({list_size} records)")
                return clean_lists
            else:
                logger.warning(f"Unexpected lists response format: {type(clean_lists)}")
                return []
                
        except Exception as e:
            logger.error(f"Error getting contact lists: {e}")
            return []
    
    def get_contact_records(self, list_name: Optional[str] = None, max_records: int = 100) -> Tuple[Optional[List[Dict]], Optional[str]]:
        """
        Get actual contact records using getContactRecords method
        
        Args:
            list_name: Name of the contact list (if None, tries first available list)
            max_records: Maximum number of records to retrieve
            
        Returns:
            Tuple of (records, list_name) where records is list of contact data
        """
        logger.info(f"Getting contact records from list: {list_name or 'first available'}")
        
        try:
            # If no list specified, get the first available list
            if not list_name:
                lists = self.get_contact_lists()
                if not lists:
                    logger.error("No contact lists found")
                    return None, None
                
                # Use the first non-empty list
                for contact_list in lists:
                    if contact_list.get('size', 0) > 0:
                        list_name = contact_list.get('name')
                        break
                
                if not list_name:
                    logger.error("No non-empty contact lists found")
                    return None, None
            
            logger.info(f"Retrieving contact records from list: {list_name}")
            
            # Try multiple lookup strategies based on actual_data_extractor.py
            lookup_strategies = [
                {'field': 'last_list', 'value': list_name},
                {'field': 'number1', 'value': ''},  # Empty value to get any records
                {'field': 'first_name', 'value': ''},  # Basic field fallback
            ]
            
            for i, lookup_criteria in enumerate(lookup_strategies):
                try:
                    logger.debug(f"Trying lookup strategy {i+1}: {lookup_criteria}")
                    
                    contact_records = self.admin_service.getContactRecords(
                        lookupCriteria={'criteria': [lookup_criteria]}
                    )
                    
                    clean_records = self.clean_zeep_object(contact_records)
                    
                    if self._validate_records(clean_records):
                        logger.info(f"Successfully retrieved records using strategy {i+1}")
                        return self._process_records(clean_records), list_name
                        
                except Exception as strategy_error:
                    logger.debug(f"Strategy {i+1} failed: {strategy_error}")
                    continue
            
            logger.warning(f"All lookup strategies failed for list: {list_name}")
            return None, list_name
                    
        except Exception as e:
            logger.error(f"Error getting contact records: {e}")
            return None, list_name
    
    def _validate_records(self, records: Any) -> bool:
        """Validate that records response contains usable data"""
        if not records:
            return False
        
        if isinstance(records, list) and len(records) > 0:
            return True
        elif isinstance(records, dict):
            # Check if it's a Five9 API response structure
            if 'fields' in records and 'records' in records:
                return len(records.get('records', [])) > 0
            return True
        
        return False
    
    def _process_records(self, records: Any) -> List[Dict]:
        """
        Process Five9 API response into standardized record format
        Based on the structure from actual_data_extractor.py
        """
        normalized_records = []
        
        if isinstance(records, list):
            for record in records:
                normalized_records.extend(self._process_single_record_structure(record))
        else:
            normalized_records.extend(self._process_single_record_structure(records))
        
        logger.info(f"Processed {len(normalized_records)} contact records")
        return normalized_records
    
    def _process_single_record_structure(self, record_structure: Any) -> List[Dict]:
        """Process a single record structure from Five9 API - matches actual_data_extractor.py"""
        processed_records = []
        
        try:
            if isinstance(record_structure, dict):
                if 'fields' in record_structure and 'records' in record_structure:
                    # This is the Five9 API response structure: {fields: [], records: []}
                    fields = record_structure['fields']
                    contact_records = record_structure['records']
                    
                    logger.debug(f"Processing {len(contact_records)} contact records with {len(fields)} fields")
                    
                    for contact_record in contact_records:
                        try:
                            if isinstance(contact_record, dict) and 'values' in contact_record:
                                values_data = contact_record['values']
                                if isinstance(values_data, dict) and 'data' in values_data:
                                    data_array = values_data['data']
                                    
                                    # Create a dictionary mapping field names to values
                                    contact_dict = {}
                                    for i, field_name in enumerate(fields):
                                        if i < len(data_array):
                                            contact_dict[field_name] = data_array[i]
                                        else:
                                            contact_dict[field_name] = None
                                    
                                    processed_records.append(contact_dict)
                        except Exception as record_error:
                            logger.error(f"Error processing contact record: {record_error}")
                            continue
                else:
                    # Handle flat record structure
                    flat_record = {}
                    for key, value in record_structure.items():
                        if isinstance(value, (dict, list)):
                            flat_record[key] = str(value)  # Convert complex types to strings
                        else:
                            flat_record[key] = value
                    processed_records.append(flat_record)
            else:
                # Convert non-dict records to string representation
                processed_records.append({"raw_data": str(record_structure)})
        except Exception as e:
            logger.error(f"Error in _process_single_record_structure: {e}")
            logger.error(f"Record structure type: {type(record_structure)}")
            if hasattr(record_structure, '__dict__'):
                logger.error(f"Record structure attributes: {dir(record_structure)}")
            raise
        
        return processed_records
    
    def get_all_contact_records(self, max_records_per_list: int = 100) -> Dict[str, List[Dict]]:
        """
        Get contact records from all available lists
        
        Args:
            max_records_per_list: Maximum records to retrieve per list
            
        Returns:
            Dictionary mapping list_name to list of contact records
        """
        logger.info("Retrieving contact records from all available lists...")
        
        lists = self.get_contact_lists()
        if not lists:
            logger.error("No contact lists found")
            return {}
        
        all_records = {}
        
        # Process each list that has records
        for i, contact_list in enumerate(lists):
            list_name = contact_list.get('name')
            list_size = contact_list.get('size', 0)
            
            if list_size > 0:  # Only try lists with records
                logger.info(f"Processing list {i+1}/{len(lists)}: {list_name} ({list_size} records)")
                
                try:
                    records, _ = self.get_contact_records(list_name, max_records_per_list)
                    if records:
                        all_records[list_name] = records
                        logger.info(f"Successfully retrieved {len(records)} records from {list_name}")
                    else:
                        logger.warning(f"No records retrieved from {list_name}")
                        
                except Exception as e:
                    logger.error(f"Error processing list {list_name}: {e}")
                    continue
            else:
                logger.debug(f"Skipping empty list: {list_name}")
        
        logger.info(f"Successfully retrieved records from {len(all_records)} lists")
        return all_records
