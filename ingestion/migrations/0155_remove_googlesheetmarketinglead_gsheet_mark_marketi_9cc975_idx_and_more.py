# Safe migration for GoogleSheetMarketingLead model
# This replaces the problematic 0155 migration

from django.db import migrations, models
import django.utils.timezone


def check_table_exists(schema_editor, schema_name, table_name):
    """Check if a table exists"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.tables 
            WHERE table_schema = %s AND table_name = %s
        """, [schema_name, table_name])
        return cursor.fetchone()[0] > 0


def check_index_exists(schema_editor, schema_name, table_name, index_name):
    """Check if an index exists before trying to remove it"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM pg_indexes 
            WHERE schemaname = %s AND tablename = %s AND indexname = %s
        """, [schema_name, table_name, index_name])
        return cursor.fetchone()[0] > 0


def check_column_exists(schema_editor, schema_name, table_name, column_name):
    """Check if a column exists"""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("""
            SELECT COUNT(*)
            FROM information_schema.columns 
            WHERE table_schema = %s AND table_name = %s AND column_name = %s
        """, [schema_name, table_name, column_name])
        return cursor.fetchone()[0] > 0


def safe_remove_index_if_exists(apps, schema_editor, schema_name, table_name, index_name):
    """Safely remove an index if it exists"""
    if check_index_exists(schema_editor, schema_name, table_name, index_name):
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f'DROP INDEX IF EXISTS "{schema_name}"."{index_name}";')
        print(f"Removed index: {schema_name}.{index_name}")
    else:
        print(f"Index {index_name} does not exist in {schema_name}, skipping removal")


def safe_rename_field_if_exists(apps, schema_editor, schema_name, table_name, old_name, new_name):
    """Safely rename a field if the old field exists and new field doesn't"""
    if check_column_exists(schema_editor, schema_name, table_name, old_name):
        if not check_column_exists(schema_editor, schema_name, table_name, new_name):
            with schema_editor.connection.cursor() as cursor:
                cursor.execute(f'ALTER TABLE "{schema_name}"."{table_name}" RENAME COLUMN "{old_name}" TO "{new_name}";')
            print(f"Renamed column: {schema_name}.{table_name}.{old_name} -> {new_name}")
        else:
            print(f"Column {new_name} already exists in {schema_name}.{table_name}, skipping rename")
    else:
        print(f"Column {old_name} does not exist in {schema_name}.{table_name}, skipping rename")


def safe_add_index_if_not_exists(apps, schema_editor, schema_name, table_name, index_name, fields):
    """Safely add an index if it doesn't exist"""
    if not check_index_exists(schema_editor, schema_name, table_name, index_name):
        fields_str = ", ".join([f'"{field}"' for field in fields])
        with schema_editor.connection.cursor() as cursor:
            cursor.execute(f'CREATE INDEX "{index_name}" ON "{schema_name}"."{table_name}" ({fields_str});')
        print(f"Added index: {schema_name}.{index_name}")
    else:
        print(f"Index {index_name} already exists in {schema_name}, skipping creation")


def apply_safe_salespro_changes(apps, schema_editor):
    """Apply SalesPro model changes safely - only if tables exist"""
    schema_name = "ingestion"  # CRM tables are in ingestion schema
    
    print("Starting safe SalesPro field updates...")
    
    salespro_tables = [
        'salespro_credit_application',
        'salespro_customer', 
        'salespro_estimate',
        'salespro_lead_result',
        'salespro_office',
        'salespro_payment',
        'salespro_user',
        'salespro_user_activity'
    ]
    
    for table_name in salespro_tables:
        if check_table_exists(schema_editor, schema_name, table_name):
            print(f"Updating sync timestamps for {schema_name}.{table_name}")
            try:
                with schema_editor.connection.cursor() as cursor:
                    # Update sync_created_at to have default timezone.now
                    cursor.execute(f'''
                        ALTER TABLE "{schema_name}"."{table_name}" 
                        ALTER COLUMN "sync_created_at" SET DEFAULT NOW();
                    ''')
                    
                    # Update sync_updated_at to auto-update
                    cursor.execute(f'''
                        ALTER TABLE "{schema_name}"."{table_name}" 
                        ALTER COLUMN "sync_updated_at" SET DEFAULT NOW();
                    ''')
                    
                print(f"✓ Updated {table_name}")
            except Exception as e:
                print(f"⚠ Warning: Failed to update {table_name}: {e}")
        else:
            print(f"⚠ Table {schema_name}.{table_name} does not exist, skipping")
    
    print("SalesPro field updates completed")


def reverse_safe_salespro_changes(apps, schema_editor):
    """Reverse SalesPro changes"""
    print("Reversing SalesPro field updates... (no action needed)")


def apply_safe_googlesheet_changes(apps, schema_editor):
    """Apply all GoogleSheet changes safely"""
    schema_name = "ingestion"  # CRM tables are in ingestion schema
    table_name = "gsheet_marketing_lead"
    
    print("Starting safe GoogleSheet migration...")
    
    # 1. Safely remove old indexes
    safe_remove_index_if_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_marketi_9cc975_idx')
    safe_remove_index_if_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_marketi_86b1a6_idx')
    
    # 2. Safely rename field
    safe_rename_field_if_exists(apps, schema_editor, schema_name, table_name, 'marketing_channel', 'channel')
    
    # 3. Safely add new indexes
    safe_add_index_if_not_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_channel_089373_idx', ['channel', 'division'])
    safe_add_index_if_not_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_channel_7a04c4_idx', ['channel', 'created_at'])
    
    print("GoogleSheet migration completed safely")


def reverse_safe_googlesheet_changes(apps, schema_editor):
    """Reverse the GoogleSheet changes"""
    schema_name = "ingestion"  # CRM tables are in ingestion schema
    table_name = "gsheet_marketing_lead"
    
    print("Reversing safe GoogleSheet migration...")
    
    # Remove new indexes
    safe_remove_index_if_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_channel_089373_idx')
    safe_remove_index_if_exists(apps, schema_editor, schema_name, table_name, 'gsheet_mark_channel_7a04c4_idx')
    
    # Rename field back
    safe_rename_field_if_exists(apps, schema_editor, schema_name, table_name, 'channel', 'marketing_channel')
    
    print("GoogleSheet migration reversed")


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0151_genius_job_genius_jobchangeorder_and_more_squashed_0154_delete_hubspot_synchistory_alter_alertmodel_options_and_more'),
    ]

    operations = [
        # Handle GoogleSheetMarketingLead changes with custom SQL
        migrations.RunPython(
            apply_safe_googlesheet_changes,
            reverse_safe_googlesheet_changes,
        ),
        
        # Handle SalesPro model field updates with custom SQL
        migrations.RunPython(
            apply_safe_salespro_changes,
            reverse_safe_salespro_changes,
        ),
    ]
