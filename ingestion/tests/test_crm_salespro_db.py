"""
SalesPro DB Command Testing
Tests for database-based SalesPro sync commands that pull data from AWS Athena
"""

import json
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.utils import timezone
from io import StringIO

from ingestion.tests.command_test_base import CRMCommandTestBase


class SalesProDBTestBase(CRMCommandTestBase):
    """Base test class for SalesPro DB command testing"""
    
    def setUp(self):
        super().setUp()
        # Mock AWS credentials and database connections
        self.aws_patcher = patch.dict('os.environ', {
            'AWS_ACCESS_KEY_ID': 'mock_aws_key',
            'AWS_SECRET_ACCESS_KEY': 'mock_aws_secret',
            'AWS_DEFAULT_REGION': 'us-east-1'
        })
        self.aws_patcher.start()
    
    def tearDown(self):
        super().tearDown()
        self.aws_patcher.stop()
    
    def create_mock_athena_response(self, count=100):
        """Create mock AWS Athena response data"""
        records = []
        for i in range(count):
            records.append({
                'customer_id': f'cust_{i+1}',
                'estimate_id': f'est_{i+1}',
                'company_id': f'comp_{i+1}',
                'company_name': f'Company {i+1}',
                'customer_first_name': f'FirstName{i+1}',
                'customer_last_name': f'LastName{i+1}',
                'crm_source': 'salesforce',
                'crm_source_id': f'sf_{i+1}'
            })
        return records


class TestSalesProCustomersCommand(SalesProDBTestBase):
    """Test SalesPro Customers DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_salespro_customers import Command
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
        args = parser.parse_args(['--full', '--debug', '--batch-size', '500'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        self.assertEqual(args.batch_size, 500)
        
    def test_unit_sync_engine_initialization(self):
        """Unit Test: SalesPro sync engine initialization"""
        # Test that the command can initialize its sync engine
        self.assertTrue(hasattr(self.command, 'sync_engine_class'))
        
    @patch('ingestion.management.commands.db_salespro_customers.SalesProCustomerSyncEngine')
    def test_integration_dry_run_execution(self, mock_engine_class):
        """Integration Test: Dry run execution with mocked engine"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 100,
            'created': 50,
            'updated': 50,
            'errors': 0
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command('db_salespro_customers', '--dry-run', '--debug', stdout=output)
        
        # Verify engine was called with dry_run
        mock_engine.run_sync.assert_called_once()
        self.assertIn('dry_run', mock_engine.run_sync.call_args[1])
        
    @patch('ingestion.management.commands.db_salespro_customers.SalesProCustomerSyncEngine')
    def test_e2e_full_sync_workflow(self, mock_engine_class):
        """E2E Test: Complete full sync workflow"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 1000,
            'created': 800,
            'updated': 200,
            'errors': 0,
            'duration': '2m 30s'
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command(
            'db_salespro_customers',
            '--full',
            '--batch-size', '250',
            '--debug',
            stdout=output
        )
        
        # Verify full sync parameters
        call_args = mock_engine.run_sync.call_args[1]
        self.assertTrue(call_args.get('full_sync', False))
        self.assertEqual(call_args.get('batch_size', 100), 250)


class TestSalesProEstimatesCommand(SalesProDBTestBase):
    """Test SalesPro Estimates DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_salespro_estimates import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command structure"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_estimates_specific_arguments(self):
        """Unit Test: Estimates-specific command arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        # Test that standard database sync arguments are present
        args = parser.parse_args(['--full', '--since', '2024-01-01'])
        self.assertTrue(args.full)
        
    @patch('ingestion.management.commands.db_salespro_estimates.SalesProEstimateSyncEngine')
    def test_integration_incremental_sync(self, mock_engine_class):
        """Integration Test: Incremental sync execution"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 150,
            'created': 100,
            'updated': 50,
            'errors': 0
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command('db_salespro_estimates', '--debug', stdout=output)
        
        mock_engine.run_sync.assert_called_once()
        
    @patch('ingestion.management.commands.db_salespro_estimates.SalesProEstimateSyncEngine')
    def test_e2e_date_range_sync(self, mock_engine_class):
        """E2E Test: Date range sync workflow"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 500,
            'created': 400,
            'updated': 100,
            'date_range': '2024-01-01 to 2024-02-01'
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command(
            'db_salespro_estimates',
            '--since', '2024-01-01',
            '--end-date', '2024-02-01',
            '--debug',
            stdout=output
        )
        
        # Verify date range parameters
        call_args = mock_engine.run_sync.call_args[1]
        self.assertIn('since_date', call_args)


class TestSalesProCreditApplicationsCommand(SalesProDBTestBase):
    """Test SalesPro Credit Applications DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_salespro_creditapplications import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_credit_applications_arguments(self):
        """Unit Test: Credit applications specific arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--batch-size', '100'])
        self.assertTrue(args.full)
        self.assertEqual(args.batch_size, 100)
        
    @patch('ingestion.management.commands.db_salespro_creditapplications.SalesProCreditApplicationSyncEngine')
    def test_integration_batch_processing(self, mock_engine_class):
        """Integration Test: Batch processing execution"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 200,
            'batches': 4,
            'batch_size': 50
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command(
            'db_salespro_creditapplications', 
            '--batch-size', '50',
            '--debug',
            stdout=output
        )
        
        mock_engine.run_sync.assert_called_once()


