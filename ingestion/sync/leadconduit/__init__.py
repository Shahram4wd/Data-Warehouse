"""
LeadConduit sync module initialization

Following the mandatory sync_crm_guide architecture for enterprise-grade CRM sync.
This module provides sync capabilities for LeadConduit data including:
- Leads synchronization
- SyncHistory framework compliance  
- UTC-optimized data processing
- Enterprise error handling and monitoring
"""

__version__ = "1.0.0"
__author__ = "Data Warehouse Team"

# Module-level configuration
CRM_SOURCE = "leadconduit"
SUPPORTED_ENTITIES = ["leads", "all"]

# Re-export key classes for convenience
from .engines.base import LeadConduitSyncEngine, LeadConduitLeadsSyncEngine
from .clients.base import LeadConduitBaseClient
from .processors.leads import LeadConduitLeadsProcessor

__all__ = [
    "LeadConduitSyncEngine",
    "LeadConduitLeadsSyncEngine",
    "LeadConduitBaseClient",
    "LeadConduitLeadsProcessor",
    "CRM_SOURCE", 
    "SUPPORTED_ENTITIES"
]
