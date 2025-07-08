#!/usr/bin/env python
"""
Docker-based tests for HubSpot integration
"""
import os
import sys
import subprocess
import django
from django.conf import settings
from django.test import TestCase

# Add the project root to Python path
sys.path.insert(0, '/app')

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

class TestHubSpotDocker:
    """Tests for HubSpot integration in Docker environment"""

    def test_django_setup(self):
        """Test if Django is properly configured"""
        try:
            from django.core.management import execute_from_command_line
            print("✓ Django setup successful")
            return True
        except Exception as e:
            print(f"✗ Django setup failed: {e}")
            return False

    def test_redis_connectivity(self):
        """Test Redis connectivity"""
        try:
            import redis
            r = redis.Redis(host='redis', port=6379, db=0)
            r.ping()
            print("✓ Redis connection successful")
            return True
        except Exception as e:
            print(f"✗ Redis connection failed: {e}")
            return False

    def test_hubspot_imports(self):
        """Test if HubSpot modules can be imported"""
        try:
            from ingestion.sync.hubspot.clients.base import HubSpotBaseClient
            from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
            print("✓ HubSpot imports successful")
            return True
        except Exception as e:
            print(f"✗ HubSpot imports failed: {e}")
            return False

    def test_database_connectivity(self):
        """Test database connectivity"""
        try:
            from django.db import connection
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()
            print("✓ Database connection successful")
            return True
        except Exception as e:
            print(f"✗ Database connection failed: {e}")
            return False

    def run_all_tests(self):
        """Run all tests and report results"""
        print("🔄 Running Docker environment tests...")
        
        tests = [
            self.test_django_setup,
            self.test_redis_connectivity,
            self.test_hubspot_imports,
            self.test_database_connectivity
        ]
        
        passed = 0
        failed = 0
        
        for test in tests:
            try:
                if test():
                    passed += 1
                else:
                    failed += 1
            except Exception as e:
                print(f"✗ Test {test.__name__} failed with exception: {e}")
                failed += 1
        
        print(f"\n📊 Test Results: {passed} passed, {failed} failed")
        
        if failed == 0:
            print("🎉 All tests passed!")
            return True
        else:
            print("❌ Some tests failed!")
            return False

if __name__ == '__main__':
    tester = TestHubSpotDocker()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)
