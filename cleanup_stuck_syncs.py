#!/usr/bin/env python
"""
Clean up stuck 'running' sync history records for SalesPro
"""
import os
import sys
import django
from datetime import datetime, timedelta

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django.utils import timezone
from ingestion.models.common import SyncHistory

print("Cleaning up stuck 'running' SalesPro sync records...")
print("=" * 50)

# Find syncs that have been running for more than 1 hour
one_hour_ago = timezone.now() - timedelta(hours=1)

stuck_syncs = SyncHistory.objects.filter(
    crm_source='salespro',
    status='running',
    start_time__lt=one_hour_ago,
    end_time__isnull=True
)

if stuck_syncs.exists():
    print(f"Found {stuck_syncs.count()} stuck sync records:")
    for sync in stuck_syncs:
        duration = timezone.now() - sync.start_time
        print(f"  {sync.sync_type}: Started {sync.start_time} ({duration} ago)")
    
    print("\nMarking them as 'failed'...")
    stuck_count = stuck_syncs.update(
        status='failed',
        end_time=timezone.now(),
        error_message='Sync process was interrupted or stuck'
    )
    print(f"✅ Marked {stuck_count} syncs as failed")
else:
    print("✅ No stuck sync records found")

print("\nChecking latest sync for each type:")
print("=" * 40)

# Show latest sync for each type
sync_types = SyncHistory.objects.filter(crm_source='salespro').values_list('sync_type', flat=True).distinct()

for sync_type in sync_types:
    latest = SyncHistory.objects.filter(
        crm_source='salespro',
        sync_type=sync_type,
        status='success'
    ).order_by('-end_time').first()
    
    if latest:
        print(f"  {sync_type}: {latest.end_time} (success)")
    else:
        print(f"  {sync_type}: No successful syncs found")

print("\n🎯 Summary:")
print("   Now the 'db_salespro_leadresults' command should properly detect")
print("   the last successful sync and perform incremental updates!")
