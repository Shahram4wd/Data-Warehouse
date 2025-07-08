import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

print("Testing HubSpot refactoring components...")

# Test 1: Import base classes
try:
    from ingestion.base.exceptions import ValidationException
    print("✓ Base exceptions imported")
except Exception as e:
    print(f"✗ Base exceptions failed: {e}")

try:
    from ingestion.base.client import BaseAPIClient
    print("✓ Base client imported")
except Exception as e:
    print(f"✗ Base client failed: {e}")

# Test 2: Import HubSpot sync modules
try:
    from ingestion.sync.hubspot.client import HubSpotClient
    print("✓ HubSpot client imported")
except Exception as e:
    print(f"✗ HubSpot client failed: {e}")

try:
    from ingestion.sync.hubspot.processors import HubSpotContactProcessor
    print("✓ HubSpot processors imported")
except Exception as e:
    print(f"✗ HubSpot processors failed: {e}")

try:
    from ingestion.sync.hubspot.engines import HubSpotContactSyncEngine
    print("✓ HubSpot engines imported")
except Exception as e:
    print(f"✗ HubSpot engines failed: {e}")

# Test 3: Check management commands
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

print("\nManagement commands check:")
for cmd in new_commands:
    if cmd in commands:
        print(f"✓ {cmd}")
    else:
        print(f"✗ {cmd}")

print("\nValidation complete!")
