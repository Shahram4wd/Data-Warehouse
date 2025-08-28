"""
CRM Sync Commands Test Suite - Refactored Structure
===================================================

This file now serves as an import hub for the refactored CRM test suite.
Individual CRM systems have been moved to dedicated test files for better maintainability:

📁 CRM-Specific Test Files:
├── test_crm_five9.py           - Five9 contacts sync tests
├── test_crm_marketsharp.py     - MarketSharp data sync tests  
├── test_crm_leadconduit.py     - LeadConduit leads & all data sync tests
├── test_crm_gsheet.py          - Google Sheets sync tests
├── test_crm_hubspot.py         - HubSpot contacts, deals & all data sync tests (10 commands, 41 tests)
├── test_crm_arrivy.py          - Arrivy bookings, tasks & all sync tests (6 commands, 24 tests)
├── test_callrail.py            - CallRail advanced testing (9 commands, 40+ tests)
├── test_crm_salespro_db.py     - SalesPro DB sync tests (5 commands, 20 tests) ⭐ NEW
├── test_crm_genius_db.py       - Genius DB sync tests (5 commands, 20 tests) ⭐ NEW
└── test_crm_sync_commands_common.py - Shared/common functionality tests

🏗️ Infrastructure Files:
├── command_test_base.py        - Base test classes and mixins
├── sync_history_validator.py   - Validation utilities
└── mock_responses.py           - Mock data generators

✅ Benefits of Refactored Structure:
- Reduced file size from 1,279 lines to focused, manageable files
- Improved maintainability and navigation
- Better separation of concerns
- Easier debugging and testing of individual CRM systems
- Cleaner git diffs when modifying specific CRM tests

⚠️ Migration Notes:
- Original large file backed up as test_crm_sync_commands_backup.py
- All test functionality preserved across the new files
- Test discovery and execution patterns remain the same
- Individual CRM files can be run independently: pytest test_crm_five9.py

🚀 Usage:
# Run all CRM tests
pytest ingestion/tests/test_crm_*.py

# Run specific CRM system tests  
pytest ingestion/tests/test_crm_five9.py
pytest ingestion/tests/test_crm_callrail.py

# Run common/shared functionality tests
pytest ingestion/tests/test_crm_sync_commands_common.py

# Run advanced specialized tests
pytest ingestion/tests/test_callrail.py
pytest ingestion/tests/test_salesrabbit.py
"""

# Import all test classes from the dedicated files to maintain backward compatibility
# This ensures existing test discovery and runners continue to work

try:
    # Five9 tests
    from ingestion.tests.test_crm_five9 import TestFive9SyncCommand
    
    # MarketSharp tests
    from ingestion.tests.test_crm_marketsharp import TestMarketSharpSyncCommand
    
    # LeadConduit tests
    from ingestion.tests.test_crm_leadconduit import (
        TestLeadConduitSyncCommand,
        TestLeadConduitAllSyncCommand
    )
    
    # Google Sheets tests
    from ingestion.tests.test_crm_gsheet import (
        TestGSheetMarketingLeadsSyncCommand,
        TestGSheetMarketingSpendsCommand,
        TestGSheetAllCommand
    )
    
    # HubSpot tests
    from ingestion.tests.test_crm_hubspot import (
        TestHubSpotContactsCommand,
        TestHubSpotDealsCommand,
        TestHubSpotAllCommand,
        TestHubSpotAppointmentsCommand,
        TestHubSpotAppointmentsRemovalCommand,
        TestHubSpotAssociationsCommand,
        TestHubSpotContactsRemovalCommand,
        TestHubSpotDivisionsCommand,
        TestHubSpotGeniusUsersCommand,
        TestHubSpotZipcodesCommand
    )
    
    # Arrivy tests
    from ingestion.tests.test_crm_arrivy import (
        TestArrivyBookingsCommand,
        TestArrivyTasksCommand,
        TestArrivyAllCommand,
        TestArrivyEntitiesCommand,
        TestArrivyGroupsCommand,
        TestArrivyStatusesCommand
    )
    
    # Common/shared tests
    from ingestion.tests.test_crm_sync_commands_common import (
        TestBaseSyncCommandArchitecture,
        TestCommonSyncPatterns,
        TestCRMSyncDocumentation,
        TestSyncEngineIntegration,
        TestPerformanceAndScaling,
        TestBackwardCompatibility,
        TestConfigurationManagement
    )
    
    # Maintain __all__ for explicit test discovery
    __all__ = [
        # Five9
        'TestFive9SyncCommand',
        
        # MarketSharp  
        'TestMarketSharpSyncCommand',
        
        # LeadConduit
        'TestLeadConduitSyncCommand',
        'TestLeadConduitAllSyncCommand',
        
        # Google Sheets
        'TestGSheetMarketingLeadsSyncCommand',
        'TestGSheetMarketingSpendsCommand', 
        'TestGSheetAllCommand',
        
        # HubSpot
        'TestHubSpotContactsCommand',
        'TestHubSpotDealsCommand',
        'TestHubSpotAllCommand',
        'TestHubSpotAppointmentsCommand',
        'TestHubSpotAppointmentsRemovalCommand',
        'TestHubSpotAssociationsCommand',
        'TestHubSpotContactsRemovalCommand',
        'TestHubSpotDivisionsCommand',
        'TestHubSpotGeniusUsersCommand',
        'TestHubSpotZipcodesCommand',
        
        # Arrivy
        'TestArrivyBookingsCommand',
        'TestArrivyTasksCommand',
        'TestArrivyAllCommand',
        'TestArrivyEntitiesCommand',
        'TestArrivyGroupsCommand',
        'TestArrivyStatusesCommand',
        
        # Common/Shared
        'TestBaseSyncCommandArchitecture',
        'TestCommonSyncPatterns',
        'TestCRMSyncDocumentation', 
        'TestSyncEngineIntegration',
        'TestPerformanceAndScaling',
        'TestBackwardCompatibility',
        'TestConfigurationManagement'
    ]

except ImportError as e:
    # Handle graceful degradation if some test files don't exist yet
    import warnings
    warnings.warn(f"Some CRM test modules are not available: {e}", ImportWarning)
    
    # Minimal __all__ for what we know exists
    __all__ = []

# Note: CallRail and SalesRabbit tests are in their dedicated specialized files
# test_callrail.py and test_salesrabbit.py and don't need imports here
# as they have comprehensive standalone test suites

# Summary comment for maintainers
"""
📊 REFACTORING SUMMARY:

BEFORE (Single Large File):
- test_crm_sync_commands.py: 1,279 lines, 22 test classes, 70+ test methods
- Difficult to navigate and maintain
- Large git diffs for small CRM-specific changes
- Mixing concerns across different CRM systems

AFTER (Modular Structure):
- 8 focused CRM-specific files (100-200 lines each)
- 1 common functionality file (150+ lines) 
- 3 infrastructure files (base classes, validators, mocks)
- This import hub file (100 lines)
- Total: Same functionality, better organization

🎯 MAINTAINER GUIDELINES:
- Add Five9 tests → edit test_crm_five9.py
- Add CallRail tests → edit test_callrail.py (advanced) or add to test_crm_callrail.py (basic)
- Add new CRM → create test_crm_[system].py following existing patterns
- Add shared functionality → edit test_crm_sync_commands_common.py
- Infrastructure changes → edit command_test_base.py, sync_history_validator.py, mock_responses.py
"""