class TestSalesProLeadResultsCommand(SalesProDBTestBase):
    """Test SalesPro Lead Results DB sync command"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_salespro_leadresults import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Basic command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_lead_results_arguments(self):
        """Unit Test: Lead results specific arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--debug'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        
    @patch('ingestion.management.commands.db_salespro_leadresults.SalesProLeadResultSyncEngine')
    def test_integration_lead_results_sync(self, mock_engine_class):
        """Integration Test: Lead results sync execution"""
        mock_engine = Mock()
        mock_engine.run_sync.return_value = {
            'processed': 300,
            'lead_results': 300,
            'estimates_updated': 150
        }
        mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command('db_salespro_leadresults', '--debug', stdout=output)
        
        mock_engine.run_sync.assert_called_once()


class TestSalesProAllCommand(SalesProDBTestBase):
    """Test SalesPro All DB sync command (unified sync)"""
    
    def setUp(self):
        super().setUp()
        from ingestion.management.commands.db_salespro_all import Command
        self.command = Command()
    
    def test_unit_basic_functionality(self):
        """Unit Test: Unified sync command functionality"""
        self.assertTrue(hasattr(self.command, 'add_arguments'))
        self.assertTrue(hasattr(self.command, 'handle'))
        
    def test_unit_unified_sync_arguments(self):
        """Unit Test: Unified sync command arguments"""
        parser = self.create_argument_parser()
        self.command.add_arguments(parser)
        
        args = parser.parse_args(['--full', '--parallel', '--debug'])
        self.assertTrue(args.full)
        self.assertTrue(args.debug)
        
    @patch('ingestion.management.commands.db_salespro_all.SalesProCustomerSyncEngine')
    @patch('ingestion.management.commands.db_salespro_all.SalesProEstimateSyncEngine')
    @patch('ingestion.management.commands.db_salespro_all.SalesProCreditApplicationSyncEngine')
    @patch('ingestion.management.commands.db_salespro_all.SalesProLeadResultSyncEngine')
    def test_integration_unified_sync_execution(self, mock_leadresults, mock_credit, mock_estimates, mock_customers):
        """Integration Test: Unified sync of all SalesPro entities"""
        # Mock all sync engines
        for mock_engine_class in [mock_leadresults, mock_credit, mock_estimates, mock_customers]:
            mock_engine = Mock()
            mock_engine.run_sync.return_value = {'processed': 100, 'created': 50, 'updated': 50}
            mock_engine_class.return_value = mock_engine
        
        output = StringIO()
        call_command('db_salespro_all', '--debug', stdout=output)
        
        # Verify all engines were called
        mock_customers.assert_called_once()
        mock_estimates.assert_called_once()
        mock_credit.assert_called_once()
        mock_leadresults.assert_called_once()
        
    @patch('ingestion.management.commands.db_salespro_all.SalesProCustomerSyncEngine')
    @patch('ingestion.management.commands.db_salespro_all.SalesProEstimateSyncEngine')
    def test_e2e_unified_full_sync(self, mock_estimates, mock_customers):
        """E2E Test: Complete unified full sync workflow"""
        # Mock sync engines with realistic responses
        mock_customer_engine = Mock()
        mock_customer_engine.run_sync.return_value = {
            'processed': 1000,
            'created': 800,
            'updated': 200
        }
        mock_customers.return_value = mock_customer_engine
        
        mock_estimate_engine = Mock()
        mock_estimate_engine.run_sync.return_value = {
            'processed': 2000,
            'created': 1500,
            'updated': 500
        }
        mock_estimates.return_value = mock_estimate_engine
        
        output = StringIO()
        call_command('db_salespro_all', '--full', '--debug', stdout=output)
        
        # Verify full sync was propagated to all engines
        customer_call_args = mock_customer_engine.run_sync.call_args[1]
        estimate_call_args = mock_estimate_engine.run_sync.call_args[1]
        
        self.assertTrue(customer_call_args.get('full_sync', False))
        self.assertTrue(estimate_call_args.get('full_sync', False))
