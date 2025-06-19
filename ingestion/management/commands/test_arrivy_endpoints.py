import asyncio
import logging
from django.core.management.base import BaseCommand
from ingestion.arrivy.arrivy_client import ArrivyClient

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Test different Arrivy API endpoints to understand crew vs crews"

    def add_arguments(self, parser):
        parser.add_argument(
            "--endpoint",
            type=str,
            default="both",
            help="Which endpoint to test: crew, crews, entities, groups, or both"
        )
        parser.add_argument(
            "--search-id",
            type=str,
            help="Search for specific ID in the results"
        )

    def handle(self, *args, **options):
        endpoint = options.get("endpoint", "both")
        search_id = options.get("search_id")
        
        asyncio.run(self.test_endpoints(endpoint, search_id))

    async def test_endpoints(self, endpoint_choice, search_id):
        client = ArrivyClient()
        
        if endpoint_choice in ["crew", "both"]:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔍 TESTING CREW ENDPOINT (singular)")
            self.stdout.write("="*60)
            try:
                result = await client.get_crew_singular(page_size=10)
                data = result.get('data', [])
                self.stdout.write(f"Crew endpoint returned {len(data)} items")
                
                if data:
                    self.stdout.write("Sample crew item:")
                    sample = data[0]
                    for key, value in sample.items():
                        if key == 'entities_data':
                            self.stdout.write(f"  {key}: {len(value) if isinstance(value, list) else value} entities")
                        else:
                            self.stdout.write(f"  {key}: {value}")
                
                if search_id:
                    found = [item for item in data if str(item.get('id')) == search_id or str(item.get('external_id')) == search_id]
                    if found:
                        self.stdout.write(f"\n🎯 FOUND ID {search_id} in CREW endpoint:")
                        for key, value in found[0].items():
                            self.stdout.write(f"  {key}: {value}")
                    else:
                        self.stdout.write(f"❌ ID {search_id} not found in crew endpoint")
                        
            except Exception as e:
                self.stdout.write(f"❌ Error testing crew endpoint: {e}")

        if endpoint_choice in ["crews", "both"]:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔍 TESTING CREWS ENDPOINT (plural)")
            self.stdout.write("="*60)
            try:
                result = await client.get_crews(page_size=10)
                data = result.get('data', [])
                self.stdout.write(f"Crews endpoint returned {len(data)} items")
                
                if data:
                    self.stdout.write("Sample crews item:")
                    sample = data[0]
                    for key, value in sample.items():
                        if key == 'entities_data':
                            self.stdout.write(f"  {key}: {len(value) if isinstance(value, list) else value} entities")
                        else:
                            self.stdout.write(f"  {key}: {value}")
                
                if search_id:
                    found = [item for item in data if str(item.get('id')) == search_id or str(item.get('external_id')) == search_id]
                    if found:
                        self.stdout.write(f"\n🎯 FOUND ID {search_id} in CREWS endpoint:")
                        for key, value in found[0].items():
                            self.stdout.write(f"  {key}: {value}")
                    else:
                        self.stdout.write(f"❌ ID {search_id} not found in crews endpoint")
                        
                        # Check inside entities_data
                        self.stdout.write(f"🔍 Searching inside entities_data for {search_id}...")
                        for item in data:
                            entities = item.get('entities_data', [])
                            if isinstance(entities, list):
                                for entity in entities:
                                    if str(entity.get('id')) == search_id or str(entity.get('external_id')) == search_id:
                                        self.stdout.write(f"\n🎯 FOUND ID {search_id} in entities_data of {item.get('name')}:")
                                        for key, value in entity.items():
                                            self.stdout.write(f"  {key}: {value}")
                                        return
                        self.stdout.write(f"❌ ID {search_id} not found in entities_data either")
                        
            except Exception as e:
                self.stdout.write(f"❌ Error testing crews endpoint: {e}")

        if endpoint_choice in ["entities", "both"]:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔍 TESTING ENTITIES ENDPOINT")
            self.stdout.write("="*60)
            try:
                result = await client.get_entities(page_size=20)
                data = result.get('data', [])
                self.stdout.write(f"Entities endpoint returned {len(data)} items")
                
                if data:
                    self.stdout.write("Sample entity item:")
                    sample = data[0]
                    for key, value in sample.items():
                        self.stdout.write(f"  {key}: {value}")
                
                if search_id:
                    found = [item for item in data if str(item.get('id')) == search_id or str(item.get('external_id')) == search_id]
                    if found:
                        self.stdout.write(f"\n🎯 FOUND ID {search_id} in ENTITIES endpoint:")
                        for key, value in found[0].items():
                            self.stdout.write(f"  {key}: {value}")
                        return  # Found it, no need to check other endpoints
                    else:
                        self.stdout.write(f"❌ ID {search_id} not found in entities endpoint")
                        
            except Exception as e:
                self.stdout.write(f"❌ Error testing entities endpoint: {e}")

        if endpoint_choice in ["groups", "both"]:
            self.stdout.write("\n" + "="*60)
            self.stdout.write("🔍 TESTING GROUPS ENDPOINT (official)")
            self.stdout.write("="*60)
            try:
                result = await client.get_groups(page_size=10)
                data = result.get('data', [])
                self.stdout.write(f"Groups endpoint returned {len(data)} items")
                
                if data:
                    self.stdout.write("Sample group item:")
                    sample = data[0]
                    for key, value in sample.items():
                        self.stdout.write(f"  {key}: {value}")
                
                if search_id:
                    found = [item for item in data if str(item.get('id')) == search_id or str(item.get('external_id')) == search_id]
                    if found:
                        self.stdout.write(f"\n🎯 FOUND ID {search_id} in GROUPS endpoint:")
                        for key, value in found[0].items():
                            self.stdout.write(f"  {key}: {value}")
                    else:
                        self.stdout.write(f"❌ ID {search_id} not found in groups endpoint")
                        
            except Exception as e:
                self.stdout.write(f"❌ Error testing groups endpoint: {e}")
