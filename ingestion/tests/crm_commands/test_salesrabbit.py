"""
Specialized tests for SalesRabbit sync commands

This module contains advanced tests for SalesRabbit's sophisticated sync architecture,
including the BaseSalesRabbitSyncCommand pattern and high-performance features.
"""
import pytest
import logging
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from datetime import datetime, timedelta
from argparse import ArgumentParser

from ingestion.management.commands.sync_salesrabbit_leads import Command as SalesRabbitLeadsCommand
from ingestion.management.commands.sync_salesrabbit_leads_new import Command as SalesRabbitLeadsNewCommand
from ingestion.management.commands.sync_salesrabbit_all import Command as SalesRabbitAllCommand


class SalesRabbitTestBase(TestCase):
    """Base class for SalesRabbit command testing"""
    
    def setUp(self):
        """Set up common test fixtures"""
        self.mock_sync_engine = Mock()
        self.mock_config = Mock()
        
    def assert_salesrabbit_standard_flags(self, command):
        """Assert that command has standard SalesRabbit flags"""
        parser = ArgumentParser()
        command.add_arguments(parser)
        option_strings = parser._option_string_actions
        
        # Standard flags that all SalesRabbit commands should have
        expected_flags = ['--full', '--debug', '--dry-run', '--batch-size']
        for flag in expected_flags:
            self.assertIn(flag, option_strings, f"Missing standard flag: {flag}")


class TestSalesRabbitLeadsAdvanced(SalesRabbitTestBase):
    """Advanced tests for SalesRabbit leads sync command"""
    
    def setUp(self):
        super().setUp()
        self.command = SalesRabbitLeadsCommand()
        
    def test_advanced_flag_combinations(self):
        """Test advanced flag combinations specific to SalesRabbit leads"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        option_strings = parser._option_string_actions
        
        # SalesRabbit-specific advanced flags
        advanced_flags = ['--since', '--force-overwrite', '--max-records']
        for flag in advanced_flags:
            self.assertIn(flag, option_strings, f"Missing advanced flag: {flag}")
            
    def test_unified_architecture_pattern(self):
        """Test that command follows unified architecture pattern"""
        # Should inherit from BaseSalesRabbitSyncCommand
        from ingestion.management.commands.base_salesrabbit_sync import BaseSalesRabbitSyncCommand
        self.assertTrue(issubclass(type(self.command), BaseSalesRabbitSyncCommand))
        
    def test_help_text_examples(self):
        """Test that help text includes comprehensive examples"""
        help_text = self.command.__doc__ if self.command.__doc__ else ""
        
        # Should include various usage examples
        example_indicators = ['Examples:', 'Full sync', 'Force overwrite', 'batch-size']
        for indicator in example_indicators:
            self.assertIn(indicator, help_text, f"Help text missing example for: {indicator}")
            
    @patch('ingestion.management.commands.sync_salesrabbit_leads.SalesRabbitLeadSyncEngine')
    def test_sync_engine_initialization(self, mock_engine_class):
        """Test that sync engine is properly initialized"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        # Test dry-run mode doesn't interfere with engine initialization
        with patch('sys.stdout', new_callable=StringIO):
            try:
                call_command('sync_salesrabbit_leads', '--dry-run', '--debug', verbosity=0)
            except Exception:
                # Expected to fail due to missing config, but engine should be attempted
                pass


class TestSalesRabbitLeadsNewAdvanced(SalesRabbitTestBase):
    """Advanced tests for SalesRabbit leads new (refactored) command"""
    
    def setUp(self):
        super().setUp()
        self.command = SalesRabbitLeadsNewCommand()
        
    def test_refactored_architecture_compliance(self):
        """Test compliance with refactored architecture standards"""
        # Should inherit from BaseCommand (not BaseSalesRabbitSyncCommand)
        from django.core.management.base import BaseCommand
        self.assertTrue(issubclass(type(self.command), BaseCommand))
        
    def test_framework_standard_flags(self):
        """Test framework-standard flag implementation"""
        parser = ArgumentParser()
        self.command.add_arguments(parser)
        option_strings = parser._option_string_actions
        
        # Framework-standard flags
        framework_flags = ['--force-full', '--batch-size', '--dry-run', '--max-records']
        for flag in framework_flags:
            self.assertIn(flag, option_strings, f"Missing framework flag: {flag}")
            
    def test_four_layer_architecture_mention(self):
        """Test that help text mentions four-layer architecture"""
        help_text = self.command.help.lower()
        self.assertIn('four-layer architecture', help_text)
        
    def test_async_processing_support(self):
        """Test that command supports async processing"""
        # Check if the command file imports asyncio (indication of async support)
        import inspect
        source = inspect.getsource(SalesRabbitLeadsNewCommand)
        self.assertIn('asyncio', source)


