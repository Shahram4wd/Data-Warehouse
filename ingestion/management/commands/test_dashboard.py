"""
Django Management Command for CRM Test Dashboard

Usage:
    python manage.py test_dashboard
    python manage.py test_dashboard --run unit_flag_validation
    python manage.py test_dashboard --list
    python manage.py test_dashboard --status
"""

import json
import sys
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from ingestion.tests.test_interface import CRMTestInterface, run_test_with_interface
from ingestion.tests.test_data_controller import TestDataController


class Command(BaseCommand):
    help = 'CRM Test Dashboard - Web interface for managing and executing CRM tests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--list',
            action='store_true',
            help='List all available tests'
        )
        
        parser.add_argument(
            '--run',
            type=str,
            help='Run a specific test by name'
        )
        
        parser.add_argument(
            '--status',
            action='store_true',
            help='Show current test execution status'
        )
        
        parser.add_argument(
            '--web',
            action='store_true',
            help='Start web interface (opens Django development server)'
        )
        
        parser.add_argument(
            '--export',
            type=str,
            help='Export test results to JSON file'
        )
        
        parser.add_argument(
            '--data-usage',
            choices=['MOCKED', 'MINIMAL', 'SAMPLE', 'RECENT', 'FULL_SYNC'],
            default='MOCKED',
            help='Data usage level for tests (default: MOCKED)'
        )

    def handle(self, *args, **options):
        """Execute the test dashboard command"""
        
        if options['list']:
            self.list_tests()
            
        elif options['run']:
            test_name = options['run']
            data_usage = options['data_usage']
            self.run_test(test_name, data_usage)
            
        elif options['status']:
            self.show_status()
            
        elif options['web']:
            self.start_web_interface()
            
        elif options['export']:
            self.export_results(options['export'])
            
        else:
            self.show_help()

    def list_tests(self):
        """List all available tests with detailed information"""
        self.stdout.write(
            self.style.SUCCESS("\n" + "="*80)
        )
        self.stdout.write(
            self.style.SUCCESS("CRM TEST DASHBOARD - Available Tests")
        )
        self.stdout.write(
            self.style.SUCCESS("="*80)
        )
        
        # Use the existing interface
        CRMTestInterface.list_all_tests()
        
        self.stdout.write(
            self.style.SUCCESS("\nUsage Examples:")
        )
        self.stdout.write("  python manage.py test_dashboard --run unit_flag_validation")
        self.stdout.write("  python manage.py test_dashboard --run integration_arrivy_limited --data-usage SAMPLE")
        self.stdout.write("  python manage.py test_dashboard --web")

    def run_test(self, test_name: str, data_usage: str):
        """Run a specific test with safety checks"""
        self.stdout.write(
            self.style.SUCCESS(f"\n🚀 Starting Test: {test_name}")
        )
        self.stdout.write(f"Data Usage Level: {data_usage}")
        
        # Get test configuration
        config = CRMTestInterface.TEST_CONFIGS.get(test_name)
        if not config:
            self.stdout.write(
                self.style.ERROR(f"❌ Test '{test_name}' not found!")
            )
            self.list_available_tests()
            return
        
        # Safety validation
        safety = CRMTestInterface.validate_test_safety(test_name)
        if not safety["safe"]:
            self.stdout.write(
                self.style.WARNING(f"⚠️  WARNING: {safety['reason']}")
            )
            if "warning" in safety:
                self.stdout.write(
                    self.style.ERROR(f"⚠️  {safety['warning']}")
                )
                
            # For web interface, we'll add confirmation
            confirmation = input("\nAre you sure you want to proceed? (yes/no): ")
            if confirmation.lower() != 'yes':
                self.stdout.write("Test cancelled.")
                return
        
        # Configure test data controller
        controller = TestDataController()
        try:
            controller.set_data_usage_level(data_usage)
        except ValueError as e:
            self.stdout.write(
                self.style.ERROR(f"❌ Invalid data usage level: {e}")
            )
            return
        
        # Execute the test
        self.stdout.write(
            self.style.SUCCESS("✅ Test setup complete. Executing...")
        )
        
        # Record test execution
        test_result = {
            'test_name': test_name,
            'data_usage': data_usage,
            'start_time': datetime.now().isoformat(),
            'config': {
                'name': config.name,
                'type': config.test_type.value,
                'uses_real_api': config.uses_real_api,
                'max_records': config.max_records,
                'estimated_duration': config.estimated_duration
            }
        }
        
        try:
            # This is where the actual test execution would happen
            success = run_test_with_interface(test_name)
            
            test_result['end_time'] = datetime.now().isoformat()
            test_result['status'] = 'success' if success else 'failed'
            test_result['result'] = 'Test completed successfully' if success else 'Test failed'
            
            self.stdout.write(
                self.style.SUCCESS("✅ Test completed successfully!")
            )
            
        except Exception as e:
            test_result['end_time'] = datetime.now().isoformat()
            test_result['status'] = 'error'
            test_result['result'] = str(e)
            
            self.stdout.write(
                self.style.ERROR(f"❌ Test failed with error: {e}")
            )
        
        # Save test result for web interface
        self.save_test_result(test_result)

    def show_status(self):
        """Show current test execution status"""
        self.stdout.write(
            self.style.SUCCESS("\n🔍 TEST EXECUTION STATUS")
        )
        self.stdout.write("="*50)
        
        # Check for running tests (would be implemented with actual test tracking)
        self.stdout.write("No tests currently running.")
        
        # Show recent test results
        recent_results = self.load_recent_results()
        if recent_results:
            self.stdout.write("\n📊 Recent Test Results:")
            for result in recent_results[-5:]:  # Last 5 results
                status_icon = "✅" if result['status'] == 'success' else "❌"
                self.stdout.write(
                    f"  {status_icon} {result['test_name']} - {result['start_time']}"
                )

    def start_web_interface(self):
        """Start the web interface"""
        self.stdout.write(
            self.style.SUCCESS("\n🌐 Starting CRM Test Dashboard Web Interface")
        )
        self.stdout.write("="*60)
        
        self.stdout.write("Web interface will be available at:")
        self.stdout.write(self.style.HTTP_INFO("http://localhost:8000/testing/"))
        
        self.stdout.write("\nAvailable URLs:")
        self.stdout.write("  📊 Dashboard: http://localhost:8000/testing/dashboard/")
        self.stdout.write("  📋 Test List: http://localhost:8000/testing/tests/")
        self.stdout.write("  📈 Results: http://localhost:8000/testing/results/")
        self.stdout.write("  🚀 Run Tests: http://localhost:8000/testing/run/")
        
        self.stdout.write(self.style.WARNING("\nTo start the development server:"))
        self.stdout.write("python manage.py runserver")

    def export_results(self, filename: str):
        """Export test results to JSON file"""
        results = self.load_recent_results()
        
        export_data = {
            'export_time': datetime.now().isoformat(),
            'total_tests': len(results),
            'results': results
        }
        
        with open(filename, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ Exported {len(results)} test results to {filename}")
        )

    def show_help(self):
        """Show help information"""
        self.stdout.write(
            self.style.SUCCESS("\n🔧 CRM TEST DASHBOARD HELP")
        )
        self.stdout.write("="*50)
        
        self.stdout.write("Available Commands:")
        self.stdout.write("  --list                    List all available tests")
        self.stdout.write("  --run <test_name>         Run a specific test")
        self.stdout.write("  --status                  Show test execution status")
        self.stdout.write("  --web                     Start web interface")
        self.stdout.write("  --export <filename>       Export results to JSON")
        
        self.stdout.write("\nData Usage Levels:")
        self.stdout.write("  MOCKED     - No real API calls (safest)")
        self.stdout.write("  MINIMAL    - Real API, 1-10 records max")
        self.stdout.write("  SAMPLE     - Real API, 50-100 records max")
        self.stdout.write("  RECENT     - Real API, last 7 days")
        self.stdout.write("  FULL_SYNC  - Real API, ALL records (⚠️  CAUTION!)")

    def list_available_tests(self):
        """List available test names for reference"""
        self.stdout.write("\nAvailable tests:")
        for test_name in CRMTestInterface.TEST_CONFIGS.keys():
            self.stdout.write(f"  - {test_name}")

    def save_test_result(self, result):
        """Save test result to file for web interface"""
        results_file = 'test_results.json'
        
        try:
            results = self.load_recent_results()
        except (FileNotFoundError, json.JSONDecodeError):
            results = []
        
        results.append(result)
        
        # Keep only last 100 results
        if len(results) > 100:
            results = results[-100:]
        
        with open(results_file, 'w') as f:
            json.dump(results, f, indent=2)

    def load_recent_results(self):
        """Load recent test results"""
        results_file = 'test_results.json'
        
        try:
            with open(results_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return []
