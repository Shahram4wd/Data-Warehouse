"""
Tests for MarketSharp CRM sync commands
"""
import asyncio
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from io import StringIO
from datetime import timedelta

from ingestion.management.commands.sync_marketsharp_data import Command as MarketSharpCommand


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
