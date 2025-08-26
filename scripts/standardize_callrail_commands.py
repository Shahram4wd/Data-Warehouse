#!/usr/bin/env python3
"""
Script to standardize all CallRail management commands to use BaseSyncCommand

This script updates all CallRail commands to inherit from BaseSyncCommand
and use standardized flag patterns.
"""

import os
import re

# List of CallRail command files to update
CALLRAIL_COMMANDS = [
    'sync_callrail_accounts.py',
    'sync_callrail_companies.py', 
    'sync_callrail_form_submissions.py',
    'sync_callrail_tags.py',
    'sync_callrail_text_messages.py',
    'sync_callrail_trackers.py',
    'sync_callrail_users.py'
]

COMMANDS_DIR = 'c:/projects/python/Data-Warehouse/ingestion/management/commands'

def standardize_callrail_command(filename):
    """Standardize a single CallRail command file"""
    filepath = os.path.join(COMMANDS_DIR, filename)
    
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        return False
    
    print(f"🔧 Standardizing {filename}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Update imports
    content = re.sub(
        r'from django\.core\.management\.base import BaseCommand',
        'from ingestion.base.commands import BaseSyncCommand',
        content
    )
    
    # Update class declaration
    content = re.sub(
        r'class Command\(BaseCommand\):',
        'class Command(BaseSyncCommand):',
        content
    )
    
    # Update help text to mention standardization
    content = re.sub(
        r"help = 'Sync CallRail ([^']+)'",
        r"help = 'Sync CallRail \1 with standardized flags'",
        content
    )
    
    # Replace add_arguments method with inheritance pattern
    old_add_args_pattern = r'def add_arguments\(self, parser\):.*?(?=def|\Z)'
    new_add_args = '''def add_arguments(self, parser):
        # Add standardized flags from BaseSyncCommand
        super().add_arguments(parser)
        
        # CallRail-specific arguments (if any)
        # Add any CRM-specific flags here
'''
    
    content = re.sub(old_add_args_pattern, new_add_args, content, flags=re.DOTALL)
    
    # Update parameter references in handle method
    parameter_updates = [
        ('force_overwrite', 'force'),
        ('since', 'start_date'),
        ('max_records', 'batch_size'),  # Adjust if needed
        ('debug', 'quiet')  # Invert logic if needed
    ]
    
    for old_param, new_param in parameter_updates:
        content = re.sub(
            f"options\\['{old_param}'\\]",
            f"options['{new_param}']",
            content
        )
        content = re.sub(
            f"options\\.get\\('{old_param}'",
            f"options.get('{new_param}'",
            content
        )
    
    # Add validation call at start of handle method
    handle_pattern = r'(def handle\(self, \*args, \*\*options\):.*?\n.*?try:)'
    handle_replacement = r'\1\n            # Validate arguments using BaseSyncCommand\n            self.validate_arguments(options)\n            '
    content = re.sub(handle_pattern, handle_replacement, content, flags=re.DOTALL)
    
    # Write updated content
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ {filename} standardized successfully")
    return True

def main():
    """Main execution function"""
    print("🚀 Starting CallRail command standardization...")
    print(f"Target directory: {COMMANDS_DIR}")
    print("="*60)
    
    success_count = 0
    total_count = len(CALLRAIL_COMMANDS)
    
    for command_file in CALLRAIL_COMMANDS:
        if standardize_callrail_command(command_file):
            success_count += 1
        print()
    
    print("="*60)
    print(f"✅ Standardization complete: {success_count}/{total_count} commands updated")
    print()
    print("🔍 Next steps:")
    print("1. Test commands: docker-compose run --rm test python manage.py sync_callrail_calls --help")
    print("2. Add CallRail tests to test_interface.py")
    print("3. Run validation tests")

if __name__ == "__main__":
    main()
