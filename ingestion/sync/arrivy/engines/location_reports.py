"""
Arrivy Location Reports Sync Engine

Handles synchronization of Arrivy location tracking and GPS data following enterprise patterns.
Location reports represent GPS tracking, check-ins, check-outs, and movement data.
"""

import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from datetime import datetime, timedelta

from .base import ArrivyBaseSyncEngine
from ..clients.location_reports import ArrivyLocationReportsClient
from ..processors.location_reports import LocationReportsProcessor
from ingestion.models.arrivy import Arrivy_LocationReport

logger = logging.getLogger(__name__)

class ArrivyLocationReportsSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy location reports"""
    
    def __init__(self, **kwargs):
        super().__init__('location_reports', **kwargs)
        self.client_class = ArrivyLocationReportsClient
        self.processor = LocationReportsProcessor()

class ArrivyLocationReportsSyncEngine(ArrivyBaseSyncEngine):
    """Sync engine for Arrivy location reports and GPS tracking data"""
    
    def __init__(self, **kwargs):
        super().__init__('location_reports', **kwargs)
        self.client_class = ArrivyLocationReportsClient
    
    def get_model_class(self):
        """Get Django model class for location reports"""
        return Arrivy_LocationReport
    
    async def fetch_data(self, last_sync: Optional[datetime] = None) -> AsyncGenerator[List[Dict], None]:
        """
        Fetch location reports data from Arrivy API
        
        Args:
            last_sync: Last sync timestamp for incremental sync
            
        Yields:
            Batches of location report records
        """
        client = await self.initialize_client()
        
        logger.info(f"Fetching location reports with last_sync={last_sync}, batch_size={self.batch_size}")
        
        # Determine time range for sync
        if last_sync:
            start_time = last_sync
        else:
            # Default to last 24 hours for incremental, or configurable range
            hours_back = getattr(self, 'date_range_hours', 24)
            start_time = datetime.utcnow() - timedelta(hours=hours_back)
        
        end_time = datetime.utcnow()
        
        logger.info(f"Fetching location data from {start_time} to {end_time}")
        
        # Fetch from location reports endpoint
        async for batch in client.fetch_location_reports(
            start_time=start_time,
            end_time=end_time,
            page_size=self.batch_size,
            max_records=self.max_records,
            location_type=getattr(self, 'location_type_filter', 'all'),
            entity_type=getattr(self, 'entity_type_filter', 'all')
        ):
            if self.dry_run:
                logger.info(f"DRY RUN: Would process {len(batch)} location reports")
                continue
            
            yield batch
        
        # Also fetch GPS tracking data if requested
        if getattr(self, 'include_gps_tracks', False):
            logger.info("Also fetching GPS tracking data")
            
            async for batch in client.fetch_gps_tracks(
                start_time=start_time,
                end_time=end_time,
                page_size=self.batch_size,
                max_records=self.max_records,
                track_interval=getattr(self, 'track_interval', 300)  # 5 minutes default
            ):
                if self.dry_run:
                    logger.info(f"DRY RUN: Would process {len(batch)} GPS tracking points")
                    continue
                
                yield batch
    
    async def execute_sync(self, **kwargs) -> Dict[str, Any]:
        """
        Execute location reports sync with additional location-specific options
        
        Args:
            **kwargs: Sync options including:
                - include_gps_tracks: Include detailed GPS tracking data
                - track_interval: GPS tracking interval in seconds
                - location_type: Filter by location event type
                - entity_type: Filter by related entity type
                - date_range_hours: Time range in hours for incremental sync
                - accuracy_threshold: GPS accuracy threshold in meters
        
        Returns:
            Sync results
        """
        # Set location-specific configuration
        self.include_gps_tracks = kwargs.get('include_gps_tracks', False)
        self.track_interval = kwargs.get('track_interval', 300)
        self.location_type_filter = kwargs.get('location_type', 'all')
        self.entity_type_filter = kwargs.get('entity_type', 'all')
        self.date_range_hours = kwargs.get('date_range_hours', 24)
        self.accuracy_threshold = kwargs.get('accuracy_threshold', 100)
        
        # Initialize tracking metrics
        self.gps_points_processed = 0
        self.data_quality_metrics = {
            'accuracy_filtered': 0,
            'duplicate_locations': 0,
            'total_accuracy': 0,
            'accuracy_count': 0
        }
        
        # Call parent execute_sync
        results = await super().execute_sync(**kwargs)
        
        # Add location-specific metrics
        if self.gps_points_processed > 0:
            results['gps_points_processed'] = self.gps_points_processed
        
        # Add data quality metrics
        if self.data_quality_metrics['accuracy_count'] > 0:
            avg_accuracy = self.data_quality_metrics['total_accuracy'] / self.data_quality_metrics['accuracy_count']
            results['data_quality'] = {
                'accuracy_filtered': self.data_quality_metrics['accuracy_filtered'],
                'duplicate_locations': self.data_quality_metrics['duplicate_locations'],
                'avg_accuracy': avg_accuracy
            }
        
        # Add time range information
        if hasattr(self, 'actual_start_time') and hasattr(self, 'actual_end_time'):
            results['time_range'] = {
                'start': self.actual_start_time.isoformat(),
                'end': self.actual_end_time.isoformat()
            }
        
        return results
    
    async def process_batch(self, batch: List[Dict]) -> Dict[str, Any]:
        """
        Process a batch of location report records using bulk operations for better performance
        
        Args:
            batch: List of location report records from API
            
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
        
        logger.debug(f"Processing batch of {len(batch)} location reports")
        
        try:
            # Process records through filtering and transformation
            processed_batch = []
            failed_count = 0
            
            for record in batch:
                try:
                    # Apply accuracy filtering if configured
                    if self._should_skip_record_by_accuracy(record):
                        self.data_quality_metrics['accuracy_filtered'] += 1
                        continue
                    
                    # Apply location type filtering if configured
                    if self._should_skip_record_by_location_type(record):
                        continue
                    
                    # Apply entity type filtering if configured
                    if self._should_skip_record_by_entity_type(record):
                        continue
                    
                    # Check for duplicates
                    if await self._is_duplicate_location(record):
                        self.data_quality_metrics['duplicate_locations'] += 1
                        continue
                    
                    # Track GPS points
                    if record.get('type') == 'gps_track':
                        self.gps_points_processed += 1
                    
                    # Track accuracy metrics
                    if 'accuracy' in record and record['accuracy']:
                        self.data_quality_metrics['total_accuracy'] += record['accuracy']
                        self.data_quality_metrics['accuracy_count'] += 1
                    
                    # Use processor to transform record
                    location_data = self.processor.transform_record(record)
                    location_data = self.processor.validate_record(location_data)
                    
                    processed_batch.append(location_data)
                    results['processed'] += 1
                        
                except Exception as e:
                    logger.error(f"Error processing location report {record.get('id', 'unknown')}: {e}")
                    failed_count += 1
                    results['errors'].append(str(e))
            
            # Use parent's bulk upsert method for actual database operations
            if processed_batch:
                bulk_results = await self._save_batch(processed_batch)
                results['created'] = bulk_results.get('created', 0)
                results['updated'] = bulk_results.get('updated', 0)
                results['failed'] += bulk_results.get('failed', 0) + failed_count
                logger.info(f"Location report batch results: {results['created']} created, {results['updated']} updated, {results['failed']} failed")
            else:
                results['failed'] += failed_count
                logger.warning("No valid records to process in batch")
            
        except Exception as e:
            logger.error(f"Batch processing failed: {str(e)}")
            results['failed'] = len(batch)
            results['errors'].append(str(e))
        
        return results
        
        return results
    
    def _should_skip_record_by_accuracy(self, record: Dict) -> bool:
        """Check if record should be skipped based on GPS accuracy threshold"""
        if not self.accuracy_threshold:
            return False
        
        accuracy = record.get('accuracy')
        if accuracy is None:
            return False  # Don't skip if accuracy is unknown
        
        return accuracy > self.accuracy_threshold
    
    def _should_skip_record_by_location_type(self, record: Dict) -> bool:
        """Check if record should be skipped based on location type filter"""
        if self.location_type_filter == 'all':
            return False
        
        record_type = record.get('type', '').lower()
        target_type = self.location_type_filter.lower()
        
        # Handle type mappings
        type_mappings = {
            'checkin': ['checkin', 'check_in', 'arrival'],
            'checkout': ['checkout', 'check_out', 'departure'],
            'track': ['track', 'gps_track', 'tracking', 'movement']
        }
        
        if target_type in type_mappings:
            return record_type not in type_mappings[target_type]
        
        return record_type != target_type
    
    def _should_skip_record_by_entity_type(self, record: Dict) -> bool:
        """Check if record should be skipped based on entity type filter"""
        if self.entity_type_filter == 'all':
            return False
        
        # Check related entity type
        entity_type = record.get('entity_type', '').lower()
        target_type = self.entity_type_filter.lower()
        
        return entity_type != target_type
    
    async def _is_duplicate_location(self, record: Dict) -> bool:
        """Check if this location record is a duplicate"""
        # Simple duplicate detection based on timestamp, coordinates, and entity
        key_fields = ['timestamp', 'latitude', 'longitude', 'entity_id']
        
        for field in key_fields:
            if field not in record or record[field] is None:
                return False  # Can't determine if duplicate without key fields
        
        # In a real implementation, you'd check the database for existing records
        # For now, return False (no duplicates detected)
        return False
    
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
            'entity_id': record.get('entity_id'),
            'entity_type': record.get('entity_type'),
            'location_type': record.get('type'),
            'timestamp': self._parse_datetime(record.get('timestamp')),
            'latitude': record.get('latitude'),
            'longitude': record.get('longitude'),
            'accuracy': record.get('accuracy'),
            'raw_data': record
        }
        
        # Handle address data
        if 'address' in record:
            address = record['address']
            if isinstance(address, dict):
                transformed.update({
                    'address': address.get('formatted_address'),
                    'city': address.get('city'),
                    'state': address.get('state'),
                    'country': address.get('country'),
                    'postal_code': address.get('postal_code')
                })
            else:
                transformed['address'] = str(address)
        
        # Handle speed and heading data
        if 'speed' in record:
            transformed['speed'] = record['speed']
        
        if 'heading' in record:
            transformed['heading'] = record['heading']
        
        # Handle altitude data
        if 'altitude' in record:
            transformed['altitude'] = record['altitude']
        
        # Handle task/job association
        if 'task_id' in record:
            transformed['task_id'] = record['task_id']
        
        if 'job_id' in record:
            transformed['job_id'] = record['job_id']
        
        # Handle battery and device info
        if 'battery_level' in record:
            transformed['battery_level'] = record['battery_level']
        
        if 'device_info' in record:
            device_info = record['device_info']
            if isinstance(device_info, dict):
                transformed['device_id'] = device_info.get('device_id')
                transformed['device_type'] = device_info.get('type')
        
        # Handle custom fields
        if 'custom_fields' in record:
            transformed['custom_fields'] = record['custom_fields']
        
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
