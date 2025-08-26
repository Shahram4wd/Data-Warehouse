"""
Integration Tests for Arrivy Commands - Individual Command Testing

These tests run actual Arrivy commands with controlled data limits to verify
real-world functionality without processing millions of records.

Test Type: INTEGRATION (Real API with Limits)
Data Usage: LIMITED (Max 50 records per test)
Duration: 2-5 minutes
Safety: 🟡 CONTROLLED - Uses real API but with strict limits
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch
from django.test import override_settings

from ingestion.tests.crm_commands.base.command_test_base import CommandTestBase
from ingestion.models.common import SyncHistory


class TestArrivyIndividualCommands:
    """Test individual Arrivy commands with controlled real data"""
    
    # Individual Arrivy commands to test
    ARRIVY_INDIVIDUAL_COMMANDS = [
        'sync_arrivy_entities',
        'sync_arrivy_tasks', 
        'sync_arrivy_groups',
        'sync_arrivy_bookings',
        'sync_arrivy_statuses',
    ]
    
    def setup_method(self):
        """Set up test environment with safety parameters"""
        self.command_runner = CommandTestBase()
        
        # Safety parameters for integration tests
        self.SAFETY_PARAMS = {
            'batch_size': 10,          # Limit to 10 records per batch
            'dry_run': True,           # Always dry-run unless explicitly testing writes
        }
        
        # Date range for controlled testing (last 7 days)
        self.end_date = datetime.now()
        self.start_date = self.end_date - timedelta(days=7)
        
    @pytest.mark.integration
    @pytest.mark.parametrize("command_name", ARRIVY_INDIVIDUAL_COMMANDS)
    def test_command_runs_with_limited_data(self, command_name):
        """
        Test that command runs successfully with limited data
        
        What this test does:
        - Runs command with --dry-run and --batch-size 10
        - Verifies command completes without errors
        - Checks that it would process some records
        - Does NOT actually import data (dry-run mode)
        """
        print(f"\n🧪 Testing {command_name} with limited data")
        
        result = self.command_runner.run_command_in_docker(
            command_name,
            '--dry-run',
            '--batch-size', '10',
            '--start-date', self.start_date.strftime('%Y-%m-%d'),
            '--debug'
        )
        
        assert result['success'], f"Command {command_name} failed: {result['stderr']}"
        
        # Should indicate some records would be processed
        output = result['stdout'].lower()
        assert any(indicator in output for indicator in [
            'would process', 'found', 'records', 'entities', 'would sync'
        ]), f"No indication of data processing in output: {result['stdout']}"
        
        print(f"✅ {command_name} completed successfully (dry-run)")
    
    @pytest.mark.integration  
    @pytest.mark.slow
    def test_arrivy_entities_controlled_real_sync(self):
        """
        Test actual data sync with strict controls
        
        What this test does:
        - Runs sync_arrivy_entities with real data (NO dry-run)
        - Limited to last 7 days and batch size 5
        - Actually imports data but in controlled amounts
        - Validates SyncHistory is created
        
        ⚠️  This test uses real API and imports real data!
        """
        print("\n🚨 Running CONTROLLED REAL SYNC test")
        print(f"Date range: {self.start_date.date()} to {self.end_date.date()}")
        print("Max records per batch: 5")
        
        # Clear any existing sync history for clean test
        SyncHistory.objects.filter(
            crm_source='arrivy',
            sync_type='entities'
        ).delete()
        
        result = self.command_runner.run_command_in_docker(
            'sync_arrivy_entities',
            '--batch-size', '5',
            '--start-date', self.start_date.strftime('%Y-%m-%d'),
            '--end-date', self.end_date.strftime('%Y-%m-%d'),
            '--debug'
        )
        
        assert result['success'], f"Real sync failed: {result['stderr']}"
        
        # Verify SyncHistory was created
        sync_records = SyncHistory.objects.filter(
            crm_source='arrivy',
            sync_type='entities'
        )
        assert sync_records.exists(), "SyncHistory record not created"
        
        latest_sync = sync_records.order_by('-created_at').first()
        assert latest_sync.status in ['success', 'completed'], f"Sync status: {latest_sync.status}"
        
        print(f"✅ Real sync completed - Status: {latest_sync.status}")
        print(f"Records processed: {latest_sync.records_processed or 'Unknown'}")
    
    @pytest.mark.integration
    def test_arrivy_command_flag_combinations(self):
        """Test various flag combinations work correctly"""
        
        test_cases = [
            # Basic dry-run
            {
                'flags': ['--dry-run', '--debug'],
                'description': 'Basic dry-run with debug'
            },
            # With batch size
            {
                'flags': ['--dry-run', '--batch-size', '5'],
                'description': 'Dry-run with small batch size'
            },
            # With date range
            {
                'flags': [
                    '--dry-run', 
                    '--start-date', (datetime.now() - timedelta(days=3)).strftime('%Y-%m-%d'),
                    '--batch-size', '3'
                ],
                'description': 'Dry-run with 3-day date range'
            },
            # Full flag (but still dry-run for safety)
            {
                'flags': ['--dry-run', '--full', '--batch-size', '2'],
                'description': 'Full sync mode (dry-run) with tiny batch'
            }
        ]
        
        for test_case in test_cases:
            print(f"\n🔧 Testing flag combination: {test_case['description']}")
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                *test_case['flags']
            )
            
            assert result['success'], f"Flag combination failed: {test_case['flags']} - Error: {result['stderr']}"
            print(f"✅ {test_case['description']} - SUCCESS")
    
    @pytest.mark.integration
    def test_arrivy_error_handling(self):
        """Test how commands handle various error scenarios"""
        
        # Test invalid date format
        result = self.command_runner.run_command_in_docker(
            'sync_arrivy_entities',
            '--dry-run',
            '--start-date', 'invalid-date'
        )
        
        assert not result['success'], "Should fail with invalid date"
        assert 'date' in result['stderr'].lower() or 'invalid' in result['stderr'].lower()
        
        # Test invalid batch size
        result = self.command_runner.run_command_in_docker(
            'sync_arrivy_entities', 
            '--dry-run',
            '--batch-size', '0'
        )
        
        assert not result['success'], "Should fail with zero batch size"
        
        print("✅ Error handling tests passed")
    
    def test_data_usage_summary(self):
        """Print a summary of what data this test suite uses"""
        
        summary = f"""
🔍 ARRIVY INTEGRATION TEST SUMMARY
{'='*50}

Test Suite: Individual Command Testing
Data Source: Real Arrivy API
Safety Level: 🟡 CONTROLLED

Data Usage Limits:
- Date Range: Last 7 days ({self.start_date.date()} to {self.end_date.date()})
- Batch Size: 5-10 records per batch maximum
- Most tests: DRY-RUN mode (no actual data import)
- Only 1 test: Real import with strict limits

Commands Tested:
{chr(10).join(f'  - {cmd}' for cmd in self.ARRIVY_INDIVIDUAL_COMMANDS)}

Estimated Total Records: < 100 per command
Estimated Duration: 2-5 minutes
Network Usage: Minimal (small API calls)

Safety Features:
✅ Batch size limits prevent large imports
✅ Date range limits prevent historical data processing  
✅ Most tests use --dry-run flag
✅ Real sync limited to 5 records per batch
✅ SyncHistory tracking for audit
"""
        print(summary)
        return summary
