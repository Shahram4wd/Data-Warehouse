"""
Tests for Google Sheets CRM sync commands
"""
from unittest.mock import Mock, patch
from django.test import TestCase
from django.core.management import call_command
from io import StringIO

from ingestion.management.commands.sync_gsheet_marketing_leads import Command as GSheetMarketingLeadsCommand
from ingestion.management.commands.sync_gsheet_marketing_spends import Command as GSheetMarketingSpendsCommand
from ingestion.management.commands.sync_gsheet_all import Command as GSheetAllCommand


class TestGSheetMarketingLeadsSyncCommand(TestCase):
    """Test GSheet marketing leads sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetMarketingLeadsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync Marketing Source Leads from Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'marketing_leads')
        
    def test_unit_argument_parsing(self):
        """Unit Test: Command argument parsing with GSheet-specific flags"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        # Verify standard flags plus GSheet-specific ones
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Standard flags
        self.assertIn('--full', argument_calls)
        self.assertIn('--force', argument_calls)
        self.assertIn('--start-date', argument_calls)
        self.assertIn('--dry-run', argument_calls)
        self.assertIn('--batch-size', argument_calls)
        
        # GSheet-specific flags
        self.assertIn('--test-connection', argument_calls)
        self.assertIn('--show-summary', argument_calls)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_leads.MarketingLeadsSyncEngine')
    def test_integration_connection_test(self, mock_engine_class):
        """Integration Test: Google Sheets API connection test"""
        # Setup mocks
        mock_engine = Mock()
        mock_client = Mock()
        mock_client.test_connection.return_value = True
        mock_engine.client = mock_client
        mock_engine_class.return_value = mock_engine
        
        # Test connection only
        out = StringIO()
        call_command('sync_gsheet_marketing_leads', '--test-connection', stdout=out)
        
        # Verify connection test was called
        mock_client.test_connection.assert_called_once()
        output = out.getvalue()
        self.assertIn('Google Sheets API connection successful', output)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_leads.MarketingLeadsSyncEngine')
    def test_e2e_standardized_sync(self, mock_engine_class):
        """E2E Test: Full sync with standardized flags and GSheet functionality"""
        # Setup mocks for safe testing
        mock_engine = Mock()
        mock_engine.sync_with_retry_sync.return_value = {
            'status': 'success',
            'success': True,
            'records_processed': 150,
            'records_created': 120,
            'records_updated': 30,
            'records_failed': 0,
            'sheet_info': {
                'name': 'Marketing Leads Test Sheet',
                'estimated_data_rows': 150
            },
            'duration': 25.7
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with standardized flags
        out = StringIO()
        call_command('sync_gsheet_marketing_leads', '--force', '--dry-run', 
                    '--max-records', '150', '--batch-size', '50', stdout=out)
        
        # Verify engine was initialized with correct parameters
        mock_engine_class.assert_called_once_with(
            batch_size=50,
            dry_run=True,
            force_overwrite=True,
            max_records=150
        )
        
        # Verify sync execution
        mock_engine.sync_with_retry_sync.assert_called_once_with(max_retries=2)
        
        # Verify output
        output = out.getvalue()
        self.assertIn('Starting GSheet marketing leads sync', output)
        self.assertIn('Marketing Leads sync completed successfully', output)


class TestGSheetMarketingSpendsCommand(TestCase):
    """Test GSheet marketing spends sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetMarketingSpendsCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync marketing spends data from Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'marketing_spends')
        
    def test_unit_gsheet_specific_features(self):
        """Unit Test: GSheet-specific feature support"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify GSheet-specific flags are present
        self.assertIn('--test-connection', argument_calls)
        self.assertIn('--show-summary', argument_calls)
        
    @patch('ingestion.management.commands.sync_gsheet_marketing_spends.MarketingSpendsSyncEngine')
    def test_integration_full_standardized_sync(self, mock_engine_class):
        """Integration Test: Full sync with all standardized flags"""
        # Setup mocks
        mock_engine = Mock()
        mock_engine.sync_with_retry_sync.return_value = {
            'status': 'success',
            'success': True,
            'records_processed': 75,
            'records_created': 50,
            'records_updated': 25,
            'records_failed': 0,
            'sheet_info': {
                'name': 'Marketing Spends Test Sheet',
                'estimated_data_rows': 75
            },
            'duration': 18.4
        }
        mock_engine_class.return_value = mock_engine
        
        # Execute with comprehensive standardized flags
        out = StringIO()
        call_command('sync_gsheet_marketing_spends', '--full', '--force', 
                    '--dry-run', '--max-records', '75', '--batch-size', '25', stdout=out)
        
        # Verify proper initialization
        mock_engine_class.assert_called_once_with(
            batch_size=25,
            dry_run=True,
            force_overwrite=True
        )
        
        # Verify output contains success message
        output = out.getvalue()
        self.assertIn('Starting GSheet marketing spends sync', output)


class TestGSheetAllCommand(TestCase):
    """Test GSheet all sync command following BaseSyncCommand pattern"""
    
    def setUp(self):
        self.command = GSheetAllCommand()
        
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertEqual(self.command.help, 'Sync all configured Google Sheets to database')
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        self.assertEqual(self.command.crm_name, 'gsheet')
        self.assertEqual(self.command.entity_name, 'all')
        
    def test_unit_comprehensive_gsheet_control(self):
        """Unit Test: Comprehensive GSheet control options"""
        parser = Mock()
        self.command.add_arguments(parser)
        
        argument_calls = [call[0][0] for call in parser.add_argument.call_args_list]
        
        # Verify all standard flags plus GSheet-specific control flags
        expected_flags = ['--full', '--force', '--start-date', '--dry-run', 
                         '--skip-marketing-leads', '--skip-marketing-spends',
                         '--test-connections', '--show-summary']
        
        for flag in expected_flags:
            self.assertIn(flag, argument_calls, f"Expected flag {flag} not found")
            
    def test_integration_comprehensive_sheet_coverage(self):
        """Integration Test: Verify comprehensive sheet coverage"""
        # This test verifies the command includes all major GSheet entities
        help_text = self.command.help.lower()
        
        # Verify comprehensive coverage mentioned
        self.assertIn('all configured', help_text)
        self.assertIn('google sheets', help_text)
        
        # Test that both skip options work
        parser = Mock()
        self.command.add_arguments(parser)
        
        skip_calls = [call for call in parser.add_argument.call_args_list 
                      if 'skip-marketing' in str(call)]
        self.assertEqual(len(skip_calls), 2)  # marketing-leads and marketing-spends
