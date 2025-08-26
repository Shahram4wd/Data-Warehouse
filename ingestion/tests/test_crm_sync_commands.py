"""
Tests for standardized CRM sync commands using BaseSyncCommand
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import sys
from datetime import datetime, timedelta
import asyncio

from ingestion.management.commands.sync_five9_contacts import Command as Five9Command
from ingestion.management.commands.sync_marketsharp_data import Command as MarketSharpCommand  
from ingestion.management.commands.sync_leadconduit_leads import Command as LeadConduitCommand
from ingestion.management.commands.sync_leadconduit_all import Command as LeadConduitAllCommand
from ingestion.management.commands.sync_gsheet_marketing_leads import Command as GSheetMarketingLeadsCommand


class TestFive9SyncCommand(TestCase):
    """Test Five9 contacts sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = Five9Command()
        self.mock_sync_engine = Mock()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync Five9 contacts data')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_argument_parsing(self):
        """Unit Test: Command argument parsing"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify standard flags are added
        expected_calls = [
            ('--full',), ('--force',), ('--start-date',), ('--end-date',),
            ('--dry-run',), ('--batch-size',), ('--max-records',), ('--debug',), ('--config',)
        ]
        
        for expected_arg in expected_calls:
            self.assertTrue(
                any(call[0][0] == expected_arg[0] for call in parser.add_argument.call_args_list),
                f"Expected argument {expected_arg[0]} not found"
            )
            
    @patch('ingestion.management.commands.sync_five9_contacts.Five9ContactsSyncEngine')
    @patch('ingestion.management.commands.sync_five9_contacts.Five9Config')
    def test_integration_dry_run(self, mock_config, mock_engine_class):
        """Integration Test: Dry run execution"""
        # Setup mocks
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        mock_engine = Mock()
        mock_engine.sync_data.return_value = {'success': True, 'records_processed': 0}
        mock_engine_class.return_value = mock_engine
        
        # Capture output
        out = StringIO()
        
        # Execute dry run
        call_command('sync_five9_contacts', '--dry-run', stdout=out)
        
        # Verify dry run was passed to config
        mock_config.get_config.assert_called_once()
        config_call_args = mock_config.get_config.call_args[0]
        self.assertEqual(config_call_args[0], 'default')
        
    @patch('ingestion.management.commands.sync_five9_contacts.Five9ContactsSyncEngine')  
    @patch('ingestion.management.commands.sync_five9_contacts.Five9Config')
    def test_e2e_limited_records(self, mock_config, mock_engine_class):
        """E2E Test: Limited records sync"""
        # Setup mocks for safe testing
        mock_config.get_config.return_value = {
            'api_key': 'test_key',
            'max_records': 5,
            'dry_run': True
        }
        
        mock_engine = Mock()
        mock_engine.sync_data.return_value = {
            'success': True, 
            'records_processed': 5,
            'records_created': 5,
            'records_updated': 0,
            'sync_duration': timedelta(seconds=10)
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with record limit
        out = StringIO()
        call_command('sync_five9_contacts', '--max-records', '5', '--dry-run', stdout=out)
        
        # Verify execution completed successfully
        output = out.getvalue()
        self.assertIn('Starting Five9', output)


class TestMarketSharpSyncCommand(TestCase):
    """Test MarketSharp data sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = MarketSharpCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync MarketSharp data from multiple endpoints')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_argument_parsing(self):
        """Unit Test: Command argument parsing with async support"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify standard flags plus MarketSharp-specific ones
        expected_calls = [
            ('--full',), ('--force',), ('--start-date',), ('--end-date',),
            ('--dry-run',), ('--batch-size',), ('--max-records',), ('--debug',), ('--config',),
            ('--endpoints',)  # MarketSharp specific
        ]
        
        for expected_arg in expected_calls:
            self.assertTrue(
                any(call[0][0] == expected_arg[0] for call in parser.add_argument.call_args_list),
                f"Expected argument {expected_arg[0]} not found"
            )
            
    @patch('ingestion.management.commands.sync_marketsharp_data.MarketSharpDataSyncEngine')
    @patch('ingestion.management.commands.sync_marketsharp_data.MarketSharpConfig')
    def test_integration_async_execution(self, mock_config, mock_engine_class):
        """Integration Test: Async execution with dry run"""
        # Setup async mocks
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        
        mock_engine = Mock()
        # Create a proper async mock
        async_result = asyncio.Future()
        async_result.set_result({'success': True, 'records_processed': 0})
        mock_engine.sync_data_async.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Execute dry run
        out = StringIO()
        call_command('sync_marketsharp_data', '--dry-run', stdout=out)
        
        # Verify async execution was called
        mock_engine.sync_data_async.assert_called_once()
        
    @patch('ingestion.management.commands.sync_marketsharp_data.MarketSharpDataSyncEngine')
    @patch('ingestion.management.commands.sync_marketsharp_data.MarketSharpConfig') 
    def test_e2e_endpoint_filtering(self, mock_config, mock_engine_class):
        """E2E Test: Endpoint filtering functionality"""
        # Setup mocks
        mock_config.get_config.return_value = {
            'api_key': 'test_key',
            'endpoints': ['leads', 'contacts'],
            'dry_run': True
        }
        
        mock_engine = Mock() 
        async_result = asyncio.Future()
        async_result.set_result({
            'success': True,
            'records_processed': 10,
            'endpoints_synced': ['leads', 'contacts'],
            'sync_duration': timedelta(seconds=15)
        })
        mock_engine.sync_data_async.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Execute with specific endpoints
        out = StringIO()
        call_command('sync_marketsharp_data', '--endpoints', 'leads,contacts', '--dry-run', stdout=out)
        
        # Verify execution completed
        output = out.getvalue()
        self.assertIn('Starting MarketSharp', output)


class TestLeadConduitSyncCommand(TestCase):
    """Test LeadConduit leads sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = LeadConduitCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync LeadConduit leads data with backward compatibility')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_backward_compatibility_flags(self):
        """Unit Test: Backward compatibility argument parsing"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify both old and new flags are supported
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # New standard flags
        self.assertIn('--start-date', argument_calls)
        self.assertIn('--force', argument_calls)
        
        # Deprecated flags for backward compatibility  
        self.assertIn('--since', argument_calls)
        self.assertIn('--force-overwrite', argument_calls)
        
    @patch('ingestion.management.commands.sync_leadconduit_leads.LeadConduitLeadsSyncEngine')
    @patch('ingestion.management.commands.sync_leadconduit_leads.LeadConduitConfig')
    def test_integration_backward_compatibility(self, mock_config, mock_engine_class):
        """Integration Test: Backward compatibility execution"""
        # Setup mocks
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        mock_engine = Mock()
        mock_engine.sync_data.return_value = {'success': True, 'records_processed': 0}
        mock_engine_class.return_value = mock_engine
        
        # Test deprecated --since flag (should show warning)
        out = StringIO()
        err = StringIO()
        call_command('sync_leadconduit_leads', '--since', '2024-01-01', '--dry-run', 
                    stdout=out, stderr=err)
        
        output = out.getvalue()
        self.assertIn('--since is deprecated', output)
        
    @patch('ingestion.management.commands.sync_leadconduit_leads.LeadConduitLeadsSyncEngine')
    @patch('ingestion.management.commands.sync_leadconduit_leads.LeadConduitConfig')
    def test_e2e_standardized_execution(self, mock_config, mock_engine_class):
        """E2E Test: Full execution with new standardized flags"""
        # Setup mocks for safe testing
        mock_config.get_config.return_value = {
            'api_key': 'test_key', 
            'max_records': 3,
            'dry_run': True
        }
        
        mock_engine = Mock()
        mock_engine.sync_data.return_value = {
            'success': True,
            'records_processed': 3,
            'records_created': 2,
            'records_updated': 1,
            'sync_duration': timedelta(seconds=8)
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with new standardized flags
        out = StringIO()
        call_command('sync_leadconduit_leads', '--start-date', '2024-01-15', 
                    '--force', '--max-records', '3', '--dry-run', stdout=out)
        
        # Verify successful execution
        output = out.getvalue()
        self.assertIn('Starting LeadConduit', output)


class TestLeadConduitAllSyncCommand(TestCase):
    """Test LeadConduit all data sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = LeadConduitAllCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync all LeadConduit data (events and leads) with standardized flags')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_backward_compatibility_flags(self):
        """Unit Test: Backward compatibility argument parsing"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify both old and new flags are supported
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # New standard flags
        self.assertIn('--start-date', argument_calls)
        self.assertIn('--force', argument_calls)
        
        # Deprecated flags for backward compatibility  
        self.assertIn('--since', argument_calls)
        self.assertIn('--force-overwrite', argument_calls)
        
    @patch('ingestion.management.commands.sync_leadconduit_all.LeadConduitSyncEngine')
    @patch('ingestion.management.commands.sync_leadconduit_all.LeadConduitConfig')
    def test_integration_comprehensive_sync(self, mock_config, mock_engine_class):
        """Integration Test: Comprehensive all-data sync execution"""
        # Setup mocks
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        mock_engine = Mock()
        
        # Mock async result for all data sync
        async_result = asyncio.Future()
        async_result.set_result({
            'success': True, 
            'entity_results': {
                'leads': {'records_processed': 5},
                'events': {'records_processed': 3}
            },
            'total_duration': 12.5
        })
        mock_engine.sync_all.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Execute comprehensive sync with dry run
        out = StringIO()
        call_command('sync_leadconduit_all', '--dry-run', '--max-records', '8', stdout=out)
        
        # Verify all data sync was called
        mock_engine.sync_all.assert_called_once()
        
    @patch('ingestion.management.commands.sync_leadconduit_all.LeadConduitSyncEngine')
    @patch('ingestion.management.commands.sync_leadconduit_all.LeadConduitConfig')
    def test_e2e_full_standardized_sync(self, mock_config, mock_engine_class):
        """E2E Test: Full execution with all standardized flags"""
        # Setup mocks for comprehensive testing
        mock_config.get_config.return_value = {
            'api_key': 'test_key', 
            'max_records': 10,
            'dry_run': True
        }
        
        mock_engine = Mock()
        
        # Create async result future
        async_result = asyncio.Future()
        async_result.set_result({
            'success': True,
            'entity_results': {
                'leads': {'records_processed': 6, 'records_created': 4, 'records_updated': 2},
                'events': {'records_processed': 4, 'records_created': 3, 'records_updated': 1}
            },
            'total_duration': 18.2
        })
        mock_engine.sync_all.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Execute with all new standardized flags
        out = StringIO()
        call_command('sync_leadconduit_all', '--start-date', '2024-01-10', 
                    '--force', '--full', '--max-records', '10', '--dry-run', stdout=out)
        
        # Verify successful comprehensive execution
        output = out.getvalue()
        self.assertIn('Starting LeadConduit full sync', output)


class TestGSheetMarketingLeadsSyncCommand(TestCase):
    """Test GSheet marketing leads sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetMarketingLeadsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync Marketing Source Leads from Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'marketing_leads')
        
    def test_unit_argument_parsing(self):
        """Unit Test: Command argument parsing with GSheet-specific flags"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify standard flags plus GSheet-specific ones
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Standard flags
        self.assertIn('--full', argument_calls)
        self.assertIn('--force', argument_calls)
        self.assertIn('--start-date', argument_calls)
        self.assertIn('--dry-run', argument_calls)
        self.assertIn('--batch-size', argument_calls)
        
        # GSheet-specific flags
        self.assertIn('--test-connection', argument_calls)
        self.assertIn('--show-summary', argument_calls)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_leads.MarketingLeadsSyncEngine')
    def test_integration_connection_test(self, mock_engine_class):
        """Integration Test: Google Sheets API connection test"""
        # Setup mocks
        mock_engine = Mock()
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_engine.client = mock_client
        mock_engine_class.return_value = mock_engine
        
        # Test connection only
        out = StringIO()
        call_command('sync_gsheet_marketing_leads', '--test-connection', stdout=out)
        
        # Verify connection test was called
        mock_client.test_connection.assert_called_once()
        output = out.getvalue()
        self.assertIn('Google Sheets API connection successful', output)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_leads.MarketingLeadsSyncEngine')
    def test_e2e_standardized_sync(self, mock_engine_class):
        """E2E Test: Full sync with standardized flags and GSheet functionality"""
        # Setup mocks for safe testing
        mock_engine = Mock()
        mock_engine.sync_with_retry_sync.return_value = {
            'status': 'success',
            'success': True,
            'records_processed': 150,
            'records_created': 120,
            'records_updated': 30,
            'records_failed': 0,
            'sheet_info': {
                'name': 'Marketing Leads Test Sheet',
                'estimated_data_rows': 150
            },
            'duration': 25.7
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with standardized flags
        out = StringIO()
        call_command('sync_gsheet_marketing_leads', '--force', '--dry-run', 
                    '--max-records', '150', '--batch-size', '50', stdout=out)
        
        # Verify engine was initialized with correct parameters
        mock_engine_class.assert_called_once_with(
            batch_size=50,
            dry_run=True,
            force_overwrite=True,
            max_records=150
        )
        
        # Verify sync execution
        mock_engine.sync_with_retry_sync.assert_called_once_with(max_retries=2)
        
        # Verify output
        output = out.getvalue()
        self.assertIn('Starting GSheet marketing leads sync', output)
        self.assertIn('Marketing Leads sync completed successfully', output)


if __name__ == '__main__':
    unittest.main()
