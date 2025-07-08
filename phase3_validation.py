#!/usr/bin/env python
"""
Phase 3 Migration Validation Script
Confirms that the migration from old to new HubSpot commands is complete
"""

import os
import sys
import django
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def validate_migration():
    """Validate that the migration is complete"""
    
    print("=" * 80)
    print("HUBSPOT REFACTORING PHASE 3 MIGRATION VALIDATION")
    print("=" * 80)
    print(f"Validation Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Check that new commands are available
    print("1. CHECKING NEW COMMANDS AVAILABILITY")
    print("-" * 40)
    
    from django.core.management import get_commands
    commands = get_commands()
    
    expected_commands = [
        'sync_hubspot_contacts',
        'sync_hubspot_appointments',
        'sync_hubspot_divisions',
        'sync_hubspot_deals',
        'sync_hubspot_associations',
        'sync_hubspot_all',
        'validate_hubspot',
        'hubspot_parallel_test'
    ]
    
    command_results = {}
    for cmd in expected_commands:
        if cmd in commands:
            command_results[cmd] = "✓ Available"
            print(f"✓ {cmd}")
        else:
            command_results[cmd] = "✗ Missing"
            print(f"✗ {cmd}")
    
    available_commands = sum(1 for status in command_results.values() if "✓" in status)
    
    print(f"\nCommands Status: {available_commands}/{len(expected_commands)} available")
    print()
    
    # Check that new architecture is working
    print("2. CHECKING NEW ARCHITECTURE")
    print("-" * 40)
    
    architecture_components = [
        ("ingestion.base.exceptions", "ValidationException"),
        ("ingestion.base.client", "BaseAPIClient"),
        ("ingestion.base.processor", "BaseDataProcessor"),
        ("ingestion.base.sync_engine", "BaseSyncEngine"),
        ("ingestion.sync.hubspot.client", "HubSpotClient"),
        ("ingestion.sync.hubspot.processors", "HubSpotContactProcessor"),
        ("ingestion.sync.hubspot.engines", "HubSpotContactSyncEngine"),
    ]
    
    working_components = 0
    for module_name, class_name in architecture_components:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✓ {module_name}.{class_name}")
            working_components += 1
        except Exception as e:
            print(f"✗ {module_name}.{class_name}: {e}")
    
    print(f"\nArchitecture Status: {working_components}/{len(architecture_components)} working")
    print()
    
    # Check for old files (should be removed)
    print("3. CHECKING OLD FILES REMOVAL")
    print("-" * 40)
    
    old_files_to_check = [
        "ingestion/hubspot/hubspot_client.py",
        "ingestion/hubspot/__init__.py",
        "ingestion/management/commands/sync_hubspot_contact_division_assoc.py",
        "ingestion/management/commands/sync_hubspot_appointment_contact_assoc.py",
        "ingestion/management/commands/validate_hubspot_data.py",
        "ingestion/management/commands/test_hubspot_parallel.py",
    ]
    
    removed_files = 0
    for file_path in old_files_to_check:
        if not os.path.exists(file_path):
            print(f"✓ {file_path} (removed)")
            removed_files += 1
        else:
            print(f"✗ {file_path} (still exists)")
    
    print(f"\nCleanup Status: {removed_files}/{len(old_files_to_check)} files removed")
    print()
    
    # Final summary
    print("=" * 80)
    print("MIGRATION VALIDATION SUMMARY")
    print("=" * 80)
    
    total_checks = 3
    passed_checks = 0
    
    if available_commands == len(expected_commands):
        print("✓ All new commands are available")
        passed_checks += 1
    else:
        print(f"✗ {len(expected_commands) - available_commands} commands missing")
    
    if working_components == len(architecture_components):
        print("✓ All architecture components working")
        passed_checks += 1
    else:
        print(f"✗ {len(architecture_components) - working_components} components not working")
    
    if removed_files == len(old_files_to_check):
        print("✓ All old files removed")
        passed_checks += 1
    else:
        print(f"✗ {len(old_files_to_check) - removed_files} old files still exist")
    
    print()
    print(f"OVERALL MIGRATION STATUS: {passed_checks}/{total_checks} checks passed")
    
    if passed_checks == total_checks:
        print("🎉 MIGRATION COMPLETE! All systems operational.")
        print("✅ Ready for production use!")
        return True
    else:
        print("❌ MIGRATION INCOMPLETE. Please address the issues above.")
        return False

def main():
    """Main function"""
    try:
        success = validate_migration()
        return 0 if success else 1
    except Exception as e:
        print(f"Validation error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
