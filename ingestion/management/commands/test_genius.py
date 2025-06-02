import json
from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.genius.genius_client import GeniusClient

class Command(BaseCommand):
    help = "Test the Genius API connection and fetch prospects"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Number of prospects to fetch (default: 10)"
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output file to save the prospects data (optional)"
        )

    def handle(self, *args, **options):
        limit = options.get('limit')
        output_file = options.get('output')

        try:
            self.stdout.write("Testing connection to Genius API...")
            client = GeniusClient(
                settings.GENIUS_API_URL,
                settings.GENIUS_USERNAME,
                settings.GENIUS_PASSWORD
            )
            
            self.stdout.write("Fetching prospects...")
            prospects = client.get_prospects(limit=limit)
            
            self.stdout.write(self.style.SUCCESS(f"Successfully fetched {len(prospects)} prospects"))
            
            # Output to file if specified
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(prospects, f, indent=2)
                self.stdout.write(self.style.SUCCESS(f"Saved prospects data to {output_file}"))
                
            # Display first prospect as sample
            if prospects:
                self.stdout.write("Sample prospect data:")
                self.stdout.write(json.dumps(prospects[0], indent=2))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error connecting to Genius API: {str(e)}"))
