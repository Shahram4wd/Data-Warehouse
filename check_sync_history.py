#!/usr/bin/env python
"""
Check SyncHistory records for SalesPro leadresult sync
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models.common import SyncHistory

print("SyncHistory records for salespro leadresult:")
print("=" * 50)

# Check for leadresult sync history
leadresult_syncs = SyncHistory.objects.filter(
    crm_source='salespro', 
    sync_type='leadresult'
).order_by('-end_time')[:10]

if leadresult_syncs:
    print(f"Found {leadresult_syncs.count()} previous sync records:")
    for h in leadresult_syncs:
        print(f"  {h.start_time} -> {h.end_time} ({h.status})")
        print(f"    Processed: {h.records_processed}, Created: {h.records_created}, Updated: {h.records_updated}")
        print()
else:
    print("❌ No previous sync records found for 'leadresult'")

print("\nChecking for any SalesPro sync records:")
print("=" * 40)

# Check for any salespro sync history
all_salespro_syncs = SyncHistory.objects.filter(crm_source='salespro').order_by('-end_time')[:10]

if all_salespro_syncs:
    print(f"Found {all_salespro_syncs.count()} SalesPro sync records:")
    for h in all_salespro_syncs:
        print(f"  {h.sync_type}: {h.start_time} -> {h.end_time} ({h.status})")
else:
    print("❌ No SalesPro sync records found at all")

print("\nChecking for alternative sync type names:")
print("=" * 40)

# Check for potential alternative names
alternative_names = ['lead_result', 'lead_results', 'leadresults', 'salespro_leadresult']
for name in alternative_names:
    count = SyncHistory.objects.filter(crm_source='salespro', sync_type=name).count()
    if count > 0:
        print(f"✅ Found {count} records with sync_type='{name}'")
        latest = SyncHistory.objects.filter(crm_source='salespro', sync_type=name).order_by('-end_time').first()
        if latest:
            print(f"   Latest: {latest.end_time} ({latest.status})")
    else:
        print(f"❌ No records with sync_type='{name}'")
