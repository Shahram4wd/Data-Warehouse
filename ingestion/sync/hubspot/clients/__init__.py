"""
HubSpot clients module
"""
from .base import HubSpotBaseClient
from .contacts import HubSpotContactsClient
from .contacts_removal import HubSpotContactsRemovalClient
from .appointments import HubSpotAppointmentsClient
from .appointments_removal import HubSpotAppointmentsRemovalClient
from .deals import HubSpotDealsClient
from .divisions import HubSpotDivisionsClient
from .associations import HubSpotAssociationsClient

__all__ = [
    'HubSpotBaseClient',
    'HubSpotContactsClient',
    'HubSpotAppointmentsClient',
    'HubSpotDealsClient',
    'HubSpotDivisionsClient',
    'HubSpotAssociationsClient',
    'HubSpotContactsRemovalClient',
    'HubSpotAppointmentsRemovalClient',
]
