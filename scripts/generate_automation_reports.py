#!/usr/bin/env python
"""
Manual script to trigger automation reports generation
This can be used for testing or one-off report generation
"""
import os
import sys
import django

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..'))

# Configure Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django.core.management import call_command

def main():
    print("🤖 Generating automation reports manually...")
    
    try:
        call_command(
            'generate_automation_reports',
            '--time-window', 24,
            '--detailed',
            '--crm', 'all',
            '--export-json',
            verbosity=2
        )
        print("✅ Manual automation reports generation completed!")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
