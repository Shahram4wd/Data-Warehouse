"""
Base infrastructure for CRM command testing.
Provides common testing patterns and utilities for all CRM systems.
"""

import json
import os
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from django.conf import settings
from ingestion.models import SyncHistory, SyncConfiguration
# from reports.models import AutomationReportSchedule  # TODO: Add when model is implemented


class CRMCommandTestBase(TestCase):
    """
    Base test class for all CRM command testing.
    Provides common setup, teardown, and utility methods.
    """
    
    # Class-level configuration
    command_name = None  # Must be overridden by subclasses
    default_options = {}  # Default command options
    requires_credentials = True
    
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.command_name is None:
            raise ValueError(f"{cls.__name__} must define command_name")
    
    def setUp(self):
        """Common setup for all CRM command tests"""
        # Clear any existing sync records
        SyncHistory.objects.all().delete()
        SyncConfiguration.objects.all().delete()
        
        # Create test sync configuration
        self.sync_config = SyncConfiguration.objects.create(
            command_name=self.command_name,
            is_active=True,
            configuration={
                "batch_size": 100,
                "max_records": 1000,
                "timeout": 30
            }
        )
        
        # Mock credentials if required
        if self.requires_credentials:
            self.setup_mock_credentials()
    
    def setup_mock_credentials(self):
        """Setup mock credentials for testing"""
        # Base credential mocking - can be overridden by subclasses
        pass
    
    def create_sync_history(self, status='SUCCESS', records_processed=50):
        """Create a test sync history record"""
        return SyncHistory.objects.create(
            command_name=self.command_name,
            status=status,
            records_processed=records_processed,
            start_time=datetime.now() - timedelta(minutes=5),
            end_time=datetime.now(),
            log_data={'test': True}
        )
    
    def assert_sync_success(self, records_expected=None):
        """Assert that sync completed successfully"""
        sync_record = SyncHistory.objects.filter(
            command_name=self.command_name
        ).latest('start_time')
        
        self.assertEqual(sync_record.status, 'SUCCESS')
        if records_expected:
            self.assertEqual(sync_record.records_processed, records_expected)
    
    def assert_sync_failure(self, error_message=None):
        """Assert that sync failed as expected"""
        sync_record = SyncHistory.objects.filter(
            command_name=self.command_name
        ).latest('start_time')
        
        self.assertEqual(sync_record.status, 'FAILED')
        if error_message:
            self.assertIn(error_message, str(sync_record.error_details))
    
    def run_command_with_options(self, **options):
        """Run the command with given options"""
        merged_options = {**self.default_options, **options}
        return call_command(self.command_name, **merged_options)
    
    def mock_api_success_response(self, data=None):
        """Create a mock successful API response"""
        return Mock(
            status_code=200,
            json=Mock(return_value=data or {'results': []}),
            raise_for_status=Mock()
        )
    
    def mock_api_error_response(self, status_code=400, error_msg="API Error"):
        """Create a mock error API response"""
        response = Mock(status_code=status_code)
        response.raise_for_status.side_effect = Exception(error_msg)
        return response


class APITestMixin:
    """Mixin for testing API-based CRM commands"""
    
    def assert_api_called_with(self, mock_request, url_pattern, method='GET'):
        """Assert that API was called with expected parameters"""
        mock_request.assert_called()
        call_args = mock_request.call_args
        
        if method == 'GET':
            self.assertIn(url_pattern, str(call_args))
        else:
            # For POST/PUT requests, check method
            self.assertEqual(call_args.kwargs.get('method', 'GET'), method)
    
    def setup_api_success_scenario(self, mock_request, response_data):
        """Setup mock for successful API scenario"""
        mock_request.return_value = self.mock_api_success_response(response_data)
    
    def setup_api_error_scenario(self, mock_request, status_code=500):
        """Setup mock for API error scenario"""
        mock_request.return_value = self.mock_api_error_response(status_code)


