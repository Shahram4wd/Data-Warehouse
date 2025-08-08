"""
Google Sheets Sync Package

This package implements Google Sheets synchronization following the CRM sync guide architecture.

Features:
- OAuth2 authentication
- Delta sync based on sheet modification time
- Standardized SyncHistory tracking
- Layered architecture (clients, engines, processors)
- Comprehensive error handling and validation

Usage:
    from ingestion.sync.gsheet.engines import MarketingLeadsSyncEngine
    
    engine = MarketingLeadsSyncEngine()
    result = await engine.run_sync()
"""

# Import main classes for easy access
from .clients import GoogleSheetsAPIClient, MarketingLeadsClient
from .engines import BaseGoogleSheetsSyncEngine, MarketingLeadsSyncEngine
from .processors import BaseGoogleSheetsProcessor, MarketingLeadsProcessor
from .validators import GoogleSheetsValidator, MarketingLeadsValidator

__version__ = '1.0.0'

__all__ = [
    # Clients
    'GoogleSheetsAPIClient',
    'MarketingLeadsClient',
    
    # Engines
    'BaseGoogleSheetsSyncEngine',
    'MarketingLeadsSyncEngine',
    
    # Processors
    'BaseGoogleSheetsProcessor',
    'MarketingLeadsProcessor',
    
    # Validators
    'GoogleSheetsValidator',
    'MarketingLeadsValidator',
]
