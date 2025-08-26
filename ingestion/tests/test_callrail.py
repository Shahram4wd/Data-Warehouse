"""
Advanced CallRail CRM testing with specialized scenarios.
Tests sophisticated CallRail features, webhook handling, and complex data flows.
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from ingestion.tests.command_test_base import (
    CRMCommandTestBase, APITestMixin, PerformanceTestMixin, 
    FlagTestMixin, BatchProcessingTestMixin
)
from ingestion.tests.sync_history_validator import SyncHistoryValidator
from ingestion.tests.mock_responses import MockResponseGenerator, MockHTTPResponses


class CallRailTestBase(CRMCommandTestBase):
    """Base test class for CallRail command testing"""
    
    requires_credentials = True
    
    def setup_mock_credentials(self):
        """Setup mock CallRail API credentials"""
        self.api_key = 'mock_callrail_api_key_123'
        self.account_id = 'mock_account_456'
        
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'CALLRAIL_API_KEY': self.api_key,
            'CALLRAIL_ACCOUNT_ID': self.account_id
        })
        self.env_patcher.start()
    
    def tearDown(self):
        super().tearDown()
        if hasattr(self, 'env_patcher'):
            self.env_patcher.stop()
    
    def create_callrail_call_data(self, count=100):
        """Create mock CallRail call data"""
        calls = []
        for i in range(count):
            calls.append({
                "id": f"call_{i+1}",
                "caller_id": f"+1555200{i+1:04d}",
                "business_phone_number": "+15551234567",
                "tracking_phone_number": f"+1555300{i+1:04d}",
                "duration": 120 + i * 5,
                "start_time": (timezone.now() - timedelta(days=i)).isoformat(),
                "direction": "inbound",
                "answered": True,
                "first_call": i % 3 == 0,
                "value": "qualified" if i % 4 == 0 else "unqualified",
                "source": {
                    "name": ["Google Ads", "Facebook", "Website", "Direct"][i % 4],
                    "medium": "cpc" if i % 2 == 0 else "organic"
                },
                "lead_status": ["new", "contacted", "converted"][i % 3],
                "tags": [f"tag_{i%3+1}"],
                "recording_url": f"https://app.callrail.com/calls/{i+1}/recording"
            })
        return calls


class TestCallRailCallsAdvanced(CallRailTestBase, APITestMixin, PerformanceTestMixin, FlagTestMixin):
    """Advanced testing for CallRail calls sync command"""
    
    command_name = 'sync_callrail_calls'
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_webhook_integration_processing(self, mock_get):
        """Test webhook data integration and processing"""
        # Setup webhook-style data payload
        webhook_calls = self.create_callrail_call_data(50)
        
        # Mock successful API response
        mock_response = MockHTTPResponses.create_success_response({
            'calls': webhook_calls,
            'total_records': 50,
            'page': 1,
            'per_page': 100
        })
        mock_get.return_value = mock_response
        
        # Execute command with webhook simulation
        self.run_command_with_options(
            start_date='2024-01-01',
            end_date='2024-01-31',
            webhook_mode=True
        )
        
        # Verify API called correctly
        self.assert_api_called_with(mock_get, 'callrail.com/v3/calls')
        
        # Verify sync completed successfully
        self.assert_sync_success(50)
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_call_recording_metadata_sync(self, mock_get):
        """Test synchronization of call recording metadata"""
        calls_with_recordings = []
        for i in range(25):
            calls_with_recordings.append({
                "id": f"recorded_call_{i+1}",
                "caller_id": f"+1555100{i+1:04d}",
                "duration": 300 + i * 10,  # Longer calls with recordings
                "answered": True,
                "recording_url": f"https://app.callrail.com/calls/{i+1}/recording",
                "recording_duration": 280 + i * 10,
                "transcription_available": True,
                "transcription_text": f"Sample call transcription {i+1}"
            })
        
        mock_response = MockHTTPResponses.create_success_response({
            'calls': calls_with_recordings,
            'total_records': 25
        })
        mock_get.return_value = mock_response
        
        # Execute with recording sync enabled
        self.run_command_with_options(
            include_recordings=True,
            include_transcriptions=True
        )
        
        self.assert_sync_success(25)
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_call_attribution_data_processing(self, mock_get):
        """Test processing of complex call attribution data"""
        attributed_calls = []
        for i in range(30):
            attributed_calls.append({
                "id": f"attributed_call_{i+1}",
                "caller_id": f"+1555400{i+1:04d}",
                "attribution": {
                    "campaign": f"Campaign_{(i % 5) + 1}",
                    "source": ["google", "facebook", "bing", "direct", "referral"][i % 5],
                    "medium": ["cpc", "social", "organic", "email", "referral"][i % 5],
                    "keyword": f"keyword_{i+1}",
                    "landing_page": f"https://example.com/page{i+1}",
                    "first_touch": True if i % 3 == 0 else False,
                    "last_touch": True if i % 2 == 0 else False
                },
                "value": "qualified" if i % 4 == 0 else "unqualified",
                "revenue_amount": 1000 + i * 50 if i % 4 == 0 else None
            })
        
        mock_response = MockHTTPResponses.create_success_response({
            'calls': attributed_calls,
            'total_records': 30
        })
        mock_get.return_value = mock_response
        
        # Execute with attribution tracking
        self.run_command_with_options(
            include_attribution=True,
            revenue_tracking=True
        )
        
        self.assert_sync_success(30)


class TestCallRailFormSubmissionsAdvanced(CallRailTestBase, APITestMixin, BatchProcessingTestMixin):
    """Advanced testing for CallRail form submissions"""
    
    command_name = 'sync_callrail_form_submissions'
    
    @patch('ingestion.management.commands.sync_callrail_form_submissions.requests.get')
    def test_form_field_mapping_validation(self, mock_get):
        """Test validation of form field mappings"""
        form_submissions = []
        for i in range(40):
            form_submissions.append({
                "id": f"form_{i+1}",
                "submitted_at": (timezone.now() - timedelta(hours=i)).isoformat(),
                "form_name": f"Contact Form {(i % 3) + 1}",
                "form_fields": {
                    "name": f"Lead Name {i+1}",
                    "email": f"lead{i+1}@example.com",
                    "phone": f"+1555500{i+1:04d}",
                    "message": f"Form message {i+1}",
                    "custom_field_1": f"Custom value {i+1}",
                    "custom_field_2": ["Option A", "Option B", "Option C"][i % 3]
                },
                "source_url": f"https://example.com/form-page-{i+1}",
                "ip_address": f"192.168.1.{i+1}",
                "user_agent": "Mozilla/5.0 (compatible test agent)"
            })
        
        mock_response = MockHTTPResponses.create_success_response({
            'form_submissions': form_submissions,
            'total_records': 40
        })
        mock_get.return_value = mock_response
        
        # Execute with field validation
        self.run_command_with_options(
            validate_fields=True,
            field_mapping='custom'
        )
        
        self.assert_sync_success(40)


class TestCallRailTextMessagesAdvanced(CallRailTestBase, APITestMixin):
    """Advanced testing for CallRail text messages"""
    
    command_name = 'sync_callrail_text_messages'
    
    @patch('ingestion.management.commands.sync_callrail_text_messages.requests.get')
    def test_message_thread_continuity(self, mock_get):
        """Test text message thread continuity and conversation tracking"""
        message_threads = []
        
        # Create conversational threads
        for thread_id in range(10):
            for msg_num in range(5):  # 5 messages per thread
                message_threads.append({
                    "id": f"msg_{thread_id}_{msg_num}",
                    "thread_id": f"thread_{thread_id}",
                    "message": f"Message {msg_num + 1} in thread {thread_id}",
                    "direction": "inbound" if msg_num % 2 == 0 else "outbound",
                    "from_number": f"+1555600{thread_id:04d}",
                    "to_number": "+15551234567",
                    "created_at": (timezone.now() - timedelta(minutes=thread_id*10 + msg_num)).isoformat(),
                    "status": "delivered",
                    "conversation_starter": True if msg_num == 0 else False
                })
        
        mock_response = MockHTTPResponses.create_success_response({
            'text_messages': message_threads,
            'total_records': 50
        })
        mock_get.return_value = mock_response
        
        # Execute with thread tracking
        self.run_command_with_options(
            track_threads=True,
            conversation_analysis=True
        )
        
        self.assert_sync_success(50)


class TestCallRailAccountsAdvanced(CallRailTestBase, APITestMixin):
    """Advanced testing for CallRail accounts"""
    
    command_name = 'sync_callrail_accounts'
    
    @patch('ingestion.management.commands.sync_callrail_accounts.requests.get')
    def test_multi_account_hierarchy_sync(self, mock_get):
        """Test synchronization of multi-account hierarchy"""
        accounts = []
        for i in range(15):
            accounts.append({
                "id": f"account_{i+1}",
                "name": f"Account {i+1}",
                "status": ["active", "inactive", "trial"][i % 3],
                "plan": ["basic", "professional", "enterprise"][i % 3],
                "created_at": "2024-01-01T00:00:00Z",
                "timezone": "America/New_York",
                "parent_account_id": f"parent_{i//5 + 1}" if i >= 5 else None,  # Create hierarchy
                "child_accounts": [f"child_{i}_{j}" for j in range(2)] if i % 3 == 0 else [],
                "settings": {
                    "call_recording_enabled": True,
                    "transcription_enabled": i % 2 == 0,
                    "webhook_urls": [f"https://webhook{i}.example.com"]
                }
            })
        
        mock_response = MockHTTPResponses.create_success_response({
            'accounts': accounts,
            'total_records': 15
        })
        mock_get.return_value = mock_response
        
        # Execute with hierarchy processing
        self.run_command_with_options(
            include_hierarchy=True,
            process_children=True
        )
        
        self.assert_sync_success(15)


class TestCallRailRateLimitingRecovery(CallRailTestBase):
    """Test CallRail rate limiting and recovery mechanisms"""
    
    command_name = 'sync_callrail_calls'
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_rate_limit_handling_with_exponential_backoff(self, mock_get):
        """Test rate limit handling with exponential backoff"""
        # Simulate rate limiting scenario
        responses = []
        
        # First few successful calls
        for i in range(3):
            responses.append(MockHTTPResponses.create_success_response({
                'calls': self.create_callrail_call_data(10),
                'total_records': 10
            }))
        
        # Rate limit responses
        for i in range(2):
            responses.append(MockHTTPResponses.create_rate_limit_response())
        
        # Recovery responses
        for i in range(3):
            responses.append(MockHTTPResponses.create_success_response({
                'calls': self.create_callrail_call_data(10),
                'total_records': 10
            }))
        
        mock_get.side_effect = responses
        
        # Execute with rate limit handling
        self.run_command_with_options(
            retry_on_rate_limit=True,
            max_retries=5,
            backoff_factor=2
        )
        
        # Should eventually succeed after rate limit recovery
        self.assert_sync_success()


class TestCallRailPerformanceOptimization(CallRailTestBase, PerformanceTestMixin):
    """Test CallRail performance optimization features"""
    
    command_name = 'sync_callrail_calls'
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_concurrent_api_processing(self, mock_get):
        """Test concurrent API request processing"""
        # Setup large dataset response
        large_dataset = self.create_callrail_call_data(500)
        
        mock_response = MockHTTPResponses.create_success_response({
            'calls': large_dataset,
            'total_records': 500
        })
        mock_get.return_value = mock_response
        
        # Execute with concurrency enabled
        self.run_command_with_options(
            concurrent_requests=True,
            max_workers=5,
            batch_size=100
        )
        
        # Verify performance within acceptable limits
        self.assert_execution_time_under(60)  # Should complete within 1 minute
        self.assert_sync_success(500)
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_memory_efficient_large_dataset_processing(self, mock_get):
        """Test memory-efficient processing of large datasets"""
        # Simulate very large dataset with pagination
        mock_responses = []
        for page in range(10):  # 10 pages of 100 records each
            page_data = self.create_callrail_call_data(100)
            mock_responses.append(MockHTTPResponses.create_success_response({
                'calls': page_data,
                'total_records': 1000,
                'page': page + 1,
                'per_page': 100,
                'has_next': page < 9
            }))
        
        mock_get.side_effect = mock_responses
        
        # Execute with memory optimization
        self.run_command_with_options(
            streaming_mode=True,
            memory_limit_mb=50,
            batch_size=100
        )
        
        self.assert_sync_success(1000)
        self.assert_memory_usage_reasonable(100)  # Under 100MB


class TestCallRailDataQualityValidation(CallRailTestBase):
    """Test CallRail data quality validation"""
    
    command_name = 'sync_callrail_calls'
    
    @patch('ingestion.management.commands.sync_callrail_calls.requests.get')
    def test_data_consistency_validation(self, mock_get):
        """Test validation of data consistency across sync operations"""
        # Create data with intentional inconsistencies for testing
        calls_with_issues = []
        for i in range(50):
            call_data = {
                "id": f"call_{i+1}",
                "caller_id": f"+1555700{i+1:04d}",
                "duration": 120 + i * 5,
                "start_time": (timezone.now() - timedelta(hours=i)).isoformat(),
                "answered": True,
            }
            
            # Add some data quality issues to test validation
            if i % 10 == 0:  # Every 10th record has issues
                call_data["caller_id"] = "INVALID_PHONE"  # Invalid phone format
            elif i % 15 == 0:  # Every 15th record
                call_data["duration"] = -30  # Negative duration
            elif i % 20 == 0:  # Every 20th record
                call_data["start_time"] = "invalid_date"  # Invalid date
            
            calls_with_issues.append(call_data)
        
        mock_response = MockHTTPResponses.create_success_response({
            'calls': calls_with_issues,
            'total_records': 50
        })
        mock_get.return_value = mock_response
        
        # Execute with data validation enabled
        self.run_command_with_options(
            validate_data_quality=True,
            skip_invalid_records=True,
            log_validation_errors=True
        )
        
        # Should succeed but with some records skipped due to validation
        sync_record = self.assert_sync_success()
        
        # Verify validation results are logged
        self.assertIn('validation_errors', sync_record.log_data)
        self.assertGreater(len(sync_record.log_data['validation_errors']), 0)


class TestCallRailSyncHistoryValidation(CallRailTestBase):
    """Test sync history validation for CallRail operations"""
    
    def test_callrail_sync_pattern_validation(self):
        """Test CallRail-specific sync patterns"""
        validator = SyncHistoryValidator('sync_callrail_calls')
        
        # Create multiple sync records
        for i in range(5):
            self.create_sync_history(
                status='SUCCESS' if i < 4 else 'FAILED',
                records_processed=100 + i * 10
            )
        
        # Generate validation report
        report = validator.generate_comprehensive_report(24)
        
        # Verify CallRail-specific validations
        self.assertTrue(report['overall_valid'])
        self.assertEqual(report['summary']['total_syncs'], 5)
        self.assertEqual(report['summary']['success_rate'], 0.8)  # 4/5 success rate
        
        # Test CallRail-specific patterns
        from ingestion.tests.sync_history_validator import CRMSyncPatterns
        webhook_pattern = CRMSyncPatterns.webhook_crm_pattern()
        
        self.assertEqual(webhook_pattern['expected_duration_range'], (5, 120))
        self.assertEqual(webhook_pattern['acceptable_failure_rate'], 0.15)
        self.assertIn('webhook_url', webhook_pattern['required_log_fields'])
