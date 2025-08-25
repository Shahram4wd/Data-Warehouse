"""
Five9 Configuration
Contains field mappings, API settings, and sync configurations for Five9 CRM integration
"""

from typing import Dict, Any, List
from decimal import Decimal


class Five9FieldTypes:
    """Five9 field type constants"""
    PHONE = "PHONE"
    EMAIL = "EMAIL"
    STRING = "STRING"
    DATE_TIME = "DATE_TIME"
    DATE = "DATE"
    NUMBER = "NUMBER"
    BOOLEAN = "BOOLEAN"


class Five9Config:
    """Five9 CRM Configuration"""
    
    # API Configuration
    API_VERSION = "v9_5"
    BASE_URL = "https://api.five9.com"
    ADMIN_WSDL_PATH = f"/wsadmin/{API_VERSION}/AdminWebService"
    SUPERVISOR_WSDL_PATH = f"/wssupervisor/{API_VERSION}/SupervisorWebService"
    
    # Session Configuration
    SESSION_TIMEOUT_MINUTES = 30
    FORCE_LOGOUT_SESSION = True
    ROLLING_PERIOD = "Minutes30"
    STATISTICS_RANGE = "CurrentWeek"
    SHIFT_START_HOUR = 8
    TIMEZONE_OFFSET_HOURS = -7
    
    # Sync Configuration
    DEFAULT_BATCH_SIZE = 100
    MAX_BATCH_SIZE = 1000
    DEFAULT_RETRY_ATTEMPTS = 3
    RETRY_BACKOFF_SECONDS = 5
    
    # Rate Limiting
    REQUESTS_PER_MINUTE = 100
    CONCURRENT_REQUESTS = 5


