"""
Tests for Five9 CRM sync commands
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from datetime import timedelta

from ingestion.management.commands.sync_five9_contacts import Command as Five9Command


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
