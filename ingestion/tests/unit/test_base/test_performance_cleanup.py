#!/usr/bin/env python3
"""Test script to verify PerformanceMonitor cleanup method works correctly"""

import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

# Mock Django imports for testing
from unittest.mock import Mock
from datetime import datetime, timedelta

# Mock Django modules
django_mock = Mock()
django_utils_mock = Mock()
django_core_mock = Mock()
django_core_cache_mock = Mock()
django_db_mock = Mock()

# Create a proper timezone mock that behaves like the real one
class MockTimezone:
    @staticmethod
    def now():
        return datetime.now()

# Create the mock structure
timezone_mock = MockTimezone()
django_utils_mock.timezone = timezone_mock
django_mock.utils = django_utils_mock
django_core_mock.cache = django_core_cache_mock
django_mock.core = django_core_mock

# Set up the module mocks
sys.modules['django'] = django_mock
sys.modules['django.utils'] = django_utils_mock
sys.modules['django.utils.timezone'] = timezone_mock
sys.modules['django.core'] = django_core_mock
sys.modules['django.core.cache'] = django_core_cache_mock
sys.modules['django.db'] = django_db_mock

# Mock other dependencies
sys.modules['ingestion.models.common'] = Mock()
sys.modules['ingestion.monitoring.alerts'] = Mock()
sys.modules['ingestion.monitoring.dashboard'] = Mock()
sys.modules['ingestion.base.config'] = Mock()

from ingestion.base.performance import PerformanceMonitor
from ingestion.base.automation import SelfHealingSystem  # Use SelfHealingSystem instead of AutomationManager
import time

def test_performance_monitor_cleanup():
    """Test that PerformanceMonitor cleanup method works correctly"""
    print("Testing PerformanceMonitor cleanup method...")
    
    # Create a performance monitor
    monitor = PerformanceMonitor("test_monitor")
    
    # Start some operations
    op1 = monitor.start_operation("test_operation_1")
    op2 = monitor.start_operation("test_operation_2")
    
    # Finish one operation to add metrics
    monitor.finish_operation(op1, records_processed=100, errors_count=0)
    
    # Verify data exists
    assert len(monitor.active_operations) == 1  # One still active
    assert len(monitor.metrics) == 1  # One finished operation
    
    print(f"Before cleanup: {len(monitor.active_operations)} active operations, {len(monitor.metrics)} metrics")
    
    # Test cleanup
    monitor.cleanup()
    
    # Verify cleanup worked
    assert len(monitor.active_operations) == 0
    assert len(monitor.metrics) == 0
    assert len(monitor.aggregated_metrics) == 0
    
    print(f"After cleanup: {len(monitor.active_operations)} active operations, {len(monitor.metrics)} metrics")
    print("✓ PerformanceMonitor cleanup test passed!")

def test_automation_manager_cleanup():
    """Test that SelfHealingSystem can now call cleanup on PerformanceMonitor"""
    print("\nTesting SelfHealingSystem cleanup with PerformanceMonitor...")
    
    # Create automation system
    automation = SelfHealingSystem(source="test_system")
    
    # Create a performance monitor and add it to automation
    monitor = PerformanceMonitor("test_monitor")
    automation.performance_monitor = monitor
    
    # Add some test data
    op = monitor.start_operation("test_operation")
    
    # Verify data exists
    assert len(monitor.active_operations) == 1
    
    print(f"Before automation cleanup: {len(monitor.active_operations)} active operations")
    
    # Test that automation cleanup works without AttributeError
    try:
        # Since cleanup is async, we need to handle it properly
        import asyncio
        asyncio.run(automation.cleanup())
        print("✓ SelfHealingSystem cleanup completed successfully!")
    except AttributeError as e:
        print(f"✗ SelfHealingSystem cleanup failed: {e}")
        return False
    
    # Verify cleanup worked
    assert len(monitor.active_operations) == 0
    
    print(f"After automation cleanup: {len(monitor.active_operations)} active operations")
    print("✓ SelfHealingSystem cleanup test passed!")
    return True

if __name__ == "__main__":
    try:
        test_performance_monitor_cleanup()
        test_automation_manager_cleanup()
        print("\n✓ All tests passed! The cleanup method is working correctly.")
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