# Five9 Field Definitions (based on your field mapping data)
FIVE9_FIELD_DEFINITIONS = [
    # Standard Contact Fields
    {"name": "number1", "displayAs": "Long", "mapTo": None, "type": Five9FieldTypes.PHONE, "system": True, "required": False},
    {"name": "number2", "displayAs": "Long", "mapTo": None, "type": Five9FieldTypes.PHONE, "system": True, "required": False},
    {"name": "number3", "displayAs": "Long", "mapTo": None, "type": Five9FieldTypes.PHONE, "system": True, "required": False},
    {"name": "first_name", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "last_name", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "company", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "street", "displayAs": "Long", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "city", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "state", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "zip", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": True, "required": False},
    {"name": "email", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.EMAIL, "system": False, "required": False},
    
    # System Fields
    {"name": "contactID", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "sys_created_date", "displayAs": "Invisible", "mapTo": "CreatedDateTime", "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    {"name": "sys_last_agent", "displayAs": "Invisible", "mapTo": "LastAgent", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "sys_last_disposition", "displayAs": "Invisible", "mapTo": "LastDisposition", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "sys_last_disposition_time", "displayAs": "Invisible", "mapTo": "LastDispositionDateTime", "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    {"name": "last_campaign", "displayAs": "Invisible", "mapTo": "LastCampaign", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "attempts", "displayAs": "Invisible", "mapTo": "AttemptsForLastCampaign", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "last_list", "displayAs": "Invisible", "mapTo": "LastList", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    
    # Custom UUID Fields
    {"name": "f65d759a-2250-4b2d-89a9-60796f624f72", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.PHONE, "system": False, "required": False},
    {"name": "4f347541-7c4d-4812-9190-e8dea6c0eb49", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    {"name": "80cf8462-cc10-41b8-a68a-5898cdba1e11", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    
    # Additional Custom Fields
    {"name": "New Contact Field", "displayAs": "Invisible", "mapTo": "LastModifiedDateTime", "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    {"name": "lead_source", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "DialAttempts", "displayAs": "Invisible", "mapTo": "AttemptsForLastCampaign", "type": Five9FieldTypes.NUMBER, "system": False, "required": False, "precision": 5, "scale": 0},
    {"name": "XCounter", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "F9_list", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "DoNotDial", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.BOOLEAN, "system": False, "required": False},
    {"name": "ggg", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "lead_prioritization", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.NUMBER, "system": False, "required": False, "precision": 2, "scale": 0},
    {"name": "metal_count", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.NUMBER, "system": False, "required": False, "precision": 5, "scale": 0},
    
    # Agent Disposition Fields
    {"name": "Last Agent Disposition", "displayAs": "Invisible", "mapTo": "LastAgentDisposition", "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Last Agent Disposition Date-Time", "displayAs": "Invisible", "mapTo": "LastAgentDispositionDateTime", "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    
    # Business Fields
    {"name": "Market", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Secondary Lead Source", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "HubSpot_ContactID", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Result", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Product", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Appointment Date and Time", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.DATE_TIME, "system": False, "required": False},
    {"name": "Carrier", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "TFUID", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Lead Status", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "PC Work Finished", "displayAs": "Short", "mapTo": None, "type": Five9FieldTypes.DATE, "system": False, "required": False},
    {"name": "Total Job Amount", "displayAs": "Long", "mapTo": None, "type": Five9FieldTypes.NUMBER, "system": False, "required": False, "precision": 7, "scale": 2},
    {"name": "Position", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.STRING, "system": False, "required": False},
    {"name": "Appointment Date", "displayAs": "Invisible", "mapTo": None, "type": Five9FieldTypes.DATE, "system": False, "required": False},
]


class Five9FieldMapper:
    """Five9 Field Mapping Utility"""
    
    def __init__(self):
        self.field_definitions = {field["name"]: field for field in FIVE9_FIELD_DEFINITIONS}
    
    def get_field_definition(self, field_name: str) -> Dict[str, Any]:
        """Get field definition by name"""
        return self.field_definitions.get(field_name, {})
    
    def get_django_field_name(self, five9_field_name: str) -> str:
        """Convert Five9 field name to Django model field name"""
        # Mapping table for exact field name conversions
        field_name_mapping = {
            # Standard fields - lowercase
            'number1': 'number1',
            'number2': 'number2', 
            'number3': 'number3',
            'first_name': 'first_name',
            'last_name': 'last_name',
            'company': 'company',
            'street': 'street',
            'city': 'city',
            'state': 'state',
            'zip': 'zip',
            'email': 'email',
            
            # System fields with mixed case
            'contactID': 'contactID',
            'contactid': 'contactID',  # Handle both variants
            'sys_created_date': 'sys_created_date',
            'sys_last_agent': 'sys_last_agent',
            'sys_last_disposition': 'sys_last_disposition', 
            'sys_last_disposition_time': 'sys_last_disposition_time',
            'last_campaign': 'last_campaign',
            'attempts': 'attempts',
            'last_list': 'last_list',
            
            # UUID fields
            'f65d759a-2250-4b2d-89a9-60796f624f72': 'f65d759a_2250_4b2d_89a9_60796f624f72',
            '4f347541-7c4d-4812-9190-e8dea6c0eb49': 'field_4f347541_7c4d_4812_9190_e8dea6c0eb49', 
            '80cf8462-cc10-41b8-a68a-5898cdba1e11': 'field_80cf8462_cc10_41b8_a68a_5898cdba1e11',
            
            # Custom fields with underscores and CamelCase
            'New Contact Field': 'New_Contact_Field',
            'new_contact_field': 'New_Contact_Field',
            'lead_source': 'lead_source',
            'DialAttempts': 'DialAttempts',
            'dialattempts': 'DialAttempts',
            'XCounter': 'XCounter', 
            'xcounter': 'XCounter',
            'F9_list': 'F9_list',
            'f9_list': 'F9_list', 
            'DoNotDial': 'DoNotDial',
            'donotdial': 'DoNotDial',
            'ggg': 'ggg',
            'lead_prioritization': 'lead_prioritization',
            'metal_count': 'metal_count',
            
            # Agent disposition fields
            'Last Agent Disposition': 'Last_Agent_Disposition',
            'last_agent_disposition': 'Last_Agent_Disposition',
            'Last Agent Disposition Date-Time': 'Last_Agent_Disposition_Date_Time', 
            'last_agent_disposition_date_time': 'Last_Agent_Disposition_Date_Time',
            
            # Business fields
            'Market': 'Market',
            'market': 'Market',
            'Secondary Lead Source': 'Secondary_Lead_Source',
            'secondary_lead_source': 'Secondary_Lead_Source',
            'HubSpot_ContactID': 'HubSpot_ContactID',
            'hubspot_contactid': 'HubSpot_ContactID',
            'Result': 'Result',
            'result': 'Result',
            'Product': 'Product',
            'product': 'Product',
            'Appointment Date and Time': 'Appointment_Date_and_Time',
            'appointment_date_and_time': 'Appointment_Date_and_Time',
            'Carrier': 'Carrier',
            'carrier': 'Carrier',
            'TFUID': 'TFUID',
            'tfuid': 'TFUID',
            'Lead Status': 'Lead_Status',
            'lead_status': 'Lead_Status',
            'PC Work Finished': 'PC_Work_Finished',
            'pc_work_finished': 'PC_Work_Finished', 
            'Total Job Amount': 'Total_Job_Amount',
            'total_job_amount': 'Total_Job_Amount',
            'Position': 'Position',
            'position': 'Position',
            'Appointment Date': 'Appointment_Date',
            'appointment_date': 'Appointment_Date',
        }
        
        # Return mapped name if found, otherwise convert to Django field format
        if five9_field_name in field_name_mapping:
            return field_name_mapping[five9_field_name]
        
        # Default conversion for unmapped fields
        django_name = five9_field_name.replace(' ', '_').replace('-', '_')
        if django_name[0].isdigit():
            django_name = f"field_{django_name}"
        
        return django_name
    
    def get_system_fields(self) -> List[str]:
        """Get list of system field names"""
        return [field["name"] for field in FIVE9_FIELD_DEFINITIONS if field.get("system", False)]
    
    def get_custom_fields(self) -> List[str]:
        """Get list of custom field names"""
        return [field["name"] for field in FIVE9_FIELD_DEFINITIONS if not field.get("system", False)]
    
    def get_required_fields(self) -> List[str]:
        """Get list of required field names"""
        return [field["name"] for field in FIVE9_FIELD_DEFINITIONS if field.get("required", False)]
    
    def get_fields_by_type(self, field_type: str) -> List[str]:
        """Get list of field names by type"""
        return [field["name"] for field in FIVE9_FIELD_DEFINITIONS if field.get("type") == field_type]
    
    def get_datetime_fields(self) -> List[str]:
        """Get list of datetime field names"""
        return self.get_fields_by_type(Five9FieldTypes.DATE_TIME)
    
    def get_date_fields(self) -> List[str]:
        """Get list of date field names"""
        return self.get_fields_by_type(Five9FieldTypes.DATE)
    
    def get_phone_fields(self) -> List[str]:
        """Get list of phone field names"""
        return self.get_fields_by_type(Five9FieldTypes.PHONE)
    
    def get_email_fields(self) -> List[str]:
        """Get list of email field names"""
        return self.get_fields_by_type(Five9FieldTypes.EMAIL)
    
    def get_boolean_fields(self) -> List[str]:
        """Get list of boolean field names"""
        return self.get_fields_by_type(Five9FieldTypes.BOOLEAN)
    
    def get_number_fields(self) -> List[str]:
        """Get list of number field names"""
        return self.get_fields_by_type(Five9FieldTypes.NUMBER)


# Create global field mapper instance
field_mapper = Five9FieldMapper()


# Delta Sync Configuration
DELTA_SYNC_CONFIG = {
    "timestamp_field": "sys_last_disposition_time",
    "fallback_timestamp_fields": [
        "sys_created_date",
        "Last Agent Disposition Date-Time",
        "New Contact Field"  # LastModifiedDateTime
    ],
    "lookback_hours": 24,  # Hours to look back for safety margin
    "initial_sync_days": 30  # Days to sync on first run
}


# Validation Rules
VALIDATION_RULES = {
    "email": {
        "regex": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        "required": False
    },
    "phone": {
        "regex": r"^\+?[\d\s\-\(\)]{7,20}$",
        "required": False
    },
    "contactID": {
        "max_length": 100,
        "required": False
    }
}


# Error Handling Configuration
ERROR_HANDLING = {
    "max_retries": 3,
    "retry_delays": [1, 5, 15],  # seconds
    "timeout_seconds": 30,
    "skip_invalid_records": True,
    "log_invalid_records": True
}
