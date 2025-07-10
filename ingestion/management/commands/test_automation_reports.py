"""
Test command to verify the automation reports generation functionality
"""
import asyncio
from django.core.management.base import BaseCommand

class Command(BaseCommand):
    help = 'Test the automation reports generation command'
    
    def handle(self, *args, **options):
        """Test the automation reports command"""
        from django.core.management import call_command
        
        self.stdout.write(self.style.SUCCESS('Testing automation reports generation...'))
        
        try:
            # Test the command with minimal options
            call_command(
                'generate_automation_reports',
                '--time-window', 1,  # 1 hour for quick test
                '--crm', 'hubspot',  # Test with just HubSpot
                verbosity=2
            )
            
            self.stdout.write(self.style.SUCCESS('✅ Automation reports test completed successfully'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ Test failed: {e}'))
            raise
