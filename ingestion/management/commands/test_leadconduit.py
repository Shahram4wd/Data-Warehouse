from django.core.management.base import BaseCommand
from ingestion.leadconduit.leadconduit_client import LeadConduitClient
import json


class Command(BaseCommand):
    help = "Test LeadConduit API connection and fetch sample data"

    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=5,
            help='Number of sample events to fetch (default: 5)'
        )
        parser.add_argument(
            '--save-response',
            action='store_true',
            help='Save API response to events_log.json file'
        )

    def handle(self, *args, **options):
        sample_size = options['sample_size']
        save_response = options['save_response']
        
        self.stdout.write(self.style.SUCCESS("=== LEADCONDUIT API CONNECTION TEST ==="))
        
        try:
            # Initialize client
            self.stdout.write("Initializing LeadConduit client...")
            client = LeadConduitClient()
            
            # Test connection
            self.stdout.write("Testing API connection...")
            if client.test_connection():
                self.stdout.write(self.style.SUCCESS("✅ API connection successful!"))
            else:
                self.stdout.write(self.style.ERROR("❌ API connection failed"))
                return
            
            # Fetch sample events
            self.stdout.write(f"\nFetching {sample_size} sample events...")
            events = client.get_events(limit=sample_size)
            
            if not events:
                self.stdout.write(self.style.WARNING("⚠️  No events found"))
                return
            
            self.stdout.write(self.style.SUCCESS(f"📊 Found {len(events)} events"))
            
            # Display sample events
            self.stdout.write("\n" + "="*60)
            self.stdout.write("SAMPLE EVENTS")
            self.stdout.write("="*60)
            
            for i, event in enumerate(events[:3], 1):
                self.stdout.write(f"\n🔸 Event {i}:")
                self.stdout.write(f"   ID: {event.get('id')}")
                self.stdout.write(f"   Type: {event.get('type')}")
                self.stdout.write(f"   Outcome: {event.get('outcome')}")
                self.stdout.write(f"   Timestamp: {event.get('start_timestamp')}")
                
                # Show lead data if available
                vars_data = event.get('vars', {})
                if vars_data:
                    self.stdout.write("   Lead Data:")
                    for key, value in list(vars_data.items())[:5]:  # Show first 5 fields
                        if value:
                            self.stdout.write(f"     {key}: {value}")
                    if len(vars_data) > 5:
                        self.stdout.write(f"     ... and {len(vars_data) - 5} more fields")
            
            # Save response if requested
            if save_response:
                filename = "events_log.json"
                with open(filename, 'w', encoding='utf-8') as f:
                    json.dump(events, f, indent=2)
                self.stdout.write(f"\n💾 Response saved to {filename}")
            
            # Show API statistics
            self.stdout.write(f"\n📈 SUMMARY:")
            self.stdout.write(f"   Total events fetched: {len(events)}")
            
            outcomes = {}
            event_types = {}
            
            for event in events:
                outcome = event.get('outcome', 'unknown')
                event_type = event.get('type', 'unknown')
                
                outcomes[outcome] = outcomes.get(outcome, 0) + 1
                event_types[event_type] = event_types.get(event_type, 0) + 1
            
            self.stdout.write(f"   Outcomes: {dict(outcomes)}")
            self.stdout.write(f"   Types: {dict(event_types)}")
            
            # Test lead search if we have lead data
            self.stdout.write("\n🔍 Testing lead search...")
            try:
                # Try to find a lead with an email
                test_query = "email"  # Simple search
                search_results = client.search_leads(query=test_query, limit=3)
                
                hits = search_results.get('hits', [])
                total = search_results.get('total', 0)
                
                self.stdout.write(f"   Search results: {len(hits)} hits out of {total} total")
                
                if hits:
                    lead = hits[0]
                    self.stdout.write("   Sample lead:")
                    self.stdout.write(f"     Name: {lead.get('first_name')} {lead.get('last_name')}")
                    self.stdout.write(f"     Email: {lead.get('email')}")
                    self.stdout.write(f"     Phone: {lead.get('phone_1')}")
                    self.stdout.write(f"     State: {lead.get('state')}")
                
            except Exception as e:
                self.stdout.write(self.style.WARNING(f"   Lead search test failed: {str(e)}"))
            
            self.stdout.write(f"\n✅ LeadConduit API test completed successfully!")
            self.stdout.write("   Ready to proceed with data import.")
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"❌ Test failed: {str(e)}"))
            raise
