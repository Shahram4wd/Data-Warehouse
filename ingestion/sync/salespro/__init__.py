"""
SalesPro sync module initialization
"""
from .clients import (
    SalesProBaseClient,
    LeadResultsClient,
    CustomerClient,
    EstimatesClient,
    CreditApplicationsClient,
)

from .engines import (
    SalesProBaseSyncEngine,
    LeadResultsSyncEngine,
    CustomerSyncEngine,
    EstimatesSyncEngine,
    CreditApplicationsSyncEngine,
)

from .processors.base import SalesProBaseProcessor
from .processors.lead_result import SalesProLeadResultProcessor

# For backward compatibility with existing code
from .engines.base import SalesProBaseSyncEngine

__all__ = [
    # Clients
    'SalesProBaseClient',
    'LeadResultsClient',
    'CustomerClient', 
    'EstimatesClient',
    'CreditApplicationsClient',
    
    # Engines
    'SalesProBaseSyncEngine',
    'LeadResultsSyncEngine',
    'CustomerSyncEngine',
    'EstimatesSyncEngine', 
    'CreditApplicationsSyncEngine',
    
    # Processors
    'SalesProBaseProcessor',
    'SalesProLeadResultProcessor',
    
    # Backward compatibility
    'BaseSalesProSyncEngine'
]
