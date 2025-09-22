"""
Sync Management Service

Handles execution of CRM sync commands, monitoring sync progress,
and managing sync operations including parameter validation and command building.
"""
import subprocess
import json
import os
import signal
import threading
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from ingestion.models.common import SyncHistory
from ingestion.services.ingestion_adapter import get_command_for_source
import logging

logger = logging.getLogger(__name__)


class SyncManagementService:
    """Service for managing CRM sync operations"""
    
    def __init__(self):
        self.running_processes = {}  # Track running sync processes
        self.sync_locks = {}  # Track ongoing sync operations to prevent race conditions
        self.management_commands_dir = os.path.join(
            os.path.dirname(__file__), '..', 'management', 'commands'
        )
    
    def get_available_commands(self, crm_source: str) -> List[Dict]:
        """Get all available management commands for a CRM source"""
        try:
            commands = []
            
            # Scan management commands directory
            if os.path.exists(self.management_commands_dir):
                for filename in os.listdir(self.management_commands_dir):
                    if filename.endswith('.py') and filename.startswith(f'sync_{crm_source}'):
                        command_name = filename[:-3]  # Remove .py extension
                        
                        # Parse command to determine sync type
                        sync_type = self._parse_sync_type_from_command(command_name)
                        
                        commands.append({
                            'command_name': command_name,
                            'sync_type': sync_type,
                            'display_name': self._format_command_display_name(command_name),
                            'supports_parameters': True
                        })
            
            return sorted(commands, key=lambda x: x['command_name'])
            
        except Exception as e:
            logger.error(f"Error getting available commands for {crm_source}: {e}")
            return []
    
    def _parse_sync_type_from_command(self, command_name: str) -> str:
        """Extract sync type from command name"""
        # Remove sync_ prefix and crm source
        parts = command_name.split('_')
        if len(parts) >= 3:
            return '_'.join(parts[2:])  # Everything after sync_{crm}
        return 'unknown'
    
    def _format_command_display_name(self, command_name: str) -> str:
        """Format command name for display"""
        return command_name.replace('_', ' ').title()
    
    def validate_sync_parameters(self, parameters: Dict) -> Dict[str, Any]:
        """Validate sync parameters and return validation result"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'sanitized_params': {}
        }
        
        try:
            # Validate --since parameter
            if 'since' in parameters and parameters['since']:
                try:
                    since_date = datetime.strptime(parameters['since'], '%Y-%m-%d')
                    validation_result['sanitized_params']['since'] = parameters['since']
                    
                    # Warn if date is too far in the past
                    if (datetime.now() - since_date).days > 365:
                        validation_result['warnings'].append(
                            "Since date is more than 1 year ago - this may result in a very large sync"
                        )
                except ValueError:
                    validation_result['valid'] = False
                    validation_result['errors'].append(
                        "Invalid since date format. Use YYYY-MM-DD (e.g., 2024-01-15)"
                    )
            
            # Validate numeric parameters
            numeric_params = ['max_records', 'batch_size']
            for param in numeric_params:
                if param in parameters and parameters[param]:
                    try:
                        value = int(parameters[param])
                        if value <= 0:
                            validation_result['valid'] = False
                            validation_result['errors'].append(f"{param} must be a positive integer")
                        else:
                            validation_result['sanitized_params'][param] = value
                            
                            # Warn about potentially problematic values
                            if param == 'max_records' and value > 100000:
                                validation_result['warnings'].append(
                                    f"max_records is very high ({value}) - consider smaller batches"
                                )
                            elif param == 'batch_size' and value > 1000:
                                validation_result['warnings'].append(
                                    f"batch_size is very high ({value}) - may cause memory issues"
                                )
                    except ValueError:
                        validation_result['valid'] = False
                        validation_result['errors'].append(f"{param} must be a valid integer")
            
            # Validate boolean parameters
            boolean_params = ['force', 'full', 'dry_run', 'debug']
            for param in boolean_params:
                if param in parameters:
                    validation_result['sanitized_params'][param] = bool(parameters[param])
            
            # Check for conflicting parameters
            if (validation_result['sanitized_params'].get('force') and 
                validation_result['sanitized_params'].get('since')):
                validation_result['warnings'].append(
                    "--force and --since are both specified. --force will override --since"
                )
            
        except Exception as e:
            logger.error(f"Error validating sync parameters: {e}")
            validation_result['valid'] = False
            validation_result['errors'].append(f"Parameter validation error: {e}")
        
        return validation_result
    
    def build_sync_command(self, crm_source: str, sync_type: str, parameters: Dict) -> str:
        """Build the management command string using IngestionAdapter"""
        try:
            logger.info(f"Building sync command for {crm_source} {sync_type} with parameters: {parameters}")
            
            # For manual sync, determine mode based on parameters
            # Most sources use 'delta' for incremental, 'full' for full sync
            mode = 'full' if parameters.get('full') else 'delta'
            
            # Convert sync_type to model_name for model-specific syncs
            # sync_type like 'appointments' should become model_name 'appointments'
            model_name = sync_type if sync_type not in ['all', 'full'] else None
            
            # Get command from adapter function
            try:
                command, default_args = get_command_for_source(crm_source, mode, model_name)
            except Exception as e:
                # If the adapter function fails, fall back to building command manually
                logger.warning(f"Adapter function failed: {e}, using fallback command building")
                if model_name:
                    command = f"db_{crm_source}_{model_name}"
                else:
                    command = f"sync_{crm_source}_all"
                default_args = {}
            
            # Build command parts
            cmd_parts = ['python', 'manage.py', command]
            
            # Add default args from the adapter
            for arg, value in default_args.items():
                if value is True:
                    cmd_parts.append(f'--{arg}')
                elif value is not False and value is not None:
                    cmd_parts.extend([f'--{arg}', str(value)])
            
            # Add additional parameters
            if parameters.get('force'):
                cmd_parts.append('--force')
            
            if parameters.get('since'):
                cmd_parts.extend(['--since', parameters['since']])
            
            if parameters.get('dry_run'):
                cmd_parts.append('--dry-run')
            
            if parameters.get('debug'):
                cmd_parts.append('--debug')
            
            if parameters.get('max_records'):
                cmd_parts.extend(['--max-records', str(parameters['max_records'])])
            
            return ' '.join(cmd_parts)
            
        except Exception as e:
            logger.error(f"Error building sync command: {e}")
            return None
    
    def execute_sync_command(self, crm_source: str, sync_type: str, parameters: Dict) -> Dict[str, Any]:
        """Execute a sync command asynchronously and return execution info"""
        sync_key = f"{crm_source}:{sync_type}"
        
        try:
            # Check for in-memory lock first (prevents race conditions within same process)
            if sync_key in self.sync_locks:
                logger.warning(f"Sync already in progress for {sync_key} (in-memory lock)")
                return {
                    'success': False,
                    'error': f'Another sync for {crm_source} {sync_type} is already being processed. Please wait.',
                    'sync_id': None
                }
            
            # Set temporary lock
            self.sync_locks[sync_key] = timezone.now()
            
            try:
                # Validate parameters first
                validation = self.validate_sync_parameters(parameters)
                if not validation['valid']:
                    return {
                        'success': False,
                        'error': 'Parameter validation failed',
                        'validation_errors': validation['errors'],
                        'sync_id': None
                    }
                
                # Check for concurrent syncs in database
                concurrent_check = self._check_concurrent_syncs(crm_source, sync_type)
                if not concurrent_check['can_proceed']:
                    return {
                        'success': False,
                        'error': concurrent_check['message'],
                        'sync_id': None
                    }
                
                # Build command
                command = self.build_sync_command(crm_source, sync_type, validation['sanitized_params'])
                if not command:
                    return {
                        'success': False,
                        'error': 'Failed to build command',
                        'sync_id': None
                    }
                
                # Log sync initiation for debugging
                logger.info(f"Initiating sync for {sync_key} with command: {command}")
                
                # Create SyncHistory record with additional race condition protection
                try:
                    sync_record = SyncHistory.objects.create(
                        crm_source=crm_source,
                        sync_type=sync_type,
                        status='running',
                        start_time=timezone.now(),
                        configuration={
                            'command': command,
                            'parameters': validation['sanitized_params'],
                            'validation_warnings': validation['warnings'],
                            'execution_method': 'manual_sync_api',
                            'sync_key': sync_key
                        }
                    )
                    
                    # Double-check for race condition after creation
                    recent_syncs = SyncHistory.objects.filter(
                        crm_source=crm_source,
                        sync_type=sync_type,
                        status='running',
                        start_time__gte=timezone.now() - timedelta(seconds=5)
                    ).order_by('start_time')
                    
                    if recent_syncs.count() > 1:
                        # Race condition detected - keep only the first one
                        first_sync = recent_syncs.first()
                        if sync_record.id != first_sync.id:
                            logger.warning(f"Race condition detected for {sync_key}. Cancelling duplicate sync {sync_record.id}")
                            sync_record.status = 'failed'
                            sync_record.end_time = timezone.now()
                            sync_record.error_message = f'Cancelled due to concurrent sync detection. First sync ID: {first_sync.id}'
                            sync_record.save()
                            
                            return {
                                'success': False,
                                'error': f'Another sync for {crm_source} {sync_type} started simultaneously. Please wait for it to complete.',
                                'sync_id': sync_record.id,
                                'duplicate_cancelled': True
                            }
                    
                    logger.info(f"Created SyncHistory record {sync_record.id} for {sync_key}")
                    
                except Exception as e:
                    logger.error(f"Error creating SyncHistory record for {sync_key}: {e}")
                    return {
                        'success': False,
                        'error': 'Failed to create sync record',
                        'sync_id': None
                    }
                
                # Execute command in background
                self._execute_command_async(sync_record.id, command)
                
                return {
                    'success': True,
                    'sync_id': sync_record.id,
                    'command': command,
                    'warnings': validation['warnings'],
                    'message': f'Sync started successfully for {crm_source} {sync_type}'
                }
                
            finally:
                # Always remove the in-memory lock after processing
                if sync_key in self.sync_locks:
                    del self.sync_locks[sync_key]
            
        except Exception as e:
            # Ensure lock is removed even if there's an error
            if sync_key in self.sync_locks:
                del self.sync_locks[sync_key]
            logger.error(f"Error executing sync command for {sync_key}: {e}")
            return {
                'success': False,
                'error': str(e),
                'sync_id': None
            }
    
    def _check_concurrent_syncs(self, crm_source: str, sync_type: str) -> Dict[str, Any]:
        """Check if there are concurrent syncs that would conflict"""
        try:
            # Check for any running syncs for this CRM source
            running_syncs = SyncHistory.objects.filter(
                crm_source=crm_source,
                status='running'
            )
            
            # If requesting an 'all' sync, check if any individual syncs are running
            if sync_type == 'all':
                if running_syncs.exists():
                    running_types = list(running_syncs.values_list('sync_type', flat=True))
                    return {
                        'can_proceed': False,
                        'message': f'Cannot start bulk sync while individual syncs are running: {", ".join(running_types)}'
                    }
            else:
                # If requesting an individual sync, check for conflicts
                for running_sync in running_syncs:
                    # Block if same sync type is already running
                    if running_sync.sync_type == sync_type:
                        return {
                            'can_proceed': False,
                            'message': f'Sync for {sync_type} is already running (started {running_sync.start_time})'
                        }
                    
                    # Block if 'all' sync is running
                    if running_sync.sync_type == 'all':
                        return {
                            'can_proceed': False,
                            'message': f'Cannot start individual sync while bulk sync is running (started {running_sync.start_time})'
                        }
            
            return {'can_proceed': True, 'message': 'No conflicts detected'}
            
        except Exception as e:
            logger.error(f"Error checking concurrent syncs: {e}")
            return {
                'can_proceed': True,  # Allow sync to proceed if check fails
                'message': 'Could not check for concurrent syncs, proceeding anyway'
            }
    
    def _execute_command_async(self, sync_id: int, command: str):
        """Execute command in a separate thread"""
        def run_command():
            try:
                # Change to project directory
                project_dir = getattr(settings, 'BASE_DIR', os.getcwd())
                logger.info(f"Executing sync command {sync_id}: {command}")
                logger.info(f"Working directory: {project_dir}")
                
                # For Docker execution, modify the command to use the correct Python path
                # The UI runs from within the Docker container, so we need to use the container's Python
                command_parts = command.split()
                if command_parts[0] == 'python':
                    # In Docker, we should use the full path or ensure Python is in PATH
                    # Since we're already in the container, 'python' should work
                    pass
                
                # Execute command
                process = subprocess.Popen(
                    command_parts,
                    cwd=project_dir,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    bufsize=1,
                    universal_newlines=True,
                    env=os.environ.copy()  # Ensure environment variables are passed
                )
                
                # Store process for potential cancellation
                self.running_processes[sync_id] = process
                
                # Wait for completion
                stdout, stderr = process.communicate()
                return_code = process.returncode
                
                logger.info(f"Command {sync_id} completed with return code: {return_code}")
                if stdout:
                    logger.info(f"Command {sync_id} stdout: {stdout[:500]}...")
                if stderr:
                    logger.warning(f"Command {sync_id} stderr: {stderr[:500]}...")
                
                # Update SyncHistory record
                self._update_sync_record_on_completion(
                    sync_id, return_code, stdout, stderr
                )
                
                # Clean up
                if sync_id in self.running_processes:
                    del self.running_processes[sync_id]
                
            except Exception as e:
                logger.error(f"Error in async command execution for sync {sync_id}: {e}")
                self._update_sync_record_on_error(sync_id, str(e))
        
        # Start thread
        thread = threading.Thread(target=run_command)
        thread.daemon = True
        thread.start()
    
    def _update_sync_record_on_completion(self, sync_id: int, return_code: int, stdout: str, stderr: str):
        """Update SyncHistory record when command completes"""
        try:
            sync_record = SyncHistory.objects.get(id=sync_id)
            sync_record.end_time = timezone.now()
            
            if return_code == 0:
                sync_record.status = 'success'
                # Try to parse output for record counts
                self._parse_command_output(sync_record, stdout)
            else:
                sync_record.status = 'failed'
                sync_record.error_message = stderr or stdout
            
            # Store command output for debugging
            performance_metrics = sync_record.performance_metrics or {}
            performance_metrics.update({
                'return_code': return_code,
                'stdout_length': len(stdout),
                'stderr_length': len(stderr),
                'command_output': stdout[:1000],  # First 1000 chars
                'command_error': stderr[:1000] if stderr else None
            })
            sync_record.performance_metrics = performance_metrics
            
            sync_record.save()
            
            logger.info(f"Sync {sync_id} completed with return code {return_code}")
            
        except Exception as e:
            logger.error(f"Error updating sync record {sync_id}: {e}")
    
    def _update_sync_record_on_error(self, sync_id: int, error_message: str):
        """Update SyncHistory record when there's an execution error"""
        try:
            sync_record = SyncHistory.objects.get(id=sync_id)
            sync_record.end_time = timezone.now()
            sync_record.status = 'failed'
            sync_record.error_message = error_message
            sync_record.save()
            
        except Exception as e:
            logger.error(f"Error updating sync record {sync_id} with error: {e}")
    
    def _parse_command_output(self, sync_record: SyncHistory, output: str):
        """Parse command output to extract record counts"""
        try:
            # Common patterns in management command output
            import re
            
            # Look for patterns like "Created: 10, Updated: 5, Failed: 0"
            created_match = re.search(r'[Cc]reated[:\s]+(\d+)', output)
            updated_match = re.search(r'[Uu]pdated[:\s]+(\d+)', output)
            failed_match = re.search(r'[Ff]ailed[:\s]+(\d+)', output)
            processed_match = re.search(r'[Pp]rocessed[:\s]+(\d+)', output)
            
            if created_match:
                sync_record.records_created = int(created_match.group(1))
            
            if updated_match:
                sync_record.records_updated = int(updated_match.group(1))
            
            if failed_match:
                sync_record.records_failed = int(failed_match.group(1))
            
            if processed_match:
                sync_record.records_processed = int(processed_match.group(1))
            else:
                # Calculate processed as sum if not explicitly stated
                sync_record.records_processed = (
                    sync_record.records_created + 
                    sync_record.records_updated + 
                    sync_record.records_failed
                )
            
        except Exception as e:
            logger.warning(f"Error parsing command output for sync {sync_record.id}: {e}")
    
    def get_sync_status(self, sync_id: int) -> Dict[str, Any]:
        """Get current status of a sync operation"""
        try:
            sync_record = SyncHistory.objects.get(id=sync_id)
            
            # Check if process is still running
            is_running = sync_id in self.running_processes
            if is_running:
                process = self.running_processes[sync_id]
                is_running = process.poll() is None  # None means still running
            
            status_info = {
                'id': sync_record.id,
                'crm_source': sync_record.crm_source,
                'sync_type': sync_record.sync_type,
                'status': sync_record.status,
                'start_time': sync_record.start_time,
                'end_time': sync_record.end_time,
                'duration': sync_record.duration_seconds,
                'records_processed': sync_record.records_processed,
                'records_created': sync_record.records_created,
                'records_updated': sync_record.records_updated,
                'records_failed': sync_record.records_failed,
                'error_message': sync_record.error_message,
                'configuration': sync_record.configuration,
                'performance_metrics': sync_record.performance_metrics,
                'is_running': is_running
            }
            
            # Add estimated completion time if running
            if is_running and sync_record.start_time:
                elapsed = (timezone.now() - sync_record.start_time).total_seconds()
                status_info['elapsed_seconds'] = elapsed
                status_info['estimated_completion'] = 'unknown'  # Could be enhanced with prediction
            
            return status_info
            
        except SyncHistory.DoesNotExist:
            return {'error': f'Sync with ID {sync_id} not found'}
        except Exception as e:
            logger.error(f"Error getting sync status for {sync_id}: {e}")
            return {'error': str(e)}
    
    def stop_sync(self, sync_id: int) -> Dict[str, Any]:
        """Stop a running sync process"""
        try:
            if sync_id not in self.running_processes:
                return {
                    'success': False,
                    'error': 'Sync process not found or not running'
                }
            
            process = self.running_processes[sync_id]
            
            if process.poll() is not None:
                # Process already finished
                del self.running_processes[sync_id]
                return {
                    'success': False,
                    'error': 'Sync process already completed'
                }
            
            # Terminate the process
            try:
                process.terminate()
                # Give it a moment to terminate gracefully
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    # Force kill if it doesn't terminate gracefully
                    process.kill()
                    process.wait()
            except Exception as e:
                logger.warning(f"Error terminating process for sync {sync_id}: {e}")
            
            # Update sync record
            sync_record = SyncHistory.objects.get(id=sync_id)
            sync_record.end_time = timezone.now()
            sync_record.status = 'failed'
            sync_record.error_message = 'Sync stopped by user'
            sync_record.save()
            
            # Clean up
            del self.running_processes[sync_id]
            
            return {
                'success': True,
                'message': f'Sync {sync_id} stopped successfully'
            }
            
        except Exception as e:
            logger.error(f"Error stopping sync {sync_id}: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_running_syncs(self) -> List[Dict]:
        """Get all currently running sync operations"""
        try:
            running_syncs = []
            
            # Check database for running status
            db_running_syncs = SyncHistory.objects.filter(status='running').order_by('-start_time')
            
            for sync_record in db_running_syncs:
                # Verify if actually running
                is_actually_running = sync_record.id in self.running_processes
                if is_actually_running:
                    process = self.running_processes[sync_record.id]
                    is_actually_running = process.poll() is None
                
                if not is_actually_running:
                    # Update stale record
                    sync_record.status = 'failed'
                    sync_record.end_time = timezone.now()
                    sync_record.error_message = 'Sync process terminated unexpectedly'
                    sync_record.save()
                    continue
                
                running_syncs.append({
                    'id': sync_record.id,
                    'crm_source': sync_record.crm_source,
                    'sync_type': sync_record.sync_type,
                    'start_time': sync_record.start_time,
                    'elapsed_seconds': (timezone.now() - sync_record.start_time).total_seconds(),
                    'configuration': sync_record.configuration
                })
            
            return running_syncs
            
        except Exception as e:
            logger.error(f"Error getting running syncs: {e}")
            return []
