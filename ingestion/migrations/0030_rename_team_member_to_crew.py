# Generated by Django 4.2.23 on 2025-06-19 03:31

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0029_remove_customer_foreign_key'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Arrivy_TeamMember',
            new_name='Arrivy_Crew',
        ),
        migrations.AlterModelOptions(
            name='arrivy_crew',
            options={'verbose_name': 'Arrivy Crew', 'verbose_name_plural': 'Arrivy Crews'},
        ),
        migrations.AlterModelTable(
            name='arrivy_crew',
            table='arrivy_crew',
        ),
    ]