class DatabaseTestMixin:
    """Mixin for testing database-based CRM commands"""
    
    def setup_mock_database_connection(self):
        """Setup mock database connection"""
        self.mock_connection = Mock()
        self.mock_cursor = Mock()
        self.mock_connection.cursor.return_value = self.mock_cursor
    
    def setup_database_success_scenario(self, result_data):
        """Setup mock for successful database query"""
        self.mock_cursor.fetchall.return_value = result_data
        self.mock_cursor.description = [
            ('id',), ('name',), ('email',), ('created_date',)
        ]
    
    def setup_database_error_scenario(self, error_msg="Database error"):
        """Setup mock for database error"""
        self.mock_cursor.execute.side_effect = Exception(error_msg)


class PerformanceTestMixin:
    """Mixin for testing command performance"""
    
    def assert_execution_time_under(self, max_seconds=30):
        """Assert that command executed within time limit"""
        sync_record = SyncHistory.objects.filter(
            command_name=self.command_name
        ).latest('start_time')
        
        execution_time = (sync_record.end_time - sync_record.start_time).total_seconds()
        self.assertLess(execution_time, max_seconds)
    
    def assert_memory_usage_reasonable(self, max_mb=100):
        """Assert that memory usage is reasonable (placeholder for now)"""
        # This would need actual memory profiling implementation
        pass


class BatchProcessingTestMixin:
    """Mixin for testing batch processing capabilities"""
    
    def test_batch_size_respected(self, mock_api_call, expected_calls=2):
        """Test that batch size limits are respected"""
        # Run command with small batch size
        self.run_command_with_options(batch_size=50)
        
        # Verify multiple API calls were made
        self.assertEqual(mock_api_call.call_count, expected_calls)
    
    def test_max_records_limit(self, mock_api_call):
        """Test that max records limit is enforced"""
        self.run_command_with_options(max_records=10)
        
        # Verify sync history shows correct record count
        sync_record = SyncHistory.objects.latest('start_time')
        self.assertLessEqual(sync_record.records_processed, 10)


class FlagTestMixin:
    """Mixin for testing command flags and options"""
    
    def test_dry_run_flag(self):
        """Test that dry run flag prevents actual changes"""
        initial_count = SyncHistory.objects.count()
        
        self.run_command_with_options(dry_run=True)
        
        # Sync history should still be created but marked as dry run
        new_count = SyncHistory.objects.count()
        self.assertEqual(new_count, initial_count + 1)
        
        sync_record = SyncHistory.objects.latest('start_time')
        self.assertTrue(sync_record.log_data.get('dry_run', False))
    
    def test_debug_flag(self):
        """Test that debug flag increases logging detail"""
        self.run_command_with_options(debug=True)
        
        sync_record = SyncHistory.objects.latest('start_time')
        # Debug runs should have more detailed logs
        self.assertGreater(len(str(sync_record.log_data)), 100)
    
    def test_force_flag(self):
        """Test that force flag overrides safety checks"""
        # Create recent sync to test force override
        self.create_sync_history(status='SUCCESS')
        
        # Should work with force flag
        self.run_command_with_options(force=True)
        
        # Should have two sync records now
        self.assertEqual(SyncHistory.objects.count(), 2)


class TestCRMCommandTestBase(TestCase):
    """Tests for the base test infrastructure itself"""
    
    def test_command_test_base_requires_command_name(self):
        """Test that subclasses must define command_name"""
        with self.assertRaises(ValueError):
            class TestCommand(CRMCommandTestBase):
                pass
            TestCommand.setUpClass()
    
    def test_sync_history_creation(self):
        """Test sync history helper method"""
        class TestCommand(CRMCommandTestBase):
            command_name = 'test_command'
        
        test_instance = TestCommand()
        test_instance.setUp()
        
        sync_record = test_instance.create_sync_history()
        self.assertEqual(sync_record.command_name, 'test_command')
        self.assertEqual(sync_record.status, 'SUCCESS')
    
    def test_mock_responses(self):
        """Test mock response helpers"""
        class TestCommand(CRMCommandTestBase):
            command_name = 'test_command'
        
        test_instance = TestCommand()
        
        # Test success response
        success_response = test_instance.mock_api_success_response({'test': True})
        self.assertEqual(success_response.status_code, 200)
        self.assertEqual(success_response.json()['test'], True)
        
        # Test error response
        error_response = test_instance.mock_api_error_response(404, "Not Found")
        self.assertEqual(error_response.status_code, 404)
        with self.assertRaises(Exception):
            error_response.raise_for_status()
