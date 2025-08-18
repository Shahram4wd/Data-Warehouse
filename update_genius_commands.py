#!/usr/bin/env python3
"""
Script to update all db_genius_* management commands to support delta sync
following the CRM sync guide patterns.
"""

import os
import re
from pathlib import Path

# Define the base directory
BASE_DIR = Path("c:/Projects/Python/Data-Warehouse")
COMMANDS_DIR = BASE_DIR / "ingestion/management/commands"

# Template for the new imports and helper methods
IMPORT_TEMPLATE = '''import os
from django.core.management.base import BaseCommand
from django.utils import timezone
{model_imports}
from ingestion.models.common import SyncHistory
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from datetime import timezone as dt_timezone
from datetime import datetime, date, timedelta, time
from typing import Optional'''

ARGUMENT_TEMPLATE = '''    def add_arguments(self, parser):
        # Standard CRM sync flags according to sync_crm_guide.md
        parser.add_argument(
            '--full',
            action='store_true',
            help='Perform full sync (ignore last sync timestamp)'
        )
        parser.add_argument(
            '--force-overwrite',
            action='store_true', 
            help='Completely replace existing records'
        )
        parser.add_argument(
            '--since',
            type=str,
            help='Manual sync start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Test run without database writes'
        )
        parser.add_argument(
            '--max-records',
            type=int,
            default=0,
            help='Limit total records (0 = unlimited)'
        )
        parser.add_argument(
            '--debug',
            action='store_true',
            help='Enable verbose logging'
        )
        
        # Genius-specific arguments (backward compatibility)
        parser.add_argument(
            '--start-date',
            type=str,
            help='(DEPRECATED) Use --since instead. Start date for sync (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date for sync (YYYY-MM-DD format)'
        ){existing_args}'''

HELPER_METHODS_TEMPLATE = '''    
    def _parse_since_parameter(self, options) -> Optional[datetime]:
        """Parse --since parameter following CRM sync guide priority order."""
        since_param = options.get('since')
        start_date_param = options.get('start_date')  # Backward compatibility
        
        if since_param:
            return self._parse_date_parameter(since_param)
        elif start_date_param:
            self.stdout.write(self.style.WARNING('--start-date is deprecated, use --since instead'))
            return self._parse_date_parameter(start_date_param)
        
        return None
    
    def _parse_date_parameter(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            return date_obj.replace(tzinfo=dt_timezone.utc)
        except ValueError:
            self.stdout.write(self.style.ERROR(f'Invalid date format "{{date_str}}". Use YYYY-MM-DD format.'))
            return None
    
    def _get_last_sync_timestamp(self) -> Optional[datetime]:
        """Get last successful sync timestamp from SyncHistory."""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source='genius',
                sync_type='{sync_type}',
                status='success'
            ).order_by('-end_time').first()
            
            return last_sync.end_time if last_sync else None
        except Exception as e:
            self.stdout.write(self.style.WARNING(f"Could not retrieve last sync timestamp: {{e}}"))
            return None
    
    def _determine_sync_strategy(self, since_param: Optional[datetime], force_overwrite: bool, full_sync: bool) -> dict:
        """Determine sync strategy following CRM sync guide."""
        if force_overwrite or full_sync:
            return {{
                'since_date': None,
                'strategy': 'full',
                'description': 'Full sync (force overwrite)' if force_overwrite else 'Full sync'
            }}
        elif since_param:
            return {{
                'since_date': since_param,
                'strategy': 'delta',
                'description': f'Delta sync since {{since_param.strftime("%Y-%m-%d")}}'
            }}
        else:
            last_sync = self._get_last_sync_timestamp()
            return {{
                'since_date': last_sync,
                'strategy': 'delta' if last_sync else 'full',
                'description': f'Delta sync since last successful sync ({{last_sync.strftime("%Y-%m-%d %H:%M:%S")}})' if last_sync else 'Full sync (no previous sync found)'
            }}
    
    def _build_where_clause(self, since_date: Optional[datetime], end_date: Optional[datetime], table_alias: str = 'a') -> str:
        """Build WHERE clause for delta sync filtering."""
        conditions = []
        timestamp_field = '{timestamp_field}'  # Will be filled per command
        
        if since_date:
            since_str = since_date.strftime('%Y-%m-%d %H:%M:%S')
            conditions.append(f"{{table_alias}}.{timestamp_field} > '{{since_str}}'")
        
        if end_date:
            end_str = end_date.strftime('%Y-%m-%d %H:%M:%S') 
            conditions.append(f"{{table_alias}}.{timestamp_field} <= '{{end_str}}'")
        
        if conditions:
            return ' WHERE ' + ' AND '.join(conditions)
        return ''
    
    def _create_sync_record(self) -> SyncHistory:
        """Create SyncHistory record for tracking."""
        return SyncHistory.objects.create(
            crm_source='genius',
            sync_type='{sync_type}',
            status='running',
            start_time=timezone.now(),
            records_processed=0,
            records_created=0,
            records_updated=0,
            records_failed=0,
            configuration={{
                'command': '{command_name}'
            }}
        )
    
    def _complete_sync_record(self, sync_record: SyncHistory, status: str, error_message: str = None):
        """Complete SyncHistory record with final status."""
        sync_record.status = status
        sync_record.end_time = timezone.now()
        sync_record.records_processed = getattr(self, 'processed_count', 0)
        sync_record.records_failed = getattr(self, 'failed_count', 0)
        
        if error_message:
            sync_record.error_message = error_message
        
        if sync_record.start_time and sync_record.end_time:
            duration = (sync_record.end_time - sync_record.start_time).total_seconds()
            sync_record.performance_metrics = {{
                'duration_seconds': duration,
                'records_per_second': sync_record.records_processed / duration if duration > 0 else 0
            }}
        
        sync_record.save()'''

