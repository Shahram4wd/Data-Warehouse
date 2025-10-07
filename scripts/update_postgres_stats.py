#!/usr/bin/env python
"""
Update PostgreSQL statistics for CRM tables.
This helps ensure that approximate counts used by the dashboard are accurate.
"""

import django
import os
import sys
from django.db import connection

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

def update_table_statistics():
    """Update PostgreSQL statistics for key CRM tables"""
    
    # Tables that frequently get large updates
    tables_to_analyze = [
        'genius_userdata',
        'genius_userassociation', 
        'genius_marketsharp_source',
        'genius_marketing_source',
        'genius_quote',
        'genius_jobchangeorderitem',
        'genius_jobchangeorder'
    ]
    
    print("🔄 Updating PostgreSQL statistics for CRM tables...")
    
    with connection.cursor() as cursor:
        for table in tables_to_analyze:
            try:
                print(f"   Analyzing table: {table}")
                cursor.execute(f"ANALYZE {table};")
                print(f"   ✅ Completed: {table}")
            except Exception as e:
                print(f"   ❌ Error analyzing {table}: {e}")
    
    print("\n📊 Updated statistics summary:")
    
    # Show updated statistics
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                relname as table_name,
                COALESCE(n_tup_ins - n_tup_del, 0) as approx_count,
                last_analyze,
                last_autoanalyze
            FROM pg_stat_user_tables 
            WHERE relname IN %s
            ORDER BY approx_count DESC
        """, [tuple(tables_to_analyze)])
        
        results = cursor.fetchall()
        
        for table_name, approx_count, last_analyze, last_autoanalyze in results:
            print(f"   {table_name}: {approx_count:,} records (analyzed: {last_analyze or last_autoanalyze or 'Never'})")

    print("\n✅ PostgreSQL statistics update completed!")
    print("💡 The dashboard should now show accurate record counts.")

if __name__ == "__main__":
    update_table_statistics()