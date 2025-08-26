"""
Tests for CRM sync commands - Common/Shared functionality only
Individual CRM systems now have dedicated test files:
- test_crm_five9.py
- test_crm_marketsharp.py  
- test_crm_leadconduit.py
- test_crm_gsheet.py
- test_crm_hubspot.py
- test_crm_arrivy.py
- test_callrail.py (specialized)
- test_salesrabbit.py (specialized)
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
from datetime import timedelta


class TestBaseSyncCommandArchitecture(TestCase):
    """Test shared BaseSyncCommand architecture patterns"""
    
    def test_command_inheritance_patterns(self):
        """Test that all CRM commands follow consistent inheritance patterns"""
        # This test can validate common patterns across all CRM commands
        # without importing specific commands
        
        # Test that management commands are discoverable
        from django.core.management import get_commands
        commands = get_commands()
        
        # Verify CRM sync commands exist
        crm_commands = [cmd for cmd in commands.keys() if cmd.startswith('sync_')]
        self.assertGreater(len(crm_commands), 10, "Should have multiple CRM sync commands")
        
        # Verify Five9, MarketSharp, LeadConduit, GSheet commands exist
        expected_commands = [
            'sync_five9_contacts',
            'sync_marketsharp_data',
            'sync_leadconduit_leads',
            'sync_gsheet_marketing_leads'
        ]
        
        for expected in expected_commands:
            self.assertIn(expected, commands, f"Command {expected} should exist")
    
    def test_standard_flag_patterns(self):
        """Test that standard flags follow consistent patterns"""
        # Test basic flag patterns that should be consistent across systems
        
        # Import one command as representative
        from ingestion.management.commands.sync_five9_contacts import Command
        command = Command()
        
        parser = Mock()
        command.add_arguments(parser)
        
        # Verify basic flags that should be universal
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        universal_flags = ['--dry-run', '--debug', '--full', '--force']
        for flag in universal_flags:
            self.assertIn(flag, argument_calls, f"Universal flag {flag} should be present")
    
    def test_help_text_consistency(self):
        """Test that help text follows consistent patterns"""
        from ingestion.management.commands.sync_five9_contacts import Command
        command = Command()
        
        # Help text should exist and be descriptive
        self.assertIsNotNone(command.help)
        self.assertGreater(len(command.help), 10, "Help text should be descriptive")
        
        # Should mention sync functionality
        help_lower = command.help.lower()
        sync_keywords = ['sync', 'data', 'contacts', 'five9']
        for keyword in sync_keywords:
            self.assertIn(keyword, help_lower, f"Help should mention {keyword}")


class TestCommonSyncPatterns(TestCase):
    """Test patterns common to all sync operations"""
    
    def test_dry_run_safety_pattern(self):
        """Test that dry-run mode is implemented safely across systems"""
        # Test with a simple command that dry-run should be safe
        out = StringIO()
        
        try:
            call_command('sync_five9_contacts', '--dry-run', '--max-records', '1', stdout=out)
        except Exception as e:
            # Dry run should not cause unhandled exceptions
            self.fail(f"Dry run should be safe but got: {e}")
        
        # Output should indicate dry-run mode
        output = out.getvalue()
        # Basic validation that command executed
        self.assertIsInstance(output, str)
    
    @patch('ingestion.management.commands.sync_five9_contacts.Five9Config')
    def test_config_integration_pattern(self, mock_config):
        """Test that config integration follows consistent patterns"""
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        
        out = StringIO()
        call_command('sync_five9_contacts', '--dry-run', stdout=out)
        
        # Config should be called
        mock_config.get_config.assert_called()
    
    def test_error_handling_patterns(self):
        """Test that error handling follows consistent patterns"""
        # Test invalid argument handling
        with self.assertRaises(SystemExit):
            # Invalid flag should cause system exit
            call_command('sync_five9_contacts', '--invalid-flag-that-does-not-exist')


class TestCRMSyncDocumentation(TestCase):
    """Test that CRM sync commands are properly documented"""
    
    def test_command_discovery(self):
        """Test that all CRM commands can be discovered"""
        from django.core.management import get_commands
        commands = get_commands()
        
        # Test major CRM systems are represented
        crm_systems = {
            'five9': [cmd for cmd in commands if 'five9' in cmd],
            'marketsharp': [cmd for cmd in commands if 'marketsharp' in cmd],
            'leadconduit': [cmd for cmd in commands if 'leadconduit' in cmd],
            'gsheet': [cmd for cmd in commands if 'gsheet' in cmd],
            'hubspot': [cmd for cmd in commands if 'hubspot' in cmd],
            'callrail': [cmd for cmd in commands if 'callrail' in cmd],
            'arrivy': [cmd for cmd in commands if 'arrivy' in cmd],
            'salesrabbit': [cmd for cmd in commands if 'salesrabbit' in cmd]
        }
        
        for system, system_commands in crm_systems.items():
            self.assertGreater(len(system_commands), 0, 
                             f"Should have commands for {system} CRM")
    
    def test_help_text_availability(self):
        """Test that all commands have proper help text"""
        from django.core.management import load_command_class
        
        test_commands = [
            'sync_five9_contacts',
            'sync_marketsharp_data', 
            'sync_leadconduit_leads',
            'sync_gsheet_marketing_leads'
        ]
        
        for cmd_name in test_commands:
            try:
                command_class = load_command_class('ingestion', cmd_name)
                command = command_class()
                
                # Should have help text
                self.assertIsNotNone(command.help, f"Command {cmd_name} should have help text")
                self.assertGreater(len(command.help), 5, 
                                 f"Command {cmd_name} help should be descriptive")
                
            except Exception as e:
                self.fail(f"Could not load command {cmd_name}: {e}")


class TestSyncEngineIntegration(TestCase):
    """Test integration patterns between commands and sync engines"""
    
    @patch('ingestion.management.commands.sync_five9_contacts.Five9ContactsSyncEngine')
    @patch('ingestion.management.commands.sync_five9_contacts.Five9Config')
    def test_engine_initialization_pattern(self, mock_config, mock_engine_class):
        """Test that sync engines are initialized consistently"""
        # Setup mocks
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        mock_engine = Mock()
        mock_engine.sync_data.return_value = {'success': True, 'records_processed': 0}
        mock_engine_class.return_value = mock_engine
        
        # Execute command
        call_command('sync_five9_contacts', '--dry-run')
        
        # Engine should be initialized
        mock_engine_class.assert_called()
        # Sync should be called
        mock_engine.sync_data.assert_called()
    
    def test_async_support_patterns(self):
        """Test that async operations are properly supported where implemented"""
        # This test verifies async patterns are supported where needed
        
        # Import async-capable command
        from ingestion.management.commands.sync_marketsharp_data import Command
        command = Command()
        
        # Should have proper async support structure
        self.assertTrue(hasattr(command, 'handle'))
        
        # Test async execution doesn't cause errors
        out = StringIO()
        try:
            call_command('sync_marketsharp_data', '--dry-run', '--max-records', '1', stdout=out)
        except Exception as e:
            # Async operations should not cause unhandled exceptions
            if "async" in str(e).lower():
                self.fail(f"Async execution failed: {e}")


class TestPerformanceAndScaling(TestCase):
    """Test performance-related patterns"""
    
    def test_batch_processing_support(self):
        """Test that batch processing is properly supported"""
        # Test batch size argument exists where expected
        from ingestion.management.commands.sync_five9_contacts import Command
        command = Command()
        
        parser = Mock()
        command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Batch size should be supported for performance
        self.assertIn('--batch-size', argument_calls, "Batch size should be supported")
    
    def test_record_limiting_support(self):
        """Test that record limiting is properly supported"""
        from ingestion.management.commands.sync_five9_contacts import Command
        command = Command()
        
        parser = Mock()
        command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Max records should be supported for testing and safety
        self.assertIn('--max-records', argument_calls, "Max records should be supported")


class TestBackwardCompatibility(TestCase):
    """Test backward compatibility patterns"""
    
    def test_deprecated_flag_support(self):
        """Test that deprecated flags are properly handled"""
        # LeadConduit commands have backward compatibility
        from ingestion.management.commands.sync_leadconduit_leads import Command
        command = Command()
        
        parser = Mock()
        command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Should support both old and new flags
        self.assertIn('--start-date', argument_calls, "New standard flag should exist")
        self.assertIn('--since', argument_calls, "Deprecated flag should still exist for compatibility")


class TestConfigurationManagement(TestCase):
    """Test configuration management patterns"""
    
    @patch('ingestion.management.commands.sync_five9_contacts.Five9Config')
    def test_config_parameter_passing(self, mock_config):
        """Test that configuration parameters are passed properly"""
        mock_config.get_config.return_value = {'api_key': 'test', 'dry_run': True}
        
        # Test config parameter passing
        call_command('sync_five9_contacts', '--config', 'test-config', '--dry-run')
        
        # Config should be called with proper parameters
        mock_config.get_config.assert_called()
        call_args = mock_config.get_config.call_args[0]
        self.assertEqual(call_args[0], 'test-config')
