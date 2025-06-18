import asyncio
import json
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.arrivy.arrivy_client import ArrivyClient

class Command(BaseCommand):
    help = "Test the Arrivy API connection and fetch sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            type=str,
            choices=["customers", "team_members", "bookings"],
            default="customers",
            help="Which endpoint to test (default: customers)"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=5,
            help="Number of records to fetch (default: 5)"
        )
        parser.add_argument(
            "--output",
            type=str,
            help="Output file to save the data (optional)"
        )

    def handle(self, *args, **options):
        endpoint = options.get('endpoint')
        limit = options.get('limit')
        output_file = options.get('output')

        try:
            self.stdout.write("Testing connection to Arrivy API...")
            
            # Check if credentials are configured
            if not all([settings.ARRIVY_API_KEY, settings.ARRIVY_AUTH_KEY, settings.ARRIVY_API_URL]):
                raise CommandError("Arrivy API credentials are not properly configured in settings.")
            
            client = ArrivyClient()
            
            # Test connection first
            success, message = asyncio.run(client.test_connection())
            if not success:
                raise CommandError(f"Connection test failed: {message}")
            
            self.stdout.write(self.style.SUCCESS("✓ Connection successful"))
            
            # Fetch sample data based on endpoint
            self.stdout.write(f"Fetching {limit} {endpoint} from Arrivy...")
            
            if endpoint == "customers":
                result = asyncio.run(client.get_customers(page_size=limit, page=1))
            elif endpoint == "team_members":
                result = asyncio.run(client.get_team_members(page_size=limit, page=1))
            elif endpoint == "bookings":
                result = asyncio.run(client.get_bookings(page_size=limit, page=1))
            
            if not result or not result.get('data'):
                self.stdout.write(self.style.WARNING(f"No {endpoint} data found"))
                return
            
            data = result['data']
            pagination = result.get('pagination', {})
            
            self.stdout.write(self.style.SUCCESS(f"✓ Successfully fetched {len(data)} {endpoint}"))
            
            if pagination:
                self.stdout.write(f"Pagination info:")
                self.stdout.write(f"  - Current page: {pagination.get('current_page', 1)}")
                self.stdout.write(f"  - Page size: {pagination.get('page_size', limit)}")
                self.stdout.write(f"  - Total count: {pagination.get('total_count', 'unknown')}")
                self.stdout.write(f"  - Has next page: {pagination.get('has_next', False)}")
            
            # Output to file if specified
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(result, f, indent=2, default=str)
                self.stdout.write(self.style.SUCCESS(f"✓ Saved data to {output_file}"))
            
            # Display first record as sample
            if data:
                self.stdout.write(f"\nSample {endpoint[:-1]} data:")
                self.stdout.write("=" * 50)
                
                sample = data[0]
                
                # Display key fields based on endpoint
                if endpoint == "customers":
                    self.stdout.write(f"ID: {sample.get('id')}")
                    self.stdout.write(f"Name: {sample.get('first_name', '')} {sample.get('last_name', '')}")
                    self.stdout.write(f"Company: {sample.get('company_name', 'N/A')}")
                    self.stdout.write(f"Email: {sample.get('email', 'N/A')}")
                    self.stdout.write(f"Phone: {sample.get('phone', 'N/A')}")
                    self.stdout.write(f"City: {sample.get('city', 'N/A')}")
                    
                elif endpoint == "team_members":
                    self.stdout.write(f"ID: {sample.get('id')}")
                    self.stdout.write(f"Name: {sample.get('name', 'N/A')}")
                    self.stdout.write(f"Email: {sample.get('email', 'N/A')}")
                    self.stdout.write(f"Role: {sample.get('role', 'N/A')}")
                    self.stdout.write(f"Group: {sample.get('group_name', 'N/A')}")
                    self.stdout.write(f"Active: {sample.get('is_active', False)}")
                    
                elif endpoint == "bookings":
                    self.stdout.write(f"ID: {sample.get('id')}")
                    self.stdout.write(f"Title: {sample.get('title', 'N/A')}")
                    self.stdout.write(f"Status: {sample.get('status', 'N/A')}")
                    self.stdout.write(f"Customer ID: {sample.get('customer_id', 'N/A')}")
                    self.stdout.write(f"Start: {sample.get('start_datetime', 'N/A')}")
                    self.stdout.write(f"End: {sample.get('end_datetime', 'N/A')}")
                
                self.stdout.write("\nFull record:")
                self.stdout.write(json.dumps(sample, indent=2, default=str))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Test failed: {str(e)}"))
            raise CommandError(f"Test failed: {str(e)}")
