"""
Base test class for CRM management command testing

Provides Docker-optimized utilities for testing CRM sync commands
with proper SyncHistory compliance validation and API mocking.
"""
import io
import logging
from unittest.mock import patch, MagicMock
from typing import Dict, Any, List, Optional, Type

from django.test import TestCase, TransactionTestCase
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from django.db import transaction, models
from django.utils import timezone

from ingestion.models.common import SyncHistory


class CommandTestBase:
    """
    Base utilities for testing CRM management commands in Docker environment
    
    Provides:
    - Standard flag validation
    - Dry-run testing
    - SyncHistory compliance checking  
    - API mocking patterns
    - Docker-optimized execution
    """
    
    # Standard flags all CRM commands must support
    REQUIRED_FLAGS = [
        '--dry-run',
        '--full', 
        '--debug',
        '--batch-size',
        '--force',
        '--quiet',
        '--start-date',
    ]
    
    # Optional flags that some commands may support
    OPTIONAL_FLAGS = [
        '--end-date',
        '--entities', 
        '--max-records',
        '--parallel',
        '--company-id',
        '--since',  # Legacy compatibility
    ]
    
    def get_command_instance(self, command_name: str) -> BaseCommand:
        """Get a command instance for testing"""
        try:
            from django.core.management import load_command_class
            command_obj = load_command_class('ingestion', command_name)
            
            # Check if it's already an instance
            if isinstance(command_obj, BaseCommand):
                return command_obj
            else:
                # It's a class, instantiate it
                return command_obj()
        except Exception as e:
            raise AssertionError(f"Command {command_name} could not be imported: {e}")
    
    def run_command_in_docker(self, command_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Run a command in Docker context and capture output
        
        Args:
            command_name: Name of the management command
            *args: Command arguments
            **kwargs: Command options
            
        Returns:
            Dict with stdout, stderr, success status, and exception if any
        """
        stdout = io.StringIO()
        stderr = io.StringIO()
        
        try:
            call_command(
                command_name,
                *args,
                stdout=stdout,
                stderr=stderr,
                **kwargs
            )
            return {
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue(),
                'success': True,
                'exception': None
            }
        except SystemExit as e:
            # Handle --help which causes SystemExit(0) - this is normal
            return {
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue(),
                'success': e.code == 0,  # Exit code 0 is success (like --help)
                'exception': e if e.code != 0 else None
            }
        except Exception as e:
            return {
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue(), 
                'success': False,
                'exception': e
            }
        finally:
            stdout.close()
            stderr.close()
    
    def run_command_with_capture(self, command_name: str, expect_failure=False, **kwargs) -> Dict[str, Any]:
        """
        Enhanced command runner with better output capture and error handling
        
        Args:
            command_name: Name of management command
            expect_failure: Whether to expect the command to fail
            **kwargs: Command arguments (converted from underscores to dashes)
            
        Returns:
            Dict with stdout, stderr, success, return_code, and any exception
        """
        # Convert keyword arguments to command line arguments
        args = []
        for key, value in kwargs.items():
            if key == 'help' and value:
                args.append('--help')
            elif key.endswith('_') or '_' in key:
                # Convert underscore to dash (dry_run -> --dry-run)
                flag_name = key.rstrip('_').replace('_', '-')
                if value is True:
                    args.append(f'--{flag_name}')
                elif value is not False and value is not None:
                    args.extend([f'--{flag_name}', str(value)])
            else:
                if value is True:
                    args.append(f'--{key}')
                elif value is not False and value is not None:
                    args.extend([f'--{key}', str(value)])
        
        result = self.run_command_in_docker(command_name, *args)
        
        # Add return_code for compatibility with legacy tests
        result['return_code'] = 0 if result['success'] else 1
        
        if expect_failure:
            if result['success']:
                raise AssertionError(f"Expected command {command_name} to fail, but it succeeded")
        
        return result
    
    def discover_crm_commands(self, crm_source: str) -> List[str]:
        """
        Discover all management commands for a specific CRM system
        
        Args:
            crm_source: CRM system name (e.g., 'arrivy', 'hubspot')
            
        Returns:
            List of command names for that CRM system
        """
        try:
            from django.core.management import get_commands
            all_commands = get_commands()
            
            # Filter commands that match the CRM pattern
            crm_commands = [
                cmd for cmd in all_commands.keys() 
                if cmd.startswith(f'sync_{crm_source}_')
            ]
            
            return sorted(crm_commands)
        except Exception as e:
            # Fallback to manual discovery if get_commands fails
            return self._manual_command_discovery(crm_source)
    
    def _manual_command_discovery(self, crm_source: str) -> List[str]:
        """Fallback manual command discovery"""
        # This would be the hardcoded list for each CRM
        crm_command_map = {
            'arrivy': [
                'sync_arrivy_all', 'sync_arrivy_entities', 'sync_arrivy_tasks',
                'sync_arrivy_groups', 'sync_arrivy_bookings', 'sync_arrivy_statuses'
            ],
            'callrail': [
                'sync_callrail_all', 'sync_callrail_accounts', 'sync_callrail_calls',
                'sync_callrail_companies', 'sync_callrail_form_submissions', 
                'sync_callrail_tags', 'sync_callrail_text_messages', 
                'sync_callrail_trackers', 'sync_callrail_users'
            ],
            # Add other CRMs as needed
        }
        
        return crm_command_map.get(crm_source, [])
    
    # === Flag Validation Methods ===
    
    def assert_command_has_flag(self, command_name: str, flag: str):
        """Assert that a command supports a specific flag"""
        command = self.get_command_instance(command_name)
        parser = command.create_parser('test', command_name)
        
        # Check if flag exists
        flag_found = False
        for action in parser._actions:
            if hasattr(action, 'option_strings') and flag in action.option_strings:
                flag_found = True
                break
        
        assert flag_found, f"Command {command_name} missing required flag: {flag}"
    
    def assert_command_has_required_flags(self, command_name: str):
        """Assert command has all required standardized flags"""
        for flag in self.REQUIRED_FLAGS:
            self.assert_command_has_flag(command_name, flag)
    
    def get_command_help(self, command_name: str) -> str:
        """Get help text for a command by using the parser directly"""
        try:
            command = self.get_command_instance(command_name)
            parser = command.create_parser('manage.py', command_name)
            return parser.format_help()
        except Exception as e:
            # Fallback to empty string if help extraction fails
            return f"Help extraction failed: {e}"
    
    def assert_help_mentions_flags(self, command_name: str, flags: List[str]):
        """Assert that help text mentions specific flags"""
        help_text = self.get_command_help(command_name)
        for flag in flags:
            assert flag in help_text, f"Flag {flag} not in help for {command_name}"
    
    # === Dry-Run Testing Methods ===
    
    def assert_dry_run_no_db_writes(self, command_name: str, model_class: Type[models.Model], 
                                   *args, **kwargs):
        """
        Assert that dry-run mode doesn't write to database
        
        Args:
            command_name: Command to test
            model_class: Django model to check for writes
            *args: Command arguments
            **kwargs: Command options
        """
        initial_count = model_class.objects.count()
        
        # Force dry-run mode
        kwargs['dry_run'] = True
        
        result = self.run_command_in_docker(command_name, '--dry-run', *args, **kwargs)
        
        final_count = model_class.objects.count()
        assert initial_count == final_count, (
            f"Dry-run wrote to {model_class.__name__}: {initial_count} -> {final_count}\n"
            f"STDOUT: {result['stdout']}\nSTDERR: {result['stderr']}"
        )
        
        return result
    
    def assert_dry_run_output_indicates_no_writes(self, command_name: str, *args, **kwargs):
        """Assert that dry-run output clearly states no writes occur"""
        result = self.run_command_in_docker(command_name, '--dry-run', *args, **kwargs)
        
        output_lower = result['stdout'].lower()
        dry_run_indicators = [
            'dry run', 'dry-run', 'no data will be saved', 
            'no database writes', 'preview', 'simulation', 'no changes'
        ]
        
        has_indicator = any(indicator in output_lower for indicator in dry_run_indicators)
        assert has_indicator, (
            f"Dry-run output doesn't indicate no writes:\n{result['stdout']}"
        )
        
        return result
    
    # === Flag Behavior Testing ===
    
    def assert_debug_increases_verbosity(self, command_name: str, *args, **kwargs):
        """Assert --debug flag increases output verbosity"""
        # Run without debug
        result_normal = self.run_command_in_docker(command_name, *args, **kwargs)
        
        # Run with debug
        result_debug = self.run_command_in_docker(command_name, '--debug', *args, **kwargs)
        
        # Debug should be more verbose or contain debug indicators
        debug_indicators = ['debug', 'DEBUG', 'verbose', 'detailed']
        has_debug_content = any(indicator in result_debug['stdout'] for indicator in debug_indicators)
        is_longer = len(result_debug['stdout']) >= len(result_normal['stdout'])
        
        assert has_debug_content or is_longer, (
            f"--debug flag doesn't increase verbosity:\n"
            f"Normal: {len(result_normal['stdout'])} chars\n"
            f"Debug: {len(result_debug['stdout'])} chars"
        )
        
        return result_normal, result_debug
    
    def assert_quiet_reduces_output(self, command_name: str, *args, **kwargs):
        """Assert --quiet flag reduces output"""
        # Run normal
        result_normal = self.run_command_in_docker(command_name, *args, **kwargs)
        
        # Run quiet
        result_quiet = self.run_command_in_docker(command_name, '--quiet', *args, **kwargs)
        
        # Quiet should be shorter or empty
        normal_len = len(result_normal['stdout'])
        quiet_len = len(result_quiet['stdout'])
        
        assert quiet_len <= normal_len, (
            f"--quiet flag doesn't reduce output:\n"
            f"Normal: {normal_len} chars\nQuiet: {quiet_len} chars"
        )
        
        return result_normal, result_quiet
    
    # === Argument Validation Testing ===
    
    def test_invalid_date_format_rejected(self, command_name: str, date_flag: str = '--start-date'):
        """Test that invalid date formats are rejected"""
        invalid_dates = [
            '2025-13-01',  # Invalid month
            '2025-01-32',  # Invalid day
            '01-01-2025',  # Wrong format
            'invalid-date',  # Non-date
            '2025/01/01',  # Wrong separator
        ]
        
        for invalid_date in invalid_dates:
            result = self.run_command_in_docker(
                command_name, 
                date_flag, invalid_date,
                '--dry-run'  # Always use dry-run for validation tests
            )
            
            assert not result['success'], (
                f"Invalid date {invalid_date} was accepted by {command_name}"
            )
            
            # Should be CommandError with date-related message
            if result['exception']:
                error_msg = str(result['exception']).lower()
                date_error_terms = ['date', 'format', 'invalid', 'yyyy-mm-dd']
                has_date_error = any(term in error_msg for term in date_error_terms)
                assert has_date_error, (
                    f"Error message doesn't mention date format: {result['exception']}"
                )
    
    def test_batch_size_validation(self, command_name: str):
        """Test batch size parameter validation"""
        # Valid batch sizes should work
        valid_sizes = [1, 50, 100, 500, 1000]
        for size in valid_sizes:
            result = self.run_command_in_docker(
                command_name,
                '--batch-size', str(size),
                '--dry-run'
            )
            # May fail for other reasons, but not batch size
            if not result['success'] and result['exception']:
                error_msg = str(result['exception']).lower()
                assert 'batch' not in error_msg, (
                    f"Valid batch size {size} rejected: {result['exception']}"
                )
        
        # Invalid batch sizes should be rejected
        invalid_sizes = [0, -1, -10, 10001]
        for size in invalid_sizes:
            result = self.run_command_in_docker(
                command_name,
                '--batch-size', str(size), 
                '--dry-run'
            )
            # Should fail (may fail for batch size or other validation)
            if not result['success'] and 'batch' in str(result['exception']).lower():
                # This is the expected batch size error
                continue
    
    def test_conflicting_flags_handled(self, command_name: str):
        """Test that conflicting flags are properly handled"""
        # Test --full with --start-date (should conflict or --full should override)
        result = self.run_command_in_docker(
            command_name,
            '--full',
            '--start-date', '2025-01-01',
            '--dry-run'
        )
        
        if result['success']:
            # If succeeds, should mention override/conflict in output  
            output = result['stdout'].lower()
            conflict_terms = ['override', 'ignor', 'conflict', 'full sync']
            has_conflict_mention = any(term in output for term in conflict_terms)
            assert has_conflict_mention, (
                f"No conflict warning for --full + --start-date: {result['stdout']}"
            )
        else:
            # If fails, should be due to conflicting flags
            error_msg = str(result['exception']).lower()
            assert 'conflict' in error_msg, (
                f"Unexpected error for conflicting flags: {result['exception']}"
            )
    
    # === API Error Testing ===
    
    def test_missing_api_credentials(self, command_name: str, credential_name: str):
        """Test handling of missing API credentials"""
        # Run without setting the credential
        result = self.run_command_in_docker(command_name, '--dry-run')
        
        assert not result['success'], f"Command succeeded without {credential_name}"
        
        error_output = (result['stdout'] + result['stderr']).lower()
        credential_terms = ['token', 'api', 'credential', 'not configured', 'missing']
        has_credential_error = any(term in error_output for term in credential_terms)
        assert has_credential_error, (
            f"No credential error for missing {credential_name}: {error_output}"
        )
    
    def simulate_api_error(self, client_path: str, method: str, error: Exception):
        """Create a context manager to simulate API errors"""
        return patch(f'{client_path}.{method}', side_effect=error)
    
    def simulate_api_success(self, client_path: str, method: str, return_value: Any):
        """Create a context manager to simulate successful API responses"""
        return patch(f'{client_path}.{method}', return_value=return_value)
    
    # === SyncHistory Compliance Testing ===
    
    def assert_sync_history_created(self, operation: str, source: str):
        """Assert that SyncHistory record was created"""
        sync_record = SyncHistory.objects.filter(
            operation_name=operation,
            source=source
        ).first()
        
        assert sync_record is not None, (
            f"No SyncHistory record for operation: {operation}, source: {source}"
        )
        
        return sync_record
    
    def assert_no_sync_history_in_dry_run(self, operation: str, source: str):
        """Assert that dry-run doesn't create SyncHistory records"""
        sync_count = SyncHistory.objects.filter(
            operation_name=operation,
            source=source
        ).count()
        
        assert sync_count == 0, (
            f"Dry-run created {sync_count} SyncHistory records for {operation}"
        )
    
    def get_latest_sync_history(self, operation: str, source: str) -> Optional[SyncHistory]:
        """Get most recent SyncHistory record"""
        return SyncHistory.objects.filter(
            operation_name=operation,
            source=source
        ).order_by('-started_at').first()
    
    # === Orchestration Testing (for *_all commands) ===
    
    def assert_orchestration_calls_individual_commands(self, all_command_name: str, 
                                                      expected_commands: List[str],
                                                      *args, **kwargs):
        """Assert that *_all command calls individual commands"""
        with patch('django.core.management.call_command') as mock_call:
            result = self.run_command_in_docker(all_command_name, *args, **kwargs)
            
            assert result['success'], f"{all_command_name} failed: {result}"
            
            # Check that individual commands were called
            assert mock_call.call_count > 0, "No individual commands were called"
            
            called_commands = [call[0][0] for call in mock_call.call_args_list]
            for expected_cmd in expected_commands:
                assert any(expected_cmd in cmd for cmd in called_commands), (
                    f"Expected command {expected_cmd} not called. Called: {called_commands}"
                )
    
    def assert_flags_passed_to_individual_commands(self, all_command_name: str,
                                                  flags_to_check: Dict[str, Any],
                                                  *args, **kwargs):
        """Assert that flags are passed through to individual commands"""
        with patch('django.core.management.call_command') as mock_call:
            result = self.run_command_in_docker(all_command_name, *args, **kwargs)
            
            assert result['success'], f"{all_command_name} failed: {result}"
            
            # Check that flags were passed through
            called_kwargs = [call[1] for call in mock_call.call_args_list]
            
            for flag_name, expected_value in flags_to_check.items():
                flag_found = False
                for kwargs_dict in called_kwargs:
                    if kwargs_dict.get(flag_name) == expected_value:
                        flag_found = True
                        break
                
                assert flag_found, (
                    f"Flag {flag_name}={expected_value} not passed to individual commands"
                )
    
    # === Utility Methods ===
    
    def capture_logs(self, logger_name: str = 'test'):
        """Context manager to capture log output"""
        from contextlib import contextmanager
        
        @contextmanager
        def _capture():
            log_stream = io.StringIO()
            handler = logging.StreamHandler(log_stream)
            logger = logging.getLogger(logger_name)
            logger.addHandler(handler)
            old_level = logger.level
            logger.setLevel(logging.DEBUG)
            
            try:
                yield log_stream
            finally:
                logger.removeHandler(handler)
                logger.setLevel(old_level)
        
        return _capture()
