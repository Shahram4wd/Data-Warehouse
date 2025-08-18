# Import common models
from .common import SyncTracker

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

# Import all models to maintain backwards compatibility
# This allows existing code to continue using: from ingestion.models import X
__all__ = [
    'SyncTracker',
    'Genius_DivisionGroup', 'Genius_Division', 'Genius_UserData', 'Genius_UserTitle',  
    'Genius_Prospect', 'Genius_ProspectSource', 'Genius_Lead', 'Genius_MarketSharpSource',
    'Genius_AppointmentType', 'Genius_AppointmentOutcome', 'Genius_Appointment', 'Genius_AppointmentService',
    'Genius_Service', 'Genius_Quote', 'Genius_MarketingSourceType', 'Genius_MarketingSource', 'Genius_AppointmentOutcomeType',
    'SalesPro_CreditApplication', 'SalesPro_Customer', 'SalesPro_Estimate', 'SalesPro_LeadResult', 'SalesPro_Payment', 'SalesPro_UserActivity', 'SalesPro_Office', 'SalesPro_User', 
    'Hubspot_Contact', 'Hubspot_Deal', 'Hubspot_Appointment', 'Hubspot_SyncHistory',
    'Arrivy_Entity', 'Arrivy_Group', 'Arrivy_Task', 'Arrivy_Status', 'Arrivy_Booking',
    'MarketSharp_Activity', 'MarketSharp_ActivityReference', 'MarketSharp_ActivityResult',
    'MarketSharp_Address', 'MarketSharp_Appointment', 'MarketSharp_AppointmentResult',
    'MarketSharp_Company', 'MarketSharp_Contact', 'MarketSharp_ContactPhone',
    'MarketSharp_ContactType', 'MarketSharp_CustomField', 'MarketSharp_Customer',    'MarketSharp_Employee', 'MarketSharp_Inquiry', 'MarketSharp_InquirySourcePrimary',
    'MarketSharp_InquirySourceSecondary', 'MarketSharp_InquiryStatus', 'MarketSharp_Job',
    'MarketSharp_Lead', 'MarketSharp_ProductDetail', 'MarketSharp_ProductInterest',
    'MarketSharp_ProductType', 'MarketSharp_Prospect',
    'SalesRabbit_Lead',
    'LeadConduit_Lead',
    'CallRail_Account', 'CallRail_Company', 'CallRail_Call', 'CallRail_Tracker',
    'CallRail_FormSubmission', 'CallRail_TextMessage', 'CallRail_Tag', 'CallRail_User',
    'AlertModel', 'AlertRule',
    'GoogleSheetMarketingLead', 'GoogleSheetMarketingSpend'
]