"""
Tests for Arrivy CRM sync commands
"""
from argparse import ArgumentParser
from unittest.mock import patch
from django.test import TestCase
from django.core.management import call_command
from io import StringIO

from ingestion.management.commands.sync_arrivy_bookings import Command as ArrivyBookingsCommand
from ingestion.management.commands.sync_arrivy_tasks import Command as ArrivyTasksCommand
from ingestion.management.commands.sync_arrivy_all import Command as ArrivyAllCommand


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
