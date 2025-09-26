"""
Job processor for Genius CRM data transformation
"""
import logging
from typing import Dict, Any, List

from .base import GeniusBaseProcessor
from ..validators import GeniusFieldValidator, GeniusRecordValidator

logger = logging.getLogger(__name__)


class GeniusJobProcessor(GeniusBaseProcessor):
    """Processor for Genius job data transformation and validation"""
    
    def __init__(self, model_class):
        super().__init__(model_class)
    
    def validate_record(self, record_data: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and clean job record data"""
        
        # Use the field validator from validators.py
        validated = GeniusFieldValidator.validate_job_record(record_data)
        
        # Ensure we have required fields - check for None, not just falsy values
        if validated.get('id') is None:
            raise ValueError("Job must have an id")
        
        # Also reject ID = 0 as it's typically invalid in database contexts
        if validated.get('id') == 0:
            raise ValueError(f"Job has invalid ID: {validated.get('id')}")
        
        # Validate business rules
        relationship_errors = GeniusRecordValidator.validate_required_relationships('job', validated)
        business_errors = GeniusRecordValidator.validate_business_rules('job', validated)
        
        all_errors = relationship_errors + business_errors
        if all_errors:
            raise ValueError(f"Job validation errors: {', '.join(all_errors)}")
        
        return validated
    
    def transform_record(self, raw_data: tuple, field_mapping: List[str]) -> Dict[str, Any]:
        """Transform raw job data to dictionary"""
        
        # Use base class transformation
        record = super().transform_record(raw_data, field_mapping)
        
        # Job-specific transformations
        
        # Handle NULL foreign keys
        for fk_field in ['prospect_id', 'division_id', 'job_status_id']:
            if record.get(fk_field) == 0:
                record[fk_field] = None
        
        # Clean job_number
        if record.get('job_number'):
            record['job_number'] = str(record['job_number']).strip()
        
        return record

    def process_batch(self, records: List[Dict[str, Any]], force_overwrite: bool = False, dry_run: bool = False) -> Dict[str, Any]:
        """
        Process a batch of jobs records using bulk operations
        
        Args:
            records: List of record dictionaries
            force_overwrite: Whether to force overwrite existing records
            dry_run: Whether to perform a dry run without database changes
            
        Returns:
            Dictionary containing processing statistics
        """
        stats = {'total_processed': 0, 'created': 0, 'updated': 0, 'errors': 0}
        
        if not records:
            return stats
        
        # Validate all records first
        validated_records = []
        for record in records:
            try:
                validated_record = self.validate_record(record)
                validated_records.append(validated_record)
                stats['total_processed'] += 1
            except Exception as e:
                logger.error(f"Validation failed for record {record}: {e}")
                stats['errors'] += 1
                continue
        
        if not validated_records:
            return stats
        
        if dry_run:
            logger.info(f"DRY RUN: Would process {len(validated_records)} jobs")
            stats['created'] = len(validated_records)
            return stats
        
        # Perform bulk operations
        logger.info(f"Bulk processing {len(validated_records)} jobs (force_overwrite={force_overwrite})")
        
        try:
            # Use Django's bulk_create with update_conflicts for PostgreSQL
            from django.db import transaction
            
            with transaction.atomic():
                model_instances = [self.model_class(**record) for record in validated_records]
                
                if force_overwrite:
                    # Delete existing records first, then create new ones
                    existing_ids = [record['id'] for record in validated_records]
                    deleted_count = self.model_class.objects.filter(id__in=existing_ids).delete()[0]
                    logger.info(f"Deleted {deleted_count} existing records")
                    
                    # Create all records as new
                    created_objects = self.model_class.objects.bulk_create(model_instances)
                    stats['created'] = len(created_objects)
                    
                else:
                    # Use bulk_create with update_conflicts for upsert behavior
                    update_fields = [
                        # Basic job info
                        'client_cid', 'prospect_id', 'division_id', 'user_id',
                        'production_user_id', 'project_coordinator_user_id', 'production_month',
                        'subcontractor_id', 'subcontractor_status_id', 'subcontractor_confirmed',
                        'status', 'is_in_progress', 'ready_status', 'service_id',
                        # Prep status info
                        'prep_status_id', 'prep_status_set_date', 'prep_status_is_reset',
                        'prep_status_notes', 'prep_issue_id', 'is_lead_pb',
                        # Contract info
                        'contract_number', 'contract_date', 'contract_amount',
                        'contract_amount_difference', 'contract_hours', 'contract_file_id',
                        # Financial info
                        'job_value', 'deposit_amount', 'deposit_type_id', 'is_financing',
                        'sales_tax_rate', 'is_sales_tax_exempt', 'commission_payout',
                        'accrued_commission_payout',
                        # Sales info
                        'sold_user_id', 'sold_date',
                        # Scheduling info
                        'start_request_date', 'deadline_date', 'ready_date', 'jsa_sent',
                        'start_date', 'end_date',
                        # Cancellation info  
                        'cancel_date', 'cancel_user_id', 'cancel_reason_id',
                        'is_refund', 'refund_date', 'refund_user_id',
                        # Completion info
                        'finish_date', 'is_earned_not_paid',
                        # Materials and scheduling
                        'materials_arrival_date', 'measure_date', 'measure_time',
                        'measure_user_id', 'time_format', 'materials_estimated_arrival_date',
                        'materials_ordered', 'install_date', 'install_time', 'install_time_format',
                        # Pricing and commission
                        'price_level', 'price_level_goal', 'price_level_commission',
                        'price_level_commission_reduction', 'is_reviewed', 'reviewed_by',
                        # Additional fields
                        'pp_id_updated', 'hoa', 'hoa_approved', 'materials_ordered_old',
                        'start_month_old', 'cogs_report_month', 'is_cogs_report_month_updated',
                        'forecast_month', 'coc_sent_on', 'coc_sent_by', 'company_cam_link',
                        'pm_finished_on', 'estimate_job_duration', 'payment_not_finalized_reason',
                        'reasons_other', 'payment_type', 'payment_amount', 'is_payment_finalized',
                        'is_company_cam', 'is_five_star_review', 'projected_end_date',
                        'is_company_cam_images_correct', 'post_pm_closeout_date',
                        'pre_pm_closeout_date', 'actual_install_date', 'in_progress_substatus_id',
                        'is_loan_document_uptodate', 'is_labor_adjustment_correct',
                        'is_change_order_correct', 'is_coc_pdf_attached',
                        'updated_at'
                    ]
                    
                    # Get existing IDs to calculate created vs updated
                    existing_ids = set(
                        self.model_class.objects.filter(
                            id__in=[record['id'] for record in validated_records]
                        ).values_list('id', flat=True)
                    )
                    
                    created_objects = self.model_class.objects.bulk_create(
                        model_instances,
                        update_conflicts=True,
                        update_fields=update_fields,
                        unique_fields=['id']
                    )
                    
                    # Calculate created vs updated counts
                    total_processed = len(model_instances)
                    existing_count = len([r for r in validated_records if r['id'] in existing_ids])
                    stats['created'] = total_processed - existing_count
                    stats['updated'] = existing_count
            
            logger.info(f"Bulk operation completed - Created: {stats['created']}, Updated: {stats['updated']}")
            
        except Exception as e:
            logger.error(f"Bulk operation failed: {e}")
            stats['errors'] += len(validated_records)
            stats['created'] = 0
            stats['updated'] = 0
        
        return stats
