#!/usr/bin/env python3
"""
Google Sheets Integration Test Script

This script tests the Google Sheets integration functionality.
Run this to validate your setup before using the sync commands.
"""

import os
import sys
import logging
from datetime import datetime

# Add the project directory to Python path
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_dir)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_imports():
    """Test that all required modules can be imported"""
    print("Testing imports...")
    
    try:
        # Test Google Sheets package imports
        from ingestion.sync.gsheet import (
            GoogleSheetsAPIClient, MarketingLeadsClient,
            MarketingLeadsSyncEngine, MarketingLeadsProcessor
        )
        print("✓ Google Sheets sync package imports successful")
        
        # Test model imports
        from ingestion.models.gsheet import GoogleSheetMarketingLead
        print("✓ Google Sheets model imports successful")
        
        # Test validators
        from ingestion.sync.gsheet.validators import MarketingLeadsValidator
        print("✓ Validator imports successful")
        
        return True
        
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    except Exception as e:
        print(f"✗ Unexpected error during imports: {e}")
        return False


def test_client_initialization():
    """Test client initialization without authentication"""
    print("\nTesting client initialization...")
    
    try:
        # This will test the basic class structure without requiring auth
        from ingestion.sync.gsheet.clients.marketing_leads import MarketingLeadsClient
        
        # Just test class instantiation (auth will fail but class should initialize)
        try:
            client = MarketingLeadsClient()
            print("✓ MarketingLeadsClient instantiation successful")
            
            # Test configuration
            assert client.sheet_id == "1FRKfuMSrm9DrdIe_vtZJn7usUpuXPDWl4TB1k7Ae4xo"
            assert client.tab_name == "Marketing Source Leads"
            print("✓ Client configuration correct")
            
        except Exception as auth_error:
            if "credentials" in str(auth_error).lower() or "authentication" in str(auth_error).lower():
                print("⚠ Client initialization failed (expected - no credentials)")
                print("  This is normal if you haven't set up Google authentication yet")
            else:
                print(f"✗ Unexpected client error: {auth_error}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Client initialization error: {e}")
        return False


def test_processor():
    """Test processor functionality"""
    print("\nTesting processor...")
    
    try:
        from ingestion.sync.gsheet.processors.marketing_leads import MarketingLeadsProcessor
        from ingestion.models.gsheet import GoogleSheetMarketingLead
        
        # Create processor
        processor = MarketingLeadsProcessor(GoogleSheetMarketingLead)
        print("✓ MarketingLeadsProcessor created successfully")
        
        # Test field mappings
        mappings = processor.get_field_mappings()
        assert isinstance(mappings, dict)
        print(f"✓ Field mappings: {len(mappings)} entries")
        
        # Test record transformation with sample data
        sample_record = {
            'Date': '2025-08-08',
            'Source': 'Google Ads',
            'Medium': 'CPC',
            'Campaign': 'Summer Campaign',
            'Leads': '25',
            'Cost': '$150.00',
            '_sheet_row_number': 2,
            '_sheet_last_modified': datetime.now(),
            '_sheet_id': 'test',
            '_tab_name': 'test'
        }
        
        transformed = processor.transform_record(sample_record)
        print("✓ Record transformation successful")
        
        validated = processor.validate_record(transformed)
        print("✓ Record validation successful")
        
        # Test summary stats
        stats = processor.get_summary_stats([validated])
        assert isinstance(stats, dict)
        print(f"✓ Summary stats: {stats.get('total_records', 0)} records")
        
        return True
        
    except Exception as e:
        print(f"✗ Processor test error: {e}")
        return False


