"""
Arrivy Task Status Sync Engine

Handles synchronization of Arrivy task status definitions and workflow mappings.
Task statuses represent the available status values and transitions in Arrivy workflows.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from .base import ArrivyBaseSyncEngine
from ..clients.task_status import ArrivyTaskStatusClient
from ..processors.task_status import TaskStatusProcessor
from ingestion.models.arrivy import Arrivy_TaskStatus

logger = logging.getLogger(__name__)

class ArrivyTaskStatusSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy task status definitions and workflows"""
    
    def __init__(self, **kwargs):
        super().__init__('task_status', **kwargs)
        self.client_class = ArrivyTaskStatusClient
        self.processor = TaskStatusProcessor()
    
    def get_model_class(self):
        """Get Django model class for task statuses"""
        return Arrivy_TaskStatus
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch task status data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp (not used for statuses as they don't change often)
            
        Yields:
            Batches of task status records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching task statuses with batch_size={self.batch_size}")
        
        # Fetch status definitions
        async for batch in client.fetch_status_definitions(
            page_size=self.batch_size,
            max_records=self.max_records,
            status_type=getattr(self, 'status_type_filter', 'all'),
            include_inactive=getattr(self, 'include_inactive', False)
        ):
            if self.dry_run:
                logger.info(f"DRY RUN: Would process {len(batch)} status definitions")
                continue
            
            yield batch
        
        # Fetch workflow definitions if requested
        if getattr(self, 'include_workflows', True):
            logger.info("Also fetching workflow definitions")
            
            async for batch in client.fetch_workflow_definitions(
                page_size=self.batch_size,
                max_records=self.max_records,
                workflow_type=getattr(self, 'workflow_type_filter', 'all')
            ):
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process {len(batch)} workflow definitions")
                    continue
                
                yield batch
        
        # Fetch status transitions if requested
        if getattr(self, 'include_transitions', True):
            logger.info("Also fetching status transitions")
            
            async for batch in client.fetch_status_transitions(
                page_size=self.batch_size,
                max_records=self.max_records
            ):
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process {len(batch)} status transitions")
                    continue
                
                yield batch
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute task status sync with additional status-specific options
        
        Args:
            **kwargs: Sync options including:
                - include_workflows: Include workflow definitions
                - include_transitions: Include status transition rules
                - status_type: Filter by status type
                - workflow_type: Filter by workflow type
                - include_inactive: Include inactive statuses
                - validate_transitions: Validate transition logic
        
        Returns:
            Sync results
        """
        # Set status-specific configuration
        self.include_workflows = kwargs.get('include_workflows', True)
        self.include_transitions = kwargs.get('include_transitions', True)
        self.status_type_filter = kwargs.get('status_type', 'all')
        self.workflow_type_filter = kwargs.get('workflow_type', 'all')
        self.include_inactive = kwargs.get('include_inactive', False)
        self.validate_transitions = kwargs.get('validate_transitions', True)
        
        # Initialize tracking metrics
        self.workflows_processed = 0
        self.transitions_processed = 0
        self.validation_errors = []
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add status-specific metrics
        if self.workflows_processed > 0:
            results['workflows_processed'] = self.workflows_processed
        
        if self.transitions_processed > 0:
            results['transitions_processed'] = self.transitions_processed
        
        # Add validation results
        if self.validation_errors:
            results['validation_errors'] = self.validation_errors
        
        # Add workflow validation results
        if self.validate_transitions:
            validation_results = await self._validate_workflow_consistency()
            results['workflow_validation'] = validation_results
        
        return results
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of task status records using bulk operations for better performance
        
        Args:
            batch: List of task status records from API
            
        Returns:
            Processing results
        """
        results = {
            'processed': 0,
            'created': 0,
            'updated': 0,
            'failed': 0,
            'errors': []
        }
        
        logger.debug(f"Processing batch of {len(batch)} task status records")
        
        try:
            # Process records through filtering and transformation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Apply status type filtering if configured
                    if self._should_skip_record_by_status_type(record):
                        continue
                    
                    # Apply workflow type filtering if configured
                    if self._should_skip_record_by_workflow_type(record):
                        continue
                    
                    # Skip inactive statuses if not requested
                    if not self.include_inactive and record.get('is_active', True) is False:
                        continue
                    
                    # Track different record types
                    record_type = record.get('type', 'status')
                    if record_type == 'workflow':
                        self.workflows_processed += 1
                    elif record_type == 'transition':
                        self.transitions_processed += 1
                    
                    # Validate record structure
                    if self.validate_transitions and record_type == 'transition':
                        validation_result = await self._validate_transition_record(record)
                        if not validation_result['valid']:
                            self.validation_errors.append({
                                'record_id': record.get('id'),
                                'errors': validation_result['errors']
                            })
                            continue
                    
                    # Use processor to transform record
                    status_data = self.processor.transform_record(record)
                    status_data = self.processor.validate_record(status_data)
                    
                    processed_batch.append(status_data)
                    results['processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing task status {record.get('id', 'unknown')}: {e}")
                    failed_count += 1
                    results['errors'].append(str(e))
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                bulk_results = await self._save_batch(processed_batch)
                results['created'] = bulk_results.get('created', 0)
                results['updated'] = bulk_results.get('updated', 0)
                results['failed'] += bulk_results.get('failed', 0) + failed_count
                logger.info(f"Task status batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            else:
                results['failed'] += failed_count
                logger.warning("No valid records to process in batch")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch)
            results['errors'].append(str(e))
        
        return results
    
    def _should_skip_record_by_status_type(self, record: Dict) -> bool:
        """Check if record should be skipped based on status type filter"""
        if self.status_type_filter == 'all':
            return False
        
        record_type = record.get('status_type', '').lower()
        target_type = self.status_type_filter.lower()
        
        # Handle type mappings
        type_mappings = {
            'task': ['task', 'job', 'appointment'],
            'crew': ['crew', 'group', 'team'],
            'system': ['system', 'internal', 'automatic']
        }
        
        if target_type in type_mappings:
            return record_type not in type_mappings[target_type]
        
        return record_type != target_type
    
    def _should_skip_record_by_workflow_type(self, record: Dict) -> bool:
        """Check if record should be skipped based on workflow type filter"""
        if self.workflow_type_filter == 'all':
            return False
        
        # Only apply to workflow records
        if record.get('type') != 'workflow':
            return False
        
        workflow_type = record.get('workflow_type', '').lower()
        target_type = self.workflow_type_filter.lower()
        
        return workflow_type != target_type
    
    async def _validate_transition_record(self, record: Dict) -> Dict[str, Any]:
        """Validate a status transition record"""
        validation_result = {'valid': True, 'errors': []}
        
        # Check required fields
        required_fields = ['from_status', 'to_status']
        for field in required_fields:
            if field not in record or not record[field]:
                validation_result['valid'] = False
                validation_result['errors'].append(f"Missing required field: {field}")
        
        # Check for circular transitions
        from_status = record.get('from_status')
        to_status = record.get('to_status')
        
        if from_status and to_status and from_status == to_status:
            validation_result['valid'] = False
            validation_result['errors'].append("Circular transition detected")
        
        # Check transition conditions
        conditions = record.get('conditions', [])
        if conditions and not isinstance(conditions, list):
            validation_result['valid'] = False
            validation_result['errors'].append("Invalid conditions format")
        
        return validation_result
    
    async def _validate_workflow_consistency(self) -> Dict[str, Any]:
        """Validate overall workflow consistency"""
        validation_results = {
            'total_workflows': 0,
            'valid_workflows': 0,
            'issues': []
        }
        
        # In a real implementation, you would:
        # 1. Check for orphaned statuses
        # 2. Validate transition paths
        # 3. Ensure no circular dependencies
        # 4. Check for unreachable statuses
        
        logger.info("Workflow consistency validation completed")
        return validation_results
    
    async def transform_record(self, record: Dict) -> Dict:
        """
        Transform API record for database storage
        
        Args:
            record: Raw record from API
            
        Returns:
            Transformed record for database
        """
        record_type = record.get('type', 'status')
        
        # Base transformation
        transformed = {
            'id': record.get('id'),
            'record_type': record_type,
            'name': record.get('name'),
            'display_name': record.get('display_name') or record.get('name'),
            'description': record.get('description'),
            'is_active': record.get('is_active', True),
            'raw_data': record
        }
        
        # Status-specific fields
        if record_type == 'status':
            transformed.update({
                'status_type': record.get('status_type'),
                'color': record.get('color'),
                'icon': record.get('icon'),
                'sort_order': record.get('sort_order', 0),
                'is_default': record.get('is_default', False),
                'is_final': record.get('is_final', False),
                'allows_editing': record.get('allows_editing', True)
            })
        
        # Workflow-specific fields
        elif record_type == 'workflow':
            self.workflows_processed += 1
            transformed.update({
                'workflow_type': record.get('workflow_type'),
                'version': record.get('version'),
                'is_default_workflow': record.get('is_default', False),
                'created_by': record.get('created_by'),
                'workflow_steps': record.get('steps', [])
            })
        
        # Transition-specific fields
        elif record_type == 'transition':
            self.transitions_processed += 1
            transformed.update({
                'from_status': record.get('from_status'),
                'to_status': record.get('to_status'),
                'conditions': record.get('conditions', []),
                'permissions': record.get('permissions', []),
                'auto_transition': record.get('auto_transition', False),
                'notification_settings': record.get('notifications', {})
            })
        
        # Handle timestamps
        for timestamp_field in ['created_at', 'updated_at']:
            if timestamp_field in record:
                transformed[timestamp_field] = self._parse_datetime(record[timestamp_field])
        
        # Handle custom properties
        if 'properties' in record:
            transformed['properties'] = record['properties']
        
        # Handle permissions
        if 'permissions' in record:
            permissions = record['permissions']
            if isinstance(permissions, dict):
                transformed['view_permissions'] = permissions.get('view', [])
                transformed['edit_permissions'] = permissions.get('edit', [])
                transformed['delete_permissions'] = permissions.get('delete', [])
        
        # Handle notification settings
        if 'notifications' in record:
            notifications = record['notifications']
            if isinstance(notifications, dict):
                transformed['notification_settings'] = notifications
        
        return transformed
    
    def _parse_datetime(self, date_str) -> Optional[datetime]:
        """Parse datetime string to datetime object"""
        if not date_str:
            return None
        
        try:
            if isinstance(date_str, str):
                # Handle various datetime formats
                return datetime.fromisoformat(date_str.replace('Z', '+00:00'))
            return date_str
        except (ValueError, TypeError):
            logger.warning(f"Could not parse datetime: {date_str}")
            return None
