"""
CallRail form submissions sync engine
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from .base import CallRailBaseSyncEngine
from ..clients.form_submissions import FormSubmissionsClient
from ..processors.form_submissions import FormSubmissionsProcessor

logger = logging.getLogger(__name__)


class FormSubmissionsSyncEngine(CallRailBaseSyncEngine):
    """Sync engine for CallRail form submissions"""
    
    def __init__(self, account_id: str, **kwargs):
        super().__init__(account_id=account_id, **kwargs)
        self.client = FormSubmissionsClient()
        self.processor = FormSubmissionsProcessor()
        self.entity_name = "form_submissions"
    
    def get_last_sync_timestamp(self, account_id: str) -> Optional[datetime]:
        """Get the last sync timestamp for form submissions"""
        from ingestion.models.callrail import CallRail_FormSubmission
        latest_submission = (CallRail_FormSubmission.objects
                           .filter(company_id=account_id)
                           .order_by('-submission_time')
                           .first())
        return latest_submission.submission_time if latest_submission else None
    
    async def sync_form_submissions(self, **kwargs) -> Dict[str, Any]:
        """Sync form submissions from CallRail API"""
        logger.info(f"Starting form submissions sync for account {self.account_id}")
        
        sync_stats = {
            'total_fetched': 0,
            'total_processed': 0,
            'total_created': 0,
            'total_updated': 0,
            'errors': []
        }
        
        try:
            # Get last sync timestamp for delta sync
            since_date = kwargs.get('since_date')
            if not since_date and not kwargs.get('force', False):
                since_date = self.get_last_sync_timestamp(self.account_id)
                logger.info(f"Delta sync since: {since_date}")
            
            # Fetch form submissions data
            async for submissions_batch in self.client.fetch_form_submissions(
                account_id=self.account_id,
                since_date=since_date,
                **kwargs
            ):
                if not submissions_batch:
                    continue
                    
                sync_stats['total_fetched'] += len(submissions_batch)
                logger.info(f"Processing {len(submissions_batch)} form submissions...")
                
                # Process form submissions batch
                processed_submissions = []
                for submission in submissions_batch:
                    try:
                        # Transform submission data
                        transformed = self.processor.transform_record(submission)
                        
                        # Validate transformed data
                        if self.processor.validate_record(transformed):
                            processed_submissions.append(transformed)
                            sync_stats['total_processed'] += 1
                        else:
                            logger.warning(f"Form submission validation failed: {submission.get('id', 'unknown')}")
                            
                    except Exception as e:
                        error_msg = f"Error processing form submission {submission.get('id', 'unknown')}: {e}"
                        logger.error(error_msg)
                        sync_stats['errors'].append(error_msg)
                        continue
                
                # Save processed form submissions
                if processed_submissions:
                    from ingestion.models.callrail import CallRail_FormSubmission
                    save_stats = await self.bulk_save_records(
                        processed_submissions,
                        CallRail_FormSubmission,
                        'id'
                    )
                    sync_stats['total_created'] += save_stats['created']
                    sync_stats['total_updated'] += save_stats['updated']
            
            logger.info(f"Form submissions sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            error_msg = f"Form submissions sync failed: {e}"
            logger.error(error_msg)
            sync_stats['errors'].append(error_msg)
            return sync_stats
