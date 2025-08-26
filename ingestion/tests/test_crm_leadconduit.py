"""
Tests for LeadConduit CRM sync commands
"""
import asyncio
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from datetime import timedelta

from ingestion.management.commands.sync_leadconduit_leads import Command as LeadConduitCommand
from ingestion.management.commands.sync_leadconduit_all import Command as LeadConduitAllCommand


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
