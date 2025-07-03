#!/usr/bin/env python
import os
import sys
import django

# Add the project root to the path
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_name LIKE 'ingestion_%'")
tables = cursor.fetchall()
print(f"Found {len(tables)} tables with 'ingestion_' prefix:")
for table in tables:
    print(f"  - {table[0]}")

# Also check all tables
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
all_tables = cursor.fetchall()
print(f"\nAll tables in database ({len(all_tables)} total):")
for table in all_tables[:20]:  # Show first 20
    print(f"  - {table[0]}")
if len(all_tables) > 20:
    print(f"  ... and {len(all_tables) - 20} more")
