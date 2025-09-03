from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("ingestion", "0175_delete_apicredential_delete_syncconfiguration_and_more"),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            database_operations=[],
            state_operations=[
                migrations.AlterModelTable(
                    name="synchistory",
                    table='"orchestration"."sync_history"',
                ),
                migrations.AlterModelTable(
                    name="syncschedule",
                    table='"orchestration"."sync_schedule"',
                ),
            ],
        ),
    ]
