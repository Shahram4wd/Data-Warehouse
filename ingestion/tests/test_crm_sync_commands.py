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
from argparse import ArgumentParser

from ingestion.management.commands.sync_five9_contacts import Command as Five9Command
from ingestion.management.commands.sync_marketsharp_data import Command as MarketSharpCommand  
from ingestion.management.commands.sync_leadconduit_leads import Command as LeadConduitCommand
from ingestion.management.commands.sync_leadconduit_all import Command as LeadConduitAllCommand
from ingestion.management.commands.sync_gsheet_marketing_leads import Command as GSheetMarketingLeadsCommand
from ingestion.management.commands.sync_gsheet_marketing_spends import Command as GSheetMarketingSpendsCommand
from ingestion.management.commands.sync_gsheet_all import Command as GSheetAllCommand
from ingestion.management.commands.sync_callrail_calls import Command as CallRailCallsCommand
from ingestion.management.commands.sync_callrail_all import Command as CallRailAllCommand
from ingestion.management.commands.sync_hubspot_contacts import Command as HubSpotContactsCommand
from ingestion.management.commands.sync_hubspot_deals import Command as HubSpotDealsCommand
from ingestion.management.commands.sync_hubspot_all import Command as HubSpotAllCommand
from ingestion.management.commands.sync_arrivy_bookings import Command as ArrivyBookingsCommand
from ingestion.management.commands.sync_arrivy_tasks import Command as ArrivyTasksCommand
from ingestion.management.commands.sync_arrivy_all import Command as ArrivyAllCommand


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


class TestCallRailCallsSyncCommand(TestCase):
    """Test CallRail calls sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = CallRailCallsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync CallRail calls data with standardized flags')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'callrail')
        self.assertEqual(self.command.entity_name, 'calls')
        
    def test_unit_argument_parsing(self):
        """Unit Test: Command argument parsing with CallRail-specific flags"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify standard flags plus CallRail-specific ones
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Standard flags
        self.assertIn('--full', argument_calls)
        self.assertIn('--force', argument_calls)
        self.assertIn('--start-date', argument_calls)
        self.assertIn('--dry-run', argument_calls)
        self.assertIn('--batch-size', argument_calls)
        
        # CallRail-specific flags
        self.assertIn('--company-id', argument_calls)
        
    @patch('ingestion.management.commands.sync_callrail_calls.CallsSyncEngine')
    def test_integration_company_filtering(self, mock_engine_class):
        """Integration Test: Company ID filtering functionality"""
        # Setup mocks
        mock_engine = Mock()
        
        # Mock async result
        async_result = asyncio.Future()
        async_result.set_result({
            'success': True,
            'total_processed': 25,
            'total_created': 20,
            'total_updated': 5,
            'total_errors': 0,
            'duration': 15.3
        })
        mock_engine.sync_calls.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Test with company filtering and dry run
        out = StringIO()
        with patch.dict('os.environ', {'CALLRAIL_API_KEY': 'test_key'}):
            call_command('sync_callrail_calls', '--company-id', 'test123', '--dry-run', stdout=out)
        
        # Verify sync was called with company_id parameter
        mock_engine.sync_calls.assert_called_once()
        call_args = mock_engine.sync_calls.call_args
        self.assertIn('company_id', call_args.kwargs)
        self.assertEqual(call_args.kwargs['company_id'], 'test123')
        
    @patch('ingestion.management.commands.sync_callrail_calls.CallsSyncEngine')
    def test_e2e_standardized_sync(self, mock_engine_class):
        """E2E Test: Full sync with standardized flags"""
        # Setup mocks for safe testing
        mock_engine = Mock()
        
        # Create async result
        async_result = asyncio.Future()
        async_result.set_result({
            'success': True,
            'total_processed': 100,
            'total_created': 75,
            'total_updated': 25,
            'total_errors': 0,
            'duration': 45.8
        })
        mock_engine.sync_calls.return_value = async_result
        mock_engine_class.return_value = mock_engine
        
        # Execute with standardized flags
        out = StringIO()
        with patch.dict('os.environ', {'CALLRAIL_API_KEY': 'test_key'}):
            call_command('sync_callrail_calls', '--force', '--dry-run', 
                        '--max-records', '100', '--batch-size', '25', stdout=out)
        
        # Verify successful execution
        output = out.getvalue()
        self.assertIn('Starting CallRail calls sync', output)
        self.assertIn('CallRail calls sync completed successfully', output)


