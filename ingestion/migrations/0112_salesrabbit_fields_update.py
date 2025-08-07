# Generated manually to handle field updates without rename detection issues

from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ('ingestion', '0111_create_leadconduit_models'),
    ]

    operations = [
        # This migration resolves the Django migration state without making
        # actual database changes since the fields already exist correctly.
        # Django was confused about field renames vs new fields.
    ]