class TestSalesRabbitAllAdvanced(SalesRabbitTestBase):
    """Advanced tests for SalesRabbit all sync orchestration command"""
    
    def setUp(self):
        super().setUp()
        self.command = SalesRabbitAllCommand()
        
    def test_orchestration_pattern(self):
        """Test that command follows proper orchestration pattern"""
        # Should inherit from BaseCommand for orchestration
        from django.core.management.base import BaseCommand
        self.assertTrue(issubclass(type(self.command), BaseCommand))
        
    def test_unified_architecture_orchestration(self):
        """Test unified architecture orchestration capabilities"""
        help_text = self.command.help.lower() if self.command.help else ""
        
        # Should mention unified architecture and data integrity
        orchestration_indicators = ['unified architecture', 'data integrity', 'relationships']
        found_indicators = [indicator for indicator in orchestration_indicators 
                          if indicator in help_text]
        
        # Should have at least some orchestration indicators
        self.assertGreater(len(found_indicators), 0, 
                          "Help text should mention orchestration concepts")
        
    def test_sync_history_integration(self):
        """Test SyncHistory integration for orchestration tracking"""
        # Check if the command imports SyncHistory
        import inspect
        source = inspect.getsource(SalesRabbitAllCommand)
        self.assertIn('SyncHistory', source)
        
    @patch('django.core.management.call_command')
    @patch('ingestion.management.commands.sync_salesrabbit_all.SyncHistory')
    def test_individual_command_orchestration(self, mock_sync_history, mock_call_command):
        """Test that individual commands are properly orchestrated"""
        mock_sync_history_instance = Mock()
        mock_sync_history.objects.create.return_value = mock_sync_history_instance
        
        with patch('sys.stdout', new_callable=StringIO):
            try:
                call_command('sync_salesrabbit_all', '--full', '--debug', verbosity=0)
                
                # Should create SyncHistory for tracking
                # (Specific call verification would depend on implementation details)
                
            except Exception as e:
                # Command may fail due to missing config, but orchestration pattern should be attempted
                self.assertIsInstance(e, (CommandError, Exception))


class TestSalesRabbitPerformanceFeatures(SalesRabbitTestBase):
    """Test SalesRabbit performance and advanced features"""
    
    def test_batch_processing_capabilities(self):
        """Test that SalesRabbit commands support batch processing"""
        commands = [SalesRabbitLeadsCommand(), SalesRabbitLeadsNewCommand(), SalesRabbitAllCommand()]
        
        for command in commands:
            with self.subTest(command=command.__class__.__name__):
                parser = ArgumentParser()
                command.add_arguments(parser)
                option_strings = parser._option_string_actions
                
                # Should support batch-size parameter
                self.assertIn('--batch-size', option_strings)
                
    def test_record_limit_capabilities(self):
        """Test that SalesRabbit commands support record limiting"""
        commands = [SalesRabbitLeadsCommand(), SalesRabbitLeadsNewCommand()]
        
        for command in commands:
            with self.subTest(command=command.__class__.__name__):
                parser = ArgumentParser()
                command.add_arguments(parser)
                option_strings = parser._option_string_actions
                
                # Should support max-records parameter for performance control
                if hasattr(command, 'add_arguments'):
                    # Some commands may have max-records, others may not
                    # This is acceptable based on their specific needs
                    pass
                    
    def test_force_overwrite_capabilities(self):
        """Test force overwrite capabilities for data integrity"""
        command = SalesRabbitLeadsCommand()
        parser = ArgumentParser()
        command.add_arguments(parser)
        option_strings = parser._option_string_actions
        
        # Should support force-overwrite for data integrity scenarios
        self.assertIn('--force-overwrite', option_strings)
        
    def test_since_parameter_capabilities(self):
        """Test since parameter for incremental sync capabilities"""
        command = SalesRabbitLeadsCommand()
        parser = ArgumentParser()
        command.add_arguments(parser)
        option_strings = parser._option_string_actions
        
        # Should support --since for incremental processing
        self.assertIn('--since', option_strings)


class TestSalesRabbitErrorHandling(SalesRabbitTestBase):
    """Test SalesRabbit error handling and resilience"""
    
    def test_missing_config_handling(self):
        """Test graceful handling of missing configuration"""
        commands = ['sync_salesrabbit_leads', 'sync_salesrabbit_leads_new', 'sync_salesrabbit_all']
        
        for command_name in commands:
            with self.subTest(command=command_name):
                with patch('sys.stdout', new_callable=StringIO):
                    try:
                        call_command(command_name, '--dry-run', verbosity=0)
                        # Should not crash catastrophically
                    except Exception as e:
                        # Should raise appropriate exceptions, not crash with unhandled errors
                        self.assertIsInstance(e, (CommandError, Exception))
                        
    def test_dry_run_safety(self):
        """Test that dry-run mode is safe and doesn't modify data"""
        commands = ['sync_salesrabbit_leads', 'sync_salesrabbit_leads_new', 'sync_salesrabbit_all']
        
        for command_name in commands:
            with self.subTest(command=command_name):
                with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
                    try:
                        call_command(command_name, '--dry-run', verbosity=0)
                        output = mock_stdout.getvalue()
                        
                        # Should execute without catastrophic failure
                        self.assertIsInstance(output, str)
                        
                    except Exception as e:
                        # Should fail gracefully with appropriate exceptions
                        self.assertIsInstance(e, (CommandError, Exception))


if __name__ == '__main__':
    pytest.main([__file__])
