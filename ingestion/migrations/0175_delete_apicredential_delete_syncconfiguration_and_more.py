from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0174_alter_syncschedule_options_and_more'),
    ]

    operations = [
        # Create orchestration schema if missing
        migrations.RunSQL("CREATE SCHEMA IF NOT EXISTS orchestration;"),

        # Fix SyncHistory: if created as a literal name in public schema, rename then move
        migrations.RunSQL(
            sql=(
                'ALTER TABLE IF EXISTS "orchestration.sync_history" RENAME TO "sync_history";\n'
                'ALTER TABLE IF EXISTS "sync_history" SET SCHEMA orchestration;'
            ),
            reverse_sql=(
                'ALTER TABLE IF EXISTS orchestration."sync_history" SET SCHEMA public;\n'
                'ALTER TABLE IF EXISTS "sync_history" RENAME TO "orchestration.sync_history";'
            ),
        ),

        # Fix SyncSchedule: if created as a literal name in public schema, rename then move
        migrations.RunSQL(
            sql=(
                'ALTER TABLE IF EXISTS "orchestration.sync_schedule" RENAME TO "sync_schedule";\n'
                'ALTER TABLE IF EXISTS "sync_schedule" SET SCHEMA orchestration;'
            ),
            reverse_sql=(
                'ALTER TABLE IF EXISTS orchestration."sync_schedule" SET SCHEMA public;\n'
                'ALTER TABLE IF EXISTS "sync_schedule" RENAME TO "orchestration.sync_schedule";'
            ),
        ),
    ]
