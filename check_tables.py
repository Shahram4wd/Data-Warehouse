import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django.db import connection

cursor = connection.cursor()
cursor.execute("SHOW TABLES LIKE '%arrivy%'")
tables = [row[0] for row in cursor.fetchall()]

print('=== Arrivy Tables (MySQL) ===')
for table in tables:
    print(f'  {table}')

# Try PostgreSQL syntax
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_name LIKE '%arrivy%'")
tables = [row[0] for row in cursor.fetchall()]

print('=== Arrivy Tables (PostgreSQL) ===')
for table in tables:
    print(f'  {table}')

# Try SQLite syntax
cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE '%arrivy%'")
tables = [row[0] for row in cursor.fetchall()]

print('=== Arrivy Tables (SQLite) ===')
for table in tables:
    print(f'  {table}')
tables = [row[0] for row in cursor.fetchall()]

print('=== Arrivy Tables ===')
for table in tables:
    print(f'  {table}')
