import requests
import json
import os
import csv
import pandas as pd
from requests.auth import HTTPBasicAuth
from dotenv import load_dotenv
import zeep
from zeep import Transport
from datetime import datetime

# Load environment variables
load_dotenv()

USERNAME = os.getenv("FIVE9_USERNAME")
PASSWORD = os.getenv("FIVE9_PASSWORD")

class Five9ActualDataExtractor:
    """Five9 Actual Data Extractor - Get real contact records using getContactRecords"""
    
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.auth = HTTPBasicAuth(username, password)
        
        # Create authenticated transport
        session = requests.Session()
        session.auth = self.auth
        self.transport = Transport(session=session)
        
        # WSDL URLs
        encoded_username = username.replace('@', '%40')
        self.admin_wsdl = f"https://api.five9.com/wsadmin/v9_5/AdminWebService?wsdl&user={encoded_username}"
        self.supervisor_wsdl = f"https://api.five9.com/wssupervisor/v9_5/SupervisorWebService?wsdl&user={encoded_username}"
        
        self.admin_service = None
        self.supervisor_service = None
        
    def clean_zeep_object(self, obj):
        """Convert Zeep objects to clean Python objects"""
        if hasattr(obj, '__values__'):
            cleaned = {}
            for key, value in obj.__values__.items():
                cleaned[key] = self.clean_zeep_object(value)
            return cleaned
        elif isinstance(obj, list):
            return [self.clean_zeep_object(item) for item in obj]
        elif isinstance(obj, dict):
            return {k: self.clean_zeep_object(v) for k, v in obj.items()}
        else:
            return obj
        
    def connect(self):
        """Connect to Five9 Web Services"""
        print(f"[🔄] Connecting to Five9 Web Services...")
        
        try:
            admin_client = zeep.Client(self.admin_wsdl, transport=self.transport)
            self.admin_service = admin_client.service
            print(f"[✅] Admin Web Service connected!")
        except Exception as e:
            print(f"[❌] Admin Web Service failed: {e}")
            return False
        
        try:
            supervisor_client = zeep.Client(self.supervisor_wsdl, transport=self.transport)
            self.supervisor_service = supervisor_client.service
            
            session_params = {
                'forceLogoutSession': True,
                'rollingPeriod': 'Minutes30',
                'statisticsRange': 'CurrentWeek',
                'shiftStart': 8 * 60 * 60 * 1000,
                'timeZone': -7 * 60 * 60 * 1000,
            }
            self.supervisor_service.setSessionParameters(session_params)
            print(f"[✅] Supervisor Web Service connected!")
        except Exception as e:
            print(f"[❌] Supervisor Web Service failed: {e}")
        
        return True
    
    def get_contact_lists(self):
        """Get available contact lists"""
        try:
            print("[🔄] Getting contact lists...")
            lists_info = self.admin_service.getListsInfo()
            clean_lists = self.clean_zeep_object(lists_info)
            print(f"[✅] Found {len(clean_lists) if isinstance(clean_lists, list) else 'some'} contact lists")
            
            if isinstance(clean_lists, list):
                print("Available Contact Lists:")
                for i, contact_list in enumerate(clean_lists):
                    list_name = contact_list.get('name', 'Unknown')
                    list_size = contact_list.get('size', 'Unknown size')
                    print(f"  {i+1}. {list_name} ({list_size} records)")
                
                return clean_lists
            else:
                print(f"Lists info: {clean_lists}")
                return []
                
        except Exception as e:
            print(f"[❌] Error getting contact lists: {e}")
            return []
    
    def get_actual_contact_records(self, list_name=None, max_records=100):
        """Get actual contact records using getContactRecords method with proper lookup criteria"""
        print(f"\n" + "="*60)
        print("GETTING ACTUAL CONTACT RECORDS")
        print("="*60)
        
        try:
            # If no list specified, get the first available list
            if not list_name:
                lists = self.get_contact_lists()
                if not lists:
                    print("[❌] No contact lists found")
                    return None
                
                # Use the first list
                list_name = lists[0].get('name') if lists else None
                if not list_name:
                    print("[❌] Could not get list name")
                    return None
            
            print(f"\n[🔄] Getting contact records from list: {list_name}")
            print(f"[📊] Requesting records...")
            
            # Create lookup criteria - this is what getContactRecords actually expects
            # Based on error: crmFieldCriterion() only accepts 'field' and 'value' parameters
            # Try using last_list field which should contain the list name
            lookup_criteria = {
                'criteria': [
                    {
                        'field': 'last_list',
                        'value': list_name
                    }
                ]
            }
            
            print(f"[🔧] Using lookup criteria: {lookup_criteria}")
            
            # Get contact records using proper lookup criteria
            contact_records = self.admin_service.getContactRecords(
                lookupCriteria=lookup_criteria
            )
            
            clean_records = self.clean_zeep_object(contact_records)
            
            print(f"[🔍] Debug - Raw response type: {type(contact_records)}")
            print(f"[🔍] Debug - Clean records type: {type(clean_records)}")
            print(f"[🔍] Debug - Clean records content (first 500 chars): {str(clean_records)[:500]}")
            
            if isinstance(clean_records, list):
                print(f"[🎉] SUCCESS! Retrieved {len(clean_records)} contact records")
                
                if clean_records:
                    # Show sample record
                    sample_record = clean_records[0]
                    print(f"\nSample record type: {type(sample_record)}")
                    print(f"Sample record fields: {list(sample_record.keys()) if isinstance(sample_record, dict) else 'Not a dict'}")
                    print(f"Sample record (first 200 chars): {str(sample_record)[:200]}...")
                
                return clean_records, list_name
            elif clean_records is not None:
                print(f"[⚠️] Non-list response: {type(clean_records)}")
                print(f"Response content: {clean_records}")
                # Try to convert single record to list
                if isinstance(clean_records, dict):
                    return [clean_records], list_name
                else:
                    return None, list_name
            else:
                print(f"[⚠️] Empty response")
                return None, list_name
                
        except Exception as e:
            print(f"[❌] Error getting contact records: {e}")
            print(f"[🔧] Trying alternative approach...")
            
            # Try alternative approach - try using a different field or method
            try:
                # Try using number1 field with empty value to get any records
                print(f"[🔧] Trying with number1 field...")
                contact_records = self.admin_service.getContactRecords(
                    lookupCriteria={'criteria': [{'field': 'number1', 'value': ''}]}
                )
                
                clean_records = self.clean_zeep_object(contact_records)
                
                print(f"[🔍] Alt Debug - Response type: {type(clean_records)}")
                print(f"[🔍] Alt Debug - Response content (first 300 chars): {str(clean_records)[:300]}")
                
                if clean_records and isinstance(clean_records, list) and len(clean_records) > 0:
                    print(f"[✅] Alternative approach worked! Got {len(clean_records)} records")
                    return clean_records, list_name
                elif clean_records and isinstance(clean_records, dict):
                    print(f"[✅] Alternative approach worked! Got single record")
                    return [clean_records], list_name
                else:
                    print(f"[❌] Alternative approach failed - no valid records")
                    return None, list_name
                    
            except Exception as e2:
                print(f"[❌] Alternative approach error: {e2}")
                print(f"[🔧] Trying with first_name field...")
                
                # Try with a basic field that might exist
                try:
                    contact_records = self.admin_service.getContactRecords(
                        lookupCriteria={'criteria': [{'field': 'first_name', 'value': ''}]}
                    )
                    
                    clean_records = self.clean_zeep_object(contact_records)
                    
                    print(f"[🔍] Final Debug - Response type: {type(clean_records)}")
                    print(f"[🔍] Final Debug - Response content (first 300 chars): {str(clean_records)[:300]}")
                    
                    if clean_records and isinstance(clean_records, list) and len(clean_records) > 0:
                        print(f"[✅] Final approach worked! Got {len(clean_records)} records")
                        return clean_records, list_name
                    elif clean_records and isinstance(clean_records, dict):
                        print(f"[✅] Final approach worked! Got single record")
                        return [clean_records], list_name
                    else:
                        print(f"[❌] Final approach failed - no valid records")
                        return None, list_name
                        
                except Exception as e3:
                    print(f"[❌] Final approach error: {e3}")
                    return None, list_name
    
    def try_multiple_lists(self, max_records=100):
        """Try to get contact records from multiple lists"""
        print(f"\n[🔍] Trying to get contact records from multiple lists...")
        
        lists = self.get_contact_lists()
        if not lists:
            return {}
        
        all_records = {}
        
        # Try first few lists
        for i, contact_list in enumerate(lists[:3]):  # Try first 3 lists
            list_name = contact_list.get('name')
            list_size = contact_list.get('size', 0)
            
            if list_size > 0:  # Only try lists with records
                print(f"\n[🎯] Trying list {i+1}: {list_name} ({list_size} records)")
                
                try:
                    records, _ = self.get_actual_contact_records(list_name, max_records)
                    if records:
                        all_records[list_name] = records
                        print(f"[✅] Successfully got {len(records)} records from {list_name}")
                    else:
                        print(f"[⚠️] No records retrieved from {list_name}")
                        
                except Exception as e:
                    print(f"[❌] Error with list {list_name}: {e}")
                    continue
            else:
                print(f"[⏭️] Skipping empty list: {list_name}")
        
        return all_records
    
    def save_contact_records_to_csv(self, records, list_name):
        """Save contact records to CSV file"""
        if not records:
            print(f"[⚠️] No records to save for {list_name}")
            return
        
        print(f"[🔍] Debug - Records to save: {len(records)} records")
        print(f"[🔍] Debug - Sample record: {str(records[0])[:200] if records else 'None'}")
        
        # Clean the list name for filename
        safe_list_name = "".join(c for c in list_name if c.isalnum() or c in (' ', '-', '_')).rstrip()
        safe_list_name = safe_list_name.replace(' ', '_')
        filename = f"five9_contacts_{safe_list_name}.csv"
        
        try:
            # Handle Five9 API response structure
            normalized_records = []
            
            for record_structure in records:
                if isinstance(record_structure, dict) and 'fields' in record_structure and 'records' in record_structure:
                    # This is the Five9 API response structure
                    fields = record_structure['fields']
                    contact_records = record_structure['records']
                    
                    print(f"[🔍] Processing {len(contact_records)} contact records with {len(fields)} fields")
                    
                    for contact_record in contact_records:
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
                                
                                normalized_records.append(contact_dict)
                else:
                    # Handle other data structures
                    if isinstance(record_structure, dict):
                        # Flatten any nested structures
                        flat_record = {}
                        for key, value in record_structure.items():
                            if isinstance(value, (dict, list)):
                                flat_record[key] = str(value)  # Convert complex types to strings
                            else:
                                flat_record[key] = value
                        normalized_records.append(flat_record)
                    else:
                        # Convert non-dict records to string representation
                        normalized_records.append({"record": str(record_structure)})
            
            if not normalized_records:
                print(f"[⚠️] No valid records to save for {list_name}")
                return
                
            # Convert to DataFrame
            df = pd.DataFrame(normalized_records)
            df.to_csv(filename, index=False, encoding='utf-8')
            
            print(f"[💾] Saved {len(normalized_records)} contact records to {filename}")
            print(f"[📊] Columns: {list(df.columns)[:10]}...")  # Show first 10 columns
            
            return filename
            
        except Exception as e:
            print(f"[❌] Failed to save {list_name} contacts to CSV: {e}")
            
            # Try saving as JSON instead
            try:
                json_filename = f"five9_contacts_{safe_list_name}.json"
                with open(json_filename, 'w', encoding='utf-8') as f:
                    json.dump(records, f, indent=2, default=str)
                print(f"[💾] Saved as JSON instead: {json_filename}")
                return json_filename
            except Exception as e2:
                print(f"[❌] Failed to save as JSON too: {e2}")
                return None

