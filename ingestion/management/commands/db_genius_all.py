import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run all db_genius_* commands in order of model dependencies"

    def handle(self, *args, **options):
        commands = [
            'db_genius_divisions',
            'db_genius_division_groups',
            'db_genius_user_titles',
            'db_genius_users',
            'db_genius_marketing_source_types',
            'db_genius_marketing_sources',
            'db_genius_prospect_sources',
            'db_genius_prospects',
            'db_genius_services',
            'db_genius_appointment_types',
            'db_genius_appointment_outcome_types',
            'db_genius_appointment_outcomes',
            'db_genius_appointments',
            'db_genius_appointment_services',
            'db_genius_quotes',
        ]

        self.stdout.write(self.style.NOTICE('Starting full Genius DB import sequence...'))
        for cmd in commands:
            self.stdout.write(self.style.NOTICE(f"Running {cmd}..."))
            try:
                call_command(cmd)
                self.stdout.write(self.style.SUCCESS(f"Completed {cmd}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error running {cmd}: {e}"))
                logger.error(f"db_genius_all: failed at {cmd}: {e}")
                break

        self.stdout.write(self.style.SUCCESS('✓ All Genius DB commands executed.'))
