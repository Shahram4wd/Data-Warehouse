#!/usr/bin/env python
"""
Test script to validate the HubSpot refactoring inside Docker
"""

import os
import sys
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def test_imports():
    """Test that all new HubSpot sync modules can be imported"""
    print("Testing HubSpot sync module imports...")
    
    tests = [
        ("ingestion.base.exceptions", "ValidationException"),
        ("ingestion.base.client", "BaseAPIClient"),
        ("ingestion.base.processor", "BaseDataProcessor"),
        ("ingestion.base.sync_engine", "BaseSyncEngine"),
        ("ingestion.sync.hubspot.client", "HubSpotClient"),
        ("ingestion.sync.hubspot.processors", "HubSpotContactProcessor"),
        ("ingestion.sync.hubspot.engines", "HubSpotContactSyncEngine"),
    ]
    
    passed = 0
    failed = 0
    
    for module_name, class_name in tests:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✓ {module_name}.{class_name}")
            passed += 1
        except Exception as e:
            print(f"✗ {module_name}.{class_name}: {e}")
            failed += 1
    
    print(f"\nImport tests: {passed} passed, {failed} failed")
    return failed == 0

def test_models():
    """Test that models are accessible"""
    print("\nTesting model imports...")
    
    try:
        from ingestion.models.common import SyncHistory, SyncConfiguration, APICredential
        print("✓ New common models imported successfully")
        
        from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal
        print("✓ HubSpot models imported successfully")
        
        return True
    except Exception as e:
        print(f"✗ Model import failed: {e}")
        return False

def test_management_commands():
    """Test that management commands are available"""
    print("\nTesting management commands...")
    
    from django.core.management import get_commands
    commands = get_commands()
    
    new_commands = [
        'sync_hubspot_contacts_new',
        'sync_hubspot_appointments_new',
        'sync_hubspot_divisions_new',
        'sync_hubspot_deals_new',
        'sync_hubspot_associations_new',
        'sync_hubspot_all_new',
        'validate_hubspot_new',
        'hubspot_parallel_test',
    ]
    
    passed = 0
    failed = 0
    
    for cmd in new_commands:
        if cmd in commands:
            print(f"✓ {cmd}")
            passed += 1
        else:
            print(f"✗ {cmd}")
            failed += 1
    
    print(f"\nCommand tests: {passed} passed, {failed} failed")
    return failed == 0

def main():
    """Run all tests"""
    print("=" * 60)
    print("HubSpot Refactoring Docker Validation")
    print("=" * 60)
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_models()
    all_passed &= test_management_commands()
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 All tests passed! HubSpot refactoring is ready for Phase 2.")
    else:
        print("❌ Some tests failed. Please check the errors above.")
    print("=" * 60)
    
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
