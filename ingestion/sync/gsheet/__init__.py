"""
Google Sheets integration package

This package provides comprehensive Google Sheets API integration
following the established CRM sync patterns.
"""

# Note: Imports are not done at module level to avoid Django configuration issues
# Import classes directly from their modules when needed:
# from .clients.marketing_leads import MarketingLeadsClient
# from .engines.marketing_leads import MarketingLeadsSyncEngine

__version__ = '1.0.0'

__all__ = [
    # Clients
    'GoogleSheetsClient',
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
