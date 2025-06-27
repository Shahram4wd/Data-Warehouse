import logging
from django.core.management.base import BaseCommand
from django.core.management import call_command

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Run all sync_hubspot_* commands to sync all HubSpot endpoints"

    def handle(self, *args, **options):
        commands = [
            'sync_hubspot_contacts',
            'sync_hubspot_deals',
            'sync_hubspot_appointments',
            'sync_hubspot_divisions',
        ]

        self.stdout.write(self.style.NOTICE('Starting full HubSpot sync sequence...'))
        for cmd in commands:
            self.stdout.write(self.style.NOTICE(f"Running {cmd}..."))
            try:
                call_command(cmd)
                self.stdout.write(self.style.SUCCESS(f"Completed {cmd}"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error running {cmd}: {e}"))
                logger.error(f"sync_hubspot_all: failed at {cmd}: {e}")
                break

        self.stdout.write(self.style.SUCCESS('✓ All HubSpot sync commands executed.'))
