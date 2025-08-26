"""
Test suite for Arrivy management commands

Comprehensive testing of all Arrivy sync commands:
- sync_arrivy_all (orchestration command)
- sync_arrivy_entities
- sync_arrivy_tasks  
- sync_arrivy_groups
- sync_arrivy_bookings
- sync_arrivy_statuses

Tests cover:
1. Flag validation and standardization compliance
2. Dry-run mode behavior and database safety
3. SyncHistory compliance (mandatory per crm_sync_guide.md)
4. API error handling with realistic scenarios
5. Real sync execution with mocked APIs
6. Orchestration and dependency management
"""
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from django.test import override_settings
from django.core.management.base import CommandError
from django.utils import timezone

from ingestion.tests.crm_commands.base.command_test_base import CommandTestBase
from ingestion.tests.crm_commands.base.sync_history_validator import SyncHistoryComplianceValidator
from ingestion.tests.crm_commands.base.mock_responses import CRMMockResponses, APIErrorSimulator
from ingestion.models.common import SyncHistory


class TestArrivyCommands:
    """
    Test suite for all Arrivy management commands
    
    Uses Docker-based testing with mocked APIs for reliable testing
    without external dependencies.
    """
    
    # All Arrivy commands to test
    ARRIVY_COMMANDS = [
        'sync_arrivy_all',       # Orchestration command
        'sync_arrivy_entities',  # Individual entity commands
        'sync_arrivy_tasks',
        'sync_arrivy_groups', 
        'sync_arrivy_bookings',
        'sync_arrivy_statuses',
    ]
    
    # Individual commands (non-orchestration)
    INDIVIDUAL_COMMANDS = [
        'sync_arrivy_entities',
        'sync_arrivy_tasks',
        'sync_arrivy_groups',
        'sync_arrivy_bookings', 
        'sync_arrivy_statuses',
    ]
    
    def setup_method(self):
        """Set up test fixtures for each test method"""
        self.command_runner = CommandTestBase()
        self.sync_validator = SyncHistoryComplianceValidator(self.command_runner)
        self.mock_responses = CRMMockResponses.get_arrivy_responses()
        
        # Test API settings
        self.test_settings = {
            'ARRIVY_API_TOKEN': 'test_arrivy_token_12345',
            'ARRIVY_BASE_URL': 'https://test-api.arrivy.com/api/v1',
        }
    
    # ============================================================================
    # PHASE 2: Unit Tests for Argument Parsing and Flag Validation
    # ============================================================================
    
    def test_arrivy_commands_exist_and_importable(self):
        """Test that all expected Arrivy commands exist and can be imported"""
        for command_name in self.ARRIVY_COMMANDS:
            command = self.command_runner.get_command_instance(command_name)
            assert command is not None, f"Command {command_name} could not be imported"
    
    def test_arrivy_commands_have_required_flags(self):
        """Test that all Arrivy commands support required standardized flags"""
        for command_name in self.ARRIVY_COMMANDS:
            self.command_runner.assert_command_has_required_flags(command_name)
    
    def test_arrivy_commands_help_text_quality(self):
        """Test that all Arrivy commands have comprehensive help text"""
        for command_name in self.ARRIVY_COMMANDS:
            help_text = self.command_runner.get_command_help(command_name)
            
            # Help should be substantial and informative
            assert len(help_text) > 100, f"Help text too brief for {command_name}"
            
            # Should mention Arrivy
            assert 'arrivy' in help_text.lower(), f"Help doesn't mention Arrivy: {command_name}"
            
            # Should document key flags
            key_flags = ['--dry-run', '--full', '--debug', '--batch-size']
            self.command_runner.assert_help_mentions_flags(command_name, key_flags)
    
    @pytest.mark.parametrize('command_name', INDIVIDUAL_COMMANDS)
    def test_individual_commands_flag_validation(self, command_name, crm_api_settings):
        """Test flag validation for individual Arrivy commands"""
        
        # Test valid date format acceptance
        valid_result = self.command_runner.run_command_in_docker(
            command_name,
            '--start-date', '2025-01-01',
            '--dry-run'
        )
        # Should not fail due to date format (may fail for other reasons like missing API token)
        if not valid_result['success'] and valid_result['exception']:
            error_msg = str(valid_result['exception']).lower()
            assert 'date' not in error_msg or 'format' not in error_msg, (
                f"Valid date rejected by {command_name}: {valid_result['exception']}"
            )
        
        # Test invalid date format rejection
        invalid_result = self.command_runner.run_command_in_docker(
            command_name,
            '--start-date', 'invalid-date',
            '--dry-run'
        )
        
        assert not invalid_result['success'], (
            f"Invalid date accepted by {command_name}"
        )
    
    def test_conflicting_flags_handling(self, crm_api_settings):
        """Test that conflicting flags are handled appropriately"""
        # Test --full with --start-date (should conflict or override)
        result = self.command_runner.run_command_in_docker(
            'sync_arrivy_entities',
            '--full',
            '--start-date', '2025-01-01', 
            '--dry-run'
        )
        
        if result['success']:
            # Should mention override or conflict in output
            output = result['stdout'].lower()
            conflict_indicators = ['override', 'ignor', 'full sync', 'conflict']
            has_conflict_mention = any(indicator in output for indicator in conflict_indicators)
            assert has_conflict_mention, (
                f"No conflict indication for --full + --start-date: {result['stdout']}"
            )
        else:
            # Should be a clear error about conflicting flags
            error_msg = str(result['exception']).lower()
            assert 'conflict' in error_msg or 'cannot use' in error_msg, (
                f"Unclear error for conflicting flags: {result['exception']}"
            )
    
    def test_batch_size_parameter_validation(self, crm_api_settings):
        """Test batch size parameter validation across commands"""
        test_command = 'sync_arrivy_entities'
        
        # Valid batch sizes
        for valid_size in [1, 50, 100, 500, 1000]:
            result = self.command_runner.run_command_in_docker(
                test_command,
                '--batch-size', str(valid_size),
                '--dry-run'
            )
            # Should not fail due to batch size (may fail for other reasons)
            if not result['success']:
                error_msg = str(result['exception']).lower()
                assert 'batch' not in error_msg, (
                    f"Valid batch size {valid_size} rejected: {result['exception']}"
                )
        
        # Invalid batch sizes
        for invalid_size in [0, -1, -10]:
            result = self.command_runner.run_command_in_docker(
                test_command,
                '--batch-size', str(invalid_size),
                '--dry-run'
            )
            
            assert not result['success'], (
                f"Invalid batch size {invalid_size} accepted"
            )
    
    # ============================================================================
    # PHASE 3: Dry-Run Integration Tests
    # ============================================================================
    
    @pytest.mark.parametrize('command_name', INDIVIDUAL_COMMANDS)
    def test_dry_run_prevents_database_writes(self, command_name, crm_api_settings, 
                                            clean_sync_history, db_transaction):
        """Test that dry-run mode prevents all database writes"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            # Mock successful API response
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 5,
                'created': 3,
                'updated': 2,
                'failed': 0,
                'duration_seconds': 2.5,
            }
            
            # Test that no SyncHistory records created in dry-run
            result = self.command_runner.assert_dry_run_no_db_writes(
                command_name,
                SyncHistory
            )
            
            assert result['success'], f"Dry-run failed: {result['exception']}"
    
    @pytest.mark.parametrize('command_name', INDIVIDUAL_COMMANDS)
    def test_dry_run_output_indicates_no_writes(self, command_name, crm_api_settings):
        """Test that dry-run clearly states no database writes will occur"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 0, 'created': 0, 'updated': 0, 'failed': 0
            }
            
            result = self.command_runner.assert_dry_run_output_indicates_no_writes(command_name)
            assert result['success'], f"Dry-run indication failed: {result['exception']}"
    
    def test_dry_run_still_validates_api_connectivity(self, crm_api_settings):
        """Test that dry-run still attempts API calls for validation"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 10, 'created': 0, 'updated': 0, 'failed': 0
            }
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run'
            )
            
            # Should succeed and show data was processed (even if not saved)
            assert result['success'], f"Dry-run with API validation failed: {result}"
            
            # Should indicate data was processed
            output = result['stdout'].lower()
            processing_indicators = ['processed', 'found', 'fetched', 'retrieved']
            has_processing = any(indicator in output for indicator in processing_indicators)
            assert has_processing, f"No processing indication in dry-run: {result['stdout']}"
    
    # ============================================================================
    # PHASE 4: Flag Behavior Tests
    # ============================================================================
    
    def test_debug_flag_increases_verbosity(self, crm_api_settings):
        """Test that --debug flag produces more detailed output"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 5, 'created': 5, 'updated': 0, 'failed': 0
            }
            
            normal_result, debug_result = self.command_runner.assert_debug_increases_verbosity(
                'sync_arrivy_entities', '--dry-run'
            )
            
            assert normal_result['success'] and debug_result['success'], (
                f"Debug flag test failed: normal={normal_result}, debug={debug_result}"
            )
    
    def test_quiet_flag_reduces_output(self, crm_api_settings):
        """Test that --quiet flag suppresses non-essential output"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 5, 'created': 5, 'updated': 0, 'failed': 0
            }
            
            normal_result, quiet_result = self.command_runner.assert_quiet_reduces_output(
                'sync_arrivy_entities', '--dry-run'
            )
            
            assert normal_result['success'] and quiet_result['success'], (
                f"Quiet flag test failed: normal={normal_result}, quiet={quiet_result}"
            )
    
    # ============================================================================
    # PHASE 5: API Error Handling Tests  
    # ============================================================================
    
    def test_missing_api_token_error_handling(self):
        """Test handling of missing ARRIVY_API_TOKEN"""
        # Run without API token configured
        result = self.command_runner.run_command_in_docker(
            'sync_arrivy_entities',
            '--dry-run'
        )
        
        assert not result['success'], "Command should fail without API token"
        
        error_output = (result['stdout'] + result['stderr']).lower()
        token_error_indicators = ['token', 'api', 'credential', 'not configured', 'missing']
        has_token_error = any(indicator in error_output for indicator in token_error_indicators)
        assert has_token_error, (
            f"No clear API token error message: {error_output}"
        )
    
    def test_api_authentication_error_handling(self, crm_api_settings):
        """Test graceful handling of API authentication errors"""
        
        auth_error = APIErrorSimulator.authentication_error('arrivy')
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.side_effect = auth_error
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities', 
                '--dry-run'
            )
            
            assert not result['success'], "Should fail on authentication error"
            
            error_output = (result['stdout'] + result['stderr']).lower()
            auth_error_indicators = ['authentication', 'token', 'unauthorized', 'invalid']
            has_auth_error = any(indicator in error_output for indicator in auth_error_indicators)
            assert has_auth_error, (
                f"No clear authentication error message: {error_output}"
            )
    
    def test_api_timeout_error_handling(self, crm_api_settings):
        """Test handling of API timeout errors"""
        
        timeout_error = APIErrorSimulator.timeout_error()
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.side_effect = timeout_error
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run'
            )
            
            assert not result['success'], "Should fail on timeout error"
            
            error_output = (result['stdout'] + result['stderr']).lower()
            timeout_indicators = ['timeout', 'time out', 'connection', 'network']
            has_timeout_error = any(indicator in error_output for indicator in timeout_indicators)
            assert has_timeout_error, (
                f"No clear timeout error message: {error_output}"
            )
    
    def test_api_rate_limit_error_handling(self, crm_api_settings):
        """Test handling of API rate limiting"""
        
        rate_limit_error = APIErrorSimulator.rate_limit_error('arrivy')
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.side_effect = rate_limit_error
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run'
            )
            
            assert not result['success'], "Should fail on rate limit error"
            
            error_output = (result['stdout'] + result['stderr']).lower()
            rate_limit_indicators = ['rate limit', 'too many requests', 'limit exceeded']
            has_rate_limit_error = any(indicator in error_output for indicator in rate_limit_indicators)
            assert has_rate_limit_error, (
                f"No clear rate limit error message: {error_output}"
            )
    
    # ============================================================================
    # PHASE 6: Advanced Testing Patterns (Extracted from Legacy Tests)
    # ============================================================================
    
    def test_arrivy_concurrent_sync_prevention(self, crm_api_settings):
        """Test that concurrent syncs are prevented"""
        # Create a running sync record
        running_sync = SyncHistory.objects.create(
            crm_source='arrivy',
            sync_type='entities',
            status='running',
            start_time=timezone.now() - timedelta(minutes=10),
            records_processed=0
        )
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine'):
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run'
            )
            
            # Should detect running sync and either prevent or warn
            if not result['success']:
                error_msg = str(result['exception']).lower()
                concurrent_indicators = ['running', 'already', 'in progress', 'concurrent']
                has_concurrent_check = any(indicator in error_msg for indicator in concurrent_indicators)
                assert has_concurrent_check, f"No concurrent sync prevention: {result['exception']}"
    
    def test_arrivy_delta_sync_detection(self, crm_api_settings, clean_sync_history):
        """Test delta sync timestamp detection and usage"""
        # Create successful previous sync
        previous_sync = SyncHistory.objects.create(
            crm_source='arrivy',
            sync_type='entities',
            status='success',
            start_time=timezone.now() - timedelta(hours=2),
            end_time=timezone.now() - timedelta(hours=1, minutes=55),
            records_processed=50,
            records_created=20,
            records_updated=30
        )
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 5, 'created': 2, 'updated': 3, 'failed': 0
            }
            
            # Run incremental sync (should detect last sync timestamp)
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run',
                '--debug'
            )
            
            assert result['success'], f"Delta sync failed: {result}"
            
            # Should mention incremental or delta sync in output
            output = result['stdout'].lower()
            delta_indicators = ['incremental', 'delta', 'since', 'timestamp', 'last sync']
            has_delta_indication = any(indicator in output for indicator in delta_indicators)
            assert has_delta_indication, f"No delta sync indication in output: {result['stdout']}"
    
    def test_arrivy_command_help_comprehensiveness(self):
        """Test that Arrivy commands provide comprehensive help documentation"""
        for command_name in self.ARRIVY_COMMANDS:
            help_text = self.command_runner.get_command_help(command_name)
            
            # Should have actual help text content
            assert len(help_text) > 50, f"Help text too short for {command_name}: {len(help_text)} chars"
            
            # Should document all required flags
            for flag in ['--dry-run', '--full', '--debug', '--quiet', '--batch-size', '--force']:
                assert flag in help_text, f"Help missing flag {flag} for {command_name}"
            
            # Should have usage examples or clear description
            help_lower = help_text.lower()
            description_indicators = ['sync', 'arrivy', 'command', 'data']
            has_description = any(indicator in help_lower for indicator in description_indicators)
            assert has_description, f"No clear description in help for {command_name}"
            
            # Should explain what the command does
            description_length = len([line for line in help_text.split('\n') if line.strip()])
            assert description_length >= 5, f"Help too brief for {command_name} ({description_length} lines)"
    
    def test_arrivy_batch_size_impact_on_performance(self, crm_api_settings):
        """Test that batch size affects processing behavior"""
        test_command = 'sync_arrivy_entities'
        
        batch_sizes_to_test = [1, 10, 100]
        
        for batch_size in batch_sizes_to_test:
            with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
                mock_instance = mock_engine.return_value
                mock_instance.execute_sync.return_value = {
                    'processed': batch_size * 2,  # Simulate processing 2 batches
                    'created': batch_size,
                    'updated': batch_size,
                    'failed': 0,
                    'batches_processed': 2,
                    'batch_size': batch_size
                }
                
                result = self.command_runner.run_command_in_docker(
                    test_command,
                    '--batch-size', str(batch_size),
                    '--dry-run'
                )
                
                if result['success']:
                    # Should mention batch processing in output
                    output = result['stdout'].lower()
                    batch_indicators = ['batch', 'processed', str(batch_size)]
                    has_batch_info = any(indicator in output for indicator in batch_indicators)
                    assert has_batch_info, f"No batch info for size {batch_size}: {result['stdout']}"
    
    # ============================================================================
    # PHASE 6: SyncHistory Compliance Tests (MANDATORY per crm_sync_guide.md)
    # ============================================================================
    
    @pytest.mark.parametrize('command_name,operation_name', [
        ('sync_arrivy_entities', 'entities'),
        ('sync_arrivy_tasks', 'tasks'),
        ('sync_arrivy_groups', 'groups'),
    ])
    def test_sync_history_compliance_validation(self, command_name, operation_name, 
                                              crm_api_settings, clean_sync_history):
        """🔴 CRITICAL: Test mandatory SyncHistory compliance"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 10,
                'created': 5,
                'updated': 3,
                'failed': 2,
                'duration_seconds': 5.5,
            }
            
            # Test SyncHistory usage compliance
            validation_result = self.sync_validator.validate_sync_history_usage(
                command_name=command_name,
                crm_source='arrivy',
                operation_name=operation_name
            )
            
            assert validation_result['compliant'], (
                f"🔴 SYNCHISTORY COMPLIANCE VIOLATION:\n"
                f"Violations: {validation_result['violations']}\n"
                f"Command: {command_name}\n"
                f"This violates crm_sync_guide.md requirements!"
            )
            
            assert validation_result['sync_history_created'], (
                f"Command {command_name} did not create SyncHistory record"
            )
    
    def test_sync_history_dry_run_compliance(self, crm_api_settings, clean_sync_history):
        """Test that dry-run mode doesn't create SyncHistory records"""
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': 10, 'created': 0, 'updated': 0, 'failed': 0
            }
            
            # Run in dry-run mode
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities',
                '--dry-run'
            )
            
            # Should not create SyncHistory records in dry-run
            sync_records = SyncHistory.objects.filter(
                source='arrivy',
                operation_name='entities'
            )
            
            assert sync_records.count() == 0, (
                f"Dry-run created {sync_records.count()} SyncHistory records"
            )
    
    # ============================================================================
    # PHASE 7: Orchestration Tests for sync_arrivy_all
    # ============================================================================
    
    def test_arrivy_all_orchestrates_individual_commands(self, crm_api_settings):
        """Test that sync_arrivy_all calls individual commands in correct order"""
        
        with patch('django.core.management.call_command') as mock_call:
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_all',
                '--entity-type', 'all',
                '--dry-run'
            )
            
            assert result['success'], f"sync_arrivy_all orchestration failed: {result}"
            
            # Should have called individual commands
            assert mock_call.call_count > 0, "No individual commands were called"
            
            # Verify expected commands were called
            called_commands = [call[0][0] for call in mock_call.call_args_list]
            expected_commands = ['sync_arrivy_entities', 'sync_arrivy_tasks', 'sync_arrivy_groups']
            
            for expected in expected_commands:
                command_called = any(expected in cmd for cmd in called_commands)
                assert command_called, (
                    f"Expected command {expected} not called. Called: {called_commands}"
                )
    
    def test_arrivy_all_passes_flags_correctly(self, crm_api_settings):
        """Test that sync_arrivy_all passes flags to individual commands"""
        
        with patch('django.core.management.call_command') as mock_call:
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_all',
                '--full',
                '--batch-size', '50',
                '--debug',
                '--dry-run'
            )
            
            assert result['success'], f"Flag passing failed: {result}"
            
            # Verify flags were passed to individual commands
            flags_to_check = {
                'full': True,
                'batch_size': 50,
                'debug': True,
                'dry_run': True,
            }
            
            self.command_runner.assert_flags_passed_to_individual_commands(
                'sync_arrivy_all',
                flags_to_check
            )
    
    def test_arrivy_all_entity_filtering(self, crm_api_settings):
        """Test that sync_arrivy_all respects --entity-type filtering"""
        
        with patch('django.core.management.call_command') as mock_call:
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_all',
                '--entity-type', 'entities',
                '--dry-run'
            )
            
            assert result['success'], f"Entity filtering failed: {result}"
            
            # Should call only entities-related command
            called_commands = [call[0][0] for call in mock_call.call_args_list if call[0]]
            arrivy_commands = [cmd for cmd in called_commands if 'arrivy' in cmd]
            
            # Should call at least one command, but not all
            assert len(arrivy_commands) > 0, "No Arrivy commands called"
            assert len(arrivy_commands) < len(self.INDIVIDUAL_COMMANDS), (
                f"All commands called despite filtering: {arrivy_commands}"
            )
            
            # Should include entities command
            entities_called = any('entities' in cmd for cmd in arrivy_commands)
            assert entities_called, f"Entities command not called: {arrivy_commands}"
    
    def test_arrivy_all_handles_individual_command_failures(self, crm_api_settings):
        """Test that sync_arrivy_all handles individual command failures gracefully"""
        
        def mock_call_command(command_name, *args, **kwargs):
            if 'entities' in command_name:
                raise Exception("Simulated entities sync failure")
            return None
        
        with patch('django.core.management.call_command', side_effect=mock_call_command):
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_all',
                '--entity-type', 'all',
                '--dry-run'
            )
            
            # Main command should handle individual failures
            # (Implementation-dependent: may succeed with warnings or fail gracefully)
            error_output = (result['stdout'] + result['stderr']).lower()
            
            # Should mention the failure
            failure_indicators = ['error', 'failed', 'exception', 'entities']
            has_failure_mention = any(indicator in error_output for indicator in failure_indicators)
            assert has_failure_mention, (
                f"Individual command failure not reported: {error_output}"
            )
    
    # ============================================================================
    # PHASE 8: Real Sync Tests with Mocked APIs
    # ============================================================================
    
    def test_successful_sync_with_mocked_api(self, crm_api_settings, clean_sync_history):
        """Test complete sync flow with realistic mocked API responses"""
        
        # Use realistic mock responses
        mock_entities_response = self.mock_responses['entities']
        
        with patch('ingestion.sync.arrivy.engines.entities.ArrivyEntitiesSyncEngine') as mock_engine:
            mock_instance = mock_engine.return_value
            mock_instance.execute_sync.return_value = {
                'processed': len(mock_entities_response['entities']),
                'created': len(mock_entities_response['entities']),
                'updated': 0,
                'failed': 0,
                'duration_seconds': 3.2,
                'records_per_second': 0.6,
            }
            
            result = self.command_runner.run_command_in_docker(
                'sync_arrivy_entities'
            )
            
            assert result['success'], f"Mocked sync failed: {result}"
            
            # Verify sync results in output
            output = result['stdout']
            assert 'processed' in output.lower(), f"No processing info in output: {output}"
            assert 'created' in output.lower(), f"No creation info in output: {output}"
            
            # Verify SyncHistory record created
            sync_record = SyncHistory.objects.filter(
                source='arrivy',
                operation_name='entities'
            ).first()
            
            assert sync_record is not None, "No SyncHistory record created"
            assert sync_record.records_processed > 0, "No records processed recorded"
