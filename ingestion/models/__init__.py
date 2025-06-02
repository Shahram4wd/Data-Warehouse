# Import common models
from .common import SyncTracker

# Import Genius models
from .genius import (
    DivisionGroup, Division, UserData, Prospect, ProspectSource,
    AppointmentType, AppointmentOutcome, Appointment, AppointmentService,
    Service, Quote, MarketingSourceType, MarketingSource, AppointmentOutcomeType
)

# Import all models to maintain backwards compatibility
# This allows existing code to continue using: from ingestion.models import X
__all__ = [
    'SyncTracker',
    'DivisionGroup', 'Division', 'UserData', 'Prospect', 'ProspectSource',
    'AppointmentType', 'AppointmentOutcome', 'Appointment', 'AppointmentService',
    'Service', 'Quote', 'MarketingSourceType', 'MarketingSource', 'AppointmentOutcomeType'
]