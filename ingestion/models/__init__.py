# Import common models
from .common import SyncTracker, SyncHistory, SyncConfiguration, APICredential

# Import Genius models
from .genius import (
    Genius_DivisionGroup,
    Genius_Division,
    Genius_UserData,
    Genius_UserTitle,
    Genius_Prospect,
    Genius_ProspectSource,
    Genius_AppointmentType,
    Genius_AppointmentOutcomeType,
    Genius_AppointmentOutcome,
    Genius_Appointment,
    Genius_Service,
    Genius_AppointmentService,
    Genius_Quote,
    Genius_MarketingSourceType,
    Genius_MarketingSource,
    Genius_Lead,
    Genius_MarketSharpSource,
    Genius_MarketSharpMarketingSourceMap,
    Genius_Job,
    Genius_JobChangeOrder,
    Genius_JobChangeOrderItem,
    Genius_JobChangeOrderReason,
    Genius_JobChangeOrderStatus,
    Genius_JobChangeOrderType,
    Genius_JobStatus,
)

# Import SalesPro models
from .salespro import (
    SalesPro_CreditApplication,
    SalesPro_Customer,
    SalesPro_Estimate,
    SalesPro_LeadResult,
    SalesPro_Payment,
    SalesPro_UserActivity,
    SalesPro_Office,
    SalesPro_User,
)

# Import SalesRabbit models
from .salesrabbit import SalesRabbit_Lead

# Import LeadConduit models
from .leadconduit import LeadConduit_Lead

# Import Hubspot models
from .hubspot import (
    Hubspot_Contact, Hubspot_Deal, Hubspot_Appointment, Hubspot_Division,
    Hubspot_AppointmentContactAssociation, Hubspot_ContactDivisionAssociation,
    Hubspot_ZipCode, Hubspot_GeniusUser
)

# Import Arrivy models
from .arrivy import Arrivy_Entity, Arrivy_Group, Arrivy_Task, Arrivy_Status, Arrivy_Booking

# Import MarketSharp models
from .marketsharp import (
    MarketSharp_Activity, MarketSharp_ActivityReference, MarketSharp_ActivityResult,
    MarketSharp_Address, MarketSharp_Appointment, MarketSharp_AppointmentResult,
    MarketSharp_Company, MarketSharp_Contact, MarketSharp_ContactPhone,
    MarketSharp_ContactType, MarketSharp_CustomField, MarketSharp_Customer,
    MarketSharp_Employee, MarketSharp_Inquiry, MarketSharp_InquirySourcePrimary,
    MarketSharp_InquirySourceSecondary, MarketSharp_InquiryStatus, MarketSharp_Job,
    MarketSharp_Lead, MarketSharp_ProductDetail, MarketSharp_ProductInterest,
    MarketSharp_ProductType, MarketSharp_Prospect
)

# Import CallRail models
from .callrail import (
    CallRail_Account, CallRail_Company, CallRail_Call, CallRail_Tracker,
    CallRail_FormSubmission, CallRail_TextMessage, CallRail_Tag, CallRail_User
)

# Import alerts models
from .alerts import AlertModel, AlertRule

# Import Google Sheets models
from .gsheet import GoogleSheetMarketingLead, GoogleSheetMarketingSpend

# Import Five9 models
from .five9 import Five9Contact

# Import all models to maintain backwards compatibility
# This allows existing code to continue using: from ingestion.models import X
__all__ = [
    # Common models
    'SyncTracker', 'SyncHistory', 'SyncConfiguration', 'APICredential',
    
    # Genius models
    'Genius_DivisionGroup', 'Genius_Division', 'Genius_UserData', 'Genius_UserTitle',
    'Genius_Prospect', 'Genius_ProspectSource', 'Genius_AppointmentType', 'Genius_AppointmentOutcomeType',
    'Genius_AppointmentOutcome', 'Genius_Appointment', 'Genius_Service', 'Genius_AppointmentService',
    'Genius_Quote', 'Genius_MarketingSourceType', 'Genius_MarketingSource', 'Genius_Lead',
    'Genius_MarketSharpSource', 'Genius_MarketSharpMarketingSourceMap', 'Genius_Job',
    'Genius_JobChangeOrder', 'Genius_JobChangeOrderItem', 'Genius_JobChangeOrderReason',
    'Genius_JobChangeOrderStatus', 'Genius_JobChangeOrderType', 'Genius_JobStatus',
    
    # SalesPro models
    'SalesPro_CreditApplication', 'SalesPro_Customer', 'SalesPro_Estimate', 'SalesPro_LeadResult',
    'SalesPro_Payment', 'SalesPro_UserActivity', 'SalesPro_Office', 'SalesPro_User',
    
    # HubSpot models
    'Hubspot_Contact', 'Hubspot_Deal', 'Hubspot_Appointment', 'Hubspot_Division',
    'Hubspot_AppointmentContactAssociation', 'Hubspot_ContactDivisionAssociation',
    'Hubspot_ZipCode', 'Hubspot_GeniusUser',
    
    # Arrivy models
    'Arrivy_Entity', 'Arrivy_Group', 'Arrivy_Task', 'Arrivy_Status', 'Arrivy_Booking',
    
    # MarketSharp models
    'MarketSharp_Activity', 'MarketSharp_ActivityReference', 'MarketSharp_ActivityResult',
    'MarketSharp_Address', 'MarketSharp_Appointment', 'MarketSharp_AppointmentResult',
    'MarketSharp_Company', 'MarketSharp_Contact', 'MarketSharp_ContactPhone',
    'MarketSharp_ContactType', 'MarketSharp_CustomField', 'MarketSharp_Customer',
    'MarketSharp_Employee', 'MarketSharp_Inquiry', 'MarketSharp_InquirySourcePrimary',
    'MarketSharp_InquirySourceSecondary', 'MarketSharp_InquiryStatus', 'MarketSharp_Job',
    'MarketSharp_Lead', 'MarketSharp_ProductDetail', 'MarketSharp_ProductInterest',
    'MarketSharp_ProductType', 'MarketSharp_Prospect',
    
    # SalesRabbit models
    'SalesRabbit_Lead',
    
    # LeadConduit models
    'LeadConduit_Lead',
    
    # CallRail models
    'CallRail_Account', 'CallRail_Company', 'CallRail_Call', 'CallRail_Tracker',
    'CallRail_FormSubmission', 'CallRail_TextMessage', 'CallRail_Tag', 'CallRail_User',
    
    # Alerts models
    'AlertModel', 'AlertRule',
    
    # Google Sheets models
    'GoogleSheetMarketingLead', 'GoogleSheetMarketingSpend',
    
    # Five9 models
    'Five9Contact',
]