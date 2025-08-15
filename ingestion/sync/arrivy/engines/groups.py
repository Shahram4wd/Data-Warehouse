"""
Arrivy Groups Sync Engine

Handles synchronization of Arrivy groups/crews/divisions following enterprise patterns.
Groups represent organizational units, teams, and crew divisions.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime

from .base import ArrivyBaseSyncEngine
from ..clients.groups import ArrivyGroupsClient
from ..processors.groups import GroupsProcessor
from ingestion.models.arrivy import Arrivy_Group

logger = logging.getLogger(__name__)

class ArrivyGroupsSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy groups/crews/divisions"""
    
    def __init__(self, **kwargs):
        super().__init__('groups', **kwargs)
        self.client_class = ArrivyGroupsClient
        self.processor = GroupsProcessor()
    
    def get_model_class(self):
        """Get Django model class for groups"""
        return Arrivy_Group
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch groups data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of group records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching groups with last_sync={last_sync}, batch_size={self.batch_size}")
        
        # Determine which endpoints to use based on configuration
        include_crews = getattr(self, 'include_crews', False)
        crews_only = getattr(self, 'crews_only', False)
        include_singular_crew = getattr(self, 'include_singular_crew', False)
        
        endpoint_usage = {}
        
        if crews_only:
            # Only fetch from crews endpoint
            logger.info("Fetching from crews endpoint only")
            async for batch in client.fetch_crews(
                last_sync=last_sync,
                page_size=self.batch_size,
                max_records=self.max_records
            ):
                endpoint_usage['crews'] = endpoint_usage.get('crews', 0) + len(batch)
                
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process {len(batch)} crews")
                    continue
                
                yield batch
        
        else:
            # Fetch from groups endpoint (default)
            logger.info("Fetching from groups endpoint")
            async for batch in client.fetch_groups(
                last_sync=last_sync,
                page_size=self.batch_size,
                max_records=self.max_records
            ):
                endpoint_usage['groups'] = endpoint_usage.get('groups', 0) + len(batch)
                
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process {len(batch)} groups")
                    continue
                
                yield batch
            
            # Also fetch from crews endpoint if requested
            if include_crews:
                logger.info("Also fetching from crews endpoint")
                async for batch in client.fetch_crews(
                    last_sync=last_sync,
                    page_size=self.batch_size,
                    max_records=self.max_records
                ):
                    endpoint_usage['crews'] = endpoint_usage.get('crews', 0) + len(batch)
                    
                    if self.dry_run:
                        logger.info(f"DRY RUN: Would process {len(batch)} crews")
                        continue
                    
                    yield batch
        
        # Fetch from singular crew endpoint if requested
        if include_singular_crew:
            logger.info("Also fetching from singular crew endpoint")
            try:
                crew_data = await client.fetch_singular_crew()
                if crew_data:
                    endpoint_usage['singular_crew'] = 1
                    
                    if self.dry_run:
                        logger.info("DRY RUN: Would process singular crew data")
                    else:
                        yield [crew_data]
            except Exception as e:
                logger.warning(f"Could not fetch singular crew data: {e}")
        
        # Store endpoint usage for reporting
        self.endpoint_usage = endpoint_usage
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute groups sync with additional group-specific options
        
        Args:
            **kwargs: Sync options including:
                - include_crews: Also sync from crews endpoint
                - crews_only: Sync only from crews endpoint
                - include_singular_crew: Include singular crew data
                - group_type: Filter by group type
                - include_inactive: Include inactive groups
        
        Returns:
            Sync results
        """
        # Set group-specific configuration
        self.include_crews = kwargs.get('include_crews', False)
        self.crews_only = kwargs.get('crews_only', False)
        self.include_singular_crew = kwargs.get('include_singular_crew', False)
        self.group_type_filter = kwargs.get('group_type', 'all')
        self.include_inactive = kwargs.get('include_inactive', False)
        
        # Initialize endpoint usage tracking
        self.endpoint_usage = {}
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add group-specific metrics
        if hasattr(self, 'endpoint_usage'):
            results['endpoint_usage'] = self.endpoint_usage
        
        # Add sync mode information
        if self.crews_only:
            results['sync_mode'] = 'crews_only'
        elif self.include_crews:
            results['sync_mode'] = 'groups_and_crews'
        else:
            results['sync_mode'] = 'groups_only'
        
        return results
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of group records using bulk operations for better performance
        
        Args:
            batch: List of group records from API
            
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
        
        logger.debug(f"Processing batch of {len(batch)} groups")
        
        try:
            # Process records through filtering and transformation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Apply group type filtering if configured
                    if self._should_skip_record_by_type(record):
                        continue
                    
                    # Apply active/inactive filtering if configured
                    if self._should_skip_record_by_status(record):
                        continue
                    
                    # Use processor to transform record
                    group_data = self.processor.transform_record(record)
                    group_data = self.processor.validate_record(group_data)
                    
                    processed_batch.append(group_data)
                    results['processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing group {record.get('id', 'unknown')}: {e}")
                    failed_count += 1
                    results['errors'].append(str(e))
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                bulk_results = await self._save_batch(processed_batch)
                results['created'] = bulk_results.get('created', 0)
                results['updated'] = bulk_results.get('updated', 0)
                results['failed'] += bulk_results.get('failed', 0) + failed_count
                logger.info(f"Group batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            else:
                results['failed'] += failed_count
                logger.warning("No valid records to process in batch")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch)
            results['errors'].append(str(e))
        
        return results
    
    def _should_skip_record_by_type(self, record: Dict) -> bool:
        """Check if record should be skipped based on group type filter"""
        if self.group_type_filter == 'all':
            return False
        
        record_type = record.get('type', '').lower()
        target_type = self.group_type_filter.lower()
        
        # Handle various type mappings
        type_mappings = {
            'division': ['division', 'dept', 'department'],
            'team': ['team', 'crew', 'group'],
            'department': ['department', 'dept', 'division']
        }
        
        if target_type in type_mappings:
            return record_type not in type_mappings[target_type]
        
        return record_type != target_type
    
    def _should_skip_record_by_status(self, record: Dict) -> bool:
        """Check if record should be skipped based on active/inactive filter"""
        if self.include_inactive:
            return False  # Include all records
        
        # Skip inactive records if include_inactive is False
        is_active = record.get('is_active', True)
        status = record.get('status', '').lower()
        
        return not is_active or status in ['inactive', 'disabled', 'archived']
    
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
            'name': record.get('name') or record.get('title'),
            'description': record.get('description'),
            'type': record.get('type') or 'group',
            'is_active': record.get('is_active', True),
            'created_date': self._parse_datetime(record.get('created_date')),
            'updated_date': self._parse_datetime(record.get('updated_date')),
            'raw_data': record
        }
        
        # Handle parent/child relationships
        if 'parent_id' in record:
            transformed['parent_group_id'] = record['parent_id']
        
        # Handle member count
        if 'member_count' in record:
            transformed['member_count'] = record['member_count']
        elif 'members' in record and isinstance(record['members'], list):
            transformed['member_count'] = len(record['members'])
        
        # Handle location/territory data
        if 'territory' in record:
            territory = record['territory']
            if isinstance(territory, dict):
                transformed['territory_name'] = territory.get('name')
                transformed['territory_id'] = territory.get('id')
        
        # Handle manager/supervisor data
        if 'manager' in record:
            manager = record['manager']
            if isinstance(manager, dict):
                transformed['manager_id'] = manager.get('id')
                transformed['manager_name'] = manager.get('name')
            else:
                transformed['manager_id'] = manager
        
        # Handle contact information
        if 'contact_info' in record:
            contact = record['contact_info']
            if isinstance(contact, dict):
                transformed['contact_email'] = contact.get('email')
                transformed['contact_phone'] = contact.get('phone')
        
        # Handle settings/preferences
        if 'settings' in record:
            settings = record['settings']
            if isinstance(settings, dict):
                transformed['settings'] = settings
        
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