def test_validators():
    """Test validation functionality"""
    print("\nTesting validators...")
    
    try:
        from ingestion.sync.gsheet.validators import MarketingLeadsValidator
        
        # Test date validation
        assert MarketingLeadsValidator.is_valid_date('2025-08-08') == True
        assert MarketingLeadsValidator.is_valid_date('invalid') == False
        print("✓ Date validation working")
        
        # Test numeric validation
        assert MarketingLeadsValidator.is_valid_numeric('123') == True
        assert MarketingLeadsValidator.is_valid_numeric('$150.00') == True
        assert MarketingLeadsValidator.is_valid_numeric('invalid') == False
        print("✓ Numeric validation working")
        
        # Test record validation
        test_record = {
            'date': '2025-08-08',
            'source': 'Google Ads',
            'leads': '25',
            'cost': '$150.00'
        }
        
        validation_result = MarketingLeadsValidator.validate_record(test_record)
        assert validation_result['is_valid'] == True
        print("✓ Record validation working")
        
        return True
        
    except Exception as e:
        print(f"✗ Validator test error: {e}")
        return False


def test_engine_initialization():
    """Test engine initialization"""
    print("\nTesting engine initialization...")
    
    try:
        from ingestion.sync.gsheet.engines.marketing_leads import MarketingLeadsSyncEngine
        
        # Test engine creation (without running sync)
        try:
            engine = MarketingLeadsSyncEngine(dry_run=True)
            print("✓ MarketingLeadsSyncEngine created successfully")
            
            # Test configuration
            assert engine.sheet_name == 'marketing_leads'
            assert engine.dry_run == True
            print("✓ Engine configuration correct")
            
        except Exception as e:
            if "credentials" in str(e).lower() or "authentication" in str(e).lower():
                print("⚠ Engine initialization failed (expected - no credentials)")
                print("  This is normal if you haven't set up Google authentication yet")
            else:
                print(f"✗ Unexpected engine error: {e}")
                return False
        
        return True
        
    except Exception as e:
        print(f"✗ Engine initialization error: {e}")
        return False


def check_requirements():
    """Check if required packages are installed"""
    print("\nChecking requirements...")
    
    required_packages = [
        'google-auth',
        'google-auth-oauthlib',
        'google-api-python-client',
        'gspread',
    ]
    
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"✓ {package}")
        except ImportError:
            print(f"✗ {package} (missing)")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\nMissing packages: {', '.join(missing_packages)}")
        print("Install with: pip install " + " ".join(missing_packages))
        return False
    
    return True


def check_files():
    """Check if required files exist"""
    print("\nChecking files...")
    
    # Check for credentials file
    if os.path.exists('credentials.json'):
        print("✓ credentials.json found")
    else:
        print("⚠ credentials.json not found (required for authentication)")
    
    # Check for manage.py (Django project indicator)
    if os.path.exists('manage.py'):
        print("✓ Django project structure detected")
    else:
        print("✗ manage.py not found - are you in the Django project root?")
        return False
    
    return True


def main():
    """Run all tests"""
    print("Google Sheets Integration Test Suite")
    print("=" * 50)
    
    tests = [
        ("Package Requirements", check_requirements),
        ("File Structure", check_files),
        ("Module Imports", test_imports),
        ("Client Initialization", test_client_initialization),
        ("Processor Functionality", test_processor),
        ("Validators", test_validators),
        ("Engine Initialization", test_engine_initialization),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\n{'-'*20} {test_name} {'-'*20}")
        try:
            if test_func():
                passed += 1
                print(f"✓ {test_name} PASSED")
            else:
                print(f"✗ {test_name} FAILED")
        except Exception as e:
            print(f"✗ {test_name} FAILED with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The Google Sheets integration is ready to use.")
        print("\nNext steps:")
        print("1. Set up Google authentication (see docs/gsheet_integration_guide.md)")
        print("2. Run: python scripts/setup_gsheet_config.py")
        print("3. Test: python manage.py sync_gsheet_marketing_leads --test-connection")
    else:
        print("❌ Some tests failed. Please address the issues above.")
        
        if not check_requirements():
            print("\nTo install missing packages:")
            print("pip install -r requirements.txt")


if __name__ == '__main__':
    main()
