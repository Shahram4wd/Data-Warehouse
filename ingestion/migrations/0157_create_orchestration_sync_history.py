# Create orchestration.sync_history table if it doesn't exist
from django.db import migrations, models
import django.utils.timezone


def create_orchestration_sync_history(apps, schema_editor):
    """Create orchestration.sync_history table if it doesn't exist"""
    
    print("Creating orchestration schema and sync_history table...")
    
    with schema_editor.connection.cursor() as cursor:
        # Create orchestration schema if it doesn't exist
        cursor.execute("CREATE SCHEMA IF NOT EXISTS orchestration;")
        
        # Check if sync_history table exists
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables 
            WHERE table_schema = 'orchestration' AND table_name = 'sync_history'
        """)
        
        if cursor.fetchone()[0] == 0:
            # Create the sync_history table
            cursor.execute("""
                CREATE TABLE orchestration.sync_history (
                    id SERIAL PRIMARY KEY,
                    crm_source VARCHAR(50) NOT NULL,
                    sync_type VARCHAR(50) NOT NULL,
                    endpoint VARCHAR(255),
                    start_time TIMESTAMPTZ NOT NULL,
                    end_time TIMESTAMPTZ,
                    status VARCHAR(20) NOT NULL DEFAULT 'running',
                    records_processed INTEGER NOT NULL DEFAULT 0,
                    records_created INTEGER NOT NULL DEFAULT 0,
                    records_updated INTEGER NOT NULL DEFAULT 0,
                    records_failed INTEGER NOT NULL DEFAULT 0,
                    error_message TEXT,
                    performance_metrics JSONB DEFAULT '{}',
                    configuration JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
                );
            """)
            
            # Create indexes
            cursor.execute("""
                CREATE INDEX orchestrati_crm_sou_dd1de6_idx ON orchestration.sync_history (crm_source, sync_type, start_time DESC);
            """)
            cursor.execute("""
                CREATE INDEX orchestrati_start_t_022c6b_idx ON orchestration.sync_history (start_time DESC);
            """)
            cursor.execute("""
                CREATE INDEX orchestrati_status_0c02b5_idx ON orchestration.sync_history (status, start_time DESC);
            """)
            cursor.execute("""
                CREATE INDEX orchestrati_end_tim_dd1de7_idx ON orchestration.sync_history (end_time DESC);
            """)
            
            print("✅ Created orchestration.sync_history table with indexes")
        else:
            print("✅ orchestration.sync_history table already exists")


def drop_orchestration_sync_history(apps, schema_editor):
    """Drop orchestration.sync_history table (reverse operation)"""
    print("Dropping orchestration.sync_history table...")
    
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("DROP TABLE IF EXISTS orchestration.sync_history CASCADE;")
        print("✅ Dropped orchestration.sync_history table")


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0156_fix_missing_salespro_tables'),
    ]

    operations = [
        migrations.RunPython(
            create_orchestration_sync_history,
            drop_orchestration_sync_history,
        ),
    ]
