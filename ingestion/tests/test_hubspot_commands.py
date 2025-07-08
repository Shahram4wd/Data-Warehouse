"""
Unit tests for HubSpot management commands
"""
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase
from django.core.management import call_command
from django.core.management.base import CommandError
from io import StringIO
import asyncio

from ingestion.management.commands.sync_hubspot_contacts_new import Command as ContactCommand
from ingestion.management.commands.sync_hubspot_appointments_new import Command as AppointmentCommand
from ingestion.management.commands.sync_hubspot_divisions_new import Command as DivisionCommand
from ingestion.management.commands.sync_hubspot_deals_new import Command as DealCommand
from ingestion.management.commands.sync_hubspot_associations_new import Command as AssociationCommand
from ingestion.models.common import SyncHistory


class TestHubSpotManagementCommands(TestCase):
    """Test HubSpot management commands"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.out = StringIO()
        
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_no_token(self, mock_settings):
        """Test contact command without HubSpot token"""
        mock_settings.HUBSPOT_API_TOKEN = None
        
        with self.assertRaises(CommandError):
            call_command('sync_hubspot_contacts_new', stdout=self.out)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run')
    def test_contact_command_with_token(self, mock_asyncio_run, mock_settings):
        """Test contact command with valid token"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        # Mock the sync result
        mock_history = MagicMock()
        mock_history.status = 'success'
        mock_history.records_processed = 100
        mock_history.records_created = 10
        mock_history.records_updated = 90
        mock_history.records_failed = 0
        mock_history.performance_metrics = {'duration_seconds': 10.0, 'records_per_second': 10.0}
        mock_history.error_message = None
        mock_asyncio_run.return_value = mock_history
        
        call_command('sync_hubspot_contacts_new', stdout=self.out)
        
        output = self.out.getvalue()
        self.assertIn('Starting contacts sync', output)
        self.assertIn('Contacts sync completed successfully', output)
        mock_asyncio_run.assert_called_once()
        
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_debug_mode(self, mock_settings):
        """Test contact command with debug mode"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run') as mock_asyncio_run:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 10
            mock_history.records_updated = 90
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 10.0, 'records_per_second': 10.0}
            mock_history.error_message = None
            mock_asyncio_run.return_value = mock_history
            
            call_command('sync_hubspot_contacts_new', '--debug', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Starting contacts sync', output)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_full_sync(self, mock_settings):
        """Test contact command with full sync"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run') as mock_asyncio_run:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 1000
            mock_history.records_created = 100
            mock_history.records_updated = 900
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 60.0, 'records_per_second': 16.67}
            mock_history.error_message = None
            mock_asyncio_run.return_value = mock_history
            
            call_command('sync_hubspot_contacts_new', '--full', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Performing full sync', output)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_dry_run(self, mock_settings):
        """Test contact command with dry run"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run') as mock_asyncio_run:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 0  # No records created in dry run
            mock_history.records_updated = 0  # No records updated in dry run
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 5.0, 'records_per_second': 20.0}
            mock_history.error_message = None
            mock_asyncio_run.return_value = mock_history
            
            call_command('sync_hubspot_contacts_new', '--dry-run', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Starting contacts sync', output)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_with_since_date(self, mock_settings):
        """Test contact command with since date"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run') as mock_asyncio_run:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 50
            mock_history.records_created = 5
            mock_history.records_updated = 45
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 3.0, 'records_per_second': 16.67}
            mock_history.error_message = None
            mock_asyncio_run.return_value = mock_history
            
            call_command('sync_hubspot_contacts_new', '--since', '2023-01-01', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Using provided since date: 2023-01-01', output)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_invalid_since_date(self, mock_settings):
        """Test contact command with invalid since date"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with self.assertRaises(CommandError):
            call_command('sync_hubspot_contacts_new', '--since', 'invalid-date', stdout=self.out)
            
    @patch('ingestion.management.commands.sync_hubspot_contacts_new.settings')
    def test_contact_command_sync_failure(self, mock_settings):
        """Test contact command with sync failure"""
        mock_settings.HUBSPOT_API_TOKEN = 'test_token'
        
        with patch('ingestion.management.commands.sync_hubspot_contacts_new.asyncio.run') as mock_asyncio_run:
            mock_asyncio_run.side_effect = Exception("Sync failed")
            
            with self.assertRaises(Exception):
                call_command('sync_hubspot_contacts_new', stdout=self.out)
                
            output = self.out.getvalue()
            self.assertIn('Sync failed', output)


class TestHubSpotSyncEngineIntegration(TestCase):
    """Test sync engine integration with management commands"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.out = StringIO()
        
    def test_get_sync_engine_contact_command(self):
        """Test sync engine creation for contact command"""
        command = ContactCommand()
        
        engine = command.get_sync_engine(batch_size=50, dry_run=True)
        
        self.assertEqual(engine.crm_source, 'hubspot')
        self.assertEqual(engine.sync_type, 'contacts')
        self.assertEqual(engine.batch_size, 50)
        self.assertTrue(engine.dry_run)
        
    def test_get_sync_engine_appointment_command(self):
        """Test sync engine creation for appointment command"""
        command = AppointmentCommand()
        
        engine = command.get_sync_engine(batch_size=75, dry_run=False)
        
        self.assertEqual(engine.crm_source, 'hubspot')
        self.assertEqual(engine.sync_type, 'appointments')
        self.assertEqual(engine.batch_size, 75)
        self.assertFalse(engine.dry_run)
        
    def test_get_sync_engine_division_command(self):
        """Test sync engine creation for division command"""
        command = DivisionCommand()
        
        engine = command.get_sync_engine()
        
        self.assertEqual(engine.crm_source, 'hubspot')
        self.assertEqual(engine.sync_type, 'divisions')
        self.assertEqual(engine.batch_size, 50)  # Default for divisions
        
    def test_get_sync_engine_deal_command(self):
        """Test sync engine creation for deal command"""
        command = DealCommand()
        
        engine = command.get_sync_engine()
        
        self.assertEqual(engine.crm_source, 'hubspot')
        self.assertEqual(engine.sync_type, 'deals')
        self.assertEqual(engine.batch_size, 100)  # Default for deals
        
    def test_get_sync_engine_association_command(self):
        """Test sync engine creation for association command"""
        command = AssociationCommand()
        
        engine = command.get_sync_engine()
        
        self.assertEqual(engine.crm_source, 'hubspot')
        self.assertEqual(engine.sync_type, 'associations')
        self.assertEqual(engine.batch_size, 100)  # Default for associations
        
    def test_get_sync_name_methods(self):
        """Test sync name methods for all commands"""
        commands = [
            (ContactCommand(), 'contacts'),
            (AppointmentCommand(), 'appointments'),
            (DivisionCommand(), 'divisions'),
            (DealCommand(), 'deals'),
            (AssociationCommand(), 'associations')
        ]
        
        for command, expected_name in commands:
            self.assertEqual(command.get_sync_name(), expected_name)


class TestHubSpotAllNewCommand(TestCase):
    """Test the comprehensive sync_hubspot_all_new command"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.out = StringIO()
        
    @patch('ingestion.management.commands.sync_hubspot_all_new.call_command')
    def test_all_sync_command_success(self, mock_call_command):
        """Test successful execution of all sync commands"""
        # Mock successful execution of all commands
        mock_call_command.return_value = None
        
        # Mock SyncHistory queries
        with patch('ingestion.management.commands.sync_hubspot_all_new.SyncHistory.objects.filter') as mock_filter:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 10
            mock_history.records_updated = 90
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 10.0}
            mock_filter.return_value.order_by.return_value.first.return_value = mock_history
            
            call_command('sync_hubspot_all_new', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Starting comprehensive HubSpot sync', output)
            self.assertIn('HUBSPOT SYNC COMPLETE', output)
            self.assertIn('All HubSpot sync operations completed successfully', output)
            
            # Check that all sync commands were called
            expected_calls = [
                'sync_hubspot_divisions_new',
                'sync_hubspot_contacts_new',
                'sync_hubspot_appointments_new',
                'sync_hubspot_deals_new',
                'sync_hubspot_associations_new'
            ]
            
            for expected_cmd in expected_calls:
                mock_call_command.assert_any_call(expected_cmd)
                
    @patch('ingestion.management.commands.sync_hubspot_all_new.call_command')
    def test_all_sync_command_with_skip_associations(self, mock_call_command):
        """Test sync command with skip associations flag"""
        mock_call_command.return_value = None
        
        with patch('ingestion.management.commands.sync_hubspot_all_new.SyncHistory.objects.filter') as mock_filter:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 10
            mock_history.records_updated = 90
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 10.0}
            mock_filter.return_value.order_by.return_value.first.return_value = mock_history
            
            call_command('sync_hubspot_all_new', '--skip-associations', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Starting comprehensive HubSpot sync', output)
            
            # Check that association commands were not called
            association_calls = [call for call in mock_call_command.call_args_list 
                               if 'associations' in str(call)]
            self.assertEqual(len(association_calls), 0)
            
    @patch('ingestion.management.commands.sync_hubspot_all_new.call_command')
    def test_all_sync_command_with_failure(self, mock_call_command):
        """Test sync command handling failures"""
        # Mock a failure in one of the commands
        def mock_call_side_effect(cmd, *args, **kwargs):
            if cmd == 'sync_hubspot_contacts_new':
                raise Exception("Contact sync failed")
            return None
            
        mock_call_command.side_effect = mock_call_side_effect
        
        with patch('ingestion.management.commands.sync_hubspot_all_new.SyncHistory.objects.filter') as mock_filter:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 10
            mock_history.records_updated = 90
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 10.0}
            mock_filter.return_value.order_by.return_value.first.return_value = mock_history
            
            call_command('sync_hubspot_all_new', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Error running contacts sync', output)
            self.assertIn('command(s) failed', output)
            
    @patch('ingestion.management.commands.sync_hubspot_all_new.call_command')
    def test_all_sync_command_dry_run(self, mock_call_command):
        """Test sync command with dry run"""
        mock_call_command.return_value = None
        
        with patch('ingestion.management.commands.sync_hubspot_all_new.SyncHistory.objects.filter') as mock_filter:
            mock_history = MagicMock()
            mock_history.status = 'success'
            mock_history.records_processed = 100
            mock_history.records_created = 0  # No records created in dry run
            mock_history.records_updated = 0  # No records updated in dry run
            mock_history.records_failed = 0
            mock_history.performance_metrics = {'duration_seconds': 10.0}
            mock_filter.return_value.order_by.return_value.first.return_value = mock_history
            
            call_command('sync_hubspot_all_new', '--dry-run', stdout=self.out)
            
            output = self.out.getvalue()
            self.assertIn('Starting comprehensive HubSpot sync', output)
            
            # Check that --dry-run was passed to all commands
            for call_args in mock_call_command.call_args_list:
                self.assertIn('--dry-run', call_args[0] if call_args[0] else [])