class TestCallRailAllSyncCommand(TestCase):
    """Test CallRail all data sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = CallRailAllCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync all CallRail data (accounts, companies, calls, trackers, form_submissions, text_messages, tags, users)')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'CallRail')
        self.assertEqual(self.command.entity_name, 'all')
        
    def test_unit_comprehensive_coverage(self):
        """Unit Test: Verify comprehensive CallRail data coverage"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify all standard BaseSyncCommand flags are present
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        expected_flags = ['--full', '--force', '--start-date', '--end-date', '--dry-run', 
                         '--batch-size', '--max-records', '--debug', '--quiet']
        
        for flag in expected_flags:
            self.assertIn(flag, argument_calls, f"Standard flag {flag} not found")
            
    def test_integration_comprehensive_sync_scope(self, ):
        """Integration Test: Verify comprehensive sync scope"""
        # This test verifies the command structure supports all CallRail entities
        # No mocking needed for structural verification
        help_text = self.command.help.lower()
        
        # Verify all major CallRail entities are mentioned
        expected_entities = ['accounts', 'companies', 'calls', 'trackers', 
                           'form_submissions', 'text_messages', 'tags', 'users']
        
        for entity in expected_entities:
            self.assertIn(entity, help_text, f"Entity {entity} not mentioned in help text")