def get_genius_command_files():
    """Get all db_genius_* command files."""
    pattern = "db_genius_*.py"
    files = list(COMMANDS_DIR.glob(pattern))
    # Remove duplicates and 'db_genius_all.py' (special case)
    unique_files = []
    seen = set()
    for f in files:
        if f.name not in seen and f.name != 'db_genius_all.py':
            unique_files.append(f)
            seen.add(f.name)
    return sorted(unique_files)

def extract_sync_type_from_filename(filename):
    """Extract sync type from filename (e.g., 'db_genius_appointments.py' -> 'appointments')."""
    match = re.match(r'db_genius_(.+)\.py$', filename)
    return match.group(1) if match else filename

def determine_timestamp_field(sync_type):
    """Determine appropriate timestamp field based on sync type."""
    # Activity/log entities use created_at, updatable entities use updated_at
    activity_entities = {
        'activities', 'user_activities', 'call_logs',
        'email_events', 'meeting_events', 'task_logs'
    }
    
    if sync_type in activity_entities:
        return 'created_at'
    else:
        # Default to updated_at for most Genius entities since they can be modified
        return 'updated_at'

def extract_existing_args(content):
    """Extract existing parser arguments that should be preserved."""
    existing_args = []
    
    # Look for existing arguments that aren't part of our standard set
    standard_args = {
        '--full', '--force-overwrite', '--since', '--dry-run', 
        '--max-records', '--debug', '--start-date', '--end-date'
    }
    
    # Extract arguments from add_arguments method
    lines = content.split('\n')
    in_add_arguments = False
    current_arg = None
    
    for line in lines:
        line = line.strip()
        
        if 'def add_arguments(self, parser):' in line:
            in_add_arguments = True
            continue
        elif in_add_arguments and line.startswith('def '):
            break
        elif in_add_arguments and 'parser.add_argument(' in line:
            # Extract argument name
            match = re.search(r'["\']([^"\']+)["\']', line)
            if match:
                arg_name = match.group(1)
                if arg_name not in standard_args:
                    # Capture this argument and its configuration
                    current_arg = [line]
        elif in_add_arguments and current_arg and (line.startswith('help=') or line.startswith('type=') or line.startswith('default=') or line.startswith('action=')):
            current_arg.append(line)
        elif in_add_arguments and current_arg and line == ')':
            current_arg.append(line)
            existing_args.append('\n        '.join(current_arg))
            current_arg = None
    
    if existing_args:
        return '\n        ' + '\n        '.join(existing_args)
    return ''

def update_command_file(file_path):
    """Update a single command file with delta sync support."""
    print(f"Updating {file_path.name}...")
    
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Extract information
    sync_type = extract_sync_type_from_filename(file_path.name)
    command_name = file_path.stem
    timestamp_field = determine_timestamp_field(sync_type)
    
    # Check if already updated (skip if SyncHistory import exists)
    if 'from ingestion.models.common import SyncHistory' in content:
        print(f"  Skipping {file_path.name} - already updated")
        return
    
    # Extract model imports (everything after the base imports)
    model_import_match = re.search(r'from ingestion\.models import[^\n]+', content)
    model_imports = model_import_match.group(0) if model_import_match else ""
    
    # Extract existing arguments
    existing_args = extract_existing_args(content)
    
    # Update imports
    new_imports = IMPORT_TEMPLATE.format(model_imports=model_imports)
    
    # Replace old imports
    import_pattern = r'import os\nfrom django\.core\.management\.base import BaseCommand[^\n]*\n(?:from [^\n]*\n)*'
    content = re.sub(import_pattern, new_imports + '\n', content, flags=re.MULTILINE)
    
    # Update add_arguments method
    new_args = ARGUMENT_TEMPLATE.format(existing_args=existing_args)
    args_pattern = r'def add_arguments\(self, parser\):.*?(?=\n    def|\nclass|\Z)'
    content = re.sub(args_pattern, new_args, content, flags=re.DOTALL)
    
    # Add helper methods before the first existing method (usually _preload or handle)
    helper_methods = HELPER_METHODS_TEMPLATE.format(
        sync_type=sync_type, 
        command_name=command_name,
        timestamp_field=timestamp_field
    )
    
    # Find insertion point (before first method that's not add_arguments or handle)
    method_pattern = r'\n    def (?!add_arguments|handle)[^(]+\([^)]*\):'
    match = re.search(method_pattern, content)
    if match:
        insertion_point = match.start()
        content = content[:insertion_point] + helper_methods + content[insertion_point:]
    else:
        # If no suitable insertion point found, add before the last class closing
        content = content.rstrip() + helper_methods + '\n'
    
    # Write updated content
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"  ✓ Updated {file_path.name}")

def main():
    """Main function to update all db_genius_* commands."""
    print("Updating all db_genius_* commands with delta sync support...")
    
    command_files = get_genius_command_files()
    print(f"Found {len(command_files)} command files to update:")
    
    for file_path in command_files:
        print(f"  - {file_path.name}")
    
    print("\nStarting updates...")
    
    for file_path in command_files:
        try:
            update_command_file(file_path)
        except Exception as e:
            print(f"  ✗ Error updating {file_path.name}: {e}")
    
    print(f"\nCompleted updating {len(command_files)} command files!")

if __name__ == "__main__":
    main()
