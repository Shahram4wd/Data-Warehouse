# Follow-up migration to handle SalesPro tables with correct names
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


def apply_missing_salespro_changes(apps, schema_editor):
    """Apply SalesPro model changes for tables that were missed"""
    schema_name = "ingestion"
    
    print("Starting follow-up SalesPro field updates...")
    
    # Tables that were missed in the previous migration due to naming
    missing_tables = [
        'salespro_credit_application',
        'salespro_lead_result', 
        'salespro_user_activity'
    ]
    
    for table_name in missing_tables:
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
    
    print("Follow-up SalesPro field updates completed")


def reverse_missing_salespro_changes(apps, schema_editor):
    """Reverse the follow-up changes"""
    print("Reversing follow-up SalesPro field updates... (no action needed)")


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0155_remove_googlesheetmarketinglead_gsheet_mark_marketi_9cc975_idx_and_more'),
    ]

    operations = [
        migrations.RunPython(
            apply_missing_salespro_changes,
            reverse_missing_salespro_changes,
        ),
    ]
