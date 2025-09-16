"""
CallRail tags sync engine (enterprise pattern)
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone
from asgiref.sync import sync_to_async
from .base import CallRailBaseSyncEngine
from ..clients.tags import TagsClient
from ..processors.tags import TagsProcessor
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)


class TagsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail tags"""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.client = TagsClient()
        self.processor = TagsProcessor()
        self.entity_name = "tags"

    async def get_last_sync_timestamp(self) -> Optional[datetime]:
        """Use SyncHistory last successful end_time for delta (callrail/tags)"""
        try:
            @sync_to_async
            def get_last():
                last = (SyncHistory.objects
                        .filter(crm_source='callrail', sync_type='tags', status='success', end_time__isnull=False)
                        .order_by('-end_time').first())
                return last.end_time if last else None

            return await get_last()
        except Exception as e:
            logger.error(f"Error getting last sync timestamp: {e}")
            return None

    async def sync_tags(self, full_sync: bool = False, force_overwrite: bool = False, **kwargs) -> Dict[str, Any]:
        """Sync tags with default delta, batching, and SyncHistory"""
        logger.info(f"Starting tags sync (full_sync={full_sync}, force_overwrite={force_overwrite})")

        @sync_to_async
        def create_sync_history():
            return SyncHistory.objects.create(
                crm_source='callrail',
                sync_type='tags',
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
            'entity': 'tags',
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
            async with TagsClient() as client:
                # Determine since_date: manual > force/full (None) > last SyncHistory
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
                    logger.info("Force overwrite/full fetch for tags")
                elif full_sync:
                    since_date = None
                    logger.info("Full tags sync (fetch all)")
                else:
                    last = await self.get_last_sync_timestamp()
                    if last:
                        since_date = last
                        logger.info(f"Delta sync since last successful: {since_date}")
                    else:
                        logger.info("No previous tags sync found; performing initial full sync")

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

                async for tags_batch in client.fetch_tags(since_date=since_date, **client_kwargs):
                    if not tags_batch:
                        continue

                    # Defensive local filter when API ignores created_at
                    if since_date:
                        try:
                            filtered = []
                            from django.utils.dateparse import parse_datetime
                            for item in tags_batch:
                                ts = item.get('updated_at') or item.get('created_at')
                                if not ts:
                                    # Without a timestamp, we can't guarantee delta; skip to avoid reprocessing
                                    continue
                                parsed = parse_datetime(ts)
                                if not parsed:
                                    from datetime import datetime as dt
                                    parsed = dt.fromisoformat(ts.replace('Z', '+00:00'))
                                if parsed and parsed >= since_date:
                                    filtered.append(item)
                            tags_batch = filtered
                            if not tags_batch:
                                logger.info("No tags >= since_date on this page; stopping early.")
                                break
                        except Exception:
                            # If parsing fails, proceed with batch
                            pass

                    # No clear updated_at field for tags; rely on API filtering only
                    if max_records and (processed_total + len(tags_batch)) > max_records:
                        take = max_records - processed_total
                        if take <= 0:
                            break
                        tags_batch = tags_batch[:take]

                    stats['total_fetched'] += len(tags_batch)
                    logger.info(f"Processing {len(tags_batch)} tags...")

                    processed = []
                    for raw in tags_batch:
                        try:
                            transformed = self.processor.transform_record(raw)
                            if self.processor.validate_record(transformed):
                                processed.append(transformed)
                                stats['total_processed'] += 1
                            else:
                                logger.warning(f"Tag validation failed: {raw.get('id', 'unknown')}")
                        except Exception as e:
                            msg = f"Error processing tag {raw.get('id', 'unknown')}: {e}"
                            logger.error(msg)
                            stats['total_errors'] += 1
                            stats['errors'].append(msg)

                    if processed and not getattr(self, 'dry_run', False):
                        from ingestion.models.callrail import CallRail_Tag
                        save_stats = await self.bulk_save_records(processed, CallRail_Tag, 'id')
                        stats['total_created'] += save_stats.get('created', 0)
                        stats['total_updated'] += save_stats.get('updated', 0)
                        stats['total_errors'] += save_stats.get('errors', 0)
                        stats['errors'].extend(save_stats.get('error_details', []))

                    processed_total += len(tags_batch)
                    if max_records and processed_total >= max_records:
                        logger.info(f"Reached max_records={max_records}; stopping.")
                        break

            stats['end_time'] = timezone.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()

            @sync_to_async
            def update_success():
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

            await update_success()
            logger.info(
                f"Tags sync completed: processed={stats['total_processed']}, created={stats['total_created']}, updated={stats['total_updated']}, errors={stats['total_errors']}"
            )
            return stats

        except Exception as e:
            logger.error(f"Tags sync failed: {e}")
            stats['end_time'] = timezone.now()
            stats['duration'] = (stats['end_time'] - stats['start_time']).total_seconds()
            stats['total_errors'] += 1
            stats['errors'].append(str(e))

            @sync_to_async
            def update_failed():
                sync_history.end_time = stats['end_time']
                sync_history.status = 'failed'
                sync_history.records_failed = stats['total_errors']
                sync_history.error_message = str(e)
                sync_history.performance_metrics = { 'duration_seconds': stats['duration'] }
                sync_history.save()
                return sync_history

            await update_failed()
            return stats
