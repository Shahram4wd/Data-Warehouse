"""
Tests for HubSpot CRM sync commands
"""
from unittest.mock import Mock, patch
from django.test import TestCase

from ingestion.management.commands.sync_hubspot_contacts import Command as HubSpotContactsCommand
from ingestion.management.commands.sync_hubspot_deals import Command as HubSpotDealsCommand
from ingestion.management.commands.sync_hubspot_all import Command as HubSpotAllCommand


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
