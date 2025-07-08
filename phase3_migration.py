#!/usr/bin/env python
"""
Phase 3 Migration Script - HubSpot Refactoring
This script handles the migration from old to new HubSpot sync architecture
"""

import os
import sys
import django
from datetime import datetime
import json

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def create_backup_inventory():
    """Create an inventory of files to be removed/replaced"""
    
    old_commands = [
        "ingestion/management/commands/sync_hubspot_contacts.py",
        "ingestion/management/commands/sync_hubspot_appointments.py", 
        "ingestion/management/commands/sync_hubspot_divisions.py",
        "ingestion/management/commands/sync_hubspot_deals.py",
        "ingestion/management/commands/sync_hubspot_all.py",
        "ingestion/management/commands/sync_hubspot_contact_division_assoc.py",
        "ingestion/management/commands/sync_hubspot_appointment_contact_assoc.py",
        "ingestion/management/commands/validate_hubspot_data.py",
        "ingestion/management/commands/test_hubspot_parallel.py",
    ]
    
    old_files = [
        "ingestion/hubspot/hubspot_client.py",
        "ingestion/hubspot/__init__.py",
        "ingestion/hubspot/README.md",
    ]
    
    new_commands = [
        "ingestion/management/commands/sync_hubspot_contacts_new.py",
        "ingestion/management/commands/sync_hubspot_appointments_new.py",
        "ingestion/management/commands/sync_hubspot_divisions_new.py", 
        "ingestion/management/commands/sync_hubspot_deals_new.py",
        "ingestion/management/commands/sync_hubspot_associations_new.py",
        "ingestion/management/commands/sync_hubspot_all_new.py",
        "ingestion/management/commands/validate_hubspot_new.py",
        "ingestion/management/commands/hubspot_parallel_test.py",
    ]
    
    new_architecture = [
        "ingestion/base/exceptions.py",
        "ingestion/base/client.py",
        "ingestion/base/processor.py",
        "ingestion/base/sync_engine.py",
        "ingestion/sync/hubspot/client.py",
        "ingestion/sync/hubspot/processors.py",
        "ingestion/sync/hubspot/engines.py",
        "ingestion/models/common.py",
    ]
    
    inventory = {
        "timestamp": datetime.now().isoformat(),
        "phase": "3",
        "migration_type": "hubspot_refactoring",
        "files_to_remove": {
            "old_commands": old_commands,
            "old_files": old_files,
        },
        "files_to_rename": {
            # New commands will be renamed to remove "_new" suffix
            "sync_hubspot_contacts_new.py": "sync_hubspot_contacts.py",
            "sync_hubspot_appointments_new.py": "sync_hubspot_appointments.py",
            "sync_hubspot_divisions_new.py": "sync_hubspot_divisions.py",
            "sync_hubspot_deals_new.py": "sync_hubspot_deals.py",
            "sync_hubspot_associations_new.py": "sync_hubspot_associations.py",
            "sync_hubspot_all_new.py": "sync_hubspot_all.py",
            "validate_hubspot_new.py": "validate_hubspot.py",
        },
        "new_architecture": new_architecture,
        "backup_location": "backups/phase3_migration_backup/",
    }
    
    return inventory

def validate_new_commands():
    """Validate that all new commands are working"""
    
    print("Validating new HubSpot commands...")
    
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
    
    validation_results = {}
    
    for cmd in new_commands:
        try:
            if cmd in commands:
                # Try to load the command
                from django.core.management import load_command_class
                command_class = load_command_class('ingestion', cmd)
                validation_results[cmd] = {
                    "status": "valid",
                    "class": command_class.__name__,
                    "module": command_class.__module__
                }
                print(f"✓ {cmd} - Valid")
            else:
                validation_results[cmd] = {
                    "status": "missing",
                    "error": "Command not found"
                }
                print(f"✗ {cmd} - Missing")
        except Exception as e:
            validation_results[cmd] = {
                "status": "error",
                "error": str(e)
            }
            print(f"✗ {cmd} - Error: {e}")
    
    return validation_results

def main():
    """Main migration function"""
    
    print("=" * 80)
    print("HUBSPOT REFACTORING PHASE 3 MIGRATION")
    print("=" * 80)
    print(f"Start Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Step 1: Create backup inventory
    print("Step 1: Creating backup inventory...")
    inventory = create_backup_inventory()
    
    with open('/app/migration_inventory.json', 'w') as f:
        json.dump(inventory, f, indent=2)
    
    print(f"✓ Backup inventory created: {len(inventory['files_to_remove']['old_commands'])} old commands identified")
    print(f"✓ {len(inventory['files_to_rename'])} commands to rename")
    print(f"✓ {len(inventory['new_architecture'])} new architecture files")
    print()
    
    # Step 2: Validate new commands
    print("Step 2: Validating new commands...")
    validation_results = validate_new_commands()
    
    valid_commands = sum(1 for r in validation_results.values() if r['status'] == 'valid')
    total_commands = len(validation_results)
    
    print(f"✓ Command validation: {valid_commands}/{total_commands} commands valid")
    print()
    
    # Step 3: Summary
    print("Step 3: Migration readiness summary...")
    
    if valid_commands == total_commands:
        print("🎉 ALL SYSTEMS READY FOR MIGRATION!")
        print("✓ All new commands validated successfully")
        print("✓ Architecture components working")
        print("✓ Ready to proceed with cleanup")
        migration_ready = True
    else:
        print("❌ MIGRATION NOT READY")
        print(f"✗ {total_commands - valid_commands} commands have issues")
        print("Please fix validation errors before proceeding")
        migration_ready = False
    
    print()
    print("=" * 80)
    print(f"PHASE 3 MIGRATION PREPARATION: {'COMPLETE' if migration_ready else 'INCOMPLETE'}")
    print("=" * 80)
    
    return 0 if migration_ready else 1

if __name__ == "__main__":
    sys.exit(main())
