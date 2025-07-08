"""
Validation script to check the HubSpot refactored integration
"""
import sys
import os
import importlib
from pathlib import Path

# Add the project root to the Python path
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

def validate_imports():
    """Validate that all new components can be imported"""
    print("🔍 Validating imports...")
    
    components = [
        # Base components
        'ingestion.base.exceptions',
        'ingestion.base.client',
        'ingestion.base.processor',
        'ingestion.base.sync_engine',
        
        # HubSpot components
        'ingestion.sync.hubspot.client',
        'ingestion.sync.hubspot.processors',
        'ingestion.sync.hubspot.engines',
        
        # Management commands
        'ingestion.management.commands.base_hubspot_sync',
        'ingestion.management.commands.sync_hubspot_contacts_new',
        'ingestion.management.commands.sync_hubspot_appointments_new',
        'ingestion.management.commands.sync_hubspot_divisions_new',
        'ingestion.management.commands.sync_hubspot_deals_new',
        'ingestion.management.commands.sync_hubspot_associations_new',
        'ingestion.management.commands.sync_hubspot_all_new',
        
        # Test modules
        'ingestion.tests.test_hubspot_engines',
        'ingestion.tests.test_hubspot_processors',
        'ingestion.tests.test_hubspot_commands',
        'ingestion.tests.test_hubspot_integration',
    ]
    
    success_count = 0
    failed_imports = []
    
    for component in components:
        try:
            importlib.import_module(component)
            print(f"  ✅ {component}")
            success_count += 1
        except Exception as e:
            print(f"  ❌ {component}: {e}")
            failed_imports.append((component, str(e)))
    
    print(f"\n📊 Import Results: {success_count}/{len(components)} successful")
    
    if failed_imports:
        print("\n❌ Failed imports:")
        for component, error in failed_imports:
            print(f"  - {component}: {error}")
        return False
    
    return True

def validate_file_structure():
    """Validate that all required files exist"""
    print("\n🗂️  Validating file structure...")
    
    required_files = [
        # Base files
        'ingestion/base/__init__.py',
        'ingestion/base/exceptions.py',
        'ingestion/base/client.py',
        'ingestion/base/processor.py',
        'ingestion/base/sync_engine.py',
        
        # Sync files
        'ingestion/sync/__init__.py',
        'ingestion/sync/hubspot/__init__.py',
        'ingestion/sync/hubspot/client.py',
        'ingestion/sync/hubspot/processors.py',
        'ingestion/sync/hubspot/engines.py',
        
        # Management commands
        'ingestion/management/commands/base_hubspot_sync.py',
        'ingestion/management/commands/sync_hubspot_contacts_new.py',
        'ingestion/management/commands/sync_hubspot_appointments_new.py',
        'ingestion/management/commands/sync_hubspot_divisions_new.py',
        'ingestion/management/commands/sync_hubspot_deals_new.py',
        'ingestion/management/commands/sync_hubspot_associations_new.py',
        'ingestion/management/commands/sync_hubspot_all_new.py',
        
        # Test files
        'ingestion/tests/__init__.py',
        'ingestion/tests/test_hubspot_engines.py',
        'ingestion/tests/test_hubspot_processors.py',
        'ingestion/tests/test_hubspot_commands.py',
        'ingestion/tests/test_hubspot_integration.py',
        'ingestion/tests/run_tests.py',
        
        # Documentation
        'docs/hubspot_refactoring_status.md',
    ]
    
    success_count = 0
    missing_files = []
    
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  ✅ {file_path}")
            success_count += 1
        else:
            print(f"  ❌ {file_path}: Not found")
            missing_files.append(file_path)
    
    print(f"\n📊 File Structure Results: {success_count}/{len(required_files)} files found")
    
    if missing_files:
        print("\n❌ Missing files:")
        for file_path in missing_files:
            print(f"  - {file_path}")
        return False
    
    return True

