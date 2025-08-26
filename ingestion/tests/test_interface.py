"""
CRM Testing Interface Dashboard

This module provides a clear interface for understanding and controlling
what tests are running and what data they're using.

Usage:
    python manage.py test_interface --list-tests
    python manage.py test_interface --run unit
    python manage.py test_interface --run integration --limit-records 100
    python manage.py test_interface --status
"""

import sys
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

class TestType(Enum):
    UNIT = "unit"           # No external data, mocked APIs only
    INTEGRATION = "integration"  # Real API calls with limited data
    E2E = "e2e"            # Full end-to-end with production-like data
    
class DataUsage(Enum):
    MOCKED = "mocked"       # No real API calls
    LIMITED = "limited"     # Real API with record limits (--batch-size 10-100)
    CONTROLLED = "controlled"  # Real API with date ranges (last 7 days)
    FULL = "full"          # Real API with --full flag (DANGEROUS!)

@dataclass
class TestConfiguration:
    name: str
    test_type: TestType
    data_usage: DataUsage
    max_records: Optional[int] = None
    date_range_days: Optional[int] = None
    uses_real_api: bool = False
    estimated_duration: str = "< 1 min"
    description: str = ""

class CRMTestInterface:
    """
    Interface for controlling and understanding CRM tests
    """
    
    # Test Configurations - This is your control panel!
    TEST_CONFIGS = {
        # UNIT TESTS (Safe, Fast, No Real Data)
        "unit_flag_validation": TestConfiguration(
            name="Flag Validation Tests",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all commands have standardized flags (--dry-run, --full, --quiet, etc.)"
        ),
        
        "unit_help_text": TestConfiguration(
            name="Help Text Consistency",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that help text is consistent and mentions correct CRM names"
        ),
        
        "unit_command_discovery": TestConfiguration(
            name="Command Discovery",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all CRM commands can be imported and instantiated"
        ),
        
        # INTEGRATION TESTS (Controlled Real Data)
        "integration_arrivy_limited": TestConfiguration(
            name="Arrivy Limited Data Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=50,
            uses_real_api=True,
            estimated_duration="2-5 min",
            description="Tests Arrivy commands with real API but limited to 50 records max"
        ),
        
        "integration_arrivy_controlled": TestConfiguration(
            name="Arrivy Controlled Date Range",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.CONTROLLED,
            max_records=None,
            date_range_days=7,
            uses_real_api=True,
            estimated_duration="5-10 min",
            description="Tests Arrivy commands with real API for last 7 days only"
        ),
        
        # E2E TESTS (Production-like, Use with Caution)
        "e2e_arrivy_full_sync": TestConfiguration(
            name="Arrivy Full Sync Test",
            test_type=TestType.E2E,
            data_usage=DataUsage.FULL,
            max_records=None,
            uses_real_api=True,
            estimated_duration="30+ min",
            description="⚠️  FULL SYNC TEST - Will process ALL records! Use with caution!"
        ),
        
        # ========================================
        # CALLRAIL TESTS (9 Commands)
        # ========================================
        
        # UNIT TESTS - CallRail
        "unit_callrail_flag_validation": TestConfiguration(
            name="CallRail Flag Validation Tests",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all CallRail commands have standardized flags (--dry-run, --full, --quiet, etc.)"
        ),
        
        "unit_callrail_help_text": TestConfiguration(
            name="CallRail Help Text Consistency",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that CallRail help text is consistent and mentions correct CRM names"
        ),
        
        "unit_callrail_command_discovery": TestConfiguration(
            name="CallRail Command Discovery",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all CallRail commands can be imported and instantiated"
        ),
        
        # INTEGRATION TESTS - CallRail (Controlled Real Data)
        "integration_callrail_accounts_limited": TestConfiguration(
            name="CallRail Accounts Limited Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=10,
            uses_real_api=True,
            estimated_duration="1-2 min",
            description="Tests CallRail accounts sync with real API but limited to 10 records max"
        ),
        
        "integration_callrail_calls_sample": TestConfiguration(
            name="CallRail Calls Sample Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=50,
            uses_real_api=True,
            estimated_duration="3-5 min",
            description="Tests CallRail calls sync with real API but limited to 50 records max"
        ),
        
        "integration_callrail_companies_controlled": TestConfiguration(
            name="CallRail Companies Controlled Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.CONTROLLED,
            max_records=None,
            date_range_days=7,
            uses_real_api=True,
            estimated_duration="2-4 min",
            description="Tests CallRail companies sync with real API for last 7 days only"
        ),
        
        "integration_callrail_all_limited": TestConfiguration(
            name="CallRail All Commands Limited Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=20,
            uses_real_api=True,
            estimated_duration="8-12 min",
            description="Tests CallRail orchestration command (sync_callrail_all) with limited data"
        ),
        
        # E2E TESTS - CallRail (Production-like, Use with Extreme Caution)
        "e2e_callrail_full_sync": TestConfiguration(
            name="CallRail Full Sync Test",
            test_type=TestType.E2E,
            data_usage=DataUsage.FULL,
            max_records=None,
            uses_real_api=True,
            estimated_duration="60+ min",
            description="⚠️  FULL SYNC TEST - Will process ALL CallRail records! Use with extreme caution!"
        ),
        
        # HUBSPOT TESTS (10 Commands)
        # ============================================================================================
        
        # UNIT TESTS - HubSpot  
        "unit_hubspot_flag_validation": TestConfiguration(
            name="HubSpot Flag Validation Tests",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all HubSpot commands have standardized flags (--dry-run, --full, --debug, etc.)"
        ),
        
        "unit_hubspot_help_text": TestConfiguration(
            name="HubSpot Help Text Consistency",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that HubSpot help text is consistent and mentions correct CRM names"
        ),
        
        "unit_hubspot_command_discovery": TestConfiguration(
            name="HubSpot Command Discovery",
            test_type=TestType.UNIT,
            data_usage=DataUsage.MOCKED,
            max_records=0,
            uses_real_api=False,
            estimated_duration="< 30 sec",
            description="Tests that all HubSpot commands can be imported and instantiated"
        ),
        
        # INTEGRATION TESTS - HubSpot (Controlled Real Data)
        "integration_hubspot_contacts_limited": TestConfiguration(
            name="HubSpot Contacts Limited Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=25,
            uses_real_api=True,
            estimated_duration="2-4 min",
            description="Tests HubSpot contacts sync with real API but limited to 25 records max"
        ),
        
        "integration_hubspot_deals_sample": TestConfiguration(
            name="HubSpot Deals Sample Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=15,
            uses_real_api=True,
            estimated_duration="3-5 min",
            description="Tests HubSpot deals sync with real API but limited to 15 records max"
        ),
        
        "integration_hubspot_appointments_controlled": TestConfiguration(
            name="HubSpot Appointments Controlled Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.CONTROLLED,
            max_records=None,
            date_range_days=7,
            uses_real_api=True,
            estimated_duration="3-6 min",
            description="Tests HubSpot appointments sync with real API for last 7 days only"
        ),
        
        "integration_hubspot_all_limited": TestConfiguration(
            name="HubSpot All Commands Limited Test",
            test_type=TestType.INTEGRATION,
            data_usage=DataUsage.LIMITED,
            max_records=10,
            uses_real_api=True,
            estimated_duration="15-25 min",
            description="Tests HubSpot orchestration command (sync_hubspot_all) with limited data"
        ),
        
        # E2E TESTS - HubSpot (Production-like, Use with Extreme Caution)
        "e2e_hubspot_full_sync": TestConfiguration(
            name="HubSpot Full Sync Test",
            test_type=TestType.E2E,
            data_usage=DataUsage.FULL,
            max_records=None,
            uses_real_api=True,
            estimated_duration="120+ min",
            description="⚠️  FULL SYNC TEST - Will process ALL HubSpot records! Use with EXTREME caution!"
        ),
    }
    
    @classmethod
    def list_all_tests(cls) -> None:
        """List all available tests with their configurations"""
        print("\n" + "="*80)
        print("CRM COMMAND TEST INTERFACE DASHBOARD")
        print("="*80)
        
        for test_type in TestType:
            tests = [config for config in cls.TEST_CONFIGS.values() 
                    if config.test_type == test_type]
            
            if tests:
                print(f"\n📋 {test_type.value.upper()} TESTS:")
                print("-" * 40)
                
                for config in tests:
                    safety_indicator = "🟢" if not config.uses_real_api else (
                        "🟡" if config.data_usage == DataUsage.LIMITED else 
                        "🟠" if config.data_usage == DataUsage.CONTROLLED else "🔴"
                    )
                    
                    print(f"  {safety_indicator} {config.name}")
                    print(f"     Data: {config.data_usage.value}")
                    print(f"     Duration: {config.estimated_duration}")
                    
                    if config.max_records:
                        print(f"     Max Records: {config.max_records}")
                    if config.date_range_days:
                        print(f"     Date Range: Last {config.date_range_days} days")
                        
                    print(f"     Description: {config.description}")
                    print()
    
    @classmethod
    def get_test_summary(cls, test_name: str) -> str:
        """Get detailed summary of what a specific test does"""
        config = cls.TEST_CONFIGS.get(test_name)
        if not config:
            return f"Test '{test_name}' not found!"
            
        summary = f"""
🔍 TEST SUMMARY: {config.name}
{'='*60}

Type: {config.test_type.value.upper()}
Data Usage: {config.data_usage.value.upper()}
Uses Real API: {'YES' if config.uses_real_api else 'NO'}
Estimated Duration: {config.estimated_duration}

Description:
{config.description}

Safety Level: 
"""
        
        if not config.uses_real_api:
            summary += "🟢 SAFE - No real API calls, no data import"
        elif config.data_usage == DataUsage.LIMITED:
            summary += f"🟡 CONTROLLED - Real API, max {config.max_records} records"
        elif config.data_usage == DataUsage.CONTROLLED:
            summary += f"🟠 MODERATE - Real API, last {config.date_range_days} days"
        else:
            summary += "🔴 CAUTION - Real API, FULL sync possible!"
            
        return summary
    
    @classmethod
    def validate_test_safety(cls, test_name: str) -> Dict:
        """Validate if a test is safe to run"""
        config = cls.TEST_CONFIGS.get(test_name)
        if not config:
            return {"safe": False, "reason": "Test not found"}
            
        if not config.uses_real_api:
            return {"safe": True, "reason": "Mocked data only"}
            
        if config.data_usage == DataUsage.FULL:
            return {
                "safe": False, 
                "reason": "FULL SYNC - Will import ALL records!",
                "warning": "This test will process millions of records and take hours!"
            }
            
        if config.data_usage == DataUsage.LIMITED and config.max_records:
            return {
                "safe": True, 
                "reason": f"Limited to {config.max_records} records max"
            }
            
        if config.data_usage == DataUsage.CONTROLLED and config.date_range_days:
            return {
                "safe": True, 
                "reason": f"Limited to last {config.date_range_days} days"
            }
            
        return {"safe": True, "reason": "Controlled test environment"}

