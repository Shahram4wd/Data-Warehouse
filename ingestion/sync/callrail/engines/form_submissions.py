"""
CallRail form submissions sync engine (enterprise pattern)
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.form_submissions import FormSubmissionsClient
from ..processors.form_submissions import FormSubmissionsProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class FormSubmissionsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail form submissions"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = FormSubmissionsClient()
        self.processor = FormSubmissionsProcessor()
        self.entity_name = "form_submissions"

    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Use SyncHistory last successful end_time for delta (callrail/form_submissions)"""
        try:
            @sync_to_async
            def get_last():
                last = (SyncHistory.objects
                        .filter(crm_source='callrail', sync_type='form_submissions', status='success', end_time__isnull=False)
                        .order_by('-end_time').first())
                return last.end_time if last else None

            return await get_last()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    async def sync_form_submissions(self, full_sync: bool = False, force_overwrite: bool = False, **kwargs) -> Dict[str, Any]:
        """Sync form submissions with default delta, batching, and SyncHistory"""
        logger.info(f"Starting form submissions sync (full_sync={full_sync}, force_overwrite={force_overwrite})")

        # Create SyncHistory
        @sync_to_async
        def create_sync_history():
            return SyncHistory.objects.create(
                crm_source='callrail',
                sync_type='form_submissions',
                start_time=timezone.now(),
                status='running',
                configuration={
                    'full_sync': full_sync,
                    'force_overwrite': force_overwrite,
                    **{k: v for k, v in kwargs.items() if k not in ['full_sync', 'force_overwrite', 'force']}
                }
            )

        sync_history = await create_sync_history()

        stats = {
            'entity': 'form_submissions',
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
            async with FormSubmissionsClient() as client:
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
                    logger.info("Force overwrite/full fetch for form submissions")
                elif full_sync:
                    since_date = None
                    logger.info("Full sync (fetch all form submissions)")
                else:
                    last = await self.get_last_sync_timestamp()
                    if last:
                        since_date = last
                        logger.info(f"Delta sync since last successful: {since_date}")
                    else:
                        logger.info("No previous sync found; performing initial full sync")

                # Client params: map batch_size->per_page, filter internals
                excluded = {'since_date', 'full_sync', 'force_overwrite', 'force', 'max_records', 'batch_size', 'dry_run', 'quiet'}
                client_kwargs = {k: v for k, v in kwargs.items() if k not in excluded}
                if getattr(self, 'batch_size', None):
                    try:
                        client_kwargs['per_page'] = int(self.batch_size)
                    except Exception:
                        pass

                max_records = kwargs.get('max_records') or 0
                processed_total = 0

                async for batch in client.fetch_form_submissions(since_date=since_date, **client_kwargs):
                    if not batch:
                        continue

                    # Defensive local filter on 'submission_time' for delta correctness
                    if since_date:
                        try:
                            filtered = []
                            from django.utils.dateparse import parse_datetime
                            for item in batch:
                                ts = item.get('submission_time')
                                if not ts:
                                    continue
                                parsed = parse_datetime(ts)
                                if not parsed:
                                    # Fallback ISO parsing
                                    from datetime import datetime as dt
                                    parsed = dt.fromisoformat(ts.replace('Z', '+00:00'))
                                if parsed and parsed >= since_date:
                                    filtered.append(item)
                            batch = filtered
                            if not batch:
                                logger.info("No form submissions >= since_date on this page; stopping early.")
                                break
                        except Exception:
                            pass

                    # Enforce max_records across batches
                    if max_records and (processed_total + len(batch)) > max_records:
                        take = max_records - processed_total
                        if take <= 0:
                            break
                        batch = batch[:take]

                    stats['total_fetched'] += len(batch)
                    logger.info(f"Processing {len(batch)} form submissions...")

                    processed = []
                    for raw in batch:
                        try:
                            transformed = self.processor.transform_record(raw)
                            if self.processor.validate_record(transformed):
                                processed.append(transformed)
                                stats['total_processed'] += 1
                            else:
                                logger.warning(f"Form submission validation failed: {raw.get('id', 'unknown')}")
                        except Exception as e:
                            msg = f"Error processing form submission {raw.get('id', 'unknown')}: {e}"
                            logger.error(msg)
                            stats['total_errors'] += 1
                            stats['errors'].append(msg)

                    if processed and not getattr(self, 'dry_run', False):
                        from ingestion.models.callrail import CallRail_FormSubmission
                        save = await self.bulk_save_records(processed, CallRail_FormSubmission, 'id')
                        stats['total_created'] += save.get('created', 0)
                        stats['total_updated'] += save.get('updated', 0)
                        stats['total_errors'] += save.get('errors', 0)
                        stats['errors'].extend(save.get('error_details', []))

                    processed_total += len(batch)
                    if max_records and processed_total >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break

            stats['end_time'] = timezone.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

            @sync_to_async
            def update_history_success():
                sync_history.end_time = stats['end_time']
                sync_history.status = 'success' if stats['total_errors'] == 0 else 'partial'
                sync_history.records_processed = stats['total_processed']
                sync_history.records_created = stats['total_created']
                sync_history.records_updated = stats['total_updated']
                sync_history.records_failed = stats['total_errors']
                sync_history.performance_metrics = {
                    'duration_seconds': stats['duration'],
                    'records_per_second': (stats['total_processed'] / stats['duration']) if stats['duration'] > 0 else 0
                }
                sync_history.save()
                return sync_history

            await update_history_success()
            logger.info(f"Form submissions sync completed: processed={stats['total_processed']}, created={stats['total_created']}, updated={stats['total_updated']}, errors={stats['total_errors']}")
            return stats

        except Exception as e:
            logger.error(f"Form submissions sync failed: {e}")
            stats['end_time'] = timezone.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['total_errors'] += 1
            stats['errors'].append(str(e))

            @sync_to_async
            def update_history_failed():
                sync_history.end_time = stats['end_time']
                sync_history.status = 'failed'
                sync_history.records_failed = stats['total_errors']
                sync_history.error_message = str(e)
                sync_history.performance_metrics = { 'duration_seconds': stats['duration'] }
                sync_history.save()
                return sync_history

            await update_history_failed()
            return stats
