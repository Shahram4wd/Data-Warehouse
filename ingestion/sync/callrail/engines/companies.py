"""
CallRail companies sync engine aligned with CRM sync guide
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.companies import CompaniesClient
from ..processors.companies import CompaniesProcessor

logger = logging.getLogger(__name__)


class CompaniesSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail companies"""
    
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = CompaniesClient()
        self.processor = CompaniesProcessor()
        self.entity_name = "companies"
    
    @sync_to_async
    def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Use SyncHistory last successful end_time for delta (callrail/companies)"""
        from ingestion.models.common import SyncHistory
        last = (SyncHistory.objects
                .filter(crm_source='callrail', sync_type='companies', status='success', end_time__isnull=False)
                .order_by('-end_time').first())
        return last.end_time if last else None
    
    async def sync_companies(self, **kwargs) -> Dict[str, Any]:
        """Sync companies from CallRail API with enterprise semantics"""
        full_sync = kwargs.get('full_sync', False)
        force_overwrite = kwargs.get('force_overwrite', False) or kwargs.get('force', False)
        logger.info(f"Starting companies sync (full_sync={full_sync}, force_overwrite={force_overwrite})")

        # Create SyncHistory record (for dashboard + delta reference)
        from ingestion.models.common import SyncHistory
        sync_history_data = {
            'crm_source': 'callrail',
            'sync_type': 'companies',
            'start_time': timezone.now(),
            'status': 'running',
            'configuration': {
                'full_sync': full_sync,
                'force_overwrite': force_overwrite,
                **{k: v for k, v in kwargs.items() if k not in ['full_sync', 'force', 'force_overwrite']}
            }
        }

        @sync_to_async
        def create_sync_history():
            return SyncHistory.objects.create(**sync_history_data)

        sync_history = await create_sync_history()

        # Working stats we will also persist into SyncHistory on completion
        sync_stats = {
            'entity': 'companies',
            'full_sync': full_sync,
            'force_overwrite': force_overwrite,
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'total_errors': 0,
            'errors': [],
            'start_time': sync_history.start_time,
        }

        try:
            async with CompaniesClient() as client:
                # Determine since_date priority: manual > force/full (None) > last SyncHistory
                since_date = kwargs.get('since_date')
                if since_date and isinstance(since_date, str):
                    from datetime import datetime as dt
                    try:
                        since_date = dt.strptime(since_date, '%Y-%m-%d')
                        logger.info(f"Using manual since date: {since_date}")
                    except ValueError:
                        logger.warning(f"Invalid since date format: {since_date}, ignoring")
                        since_date = None

                if force_overwrite:
                    since_date = None
                    logger.info("Force overwrite/full fetch for companies")
                elif full_sync:
                    since_date = None
                    logger.info("Full companies sync (fetch all)")
                else:
                    since_date = await self.get_last_sync_timestamp()
                    if since_date:
                        logger.info(f"Delta sync since last successful: {since_date}")
                    else:
                        logger.info("No previous companies sync found; performing initial full sync")

                # Prepare client params
                excluded = {'since_date', 'full_sync', 'force_overwrite', 'force', 'max_records', 'batch_size', 'dry_run', 'quiet'}
                client_kwargs = {k: v for k, v in kwargs.items() if k not in excluded}
                if getattr(self, 'batch_size', None):
                    try:
                        client_kwargs['per_page'] = int(self.batch_size)
                    except Exception:
                        pass

                max_records = kwargs.get('max_records') or 0
                processed_total = 0

                async for companies_batch in client.fetch_companies(since_date=since_date, **client_kwargs):
                    if not companies_batch:
                        continue

                    # Apply max_records cap across batches
                    if max_records and (processed_total + len(companies_batch)) > max_records:
                        take = max_records - processed_total
                        if take <= 0:
                            break
                        companies_batch = companies_batch[:take]

                    sync_stats['total_fetched'] += len(companies_batch)
                    logger.info(f"Processing {len(companies_batch)} companies...")

                    processed = []
                    for company in companies_batch:
                        try:
                            transformed = self.processor.transform_record(company)
                            if self.processor.validate_record(transformed):
                                processed.append(transformed)
                                sync_stats['total_processed'] += 1
                            else:
                                logger.warning(f"Company validation failed: {company.get('id', 'unknown')}")
                        except Exception as e:
                            msg = f"Error processing company {company.get('id', 'unknown')}: {e}"
                            logger.error(msg)
                            sync_stats['total_errors'] += 1
                            sync_stats['errors'].append(msg)

                    if processed and not getattr(self, 'dry_run', False):
                        from ingestion.models.callrail import CallRail_Company
                        save_stats = await self.bulk_save_records(processed, CallRail_Company, 'id')
                        sync_stats['total_created'] += save_stats.get('created', 0)
                        sync_stats['total_updated'] += save_stats.get('updated', 0)
                        sync_stats['total_errors'] += save_stats.get('errors', 0)
                        sync_stats['errors'].extend(save_stats.get('error_details', []))

                    processed_total += len(companies_batch)
                    if max_records and processed_total >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break

            sync_stats['end_time'] = timezone.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()

            # Update SyncHistory with results
            @sync_to_async
            def update_sync_history_success():
                sync_history.end_time = sync_stats['end_time']
                sync_history.status = 'success' if sync_stats['total_errors'] == 0 else 'partial'
                sync_history.records_processed = sync_stats['total_processed']
                sync_history.records_created = sync_stats['total_created']
                sync_history.records_updated = sync_stats['total_updated']
                sync_history.records_failed = sync_stats['total_errors']
                sync_history.performance_metrics = {
                    'duration_seconds': sync_stats['duration'],
                    'records_per_second': (sync_stats['total_processed'] / sync_stats['duration']) if sync_stats['duration'] > 0 else 0
                }
                sync_history.save()
                return sync_history

            await update_sync_history_success()

            logger.info(
                f"Companies sync completed: processed={sync_stats['total_processed']}, created={sync_stats['total_created']}, updated={sync_stats['total_updated']}, errors={sync_stats['total_errors']}"
            )
            return sync_stats

        except Exception as e:
            logger.error(f"Companies sync failed: {e}")
            sync_stats['end_time'] = timezone.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            sync_stats['total_errors'] += 1
            sync_stats['errors'].append(str(e))
            # Update SyncHistory with failure
            @sync_to_async
            def update_sync_history_failed():
                sync_history.end_time = sync_stats['end_time']
                sync_history.status = 'failed'
                sync_history.records_failed = sync_stats['total_errors']
                sync_history.error_message = str(e)
                sync_history.performance_metrics = {
                    'duration_seconds': sync_stats['duration']
                }
                sync_history.save()
                return sync_history

            await update_sync_history_failed()
            return sync_stats
