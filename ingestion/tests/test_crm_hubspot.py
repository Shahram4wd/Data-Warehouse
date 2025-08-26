"""
Tests for HubSpot CRM sync commands
"""
from unittest.mock import Mock, patch
from django.test import TestCase

from ingestion.management.commands.sync_hubspot_contacts import Command as HubSpotContactsCommand
from ingestion.management.commands.sync_hubspot_deals import Command as HubSpotDealsCommand
from ingestion.management.commands.sync_hubspot_all import Command as HubSpotAllCommand
from ingestion.management.commands.sync_hubspot_appointments import Command as HubSpotAppointmentsCommand
from ingestion.management.commands.sync_hubspot_appointments_removal import Command as HubSpotAppointmentsRemovalCommand
from ingestion.management.commands.sync_hubspot_associations import Command as HubSpotAssociationsCommand
from ingestion.management.commands.sync_hubspot_contacts_removal import Command as HubSpotContactsRemovalCommand
from ingestion.management.commands.sync_hubspot_divisions import Command as HubSpotDivisionsCommand
from ingestion.management.commands.sync_hubspot_genius_users import Command as HubSpotGeniusUsersCommand
from ingestion.management.commands.sync_hubspot_zipcodes import Command as HubSpotZipcodesCommand


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
        
        # Verify HubSpot's flag system uses consolidated flags
        expected_flags = ['--full', '--debug', '--skip-validation', '--dry-run', '--batch-size', 
                         '--max-records', '--start-date', '--force']
        
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
        hubspot_flags = ['--full', '--debug', '--skip-validation', '--dry-run', '--batch-size', '--max-records', '--start-date', '--force']
        
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


class TestHubSpotAppointmentsCommand(TestCase):
    """Test HubSpot appointments sync command"""
    
    def setUp(self):
        self.command = HubSpotAppointmentsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertIn('HubSpot', self.command.help)
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_appointments_sync_name(self):
        """Unit Test: Appointments-specific sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'appointments')
        
    @patch('ingestion.management.commands.sync_hubspot_appointments.HubSpotAppointmentSyncEngine')
    def test_integration_appointments_engine_init(self, mock_engine_class):
        """Integration Test: Appointments engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 75, 'dry_run': False, 'force_overwrite': True}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once_with(
            batch_size=75,
            dry_run=False, 
            force_overwrite=True
        )
        
    def test_unit_hubspot_architecture_compliance(self):
        """Unit Test: BaseHubSpotSyncCommand architecture compliance"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        hubspot_flags = ['--force', '--batch-size', '--max-records', '--start-date']
        
        for flag in hubspot_flags:
            self.assertIn(flag, argument_calls, f"HubSpot architecture flag {flag} missing")


class TestHubSpotAppointmentsRemovalCommand(TestCase):
    """Test HubSpot appointments removal sync command"""
    
    def setUp(self):
        self.command = HubSpotAppointmentsRemovalCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_appointments_removal_sync_name(self):
        """Unit Test: Appointments removal sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'appointments_removal')
        
    @patch('ingestion.management.commands.sync_hubspot_appointments_removal.HubSpotAppointmentRemovalSyncEngine')
    def test_integration_removal_engine_init(self, mock_engine_class):
        """Integration Test: Removal engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 50, 'dry_run': True, 'force_overwrite': False}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once()
        
    def test_e2e_removal_command_workflow(self):
        """E2E Test: Removal command workflow validation"""
        # Test that removal commands maintain HubSpot architecture
        self.assertTrue(callable(getattr(self.command, 'get_sync_engine', None)))
        help_text = self.command.help.lower() if self.command.help else ""
        self.assertIn('removal', help_text)


class TestHubSpotAssociationsCommand(TestCase):
    """Test HubSpot associations sync command"""
    
    def setUp(self):
        self.command = HubSpotAssociationsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_associations_sync_name(self):
        """Unit Test: Associations sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'associations')
        
    @patch('ingestion.management.commands.sync_hubspot_associations.HubSpotAssociationSyncEngine')
    def test_integration_associations_engine_init(self, mock_engine_class):
        """Integration Test: Associations engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 100, 'dry_run': False, 'force_overwrite': False}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once()
        
    def test_unit_associations_hubspot_flags(self):
        """Unit Test: HubSpot associations flags"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        self.assertIn('--batch-size', argument_calls)
        self.assertIn('--force', argument_calls)


