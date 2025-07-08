#!/usr/bin/env python
"""
Comprehensive validation script for HubSpot refactoring in Docker
This script creates a report file with results.
"""

import os
import sys
import traceback
from datetime import datetime

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
import django
django.setup()

def create_validation_report():
    """Create a comprehensive validation report"""
    
    report_lines = []
    report_lines.append("=" * 80)
    report_lines.append("HUBSPOT REFACTORING VALIDATION REPORT")
    report_lines.append("=" * 80)
    report_lines.append(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    report_lines.append(f"Environment: Docker Container")
    report_lines.append("")
    
    # Test 1: Base Classes Import
    report_lines.append("1. BASE CLASSES IMPORT TEST")
    report_lines.append("-" * 40)
    
    base_classes = [
        ("ingestion.base.exceptions", "ValidationException"),
        ("ingestion.base.client", "BaseAPIClient"),
        ("ingestion.base.processor", "BaseDataProcessor"),
        ("ingestion.base.sync_engine", "BaseSyncEngine"),
    ]
    
    passed_base = 0
    for module_name, class_name in base_classes:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            report_lines.append(f"✓ {module_name}.{class_name}")
            passed_base += 1
        except Exception as e:
            report_lines.append(f"✗ {module_name}.{class_name}: {str(e)}")
    
    report_lines.append(f"Base classes: {passed_base}/{len(base_classes)} passed")
    report_lines.append("")
    
    # Test 2: HubSpot Sync Components
    report_lines.append("2. HUBSPOT SYNC COMPONENTS TEST")
    report_lines.append("-" * 40)
    
    hubspot_classes = [
        ("ingestion.sync.hubspot.client", "HubSpotClient"),
        ("ingestion.sync.hubspot.processors", "HubSpotContactProcessor"),
        ("ingestion.sync.hubspot.processors", "HubSpotAppointmentProcessor"),
        ("ingestion.sync.hubspot.processors", "HubSpotDivisionProcessor"),
        ("ingestion.sync.hubspot.processors", "HubSpotDealProcessor"),
        ("ingestion.sync.hubspot.engines", "HubSpotContactSyncEngine"),
        ("ingestion.sync.hubspot.engines", "HubSpotAppointmentSyncEngine"),
        ("ingestion.sync.hubspot.engines", "HubSpotDivisionSyncEngine"),
        ("ingestion.sync.hubspot.engines", "HubSpotDealSyncEngine"),
        ("ingestion.sync.hubspot.engines", "HubSpotAssociationSyncEngine"),
    ]
    
    passed_hubspot = 0
    for module_name, class_name in hubspot_classes:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            report_lines.append(f"✓ {module_name}.{class_name}")
            passed_hubspot += 1
        except Exception as e:
            report_lines.append(f"✗ {module_name}.{class_name}: {str(e)}")
    
    report_lines.append(f"HubSpot components: {passed_hubspot}/{len(hubspot_classes)} passed")
    report_lines.append("")
    
    # Test 3: Model Imports
    report_lines.append("3. MODEL IMPORTS TEST")
    report_lines.append("-" * 40)
    
    try:
        from ingestion.models.common import SyncHistory, SyncConfiguration, APICredential
        report_lines.append("✓ Common models (SyncHistory, SyncConfiguration, APICredential)")
        models_passed = True
    except Exception as e:
        report_lines.append(f"✗ Common models: {str(e)}")
        models_passed = False
    
    try:
        from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal
        report_lines.append("✓ HubSpot models (Contact, Appointment, Division, Deal)")
        models_passed = models_passed and True
    except Exception as e:
        report_lines.append(f"✗ HubSpot models: {str(e)}")
        models_passed = False
    
    report_lines.append(f"Models: {'All passed' if models_passed else 'Some failed'}")
    report_lines.append("")
    
    # Test 4: Management Commands
    report_lines.append("4. MANAGEMENT COMMANDS TEST")
    report_lines.append("-" * 40)
    
    try:
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
            'hubspot_parallel_test'
        ]
        
        passed_commands = 0
        for cmd in new_commands:
            if cmd in commands:
                report_lines.append(f"✓ {cmd}")
                passed_commands += 1
            else:
                report_lines.append(f"✗ {cmd}")
        
        report_lines.append(f"Commands: {passed_commands}/{len(new_commands)} passed")
        
    except Exception as e:
        report_lines.append(f"✗ Command check failed: {str(e)}")
    
    report_lines.append("")
    
    # Test 5: File Structure
    report_lines.append("5. FILE STRUCTURE TEST")
    report_lines.append("-" * 40)
    
    required_files = [
        "ingestion/base/__init__.py",
        "ingestion/base/exceptions.py",
        "ingestion/base/client.py",
        "ingestion/base/processor.py",
        "ingestion/base/sync_engine.py",
        "ingestion/sync/__init__.py",
        "ingestion/sync/hubspot/__init__.py",
        "ingestion/sync/hubspot/client.py",
        "ingestion/sync/hubspot/processors.py",
        "ingestion/sync/hubspot/engines.py",
        "ingestion/management/commands/sync_hubspot_contacts_new.py",
        "ingestion/management/commands/sync_hubspot_appointments_new.py",
        "ingestion/management/commands/sync_hubspot_divisions_new.py",
        "ingestion/management/commands/sync_hubspot_deals_new.py",
        "ingestion/management/commands/sync_hubspot_associations_new.py",
        "ingestion/management/commands/sync_hubspot_all_new.py",
        "ingestion/management/commands/validate_hubspot_new.py",
        "ingestion/management/commands/hubspot_parallel_test.py",
    ]
    
    passed_files = 0
    for file_path in required_files:
        if os.path.exists(file_path):
            report_lines.append(f"✓ {file_path}")
            passed_files += 1
        else:
            report_lines.append(f"✗ {file_path}")
    
    report_lines.append(f"Files: {passed_files}/{len(required_files)} passed")
    report_lines.append("")
    
    # Summary
    report_lines.append("=" * 80)
    report_lines.append("SUMMARY")
    report_lines.append("=" * 80)
    
    total_tests = 5
    passed_tests = 0
    
    if passed_base == len(base_classes):
        passed_tests += 1
    if passed_hubspot == len(hubspot_classes):
        passed_tests += 1
    if models_passed:
        passed_tests += 1
    if passed_commands == len(new_commands):
        passed_tests += 1
    if passed_files == len(required_files):
        passed_tests += 1
    
    report_lines.append(f"Overall: {passed_tests}/{total_tests} test suites passed")
    
    if passed_tests == total_tests:
        report_lines.append("🎉 ALL TESTS PASSED! HubSpot refactoring is ready for Phase 2.")
        status = "SUCCESS"
    else:
        report_lines.append("❌ Some tests failed. Please review the details above.")
        status = "FAILED"
    
    report_lines.append("")
    report_lines.append("NEXT STEPS:")
    if status == "SUCCESS":
        report_lines.append("1. Run parallel testing to compare old vs new sync results")
        report_lines.append("2. Validate data consistency and performance")
        report_lines.append("3. Plan for Phase 3 (remove old commands)")
    else:
        report_lines.append("1. Fix the failing components above")
        report_lines.append("2. Re-run this validation")
        report_lines.append("3. Proceed with Phase 2 once all tests pass")
    
    report_lines.append("=" * 80)
    
    return "\n".join(report_lines), status

def main():
    """Main function"""
    try:
        report_content, status = create_validation_report()
        
        # Write report to file
        with open('/app/HUBSPOT_VALIDATION_REPORT.txt', 'w') as f:
            f.write(report_content)
        
        # Also print to console
        print(report_content)
        
        return 0 if status == "SUCCESS" else 1
        
    except Exception as e:
        error_msg = f"VALIDATION ERROR: {str(e)}\n{traceback.format_exc()}"
        print(error_msg)
        
        with open('/app/HUBSPOT_VALIDATION_ERROR.txt', 'w') as f:
            f.write(error_msg)
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
