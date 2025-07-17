"""
HubSpot zipcodes sync engine using unified architecture
"""
import logging
from typing import Dict, Any, List, Optional, AsyncGenerator
from asgiref.sync import sync_to_async
from ingestion.base.exceptions import SyncException, ValidationException
from ingestion.sync.hubspot.clients.zipcodes import HubSpotZipCodeClient
from ingestion.sync.hubspot.processors.zipcodes import HubSpotZipCodeProcessor
from ingestion.sync.hubspot.engines.base import HubSpotBaseSyncEngine
from ingestion.models.hubspot import Hubspot_ZipCode

logger = logging.getLogger(__name__)

class HubSpotZipcodeSyncEngine(HubSpotBaseSyncEngine):
    """Sync engine for HubSpot zipcodes from GitHub CSV"""
    
    def __init__(self, **kwargs):
        super().__init__('zipcodes', **kwargs)
        self.force_overwrite = kwargs.get('force_overwrite', False)
        
    async def initialize_client(self) -> None:
        """Initialize GitHub CSV client and processor"""
        await self.initialize_enterprise_features()
        
        self.client = HubSpotZipCodeClient()
        self.processor = HubSpotZipCodeProcessor()
        
    async def fetch_data(self, **kwargs) -> AsyncGenerator[List[Dict[str, Any]], None]:
        """Fetch zipcode data from GitHub CSV"""
        if not self.client:
            raise SyncException("Client not initialized")
        
        try:
            # Fetch CSV from GitHub
            csv_content = await sync_to_async(self.client.fetch_csv)()
            
            # Parse CSV into records
            records = await sync_to_async(self.processor.parse_csv)(csv_content)
            valid_records = await sync_to_async(self.processor.filter_valid)(records)
            
            # Yield in batches
            for i in range(0, len(valid_records), self.batch_size):
                batch = valid_records[i:i+self.batch_size]
                yield batch
                
        except Exception as e:
            logger.error(f"Error fetching zipcodes: {e}")
            await self.handle_sync_error(e, {
                'operation': 'fetch_data',
                'entity_type': 'zipcodes'
            })
            raise SyncException(f"Failed to fetch zipcodes: {e}")
            
    async def transform_data(self, raw_data: List[Dict]) -> List[Dict]:
        """Transform zipcode data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        transformed_data = []
        for record in raw_data:
            try:
                transformed = await sync_to_async(self.processor.transform_record)(record)
                transformed_data.append(transformed)
            except Exception as e:
                logger.error(f"Error transforming zipcode record: {e}")
                # Continue processing other records
                
        return transformed_data
        
    async def validate_data(self, data: List[Dict]) -> List[Dict]:
        """Validate zipcode data"""
        if not self.processor:
            raise SyncException("Processor not initialized")
        
        validated_data = []
        for record in data:
            try:
                validated = await sync_to_async(self.processor.validate_record)(record)
                validated_data.append(validated)
            except ValidationException as e:
                logger.error(f"Validation error for zipcode: {e}")
                # Continue processing other records
                
        return validated_data
        
    async def save_data(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Save zipcode data to database with enterprise monitoring and bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        if not validated_data:
            return results
        
        try:
            if self.force_overwrite:
                logger.info("Force overwrite mode - all records will be updated regardless of timestamps")
                results = await self._force_overwrite_zipcodes(validated_data)
            else:
                results = await self._bulk_save_zipcodes(validated_data)
        except Exception as bulk_error:
            logger.warning(f"Bulk save failed, falling back to individual saves: {bulk_error}")
            if self.force_overwrite:
                results = await self._individual_force_save_zipcodes(validated_data)
            else:
                results = await self._individual_save_zipcodes(validated_data)
        
        # Calculate and report enterprise metrics
        total_processed = len(validated_data)
        success_count = results['created'] + results['updated']
        success_rate = success_count / total_processed if total_processed > 0 else 0
        
        # Report metrics to enterprise monitoring system
        await self.report_sync_metrics({
            'entity_type': 'zipcodes',
            'processed': total_processed,
            'success_rate': success_rate,
            'data_quality_score': self._calculate_data_quality_score(validated_data, results),
            'results': results
        })
        
        logger.info(f"Zipcode sync completed - Created: {results['created']}, "
                   f"Updated: {results['updated']}, Failed: {results['failed']}, "
                   f"Success Rate: {success_rate:.2%}")
        
        return results
    
    async def _bulk_save_zipcodes(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Bulk save zipcodes using bulk_create with update_conflicts"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        try:
            zipcode_objects = [Hubspot_ZipCode(**record) for record in validated_data]
            created_zipcodes = await sync_to_async(Hubspot_ZipCode.objects.bulk_create)(
                zipcode_objects,
                batch_size=self.batch_size,
                update_conflicts=True,
                update_fields=['division', 'city', 'county', 'state', 'archived', 'updated_at'],
                unique_fields=['zipcode']
            )
            results['created'] = len([obj for obj in created_zipcodes if obj._state.adding])
            results['updated'] = len(validated_data) - results['created']
        except Exception as e:
            logger.error(f"Bulk upsert failed: {e}")
            results['failed'] = len(validated_data)
        return results
    
    async def _individual_save_zipcodes(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Individual save with get_or_create"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                zipcode = record.get('zipcode')
                if not zipcode:
                    logger.error(f"Zipcode record missing zipcode field: {record}")
                    results['failed'] += 1
                    continue
                
                zipcode_obj, created = await sync_to_async(Hubspot_ZipCode.objects.get_or_create)(
                    zipcode=zipcode,
                    defaults=record
                )
                
                if not created:
                    for field, value in record.items():
                        if hasattr(zipcode_obj, field):
                            setattr(zipcode_obj, field, value)
                    await sync_to_async(zipcode_obj.save)()
                
                if created:
                    results['created'] += 1
                else:
                    results['updated'] += 1
                    
            except Exception as e:
                logger.error(f"Error saving zipcode {record.get('zipcode')}: {e}")
                results['failed'] += 1
                
        return results
    
    async def _force_overwrite_zipcodes(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite all zipcodes using bulk operations"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        if not validated_data:
            return results

        zipcodes = [record['zipcode'] for record in validated_data if record.get('zipcode')]
        
        try:
            # Get existing zipcodes
            existing_zipcodes = await sync_to_async(list)(
                Hubspot_ZipCode.objects.filter(zipcode__in=zipcodes).values_list('zipcode', flat=True)
            )
            existing_zipcode_set = set(existing_zipcodes)
            
            # Separate new vs existing records
            new_records = [record for record in validated_data if record.get('zipcode') not in existing_zipcode_set]
            update_records = [record for record in validated_data if record.get('zipcode') in existing_zipcode_set]
            
            # Force create new records
            if new_records:
                new_zipcode_objects = [Hubspot_ZipCode(**record) for record in new_records]
                await sync_to_async(Hubspot_ZipCode.objects.bulk_create)(
                    new_zipcode_objects,
                    batch_size=self.batch_size
                )
                results['created'] = len(new_records)
                logger.info(f"Force created {results['created']} new zipcodes")
            
            # Force update existing records - delete and recreate
            if update_records:
                await sync_to_async(Hubspot_ZipCode.objects.filter(zipcode__in=[r['zipcode'] for r in update_records]).delete)()
                
                update_zipcode_objects = [Hubspot_ZipCode(**record) for record in update_records]
                await sync_to_async(Hubspot_ZipCode.objects.bulk_create)(
                    update_zipcode_objects,
                    batch_size=self.batch_size
                )
                results['updated'] = len(update_records)
                logger.info(f"Force overwritten {results['updated']} existing zipcodes")
                
        except Exception as e:
            logger.error(f"Force bulk overwrite failed: {e}")
            results['failed'] = len(validated_data)
            
        return results
    
    async def _individual_force_save_zipcodes(self, validated_data: List[Dict]) -> Dict[str, int]:
        """Force overwrite zipcodes individually"""
        results = {'created': 0, 'updated': 0, 'failed': 0}
        
        for record in validated_data:
            try:
                zipcode = record.get('zipcode')
                if not zipcode:
                    logger.error(f"Zipcode record missing zipcode field: {record}")
                    results['failed'] += 1
                    continue
                
                # Check if zipcode exists
                zipcode_exists = await sync_to_async(Hubspot_ZipCode.objects.filter(zipcode=zipcode).exists)()
                
                if zipcode_exists:
                    # Force delete and recreate
                    await sync_to_async(Hubspot_ZipCode.objects.filter(zipcode=zipcode).delete)()
                    zipcode_obj = Hubspot_ZipCode(**record)
                    await sync_to_async(zipcode_obj.save)()
                    results['updated'] += 1
                else:
                    # Create new
                    zipcode_obj = Hubspot_ZipCode(**record)
                    await sync_to_async(zipcode_obj.save)()
                    results['created'] += 1
                    
            except Exception as e:
                logger.error(f"Error force saving zipcode {record.get('zipcode')}: {e}")
                results['failed'] += 1
                
        return results
    
    def _calculate_data_quality_score(self, validated_data: List[Dict], results: Dict[str, int]) -> float:
        """Calculate data quality score for zipcodes"""
        if not validated_data:
            return 1.0
        
        total_records = len(validated_data)
        successful_records = results['created'] + results['updated']
        
        # Base score from success rate
        success_score = successful_records / total_records
        
        # Quality factors for zipcodes
        quality_factors = []
        
        for record in validated_data:
            record_quality = 0.0
            total_checks = 0
            
            # Check completeness of key fields
            if record.get('zipcode'):
                record_quality += 1
                total_checks += 1
            if record.get('state'):
                record_quality += 1
                total_checks += 1
            if record.get('city'):
                record_quality += 1
                total_checks += 1
            if record.get('county'):
                record_quality += 1
                total_checks += 1
            
            if total_checks > 0:
                quality_factors.append(record_quality / total_checks)
            else:
                quality_factors.append(0.5)
        
        avg_quality = sum(quality_factors) / len(quality_factors) if quality_factors else 0.5
        final_score = (success_score * 0.7) + (avg_quality * 0.3)
        
        return min(final_score, 1.0)