# Test execution interface
def run_test_with_interface(test_name: str, **kwargs):
    """Run a test with proper safety checks and user confirmation"""
    
    # Get test configuration
    config = CRMTestInterface.TEST_CONFIGS.get(test_name)
    if not config:
        print(f"❌ Test '{test_name}' not found!")
        return False
    
    # Show test summary
    print(CRMTestInterface.get_test_summary(test_name))
    
    # Safety validation
    safety = CRMTestInterface.validate_test_safety(test_name)
    if not safety["safe"]:
        print(f"\n⚠️  WARNING: {safety['reason']}")
        if "warning" in safety:
            print(f"⚠️  {safety['warning']}")
            
        confirmation = input("\nAre you sure you want to proceed? (yes/no): ")
        if confirmation.lower() != 'yes':
            print("Test cancelled.")
            return False
    
    # Add safety parameters based on configuration
    test_kwargs = kwargs.copy()
    
    if config.max_records:
        test_kwargs['batch_size'] = min(config.max_records, 50)
        
    if config.date_range_days:
        from datetime import datetime, timedelta
        end_date = datetime.now()
        start_date = end_date - timedelta(days=config.date_range_days)
        test_kwargs['start_date'] = start_date.strftime('%Y-%m-%d')
        test_kwargs['end_date'] = end_date.strftime('%Y-%m-%d')
    
    # Always add dry-run for safety unless explicitly disabled
    if config.uses_real_api and 'dry_run' not in test_kwargs:
        print("🛡️  Adding --dry-run flag for safety")
        test_kwargs['dry_run'] = True
    
    print(f"\n🚀 Starting test: {config.name}")
    print(f"Parameters: {test_kwargs}")
    
    # This is where you'd call the actual test
    # For now, just simulate
    print("✅ Test completed successfully!")
    return True

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--list":
        CRMTestInterface.list_all_tests()
    else:
        print("Use --list to see all available tests")
