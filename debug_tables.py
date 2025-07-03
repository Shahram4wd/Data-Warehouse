from django.db import connection

# Check if we can get table info using Django's introspection
cursor = connection.cursor()

# First try to see if we can access any information_schema
try:
    cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'")
    count = cursor.fetchone()[0]
    print(f"Tables in information_schema: {count}")
except Exception as e:
    print(f"Error accessing information_schema: {e}")

# Try to get tables using Django's introspection
from django.db import connections
from django.core.management.color import no_style
from django.db.backends.utils import truncate_name

db_connection = connections['default']
with db_connection.cursor() as cursor:
    try:
        table_names = db_connection.introspection.table_names(cursor)
        print(f"Django introspection found {len(table_names)} tables:")
        ingestion_tables = [name for name in table_names if name.startswith('ingestion_')]
        print(f"Tables with ingestion_ prefix: {len(ingestion_tables)}")
        for table in ingestion_tables:
            print(f"  - {table}")
    except Exception as e:
        print(f"Error with Django introspection: {e}")

# Try a more direct query
try:
    cursor.execute("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
    tables = cursor.fetchall()
    print(f"pg_tables found {len(tables)} tables:")
    ingestion_tables = [table[0] for table in tables if table[0].startswith('ingestion_')]
    print(f"Tables with ingestion_ prefix: {len(ingestion_tables)}")
    for table in ingestion_tables:
        print(f"  - {table}")
except Exception as e:
    print(f"Error with pg_tables: {e}")