def main():
    """Main function"""
    print("=== Five9 Actual Contact Data Extractor ===")
    print("Using getContactRecords to get real contact data")
    print()
    
    if not USERNAME or not PASSWORD:
        print("[❌] Error: Credentials not found in .env file")
        return
    
    # Create extractor
    extractor = Five9ActualDataExtractor(USERNAME, PASSWORD)
    
    if not extractor.connect():
        print("[❌] Failed to connect")
        return
    
    try:
        # Try to get contact records from multiple lists
        all_records = extractor.try_multiple_lists(max_records=100)
        
        if all_records:
            print(f"\n" + "="*60)
            print("SAVING CONTACT RECORDS TO CSV")
            print("="*60)
            
            saved_files = []
            total_records = 0
            
            for list_name, records in all_records.items():
                filename = extractor.save_contact_records_to_csv(records, list_name)
                if filename:
                    saved_files.append(filename)
                    total_records += len(records)
            
            print(f"\n[🎉] SUCCESS! Contact data extraction complete:")
            print(f"  • Total lists processed: {len(all_records)}")
            print(f"  • Total contact records: {total_records}")
            print(f"  • CSV files created: {len(saved_files)}")
            for filename in saved_files:
                print(f"    - {filename}")
                
        else:
            print("\n[❌] No contact records could be retrieved")
            print("This could be due to:")
            print("  • Empty contact lists")
            print("  • Permission restrictions")
            print("  • API limitations")
        
    finally:
        try:
            if extractor.admin_service:
                extractor.admin_service.closeSession()
            if extractor.supervisor_service:
                extractor.supervisor_service.closeSession()
            print("[✅] Sessions closed")
        except:
            pass

if __name__ == '__main__':
    main()
