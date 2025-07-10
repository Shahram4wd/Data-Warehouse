#!/usr/bin/env python
"""
Test for the report_metrics() method in SelfHealingSystem
"""
import asyncio
import json
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, Mock

# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

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
sys.modules['ingestion.base.performance'] = Mock()
sys.modules['ingestion.monitoring.alerts'] = Mock()
sys.modules['ingestion.monitoring.dashboard'] = Mock()
sys.modules['ingestion.base.config'] = Mock()

# Now import the automation module
from ingestion.base.automation import SelfHealingSystem, AutomationAction, AutomationLevel, AutomationStrategy


async def test_report_metrics():
    """Test the report_metrics method"""
    print("Testing report_metrics() method...")
    
    # Create automation system
    system = SelfHealingSystem(source="test_system")
    
    # Create some test actions
    now = datetime.now()
    test_actions = [
        AutomationAction(
            rule_name="test_rule_1",
            action_type="restart_sync",
            success=True,
            message="Test successful action",
            timestamp=now - timedelta(hours=1)
        ),
        AutomationAction(
            rule_name="test_rule_2",
            action_type="adjust_batch_size",
            success=False,
            message="Test failed action",
            timestamp=now - timedelta(hours=2)
        ),
        AutomationAction(
            rule_name="test_rule_1",
            action_type="restart_sync",
            success=True,
            message="Another successful action",
            timestamp=now - timedelta(hours=3)
        )
    ]
    
    # Add test actions to system
    system.action_history = test_actions
    
    try:
        # Test basic report
        print("Testing basic report...")
        report = await system.report_metrics(time_window_hours=24, include_detailed=False)
        
        assert 'metadata' in report
        assert 'performance_metrics' in report
        assert 'system_health' in report
        assert 'quality_metrics' in report
        assert 'recommendations' in report
        
        print("✓ Basic report structure validated")
        
        # Test detailed report
        print("Testing detailed report...")
        detailed_report = await system.report_metrics(time_window_hours=24, include_detailed=True)
        
        assert 'detailed_metrics' in detailed_report
        assert 'rule_metrics' in detailed_report['detailed_metrics']
        assert 'recent_actions' in detailed_report['detailed_metrics']
        
        print("✓ Detailed report structure validated")
        
        # Test metrics calculation
        perf_metrics = report['performance_metrics']
        assert perf_metrics['total_actions'] == 3
        assert perf_metrics['successful_actions'] == 2
        assert perf_metrics['failed_actions'] == 1
        assert perf_metrics['overall_success_rate'] == 2/3
        
        print("✓ Metrics calculation validated")
        
        # Test recommendations
        recommendations = report['recommendations']
        assert isinstance(recommendations, list)
        assert len(recommendations) > 0
        
        print("✓ Recommendations generated")
        
        # Test metrics summary
        print("Testing metrics summary...")
        summary = await system.get_metrics_summary(time_window_hours=24)
        
        assert 'key_metrics' in summary
        assert 'health_status' in summary
        assert 'top_recommendations' in summary
        
        print("✓ Metrics summary validated")
        
        # Test health status determination
        health_status = system._determine_health_status(report)
        assert health_status in ['excellent', 'good', 'fair', 'poor', 'critical']
        
        print(f"✓ Health status: {health_status}")
        
        # Test JSON export
        print("Testing JSON export...")
        json_export = system.export_metrics_to_json(time_window_hours=24)
        
        # Validate JSON structure
        json_data = json.loads(json_export)
        assert 'metadata' in json_data
        assert 'performance_metrics' in json_data
        
        print("✓ JSON export validated")
        
        # Print sample report
        print("\n" + "="*50)
        print("SAMPLE METRICS REPORT")
        print("="*50)
        print(f"Source: {report['metadata']['source']}")
        print(f"Time Window: {report['metadata']['time_window_hours']} hours")
        print(f"Total Actions: {perf_metrics['total_actions']}")
        print(f"Success Rate: {perf_metrics['overall_success_rate']:.1%}")
        print(f"Health Status: {health_status}")
        print(f"Active Rules: {report['system_health']['active_rules']}")
        print(f"Actions per Hour: {perf_metrics['actions_per_hour']:.1f}")
        
        print("\nTop Recommendations:")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"{i}. [{rec['priority'].upper()}] {rec['recommendation']}")
        
        print("="*50)
        
        print("✅ All tests passed!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        return False


async def test_edge_cases():
    """Test edge cases for report_metrics method"""
    print("\nTesting edge cases...")
    
    # Test with empty action history
    system = SelfHealingSystem(source="empty_system")
    
    try:
        report = await system.report_metrics(time_window_hours=24)
        assert report['performance_metrics']['total_actions'] == 0
        assert report['performance_metrics']['overall_success_rate'] == 0
        print("✓ Empty action history handled correctly")
        
        # Test with very short time window
        report = await system.report_metrics(time_window_hours=1)
        assert 'metadata' in report
        print("✓ Short time window handled correctly")
        
        # Test with very long time window
        report = await system.report_metrics(time_window_hours=8760)  # 1 year
        assert 'metadata' in report
        print("✓ Long time window handled correctly")
        
        print("✅ Edge cases passed!")
        return True
        
    except Exception as e:
        print(f"❌ Edge case test failed: {e}")
        return False


async def main():
    """Run all tests"""
    print("Starting SelfHealingSystem.report_metrics() tests...")
    print("=" * 60)
    
    test1_passed = await test_report_metrics()
    test2_passed = await test_edge_cases()
    
    print("\n" + "=" * 60)
    if test1_passed and test2_passed:
        print("🎉 All tests passed successfully!")
    else:
        print("❌ Some tests failed")
    
    return test1_passed and test2_passed


if __name__ == "__main__":
    asyncio.run(main())
