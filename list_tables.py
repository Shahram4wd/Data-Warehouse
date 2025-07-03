from django.db import connection

cursor = connection.cursor()
cursor.execute("SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' ORDER BY table_name")
tables = cursor.fetchall()
print(f'Total tables: {len(tables)}')
ingestion_tables = [table[0] for table in tables if 'ingestion_' in table[0]]
print(f'Ingestion tables: {len(ingestion_tables)}')
for table in ingestion_tables:
    print(f'  - {table}')

# Show all tables
print('\nAll tables:')
for table in tables:
    print(f'  - {table[0]}')
