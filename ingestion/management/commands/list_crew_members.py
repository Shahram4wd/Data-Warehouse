import asyncio
import logging
from django.core.management.base import BaseCommand
from ingestion.arrivy.arrivy_client import ArrivyClient

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Get all individual crew members from Arrivy API"

    def add_arguments(self, parser):
        parser.add_argument(
            "--search-id",
            type=str,
            help="Search for specific crew member ID"
        )
        parser.add_argument(
            "--search-name",
            type=str,
            help="Search for crew member by name (partial match)"
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=10,
            help="Limit number of results to display"
        )

    def handle(self, *args, **options):
        search_id = options.get("search_id")
        search_name = options.get("search_name")
        limit = options.get("limit", 10)
        
        asyncio.run(self.get_crew_members(search_id, search_name, limit))

    async def get_crew_members(self, search_id, search_name, limit):
        client = ArrivyClient()
        
        self.stdout.write("🔍 Fetching all crew members from divisions...")
        
        try:
            result = await client.get_all_crew_members(page_size=100)
            crew_members = result.get('data', [])
            
            self.stdout.write(f"📊 Found {len(crew_members)} crew members across {result.get('total_divisions', 0)} divisions")
            
            # Filter results if search criteria provided
            filtered_members = crew_members
            
            if search_id:
                filtered_members = [m for m in crew_members if str(m.get('id')) == search_id]
                if filtered_members:
                    self.stdout.write(f"\n🎯 FOUND CREW MEMBER WITH ID {search_id}:")
                    member = filtered_members[0]
                    for key, value in member.items():
                        self.stdout.write(f"  {key}: {value}")
                    return
                else:
                    self.stdout.write(f"❌ No crew member found with ID {search_id}")
                    return
            
            if search_name:
                filtered_members = [m for m in crew_members 
                                  if search_name.lower() in str(m.get('name', '')).lower()]
                self.stdout.write(f"\n🔍 Found {len(filtered_members)} crew members matching '{search_name}':")
            
            # Display results
            display_count = min(limit, len(filtered_members))
            
            if display_count == 0:
                self.stdout.write("❌ No crew members found matching criteria")
                return
                
            self.stdout.write(f"\n📋 Showing {display_count} of {len(filtered_members)} crew members:")
            self.stdout.write("="*80)
            
            for i, member in enumerate(filtered_members[:display_count]):
                self.stdout.write(f"\n{i+1}. {member.get('name', 'Unknown')} (ID: {member.get('id')})")
                self.stdout.write(f"   Division: {member.get('division_name')} (ID: {member.get('division_id')})")
                self.stdout.write(f"   Group ID: {member.get('group_id')}")
                if member.get('image_path'):
                    self.stdout.write(f"   Image: {member.get('image_path')}")
                
                # Show additional fields if available
                additional_fields = {k: v for k, v in member.items() 
                                   if k not in ['id', 'name', 'division_id', 'division_name', 'group_id', 'image_path'] 
                                   and v is not None}
                if additional_fields:
                    self.stdout.write(f"   Additional: {additional_fields}")
            
            if len(filtered_members) > limit:
                self.stdout.write(f"\n... and {len(filtered_members) - limit} more crew members")
            
        except Exception as e:
            self.stdout.write(f"❌ Error fetching crew members: {e}")
            logger.exception("Error in get_crew_members")
