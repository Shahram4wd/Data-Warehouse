"""
Test runner for HubSpot refactored components
"""
import os
import sys
import django
from django.conf import settings
from django.test.utils import get_runner

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Configure Django settings
if not settings.configured:
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
    django.setup()

def run_tests():
    """Run all HubSpot-related tests"""
    TestRunner = get_runner(settings)
    test_runner = TestRunner()
    
    # Define test modules
    test_modules = [
        'ingestion.tests.test_hubspot_engines',
        'ingestion.tests.test_hubspot_processors',
        'ingestion.tests.test_hubspot_commands',
        'ingestion.tests.test_hubspot_integration',
    ]
    
    print("Running HubSpot refactored component tests...")
    print("=" * 60)
    
    failures = test_runner.run_tests(test_modules)
    
    if failures:
        print(f"\n❌ {failures} test(s) failed")
        return 1
    else:
        print("\n✅ All tests passed!")
        return 0

if __name__ == '__main__':
    sys.exit(run_tests())
