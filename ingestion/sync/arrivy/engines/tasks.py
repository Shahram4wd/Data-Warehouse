"""
Arrivy Tasks Sync Engine

Handles synchronization of Arrivy tasks/jobs following enterprise patterns.
Tasks represent work assignments, appointments, and service calls.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from .base import ArrivyBaseSyncEngine
from ..clients.tasks import ArrivyTasksClient
from ..processors.tasks import TasksProcessor
from ingestion.models.arrivy import Arrivy_Task

logger = logging.getLogger(__name__)

class ArrivyTasksSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy tasks/jobs"""
    
    def __init__(self, **kwargs):
        super().__init__('tasks', **kwargs)
        self.client_class = ArrivyTasksClient
        self.processor = TasksProcessor()
        self.client_class = ArrivyTasksClient
    
    def get_model_class(self):
        """Get Django model class for tasks"""
        return Arrivy_Task
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch tasks data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of task records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching tasks with last_sync={last_sync}, batch_size={self.batch_size}")
        
        # Use tasks endpoint
        logger.info("Using tasks endpoint")
        async for batch in client.fetch_tasks(
            last_sync=last_sync,
            page_size=self.batch_size,
            max_records=self.max_records
        ):
            if self.dry_run:
                logger.info(f"DRY RUN: Would process {len(batch)} tasks")
                continue
                
            yield batch
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute tasks sync with additional task-specific options
        
        Args:
            **kwargs: Sync options including:
                - start_date: Filter tasks from this date
                - end_date: Filter tasks until this date
                - task_status: Filter by task status
                - assigned_to: Filter by assignee
        
        Returns:
            Sync results
        """
        # Configure date filters
        self.start_date = kwargs.get('start_date')
        self.end_date = kwargs.get('end_date')
        
        # Configure status and assignment filters
        self.task_status = kwargs.get('task_status')
        self.assigned_to = kwargs.get('assigned_to')
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add task-specific metrics
        results['endpoint_used'] = 'tasks'
        
        if self.start_date or self.end_date:
            results['date_range'] = {
                'start': self.start_date.isoformat() if self.start_date else None,
                'end': self.end_date.isoformat() if self.end_date else None
            }
        
        return results
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of task records using bulk operations for better performance
        
        Args:
            batch: List of task records from API
            
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
        
        logger.debug(f"Processing batch of {len(batch)} tasks")
        
        try:
            # Process records through filtering and transformation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Apply date filtering if configured
                    if self._should_skip_record_by_date(record):
                        continue
                    
                    # Apply status filtering if configured
                    if self._should_skip_record_by_status(record):
                        continue
                    
                    # Apply assignment filtering if configured
                    if self._should_skip_record_by_assignment(record):
                        continue
                    
                    # Use processor to transform record
                    task_data = self.processor.transform_record(record)
                    task_data = self.processor.validate_record(task_data)
                    
                    processed_batch.append(task_data)
                    results['processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing task {record.get('id', 'unknown')}: {e}")
                    failed_count += 1
                    results['errors'].append(str(e))
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                bulk_results = await self._save_batch(processed_batch)
                results['created'] = bulk_results.get('created', 0)
                results['updated'] = bulk_results.get('updated', 0)
                results['failed'] += bulk_results.get('failed', 0) + failed_count
                logger.info(f"Task batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            else:
                results['failed'] += failed_count
                logger.warning("No valid records to process in batch")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch)
            results['errors'].append(str(e))
        
        return results
    
    def _should_skip_record_by_date(self, record: Dict) -> bool:
        """Check if record should be skipped based on date filters"""
        if not (self.start_date or self.end_date):
            return False
        
        # Get record date (could be created_date, updated_date, or scheduled_date)
        record_date = None
        for date_field in ['scheduled_date', 'created_date', 'updated_date', 'datetime']:
            if date_field in record and record[date_field]:
                try:
                    if isinstance(record[date_field], str):
                        record_date = datetime.fromisoformat(record[date_field].replace('Z', '+00:00'))
                    else:
                        record_date = record[date_field]
                    break
                except (ValueError, TypeError):
                    continue
        
        if not record_date:
            return False  # Don't skip if we can't determine date
        
        # Apply date filters
        if self.start_date and record_date < self.start_date:
            return True
        
        if self.end_date and record_date > self.end_date:
            return True
        
        return False
    
    def _should_skip_record_by_status(self, record: Dict) -> bool:
        """Check if record should be skipped based on status filter"""
        if not self.task_status:
            return False
        
        record_status = record.get('status', '').lower()
        target_status = self.task_status.lower()
        
        return record_status != target_status
    
    def _should_skip_record_by_assignment(self, record: Dict) -> bool:
        """Check if record should be skipped based on assignment filter"""
        if not self.assigned_to:
            return False
        
        # Check various assignment fields
        assigned_fields = ['assigned_to', 'assignee', 'crew_id', 'team_id']
        for field in assigned_fields:
            if field in record and record[field]:
                if str(record[field]) == str(self.assigned_to):
                    return False
        
        return True  # Skip if not assigned to target
    
    async def transform_record(self, record: Dict) -> Dict:
        """
        Transform API record for database storage
        
        Args:
            record: Raw record from API
            
        Returns:
            Transformed record for database
        """
        # Basic field mapping
        transformed = {
            'id': record.get('id'),
            'title': record.get('title') or record.get('job_title'),
            'description': record.get('description') or record.get('job_description'),
            'status': record.get('status'),
            'customer_id': record.get('customer_id'),
            'assignee_id': record.get('assigned_to') or record.get('assignee'),
            'created_date': self._parse_datetime(record.get('created_date')),
            'updated_date': self._parse_datetime(record.get('updated_date')),
            'scheduled_date': self._parse_datetime(record.get('scheduled_date') or record.get('datetime')),
            'raw_data': record
        }
        
        # Handle address/location data
        if 'customer_address' in record:
            address = record['customer_address']
            transformed.update({
                'customer_address': address.get('complete_address'),
                'customer_city': address.get('city'),
                'customer_state': address.get('state'),
                'customer_zipcode': address.get('zipcode')
            })
        
        # Handle pricing/estimate data
        if 'estimate' in record:
            transformed['estimate_amount'] = record['estimate']
        
        # Handle completion data
        if 'completion_time' in record:
            transformed['completion_time'] = self._parse_datetime(record['completion_time'])
        
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
