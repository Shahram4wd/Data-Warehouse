from .models.common import SyncSchedule, SyncHistory
from .models.genius import (
    DivisionGroup, Division, UserData, Prospect, ProspectSource,
    AppointmentType, AppointmentOutcome, Appointment, AppointmentService,
    Service, Quote, MarketingSourceType, MarketingSource, AppointmentOutcomeType
)
from .models.hubspot import Hubspot_Contact, Hubspot_Deal, Hubspot_SyncHistory
from .models.marketsharp import (
    MarketSharp_Activity, MarketSharp_ActivityReference, MarketSharp_ActivityResult,
    MarketSharp_Address, MarketSharp_Appointment, MarketSharp_AppointmentResult,
    MarketSharp_Company, MarketSharp_Contact, MarketSharp_ContactPhone,
    MarketSharp_ContactType, MarketSharp_CustomField, MarketSharp_Customer,
    MarketSharp_Employee, MarketSharp_Inquiry, MarketSharp_InquirySourcePrimary,
    MarketSharp_InquirySourceSecondary, MarketSharp_InquiryStatus, MarketSharp_Job,
    MarketSharp_Lead, MarketSharp_ProductDetail, MarketSharp_ProductInterest,
    MarketSharp_ProductType, MarketSharp_Prospect
)

# Keep all the model references available
__all__ = [
    # Schedule models
    'SyncSchedule', 'SyncHistory',
    # Common models
    # Genius models
    'DivisionGroup', 'Division', 'UserData', 'Prospect', 'ProspectSource',
    'AppointmentType', 'AppointmentOutcome', 'Appointment', 'AppointmentService',
    'Service', 'Quote', 'MarketingSourceType', 'MarketingSource', 'AppointmentOutcomeType',
    # Hubspot models
    'Hubspot_Contact', 'Hubspot_Deal', 'Hubspot_SyncHistory',
    # MarketSharp models
    'MarketSharp_Activity', 'MarketSharp_ActivityReference', 'MarketSharp_ActivityResult',
    'MarketSharp_Address', 'MarketSharp_Appointment', 'MarketSharp_AppointmentResult',
    'MarketSharp_Company', 'MarketSharp_Contact', 'MarketSharp_ContactPhone',
    'MarketSharp_ContactType', 'MarketSharp_CustomField', 'MarketSharp_Customer',
    'MarketSharp_Employee', 'MarketSharp_Inquiry', 'MarketSharp_InquirySourcePrimary',
    'MarketSharp_InquirySourceSecondary', 'MarketSharp_InquiryStatus', 'MarketSharp_Job',
    'MarketSharp_Lead', 'MarketSharp_ProductDetail', 'MarketSharp_ProductInterest',
    'MarketSharp_ProductType', 'MarketSharp_Prospect'
]