class TestHubSpotContactsRemovalCommand(TestCase):
    """Test HubSpot contacts removal sync command"""
    
    def setUp(self):
        self.command = HubSpotContactsRemovalCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_contacts_removal_sync_name(self):
        """Unit Test: Contacts removal sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'contacts_removal')
        
    @patch('ingestion.management.commands.sync_hubspot_contacts_removal.HubSpotContactRemovalSyncEngine')
    def test_integration_contacts_removal_engine_init(self, mock_engine_class):
        """Integration Test: Contacts removal engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 200, 'dry_run': True, 'force_overwrite': True}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once()
        
    def test_e2e_contacts_removal_workflow(self):
        """E2E Test: Contacts removal workflow validation"""
        help_text = self.command.help.lower() if self.command.help else ""
        removal_indicators = ['contact', 'removal', 'hubspot']
        
        for indicator in removal_indicators:
            self.assertIn(indicator, help_text, f"Contacts removal should mention '{indicator}'")


class TestHubSpotDivisionsCommand(TestCase):
    """Test HubSpot divisions sync command"""
    
    def setUp(self):
        self.command = HubSpotDivisionsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_divisions_sync_name(self):
        """Unit Test: Divisions sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'divisions')
        
    @patch('ingestion.management.commands.sync_hubspot_divisions.HubSpotDivisionSyncEngine')
    def test_integration_divisions_engine_init(self, mock_engine_class):
        """Integration Test: Divisions engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 25, 'dry_run': False, 'force_overwrite': False}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once_with(
            batch_size=25,
            dry_run=False,
            force_overwrite=False
        )
        
    def test_unit_divisions_architecture_validation(self):
        """Unit Test: Divisions command architecture validation"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        required_flags = ['--full', '--debug', '--dry-run']
        
        for flag in required_flags:
            self.assertIn(flag, argument_calls, f"Required HubSpot flag {flag} missing")


class TestHubSpotGeniusUsersCommand(TestCase):
    """Test HubSpot genius users sync command"""
    
    def setUp(self):
        self.command = HubSpotGeniusUsersCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertIn('Genius Users', self.command.help)
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_genius_users_sync_name(self):
        """Unit Test: Genius users sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'genius_users')
        
    @patch('ingestion.management.commands.sync_hubspot_genius_users.HubSpotGeniusUsersSyncEngine')
    def test_integration_genius_users_engine_init(self, mock_engine_class):
        """Integration Test: Genius users engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 100, 'dry_run': True, 'force_overwrite': True}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once_with(
            batch_size=100,
            dry_run=True,
            force_overwrite=True
        )
        
    def test_e2e_genius_users_custom_object_support(self):
        """E2E Test: Custom object support validation"""
        # Genius users is a custom object - test specific features
        help_text = self.command.help.lower()
        custom_object_indicators = ['genius', 'custom object', 'delta sync']
        
        for indicator in custom_object_indicators:
            self.assertIn(indicator, help_text, f"Genius users should mention '{indicator}'")
            
    def test_unit_genius_users_advanced_flags(self):
        """Unit Test: Genius users advanced flags"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        advanced_flags = ['--max-records', '--start-date', '--force']
        
        for flag in advanced_flags:
            self.assertIn(flag, argument_calls, f"Advanced flag {flag} missing")


class TestHubSpotZipcodesCommand(TestCase):
    """Test HubSpot zipcodes sync command"""
    
    def setUp(self):
        self.command = HubSpotZipcodesCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'get_sync_engine'))
        self.assertTrue(hasattr(self.command, 'get_sync_name'))
        
    def test_unit_zipcodes_sync_name(self):
        """Unit Test: Zipcodes sync name"""
        sync_name = self.command.get_sync_name()
        self.assertEqual(sync_name, 'zipcodes')
        
    @patch('ingestion.management.commands.sync_hubspot_zipcodes.HubSpotZipcodeSyncEngine')
    def test_integration_zipcodes_engine_init(self, mock_engine_class):
        """Integration Test: Zipcodes engine initialization"""
        mock_engine = Mock()
        mock_engine_class.return_value = mock_engine
        
        options = {'batch_size': 150, 'dry_run': False, 'force_overwrite': False}
        engine = self.command.get_sync_engine(**options)
        
        mock_engine_class.assert_called_once_with(
            batch_size=150,
            dry_run=False,
            force_overwrite=False
        )
        
    def test_e2e_zipcodes_data_validation(self):
        """E2E Test: Zipcodes data validation"""
        # Test that zipcodes command follows HubSpot patterns
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        self.assertIn('--batch-size', argument_calls)
        
        # Verify help text mentions zipcodes
        help_text = self.command.help.lower() if self.command.help else ""
        self.assertIn('zipcode', help_text)
        
    def test_unit_zipcodes_hubspot_consistency(self):
        """Unit Test: Zipcodes HubSpot consistency"""
        # Verify consistent flag structure across all HubSpot commands
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        consistent_flags = ['--full', '--debug', '--skip-validation', '--dry-run', '--force']
        
        for flag in consistent_flags:
            self.assertIn(flag, argument_calls, f"Consistent HubSpot flag {flag} missing from zipcodes")
