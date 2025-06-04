# Import common models
from .common import SyncTracker

# Import Genius models
from .genius import (
    Genius_DivisionGroup,  # Updated import
    Genius_Division,  # Updated import
    Genius_UserData,  # Updated import
    Genius_Prospect,  # Updated import
    Genius_ProspectSource,  # Updated import
    Genius_AppointmentType,  # Updated import
    Genius_AppointmentOutcomeType,  # Updated import
    Genius_AppointmentOutcome,  # Updated import
    Genius_Appointment,  # Updated import
    Genius_Service,  # Updated import
    Genius_AppointmentService,  # Updated import
    Genius_Quote,  # Updated import
    Genius_MarketingSourceType,  # Updated import
    Genius_MarketingSource,  # Updated import
)

# Import Hubspot models
from .hubspot import Hubspot_Contact, Hubspot_Deal, Hubspot_SyncHistory  # Updated imports

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

# Import MarketingSource model
from .marketing_source import MarketingSource  # New import

# Import all models to maintain backwards compatibility
# This allows existing code to continue using: from ingestion.models import X
__all__ = [
    'SyncTracker',
    'Genius_DivisionGroup', 'Genius_Division', 'Genius_UserData', 'Genius_Prospect', 'Genius_ProspectSource',
    'Genius_AppointmentType', 'Genius_AppointmentOutcome', 'Genius_Appointment', 'Genius_AppointmentService',
    'Genius_Service', 'Genius_Quote', 'Genius_MarketingSourceType', 'Genius_MarketingSource', 'Genius_AppointmentOutcomeType',
    'Hubspot_Contact', 'Hubspot_Deal', 'Hubspot_SyncHistory',
    'MarketSharp_Activity', 'MarketSharp_ActivityReference', 'MarketSharp_ActivityResult',
    'MarketSharp_Address', 'MarketSharp_Appointment', 'MarketSharp_AppointmentResult',
    'MarketSharp_Company', 'MarketSharp_Contact', 'MarketSharp_ContactPhone',
    'MarketSharp_ContactType', 'MarketSharp_CustomField', 'MarketSharp_Customer',
    'MarketSharp_Employee', 'MarketSharp_Inquiry', 'MarketSharp_InquirySourcePrimary',
    'MarketSharp_InquirySourceSecondary', 'MarketSharp_InquiryStatus', 'MarketSharp_Job',
    'MarketSharp_Lead', 'MarketSharp_ProductDetail', 'MarketSharp_ProductInterest',
    'MarketSharp_ProductType', 'MarketSharp_Prospect',
    'MarketingSource'  # Newly added model
]