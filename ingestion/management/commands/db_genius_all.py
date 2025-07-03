import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run all db_genius_* commands in order of model dependencies"

    def handle(self, *args, **options):
        commands = [
            {"name": "db_genius_leads", "options": {"added_on_after": "2025-07-01"}},
            {"name": "db_genius_user_titles", "options": {}},
            {"name": "db_genius_users", "options": {}},
            {"name": "db_genius_services", "options": {}},
            {"name": "db_genius_quotes", "options": {}},
            {"name": "db_genius_prospect_sources", "options": {}},
            {"name": "db_genius_prospects", "options": {}},
            {"name": "db_genius_marketsharp_sources", "options": {}},
            {"name": "db_genius_marketsharp_marketing_source_maps", "options": {}},
            {"name": "db_genius_marketing_source_types", "options": {}},
            {"name": "db_genius_marketing_sources", "options": {}},
            {"name": "db_genius_division_groups", "options": {}},
            {"name": "db_genius_divisions", "options": {}},
            {"name": "db_genius_appointment_types", "options": {}},
            {"name": "db_genius_appointment_services", "options": {}},
            {"name": "db_genius_appointment_outcome_types", "options": {}},
            {"name": "db_genius_appointment_outcomes", "options": {}},
            {"name": "db_genius_appointments", "options": {}}
        ]

        self.stdout.write(self.style.NOTICE('Starting full Genius DB import sequence...'))
        for cmd in commands:
            self.stdout.write(self.style.NOTICE(f"Running {cmd['name']}..."))
            try:
                call_command(cmd['name'], **cmd['options'])
                self.stdout.write(self.style.SUCCESS(f"Completed {cmd['name']}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error running {cmd['name']}: {e}"))
                logger.error(f"db_genius_all: failed at {cmd['name']}: {e}")
                break

        self.stdout.write(self.style.SUCCESS('✓ All Genius DB commands executed.'))