def validate_classes():
    """Validate that key classes can be instantiated"""
    print("\n🏗️  Validating class instantiation...")
    
    try:
        # Test base classes
        from ingestion.base.exceptions import SyncException, ValidationException
        from ingestion.base.client import BaseAPIClient
        from ingestion.base.processor import BaseDataProcessor
        from ingestion.base.sync_engine import BaseSyncEngine
        
        # Test HubSpot classes
        from ingestion.sync.hubspot.client import HubSpotClient
        from ingestion.sync.hubspot.processors import (
            HubSpotContactProcessor, HubSpotAppointmentProcessor,
            HubSpotDivisionProcessor, HubSpotDealProcessor
        )
        from ingestion.sync.hubspot.engines import (
            HubSpotContactSyncEngine, HubSpotAppointmentSyncEngine,
            HubSpotDivisionSyncEngine, HubSpotDealSyncEngine,
            HubSpotAssociationSyncEngine
        )
        
        # Test management commands
        from ingestion.management.commands.sync_hubspot_contacts_new import Command as ContactCommand
        from ingestion.management.commands.sync_hubspot_all_new import Command as AllCommand
        
        # Test instantiation
        classes_to_test = [
            ('SyncException', lambda: SyncException("Test")),
            ('ValidationException', lambda: ValidationException("Test")),
            ('HubSpotClient', lambda: HubSpotClient('test_token')),
            ('HubSpotContactProcessor', lambda: HubSpotContactProcessor()),
            ('HubSpotAppointmentProcessor', lambda: HubSpotAppointmentProcessor()),
            ('HubSpotDivisionProcessor', lambda: HubSpotDivisionProcessor()),
            ('HubSpotDealProcessor', lambda: HubSpotDealProcessor()),
            ('HubSpotContactSyncEngine', lambda: HubSpotContactSyncEngine()),
            ('HubSpotAppointmentSyncEngine', lambda: HubSpotAppointmentSyncEngine()),
            ('HubSpotDivisionSyncEngine', lambda: HubSpotDivisionSyncEngine()),
            ('HubSpotDealSyncEngine', lambda: HubSpotDealSyncEngine()),
            ('HubSpotAssociationSyncEngine', lambda: HubSpotAssociationSyncEngine()),
            ('ContactCommand', lambda: ContactCommand()),
            ('AllCommand', lambda: AllCommand()),
        ]
        
        success_count = 0
        
        for class_name, instantiator in classes_to_test:
            try:
                instance = instantiator()
                print(f"  ✅ {class_name}")
                success_count += 1
            except Exception as e:
                print(f"  ❌ {class_name}: {e}")
        
        print(f"\n📊 Class Instantiation Results: {success_count}/{len(classes_to_test)} successful")
        
        return success_count == len(classes_to_test)
        
    except Exception as e:
        print(f"  ❌ Error during class validation: {e}")
        return False

def validate_method_signatures():
    """Validate that key methods have expected signatures"""
    print("\n🔍 Validating method signatures...")
    
    try:
        from ingestion.sync.hubspot.engines import HubSpotContactSyncEngine
        from ingestion.sync.hubspot.processors import HubSpotContactProcessor
        
        # Test sync engine methods
        engine = HubSpotContactSyncEngine()
        
        # Check that required methods exist
        required_methods = [
            'get_default_batch_size',
            'initialize_client',
            'fetch_data',
            'transform_data',
            'validate_data',
            'save_data',
            'cleanup',
            'run_sync'
        ]
        
        engine_methods_found = 0
        for method in required_methods:
            if hasattr(engine, method):
                print(f"  ✅ HubSpotContactSyncEngine.{method}")
                engine_methods_found += 1
            else:
                print(f"  ❌ HubSpotContactSyncEngine.{method}: Not found")
        
        # Test processor methods
        processor = HubSpotContactProcessor()
        
        processor_methods = [
            'get_field_mappings',
            'transform_record',
            'validate_record'
        ]
        
        processor_methods_found = 0
        for method in processor_methods:
            if hasattr(processor, method):
                print(f"  ✅ HubSpotContactProcessor.{method}")
                processor_methods_found += 1
            else:
                print(f"  ❌ HubSpotContactProcessor.{method}: Not found")
        
        total_methods = len(required_methods) + len(processor_methods)
        total_found = engine_methods_found + processor_methods_found
        
        print(f"\n📊 Method Signature Results: {total_found}/{total_methods} methods found")
        
        return total_found == total_methods
        
    except Exception as e:
        print(f"  ❌ Error during method validation: {e}")
        return False

def main():
    """Run all validation checks"""
    print("🚀 HubSpot Refactoring Validation")
    print("=" * 50)
    
    checks = [
        ("File Structure", validate_file_structure),
        ("Imports", validate_imports),
        ("Class Instantiation", validate_classes),
        ("Method Signatures", validate_method_signatures),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"\n❌ {check_name} validation failed with exception: {e}")
            results.append((check_name, False))
    
    print("\n" + "=" * 50)
    print("📋 VALIDATION SUMMARY")
    print("=" * 50)
    
    passed = 0
    for check_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{check_name:20} {status}")
        if result:
            passed += 1
    
    print(f"\n📊 Overall Results: {passed}/{len(results)} checks passed")
    
    if passed == len(results):
        print("\n🎉 All validation checks passed! The HubSpot refactoring is ready for testing.")
        return 0
    else:
        print(f"\n⚠️  {len(results) - passed} validation check(s) failed. Please review the issues above.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