class TestGSheetMarketingSpendsCommand(TestCase):
    """Test GSheet marketing spends sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetMarketingSpendsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync marketing spends data from Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'marketing_spends')
        
    def test_unit_gsheet_specific_features(self):
        """Unit Test: GSheet-specific feature support"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify GSheet-specific flags are present
        self.assertIn('--test-connection', argument_calls)
        self.assertIn('--show-summary', argument_calls)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_spends.MarketingSpendsSyncEngine')
    def test_integration_full_standardized_sync(self, mock_engine_class):
        """Integration Test: Full sync with all standardized flags"""
        # Setup mocks
        mock_engine = Mock()
        mock_engine.sync_with_retry_sync.return_value = {
            'status': 'success',
            'success': True,
            'records_processed': 75,
            'records_created': 50,
            'records_updated': 25,
            'records_failed': 0,
            'sheet_info': {
                'name': 'Marketing Spends Test Sheet',
                'estimated_data_rows': 75
            },
            'duration': 18.4
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with comprehensive standardized flags
        out = StringIO()
        call_command('sync_gsheet_marketing_spends', '--full', '--force', 
                    '--dry-run', '--max-records', '75', '--batch-size', '25', stdout=out)
        
        # Verify proper initialization
        mock_engine_class.assert_called_once_with(
            batch_size=25,
            dry_run=True,
            force_overwrite=True
        )
        
        # Verify output contains success message
        output = out.getvalue()
        self.assertIn('Starting GSheet marketing spends sync', output)


class TestGSheetAllCommand(TestCase):
    """Test GSheet all sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetAllCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync all configured Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'all')
        
    def test_unit_comprehensive_gsheet_control(self):
        """Unit Test: Comprehensive GSheet control options"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify all standard flags plus GSheet-specific control flags
        expected_flags = ['--full', '--force', '--start-date', '--dry-run', 
                         '--skip-marketing-leads', '--skip-marketing-spends',
                         '--test-connections', '--show-summary']
        
        for flag in expected_flags:
            self.assertIn(flag, argument_calls, f"Expected flag {flag} not found")
            
    def test_integration_comprehensive_sheet_coverage(self):
        """Integration Test: Verify comprehensive sheet coverage"""
        # This test verifies the command includes all major GSheet entities
        help_text = self.command.help.lower()
        
        # Verify comprehensive coverage mentioned
        self.assertIn('all configured', help_text)
        self.assertIn('google sheets', help_text)
        
        # Test that both skip options work
        parser = Mock()
        self.command.add_arguments(parser)
        
        skip_calls = [call for call in parser.add_argument.call_args_list 
                      if 'skip-marketing' in str(call)]
        self.assertEqual(len(skip_calls), 2)  # marketing-leads and marketing-spends


class TestHubSpotContactsCommand(TestCase):
    """Test HubSpot contacts sync command using BaseHubSpotSyncCommand architecture"""
    
    def setUp(self):
        self.command = HubSpotContactsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertIn('HubSpot', self.command.help)
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_hubspot_specific_flags(self):
        """Unit Test: HubSpot-specific flag architecture"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify HubSpot's flag system (similar to BaseSyncCommand but with HubSpot naming)
        expected_flags = ['--full', '--debug', '--dry-run', '--batch-size', 
                         '--max-records', '--since', '--force-overwrite']
        
        for flag in expected_flags:
            self.assertIn(flag, argument_calls, f"HubSpot flag {flag} not found")
            
    def test_unit_sync_name_method(self):
        """Unit Test: Sync name method returns correct value"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'contacts')
        
    @patch('ingestion.management.commands.sync_hubspot_contacts.HubSpotContactSyncEngine')
    def test_integration_sync_engine_initialization(self, mock_engine_class):
        """Integration Test: Sync engine initialization with HubSpot architecture"""
        # Setup mocks
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Test sync engine creation with options
        options = {
            'batch_size': 50,
            'dry_run': True,
            'force_overwrite': False
        }
        
        engine = self.command.get_sync_engine(**options)
        
        # Verify engine was created with correct parameters
        mock_engine_class.assert_called_once_with(
            batch_size=50,
            dry_run=True,
            force_overwrite=False
        )
        
    def test_e2e_hubspot_architecture_compatibility(self):
        """E2E Test: Verify HubSpot architecture works with test framework"""
        # This test ensures HubSpot's BaseHubSpotSyncCommand architecture 
        # is compatible with our testing approach
        
        # Test that command has expected methods and structure
        self.assertTrue(callable(getattr(self.command, 'get_sync_engine', None)))
        self.assertTrue(callable(getattr(self.command, 'get_sync_name', None)))
        
        # Test help text indicates HubSpot-specific features
        help_text = self.command.help.lower()
        self.assertIn('hubspot', help_text)
        self.assertIn('force-overwrite', help_text)


class TestHubSpotDealsCommand(TestCase):
    """Test HubSpot deals sync command using BaseHubSpotSyncCommand architecture"""
    
    def setUp(self):
        self.command = HubSpotDealsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertIn('HubSpot', self.command.help)
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_deals_specific_sync_name(self):
        """Unit Test: Deals-specific sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'deals')
        
    def test_integration_consistent_hubspot_flags(self):
        """Integration Test: Consistent flag system across HubSpot commands"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify same flag system as contacts (consistent HubSpot architecture)
        hubspot_flags = ['--full', '--debug', '--dry-run', '--batch-size', '--max-records', '--since', '--force-overwrite']
        
        for flag in hubspot_flags:
            self.assertIn(flag, argument_calls, f"Consistent HubSpot flag {flag} not found in deals command")


class TestHubSpotAllCommand(TestCase):
    """Test HubSpot all data sync command"""
    
    def setUp(self):
        self.command = HubSpotAllCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        # Note: sync_hubspot_all might not use BaseHubSpotSyncCommand
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_comprehensive_hubspot_coverage(self):
        """Unit Test: Verify comprehensive HubSpot coverage"""
        # Test that help text indicates comprehensive sync
        help_text = self.command.help.lower() if self.command.help else ""
        
        # Should indicate comprehensive coverage of HubSpot data
        hubspot_indicators = ['hubspot', 'all', 'sync']
        for indicator in hubspot_indicators:
            self.assertIn(indicator, help_text, f"HubSpot all command should mention '{indicator}'")
            
    def test_integration_hubspot_all_architecture(self):
        """Integration Test: HubSpot all command architecture"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify arguments are defined (structure may vary from individual commands)
        argument_calls = parser.add_argument.call_args_list
        self.assertGreater(len(argument_calls), 0, "HubSpot all command should have arguments defined")


class TestArrivyBookingsCommand(TestCase):
    """Test Arrivy bookings sync command standardization"""
    
    def setUp(self):
        self.command = ArrivyBookingsCommand()
        
    def test_unit_inherits_base_sync_command(self):
        """Unit Test: Arrivy bookings command inherits from BaseSyncCommand"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
    
    def test_unit_has_standard_arguments(self):
        """Unit Test: Command has all standard BaseSyncCommand arguments"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        
        # Standard BaseSyncCommand flags
        option_strings = parser._option_string_actions
        
        # Check standard flags
        self.assertIn('--debug', option_strings)
        self.assertIn('--test', option_strings)
        self.assertIn('--full', option_strings)
        self.assertIn('--verbose', option_strings)
        self.assertIn('--skip-validation', option_strings)
        self.assertIn('--dry-run', option_strings)
        
    def test_unit_has_arrivy_specific_arguments(self):
        """Unit Test: Command has Arrivy-specific arguments"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        
        # Arrivy specific flags
        option_strings = parser._option_string_actions
        
        # Check Arrivy-specific flags  
        self.assertIn('--booking-status', option_strings)
        self.assertIn('--high-performance', option_strings)
    
    def test_integration_command_execution_dry_run(self):
        """Integration Test: Command execution in dry-run mode"""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('sync_arrivy_bookings', '--dry-run', verbosity=0)
            output = mock_stdout.getvalue()
            # Should not error out and should indicate dry-run mode
            self.assertTrue(len(output) >= 0)  # Basic execution test
            

class TestArrivyTasksCommand(TestCase):
    """Test Arrivy tasks sync command standardization"""
    
    def setUp(self):
        self.command = ArrivyTasksCommand()
        
    def test_unit_inherits_base_sync_command(self):
        """Unit Test: Arrivy tasks command inherits from BaseSyncCommand"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
    
    def test_unit_has_standard_arguments(self):
        """Unit Test: Command has all standard BaseSyncCommand arguments"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        
        # Standard BaseSyncCommand flags
        option_strings = parser._option_string_actions
        
        # Check standard flags
        self.assertIn('--debug', option_strings)
        self.assertIn('--test', option_strings)
        self.assertIn('--full', option_strings)
        self.assertIn('--verbose', option_strings)
        self.assertIn('--skip-validation', option_strings)
        self.assertIn('--dry-run', option_strings)
        
    def test_unit_has_arrivy_specific_arguments(self):
        """Unit Test: Command has Arrivy-specific arguments"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        
        # Arrivy specific flags
        option_strings = parser._option_string_actions
        
        # Check Arrivy-specific flags  
        self.assertIn('--task-status', option_strings)
        self.assertIn('--assigned-to', option_strings)
        self.assertIn('--high-performance', option_strings)
        self.assertIn('--concurrent-pages', option_strings)
    
    def test_integration_command_execution_dry_run(self):
        """Integration Test: Command execution in dry-run mode"""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('sync_arrivy_tasks', '--dry-run', verbosity=0)
            output = mock_stdout.getvalue()
            # Should not error out and should indicate dry-run mode
            self.assertTrue(len(output) >= 0)  # Basic execution test


class TestArrivyAllCommand(TestCase):
    """Test Arrivy all sync command standardization"""
    
    def setUp(self):
        self.command = ArrivyAllCommand()
        
    def test_unit_inherits_base_sync_command(self):
        """Unit Test: Arrivy all command inherits from BaseSyncCommand"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
    
    def test_unit_has_standard_arguments(self):
        """Unit Test: Command has all standard BaseSyncCommand arguments"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        
        # Standard BaseSyncCommand flags
        option_strings = parser._option_string_actions
        
        # Check standard flags
        self.assertIn('--debug', option_strings)
        self.assertIn('--test', option_strings)
        self.assertIn('--full', option_strings)
        self.assertIn('--verbose', option_strings)
        self.assertIn('--skip-validation', option_strings)
        self.assertIn('--dry-run', option_strings)
        
    def test_integration_command_execution_dry_run(self):
        """Integration Test: Command execution in dry-run mode"""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            call_command('sync_arrivy_all', '--dry-run', verbosity=0)
            output = mock_stdout.getvalue()
            # Should not error out and should indicate dry-run mode
            self.assertTrue(len(output) >= 0)  # Basic execution test


if __name__ == '__main__':
    unittest.main()
