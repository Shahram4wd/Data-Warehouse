#!/usr/bin/env python3
"""
Migration script to rename existing log files from the old format to the new format.
Changes from filename.log.X to filename.X.log
"""
import os
import glob
from pathlib import Path

def migrate_log_files():
    """Migrate existing log files to the new naming convention."""
    logs_dir = Path(__file__).resolve().parent / 'logs'
    
    if not logs_dir.exists():
        print(f"Logs directory {logs_dir} does not exist")
        return
    
    print(f"Migrating log files in {logs_dir}")
    
    # Find all files matching the old pattern (*.log.X)
    old_pattern_files = list(logs_dir.glob('*.log.*'))
    
    if not old_pattern_files:
        print("No files found with old naming pattern (*.log.X)")
        return
    
    print(f"Found {len(old_pattern_files)} files with old naming pattern:")
    
    for old_file in old_pattern_files:
        print(f"  - {old_file.name}")
        
        # Parse the filename
        parts = old_file.name.split('.')
        if len(parts) >= 3 and parts[-1].isdigit():
            # Extract components: filename.log.number -> filename.number.log
            filename_parts = parts[:-2]  # Everything except .log.number
            extension = parts[-2]        # Should be 'log'
            number = parts[-1]           # The rotation number
            
            new_name = '.'.join(filename_parts) + f'.{number}.{extension}'
            new_file = logs_dir / new_name
            
            print(f"    Renaming to: {new_name}")
            
            try:
                old_file.rename(new_file)
                print(f"    ✓ Successfully renamed")
            except Exception as e:
                print(f"    ✗ Error renaming: {e}")
        else:
            print(f"    ⚠ Skipping - doesn't match expected pattern")
    
    print("\nMigration complete!")
    
    # Show the final state
    print("\nFinal log files:")
    all_log_files = sorted(logs_dir.glob('*.log*'))
    for log_file in all_log_files:
        print(f"  - {log_file.name}")

if __name__ == "__main__":
    migrate_log_files()
