from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.models import MarketingSource
import requests
import uuid
import logging

class Command(BaseCommand):
    help = "Synchronize marketing sources from the Genius CRM"

    def add_arguments(self, parser):
        # Add any command line arguments similar to sync_genius_divisions
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force recreation of all marketing sources'
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Syncing Marketing Sources..."))
        
        # Check if force option is used
        force = options.get('force', False)
        if force:
            self.stdout.write(self.style.WARNING("Force mode enabled - recreating all marketing sources"))
            # If using force, clear existing sources
            MarketingSource.objects.all().delete()
        
        # Get marketing sources
        saved_count = self._create_sources()
        
        self.stdout.write(self.style.SUCCESS(f"Successfully created {saved_count} marketing sources"))
    
    def _create_sources(self):
        """Create marketing sources in the database"""
        # Similar structure to sync_genius_divisions
        # Check if we already have sources
        existing_count = MarketingSource.objects.count()
        if existing_count > 0:
            self.stdout.write(self.style.SUCCESS(f"Found {existing_count} existing marketing sources. Use --force to recreate."))
            return existing_count
        
        # Standard marketing sources
        sources = [
            {"name": "Website", "description": "Company website"},
            {"name": "Google", "description": "Google ads and search"},
            {"name": "Facebook", "description": "Facebook and Instagram ads"},
            {"name": "Referral", "description": "Customer referrals"},
            {"name": "Direct Mail", "description": "Direct mail campaigns"},
            {"name": "Television", "description": "TV advertisements"},
            {"name": "Radio", "description": "Radio advertisements"},
            {"name": "Billboard", "description": "Billboard and outdoor advertising"},
            {"name": "Email", "description": "Email marketing campaigns"},
            {"name": "Trade Show", "description": "Trade shows and events"},
            {"name": "Home Show", "description": "Home and garden shows"},
            {"name": "Print", "description": "Newspaper and magazine ads"},
            {"name": "Door Hanger", "description": "Door-to-door marketing"},
            {"name": "Canvassing", "description": "In-person neighborhood canvassing"},
            {"name": "Other", "description": "Other marketing sources"}
        ]
        
        # Create all sources
        created_count = 0
        for source in sources:
            try:
                MarketingSource.objects.create(
                    id=uuid.uuid4(),
                    name=source["name"],
                    description=source["description"],
                    is_active=True
                )
                created_count += 1
                self.stdout.write(f"Created marketing source: {source['name']}")
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Error creating {source['name']}: {str(e)}"))
        
        return created_count