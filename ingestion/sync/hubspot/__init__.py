"""
HubSpot sync module with modular architecture
"""

# Import all clients
from .clients import *

# Import all engines
from .engines import *

# Import all processors
from .processors import *

__all__ = [
    # Clients
    'HubSpotBaseClient',
    'HubSpotContactsClient',
    'HubSpotAppointmentsClient',
    'HubSpotDealsClient',
    'HubSpotDivisionsClient',
    'HubSpotAssociationsClient',
    
    # Engines
    'HubSpotBaseSyncEngine',
    'HubSpotContactSyncEngine',
    'HubSpotAppointmentSyncEngine',
    'HubSpotDealSyncEngine',
    'HubSpotDivisionSyncEngine',
    'HubSpotAssociationSyncEngine',
    
    # Processors
    'HubSpotBaseProcessor',
    'HubSpotContactProcessor',
    'HubSpotAppointmentProcessor',
    'HubSpotDealProcessor',
    'HubSpotDivisionProcessor',
]

# Legacy imports for backward compatibility
from .clients.base import HubSpotBaseClient as HubSpotClient
from .engines.contacts import HubSpotContactSyncEngine
from .engines.appointments import HubSpotAppointmentSyncEngine
from .engines.deals import HubSpotDealSyncEngine
from .engines.divisions import HubSpotDivisionSyncEngine
from .engines.associations import HubSpotAssociationSyncEngine
from .processors.contacts import HubSpotContactProcessor
from .processors.appointments import HubSpotAppointmentProcessor
from .processors.deals import HubSpotDealProcessor
from .processors.divisions import HubSpotDivisionProcessor
