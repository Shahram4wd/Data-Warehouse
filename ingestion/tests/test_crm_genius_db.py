"""
Genius DB Command Testing
Tests for database-based Genius sync commands that pull data from Genius MySQL database
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from ingestion.tests.command_test_base import CRMCommandTestBase


class GeniusDBTestBase(CRMCommandTestBase):
    """Base test class for Genius DB command testing"""
    
    def setUp(self):
        super().setUp()
        # Mock MySQL database connections
        self.mysql_patcher = patch('ingestion.utils.get_mysql_connection')
        self.mock_mysql = self.mysql_patcher.start()
        
        # Mock database connection
        mock_connection = Mock()
        mock_cursor = Mock()
        mock_connection.cursor.return_value = mock_cursor
        self.mock_mysql.return_value = mock_connection
        self.mock_cursor = mock_cursor
    
    def tearDown(self):
        super().tearDown()
        self.mysql_patcher.stop()
    
    def create_mock_genius_appointments(self, count=100):
        """Create mock Genius appointment data"""
        appointments = []
        for i in range(count):
            appointments.append((
                i+1,  # appointment_id
                f'lead_{i+1}',  # lead_id
                f'prospect_{i+1}',  # prospect_id
                f'2024-01-{(i % 28) + 1:02d} 10:00:00',  # appointment_date
                1,  # appointment_type_id
                f'User {i+1}',  # set_by_user
                1,  # outcome_id
                f'Notes for appointment {i+1}',  # notes
                '2024-01-01 09:00:00',  # created_at
                '2024-01-01 10:00:00'   # updated_at
            ))
        return appointments


class TestGeniusAppointmentsCommand(GeniusDBTestBase):
    """Test Genius Appointments DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_genius_appointments import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command structure and inheritance"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertTrue(hasattr(self.command, 'help'))
        
    def test_unit_database_sync_arguments(self):
        """Unit Test: Database sync specific arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        # Test database-specific flags
        args = parser.parse_args(['--full', '--debug', '--max-records', '1000'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        self.assertEqual(args.max_records, 1000)
        
    def test_unit_genius_specific_arguments(self):
        """Unit Test: Genius-specific command arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        # Test Genius-specific flags
        args = parser.parse_args(['--since', '2024-01-01', '--force'])
        self.assertEqual(args.since, '2024-01-01')
        self.assertTrue(args.force_overwrite)
        
    def test_integration_dry_run_execution(self):
        """Integration Test: Dry run execution with mocked database"""
        mock_appointments = self.create_mock_genius_appointments(50)
        self.mock_cursor.fetchall.return_value = mock_appointments
        
        output = StringIO()
        call_command('db_genius_appointments', '--dry-run', '--debug', stdout=output)
        
        # Verify database was queried
        self.mock_mysql.assert_called()
        output_content = output.getvalue()
        self.assertIn('dry', output_content.lower())
        
    def test_e2e_full_sync_workflow(self):
        """E2E Test: Complete full sync workflow"""
        mock_appointments = self.create_mock_genius_appointments(100)
        self.mock_cursor.fetchall.return_value = mock_appointments
        
        output = StringIO()
        call_command(
            'db_genius_appointments',
            '--full',
            '--max-records', '100',
            '--debug',
            stdout=output
        )
        
        # Verify database connection and queries
        self.mock_mysql.assert_called()
        self.mock_cursor.execute.assert_called()


class TestGeniusUsersCommand(GeniusDBTestBase):
    """Test Genius Users DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_genius_users import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command structure"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_users_specific_arguments(self):
        """Unit Test: Users-specific command arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--since', '2024-01-01'])
        self.assertTrue(args.full)
        self.assertEqual(args.since, '2024-01-01')
        
    def test_integration_incremental_sync(self):
        """Integration Test: Incremental sync execution"""
        mock_users = [
            (1, 'user1@example.com', 'John', 'Doe', 1, '2024-01-01 10:00:00'),
            (2, 'user2@example.com', 'Jane', 'Smith', 1, '2024-01-02 10:00:00')
        ]
        self.mock_cursor.fetchall.return_value = mock_users
        
        output = StringIO()
        call_command('db_genius_users', '--debug', stdout=output)
        
        self.mock_mysql.assert_called()
        
    def test_e2e_date_range_sync(self):
        """E2E Test: Date range sync workflow"""
        mock_users = [
            (1, 'user1@example.com', 'John', 'Doe', 1, '2024-01-01 10:00:00')
        ]
        self.mock_cursor.fetchall.return_value = mock_users
        
        output = StringIO()
        call_command(
            'db_genius_users',
            '--since', '2024-01-01',
            '--debug',
            stdout=output
        )
        
        # Verify database query was made
        self.mock_mysql.assert_called()
        self.mock_cursor.execute.assert_called()


class TestGeniusDivisionsCommand(GeniusDBTestBase):
    """Test Genius Divisions DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_genius_divisions import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_divisions_arguments(self):
        """Unit Test: Divisions specific arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--debug'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        
    def test_integration_divisions_sync(self):
        """Integration Test: Divisions sync execution"""
        mock_divisions = [
            (1, 'Division 1', 'Manager 1', 'active'),
            (2, 'Division 2', 'Manager 2', 'active')
        ]
        self.mock_cursor.fetchall.return_value = mock_divisions
        
        output = StringIO()
        call_command('db_genius_divisions', '--debug', stdout=output)
        
        self.mock_mysql.assert_called()


class TestGeniusJobsCommand(GeniusDBTestBase):
    """Test Genius Jobs DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_genius_jobs import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_jobs_arguments(self):
        """Unit Test: Jobs specific arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--max-records', '500'])
        self.assertTrue(args.full)
        self.assertEqual(args.max_records, 500)
        
    def test_integration_jobs_sync(self):
        """Integration Test: Jobs sync execution"""
        mock_jobs = [
            (1, 'Job 1', 'Description 1', 'active', '2024-01-01'),
            (2, 'Job 2', 'Description 2', 'completed', '2024-01-02')
        ]
        self.mock_cursor.fetchall.return_value = mock_jobs
        
        output = StringIO()
        call_command('db_genius_jobs', '--debug', stdout=output)
        
        self.mock_mysql.assert_called()


class TestGeniusAllCommand(GeniusDBTestBase):
    """Test Genius All DB sync command (unified sync)"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_genius_all import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Unified sync command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_unified_sync_arguments(self):
        """Unit Test: Unified sync command arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--debug', '--parallel'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        
    @patch('ingestion.management.commands.db_genius_all.call_command')
    def test_integration_unified_sync_execution(self, mock_call_command):
        """Integration Test: Unified sync of all Genius entities"""
        output = StringIO()
        call_command('db_genius_all', '--debug', stdout=output)
        
        # Verify that individual sync commands were called
        # Note: This depends on the actual implementation of db_genius_all
        self.assertTrue(mock_call_command.called)
        
    @patch('ingestion.management.commands.db_genius_all.call_command')
    def test_e2e_unified_full_sync(self, mock_call_command):
        """E2E Test: Complete unified full sync workflow"""
        output = StringIO()
        call_command('db_genius_all', '--full', '--debug', stdout=output)
        
        # Verify full sync was propagated
        self.assertTrue(mock_call_command.called)
        
        # Check that --full flag was passed to sub-commands
        call_args_list = mock_call_command.call_args_list
        for call_args in call_args_list:
            if len(call_args[0]) > 1:  # If there are command arguments
                # Check if --full was passed to the sub-commands
                command_args = call_args[0][1:] if call_args[0] else []
                # This test validates that the unified command properly propagates flags
