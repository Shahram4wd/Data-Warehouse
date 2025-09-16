"""
Arrivy Status Sync Engine

Handles synchronization of Arrivy status definitions following enterprise patterns.
Statuses represent the available status values in Arrivy workflows.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from .base import ArrivyBaseSyncEngine
from ..clients.status import ArrivyStatusClient
from ..processors.status import StatusProcessor
from ingestion.models.arrivy import Arrivy_Status

logger = logging.getLogger(__name__)

class ArrivyStatusSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy status definitions"""
    
    def __init__(self, **kwargs):
        super().__init__('statuses', **kwargs)
        self.client_class = ArrivyStatusClient
        self.processor = StatusProcessor()
    
    def get_model_class(self):
        """Get Django model class for statuses"""
        return Arrivy_Status
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch status data from Arrivy API using only the statuses endpoint
        
        Args:
            last_sync: Last sync timestamp (not used for statuses as they don't change often)
            
        Yields:
            Batches of status records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching statuses from 'statuses' endpoint with batch_size={self.batch_size}")
        
        # Only use the statuses endpoint as requested
        async for all_statuses in client.fetch_statuses(
            page_size=self.batch_size,
            max_records=self.max_records,
            include_inactive=getattr(self, 'include_inactive', False)
        ):
            if not all_statuses:
                continue

            # Apply delta filtering when last_sync is provided and records have updated_at
            filtered = all_statuses
            if last_sync:
                def parse_dt(v):
                    try:
                        if isinstance(v, str):
                            return datetime.fromisoformat(v.replace('Z', '+00:00'))
                        return v
                    except Exception:
                        return None
                filtered = []
                for s in all_statuses:
                    updated_at = s.get('updated_at') or s.get('modified_at') or s.get('modifiedAt')
                    dt = parse_dt(updated_at)
                    # If no timestamp, skip in incremental mode
                    if dt is None:
                        continue
                    if dt >= last_sync:
                        filtered.append(s)

                logger.info(f"Delta filter applied: {len(filtered)}/{len(all_statuses)} statuses after {last_sync}")

            # Implement artificial chunking to respect batch_size
            batch_size = max(1, int(self.batch_size or 100))
            for i in range(0, len(filtered), batch_size):
                batch = filtered[i:i + batch_size]
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process chunk with {len(batch)} statuses")
                    continue
                yield batch
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute status sync with status-specific options
        
        Args:
            **kwargs: Sync options including:
                - include_inactive: Include inactive statuses
        
        Returns:
            Sync results
        """
        # Set status-specific configuration
        self.include_inactive = kwargs.get('include_inactive', False)
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add status-specific metrics
        results['endpoint_used'] = 'statuses'
        results['include_inactive'] = self.include_inactive
        
        return results
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of status records using the base engine's bulk operations
        
        Args:
            batch: List of status records from API
            
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
        
        logger.debug(f"Processing batch of {len(batch)} status records")
        
        try:
            # Process records through transformation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Skip inactive statuses if not requested
                    if not self.include_inactive and record.get('is_active', True) is False:
                        continue
                    
                    # Use processor to transform record
                    status_data = self.processor.transform_record(record)
                    status_data = self.processor.validate_record(status_data)
                    
                    processed_batch.append(status_data)
                    results['processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing status {record.get('id', 'unknown')}: {e}")
                    failed_count += 1
                    results['errors'].append(str(e))
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                bulk_results = await self._save_batch(processed_batch)
                results['created'] = bulk_results.get('created', 0)
                results['updated'] = bulk_results.get('updated', 0)
                results['failed'] += bulk_results.get('failed', 0) + failed_count
                logger.info(f"Status batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            else:
                results['failed'] += failed_count
                logger.warning("No valid records to process in batch")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch)
            results['errors'].append(str(e))
        
        return results

    
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
