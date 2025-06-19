import asyncio
import json
import logging
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.activeprospect.activeprospect_client import ActiveProspectClient

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Test ActiveProspect LeadConduit API connection and fetch sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            type=str,
            default="events",
            choices=["events", "leads", "stats"],
            help="Which endpoint to test (events, leads, stats)"
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
            help="Save output to file"
        )
        parser.add_argument(
            "--query",
            type=str,
            help="Search query for leads endpoint"
        )
        parser.add_argument(
            "--days",
            type=int,
            default=7,
            help="Number of days back to fetch data (default: 7)"
        )

    def handle(self, *args, **options):
        endpoint = options.get("endpoint")
        limit = options.get("limit")
        output_file = options.get("output")
        query = options.get("query")
        days = options.get("days")

        if not all([settings.ACTIVEPROSPECT_API_TOKEN]):
            raise CommandError("ActiveProspect API token is not configured in settings.")

        self.stdout.write(f"Testing ActiveProspect API - Endpoint: {endpoint}")
        self.stdout.write(f"API Base URL: {settings.ACTIVEPROSPECT_BASE_URL}")
        self.stdout.write(f"API Token: {settings.ACTIVEPROSPECT_API_TOKEN[:8]}...")
        self.stdout.write("")

        try:
            result = asyncio.run(self.test_api(endpoint, limit, query, days))
            
            if output_file:
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(result, f, indent=2, default=str)
                self.stdout.write(f"Output saved to: {output_file}")
            else:
                self.stdout.write("Sample data:")
                self.stdout.write(json.dumps(result, indent=2, default=str)[:2000] + "...")

        except Exception as e:
            logger.exception("Error testing ActiveProspect API")
            raise CommandError(f"API test failed: {str(e)}")

    async def test_api(self, endpoint, limit, query, days):
        """Test the specified API endpoint"""
        client = ActiveProspectClient()
        
        # Test connection first
        self.stdout.write("Testing connection...")
        success, message = await client.test_connection()
        if not success:
            raise CommandError(f"Connection test failed: {message}")
        
        self.stdout.write(self.style.SUCCESS(f"✓ Connection successful: {message}"))
        self.stdout.write("")

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        if endpoint == "events":
            self.stdout.write(f"Fetching {limit} events from last {days} days...")
            result = await client.get_events(
                limit=limit,
                start=start_date,
                end=end_date
            )
            
            if result and 'data' in result:
                events = result['data']
                self.stdout.write(f"Retrieved {len(events)} events")
                
                # Show summary
                if events:
                    outcomes = {}
                    types = {}
                    for event in events:
                        outcome = event.get('outcome', 'unknown')
                        event_type = event.get('type', 'unknown')
                        outcomes[outcome] = outcomes.get(outcome, 0) + 1
                        types[event_type] = types.get(event_type, 0) + 1
                    
                    self.stdout.write(f"Outcomes: {dict(outcomes)}")
                    self.stdout.write(f"Types: {dict(types)}")
                
                return result
            else:
                self.stdout.write("No events found")
                return result

        elif endpoint == "leads":
            self.stdout.write(f"Searching leads with query: '{query or 'all'}' (limit: {limit})...")
            result = await client.search_leads(
                query=query,
                limit=limit
            )
            
            if result and 'hits' in result:
                leads = result['hits']
                total = result.get('total', len(leads))
                self.stdout.write(f"Found {len(leads)} leads (total: {total})")
                
                # Show summary
                if leads:
                    states = {}
                    sources = {}
                    for lead in leads:
                        state = lead.get('state', 'unknown')
                        source = lead.get('source_name', 'unknown')
                        states[state] = states.get(state, 0) + 1
                        sources[source] = sources.get(source, 0) + 1
                    
                    self.stdout.write(f"States: {dict(list(states.items())[:5])}")
                    self.stdout.write(f"Sources: {dict(list(sources.items())[:5])}")
                
                return result
            else:
                self.stdout.write("No leads found")
                return result

        elif endpoint == "stats":
            self.stdout.write(f"Fetching event statistics for last {days} days...")
            result = await client.get_event_statistics(
                start=start_date,
                end=end_date
            )
            
            if result:
                self.stdout.write("Statistics retrieved:")
                if isinstance(result, list) and result:
                    stats = result[0]
                    for key, value in stats.items():
                        if isinstance(value, (int, float)) and value > 0:
                            self.stdout.write(f"  {key}: {value}")
                
                return result
            else:
                self.stdout.write("No statistics found")
                return result

        else:
            raise CommandError(f"Unknown endpoint: {endpoint}")
