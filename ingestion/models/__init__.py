# Import common models
from .common import SyncTracker

# Import Genius models
from .genius import (
    Genius_DivisionGroup,
    Genius_Division,
    Genius_UserData,
    Genius_UserTitle,  # Added new model
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
)

# Import SalesPro models
from .salespro import SalesPro_Users, SalesPro_Appointment, SalesPro_SyncHistory

# Import Hubspot models
from .hubspot import Hubspot_Contact, Hubspot_Deal, Hubspot_Appointment, Hubspot_SyncHistory

# Import Arrivy models
from .arrivy import Arrivy_Customer, Arrivy_Entity, Arrivy_Group, Arrivy_Booking, Arrivy_SyncHistory

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

# Import ActiveProspect models
from .activeprospect import (
    ActiveProspect_Event, ActiveProspect_Lead, ActiveProspect_SyncHistory
)

# Import LeadConduit models
from .leadconduit import (
    LeadConduit_Event, LeadConduit_Lead, LeadConduit_SyncHistory
)

# Import all models to maintain backwards compatibility
# This allows existing code to continue using: from ingestion.models import X
__all__ = [
    'SyncTracker',
    'Genius_DivisionGroup', 'Genius_Division', 'Genius_UserData', 'Genius_UserTitle',  # Added new model
    'Genius_Prospect', 'Genius_ProspectSource',
    'Genius_AppointmentType', 'Genius_AppointmentOutcome', 'Genius_Appointment', 'Genius_AppointmentService',
    'Genius_Service', 'Genius_Quote', 'Genius_MarketingSourceType', 'Genius_MarketingSource', 'Genius_AppointmentOutcomeType',
    'SalesPro_Users', 'SalesPro_Appointment', 'SalesPro_SyncHistory',
    'Hubspot_Contact', 'Hubspot_Deal', 'Hubspot_Appointment', 'Hubspot_SyncHistory',
    'Arrivy_Customer', 'Arrivy_Entity', 'Arrivy_Group', 'Arrivy_Booking', 'Arrivy_SyncHistory',    'MarketSharp_Activity', 'MarketSharp_ActivityReference', 'MarketSharp_ActivityResult',
    'MarketSharp_Address', 'MarketSharp_Appointment', 'MarketSharp_AppointmentResult',
    'MarketSharp_Company', 'MarketSharp_Contact', 'MarketSharp_ContactPhone',
    'MarketSharp_ContactType', 'MarketSharp_CustomField', 'MarketSharp_Customer',    'MarketSharp_Employee', 'MarketSharp_Inquiry', 'MarketSharp_InquirySourcePrimary',
    'MarketSharp_InquirySourceSecondary', 'MarketSharp_InquiryStatus', 'MarketSharp_Job',
    'MarketSharp_Lead', 'MarketSharp_ProductDetail', 'MarketSharp_ProductInterest',
    'MarketSharp_ProductType', 'MarketSharp_Prospect',
    'ActiveProspect_Event', 'ActiveProspect_Lead', 'ActiveProspect_SyncHistory',
    'LeadConduit_Event', 'LeadConduit_Lead', 'LeadConduit_SyncHistory'
]