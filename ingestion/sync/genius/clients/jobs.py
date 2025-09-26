"""
Job client for Genius CRM database access
"""
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime
from .base import GeniusBaseClient

logger = logging.getLogger(__name__)


class GeniusJobClient(GeniusBaseClient):
    """Client for accessing Genius CRM job data"""
    
    def __init__(self):
        super().__init__()
        self.table_name = 'job'
    
    def get_jobs(self, since_date: Optional[datetime] = None, limit: int = 0) -> List[tuple]:
        """Fetch jobs from Genius database"""
        
        # Base query with comprehensive fields from the job table
        query = """
        SELECT
            j.id,
            j.client_cid,
            j.prospect_id,
            j.division_id,
            j.user_id,
            j.production_user_id,
            j.project_coordinator_user_id,
            j.production_month,
            j.subcontractor_id,
            j.subcontractor_status_id,
            j.subcontractor_confirmed,
            j.status,
            j.is_in_progress,
            j.ready_status,
            j.prep_status_id,
            j.prep_status_set_date,
            j.prep_status_is_reset,
            j.prep_status_notes,
            j.prep_issue_id,
            j.service_id,
            j.is_lead_pb,
            j.contract_number,
            j.contract_date,
            j.contract_amount,
            j.contract_amount_difference,
            j.contract_hours,
            j.contract_file_id,
            j.job_value,
            j.deposit_amount,
            j.deposit_type_id,
            j.is_financing,
            j.sales_tax_rate,
            j.is_sales_tax_exempt,
            j.commission_payout,
            j.accrued_commission_payout,
            j.sold_user_id,
            j.sold_date,
            j.start_request_date,
            j.deadline_date,
            j.ready_date,
            j.jsa_sent,
            j.start_date,
            j.end_date,
            j.add_user_id,
            j.add_date,
            j.cancel_date,
            j.cancel_user_id,
            j.cancel_reason_id,
            j.is_refund,
            j.refund_date,
            j.refund_user_id,
            j.finish_date,
            j.is_earned_not_paid,
            j.materials_arrival_date,
            j.measure_date,
            j.measure_time,
            j.measure_user_id,
            j.time_format,
            j.materials_estimated_arrival_date,
            j.materials_ordered,
            j.install_date,
            j.install_time,
            j.install_time_format,
            j.price_level,
            j.price_level_goal,
            j.price_level_commission,
            j.price_level_commission_reduction,
            j.is_reviewed,
            j.reviewed_by,
            j.pp_id_updated,
            j.hoa,
            j.hoa_approved,
            j.materials_ordered_old,
            j.start_month_old,
            j.cogs_report_month,
            j.is_cogs_report_month_updated,
            j.forecast_month,
            j.coc_sent_on,
            j.coc_sent_by,
            j.company_cam_link,
            j.pm_finished_on,
            j.estimate_job_duration,
            j.payment_not_finalized_reason,
            j.reasons_other,
            j.payment_type,
            j.payment_amount,
            j.is_payment_finalized,
            j.is_company_cam,
            j.is_five_star_review,
            j.projected_end_date,
            j.is_company_cam_images_correct,
            j.post_pm_closeout_date,
            j.pre_pm_closeout_date,
            j.actual_install_date,
            j.in_progress_substatus_id,
            j.is_loan_document_uptodate,
            j.is_labor_adjustment_correct,
            j.is_change_order_correct,
            j.is_coc_pdf_attached,
            j.updated_at
        FROM job j
        """        # Add WHERE clause for incremental sync
        where_clause = self.build_where_clause(since_date, self.table_name)
        if where_clause:
            query += f" {where_clause}"
        
        # Add ordering and limit
        query += " ORDER BY j.id"
        if limit > 0:
            query += f" LIMIT {limit}"
        
        logger.info(f"Executing query: {query}")
        return self.execute_query(query)
    
    def get_chunked_jobs(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> List[tuple]:
        """Fetch jobs data in chunks for large datasets"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        query = self.get_chunked_query(offset, chunk_size, since_date)
        return self.execute_query(query)

    def get_chunked_query(self, offset: int, chunk_size: int, since_date: Optional[datetime] = None) -> str:
        """Get the chunked query for logging purposes"""
        where_clause = ""
        if since_date:
            where_clause = f"updated_at >= '{since_date.strftime('%Y-%m-%d %H:%M:%S')}'"
        
        # Use same comprehensive field list as main query
        query = f"""
        SELECT
            j.id,
            j.client_cid,
            j.prospect_id,
            j.division_id,
            j.user_id,
            j.production_user_id,
            j.project_coordinator_user_id,
            j.production_month,
            j.subcontractor_id,
            j.subcontractor_status_id,
            j.subcontractor_confirmed,
            j.status,
            j.is_in_progress,
            j.ready_status,
            j.prep_status_id,
            j.prep_status_set_date,
            j.prep_status_is_reset,
            j.prep_status_notes,
            j.prep_issue_id,
            j.service_id,
            j.is_lead_pb,
            j.contract_number,
            j.contract_date,
            j.contract_amount,
            j.contract_amount_difference,
            j.contract_hours,
            j.contract_file_id,
            j.job_value,
            j.deposit_amount,
            j.deposit_type_id,
            j.is_financing,
            j.sales_tax_rate,
            j.is_sales_tax_exempt,
            j.commission_payout,
            j.accrued_commission_payout,
            j.sold_user_id,
            j.sold_date,
            j.start_request_date,
            j.deadline_date,
            j.ready_date,
            j.jsa_sent,
            j.start_date,
            j.end_date,
            j.add_user_id,
            j.add_date,
            j.cancel_date,
            j.cancel_user_id,
            j.cancel_reason_id,
            j.is_refund,
            j.refund_date,
            j.refund_user_id,
            j.finish_date,
            j.is_earned_not_paid,
            j.materials_arrival_date,
            j.measure_date,
            j.measure_time,
            j.measure_user_id,
            j.time_format,
            j.materials_estimated_arrival_date,
            j.materials_ordered,
            j.install_date,
            j.install_time,
            j.install_time_format,
            j.price_level,
            j.price_level_goal,
            j.price_level_commission,
            j.price_level_commission_reduction,
            j.is_reviewed,
            j.reviewed_by,
            j.pp_id_updated,
            j.hoa,
            j.hoa_approved,
            j.materials_ordered_old,
            j.start_month_old,
            j.cogs_report_month,
            j.is_cogs_report_month_updated,
            j.forecast_month,
            j.coc_sent_on,
            j.coc_sent_by,
            j.company_cam_link,
            j.pm_finished_on,
            j.estimate_job_duration,
            j.payment_not_finalized_reason,
            j.reasons_other,
            j.payment_type,
            j.payment_amount,
            j.is_payment_finalized,
            j.is_company_cam,
            j.is_five_star_review,
            j.projected_end_date,
            j.is_company_cam_images_correct,
            j.post_pm_closeout_date,
            j.pre_pm_closeout_date,
            j.actual_install_date,
            j.in_progress_substatus_id,
            j.is_loan_document_uptodate,
            j.is_labor_adjustment_correct,
            j.is_change_order_correct,
            j.is_coc_pdf_attached,
            j.updated_at
        FROM {self.table_name} j
        """
        if where_clause:
            query += f" WHERE {where_clause}"
        query += f" ORDER BY j.id LIMIT {chunk_size} OFFSET {offset}"
        return query
    
    def get_field_mapping(self) -> Dict[str, int]:
        """Return field mapping for processor (field_name -> column_index)"""
        return {
            'id': 0,
            'client_cid': 1,
            'prospect_id': 2,
            'division_id': 3,
            'user_id': 4,
            'production_user_id': 5,
            'project_coordinator_user_id': 6,
            'production_month': 7,
            'subcontractor_id': 8,
            'subcontractor_status_id': 9,
            'subcontractor_confirmed': 10,
            'status': 11,
            'is_in_progress': 12,
            'ready_status': 13,
            'prep_status_id': 14,
            'prep_status_set_date': 15,
            'prep_status_is_reset': 16,
            'prep_status_notes': 17,
            'prep_issue_id': 18,
            'service_id': 19,
            'is_lead_pb': 20,
            'contract_number': 21,
            'contract_date': 22,
            'contract_amount': 23,
            'contract_amount_difference': 24,
            'contract_hours': 25,
            'contract_file_id': 26,
            'job_value': 27,
            'deposit_amount': 28,
            'deposit_type_id': 29,
            'is_financing': 30,
            'sales_tax_rate': 31,
            'is_sales_tax_exempt': 32,
            'commission_payout': 33,
            'accrued_commission_payout': 34,
            'sold_user_id': 35,
            'sold_date': 36,  # This is the field you mentioned!
            'start_request_date': 37,
            'deadline_date': 38,
            'ready_date': 39,
            'jsa_sent': 40,
            'start_date': 41,
            'end_date': 42,
            'add_user_id': 43,
            'add_date': 44,
            'cancel_date': 45,
            'cancel_user_id': 46,
            'cancel_reason_id': 47,
            'is_refund': 48,
            'refund_date': 49,
            'refund_user_id': 50,
            'finish_date': 51,
            'is_earned_not_paid': 52,
            'materials_arrival_date': 53,
            'measure_date': 54,
            'measure_time': 55,
            'measure_user_id': 56,
            'time_format': 57,
            'materials_estimated_arrival_date': 58,
            'materials_ordered': 59,
            'install_date': 60,
            'install_time': 61,
            'install_time_format': 62,
            'price_level': 63,
            'price_level_goal': 64,
            'price_level_commission': 65,
            'price_level_commission_reduction': 66,
            'is_reviewed': 67,
            'reviewed_by': 68,
            'pp_id_updated': 69,
            'hoa': 70,
            'hoa_approved': 71,
            'materials_ordered_old': 72,
            'start_month_old': 73,
            'cogs_report_month': 74,
            'is_cogs_report_month_updated': 75,
            'forecast_month': 76,
            'coc_sent_on': 77,
            'coc_sent_by': 78,
            'company_cam_link': 79,
            'pm_finished_on': 80,
            'estimate_job_duration': 81,
            'payment_not_finalized_reason': 82,
            'reasons_other': 83,
            'payment_type': 84,
            'payment_amount': 85,
            'is_payment_finalized': 86,
            'is_company_cam': 87,
            'is_five_star_review': 88,
            'projected_end_date': 89,
            'is_company_cam_images_correct': 90,
            'post_pm_closeout_date': 91,
            'pre_pm_closeout_date': 92,
            'actual_install_date': 93,
            'in_progress_substatus_id': 94,
            'is_loan_document_uptodate': 95,
            'is_labor_adjustment_correct': 96,
            'is_change_order_correct': 97,
            'is_coc_pdf_attached': 98,
            'updated_at': 99
        }
    
    def get_chunked_items(self, chunk_size: int = 10000, since: Optional[datetime] = None):
        """
        Generator that yields chunks of jobs using cursor-based pagination for better performance
        
        Args:
            chunk_size: Number of records per chunk
            since: Optional datetime to filter records updated after this time
            
        Yields:
            Lists of job tuples in chunks
        """
        last_id = 0
        total_fetched = 0
        
        while True:
            # Build the cursor-based query
            query = """
            SELECT
                j.id,
                j.client_cid,
                j.prospect_id,
                j.division_id,
                j.user_id,
                j.production_user_id,
                j.project_coordinator_user_id,
                j.production_month,
                j.subcontractor_id,
                j.subcontractor_status_id,
                j.subcontractor_confirmed,
                j.status,
                j.is_in_progress,
                j.ready_status,
                j.prep_status_id,
                j.prep_status_set_date,
                j.prep_status_is_reset,
                j.prep_status_notes,
                j.prep_issue_id,
                j.service_id,
                j.is_lead_pb,
                j.contract_number,
                j.contract_date,
                j.contract_amount,
                j.contract_amount_difference,
                j.contract_hours,
                j.contract_file_id,
                j.job_value,
                j.deposit_amount,
                j.deposit_type_id,
                j.is_financing,
                j.sales_tax_rate,
                j.is_sales_tax_exempt,
                j.commission_payout,
                j.accrued_commission_payout,
                j.sold_user_id,
                j.sold_date,
                j.start_request_date,
                j.deadline_date,
                j.ready_date,
                j.jsa_sent,
                j.start_date,
                j.end_date,
                j.add_user_id,
                j.add_date,
                j.cancel_date,
                j.cancel_user_id,
                j.cancel_reason_id,
                j.is_refund,
                j.refund_date,
                j.refund_user_id,
                j.finish_date,
                j.is_earned_not_paid,
                j.materials_arrival_date,
                j.measure_date,
                j.measure_time,
                j.measure_user_id,
                j.time_format,
                j.materials_estimated_arrival_date,
                j.materials_ordered,
                j.install_date,
                j.install_time,
                j.install_time_format,
                j.price_level,
                j.price_level_goal,
                j.price_level_commission,
                j.price_level_commission_reduction,
                j.is_reviewed,
                j.reviewed_by,
                j.pp_id_updated,
                j.hoa,
                j.hoa_approved,
                j.materials_ordered_old,
                j.start_month_old,
                j.cogs_report_month,
                j.is_cogs_report_month_updated,
                j.forecast_month,
                j.coc_sent_on,
                j.coc_sent_by,
                j.company_cam_link,
                j.pm_finished_on,
                j.estimate_job_duration,
                j.payment_not_finalized_reason,
                j.reasons_other,
                j.payment_type,
                j.payment_amount,
                j.is_payment_finalized,
                j.is_company_cam,
                j.is_five_star_review,
                j.projected_end_date,
                j.is_company_cam_images_correct,
                j.post_pm_closeout_date,
                j.pre_pm_closeout_date,
                j.actual_install_date,
                j.in_progress_substatus_id,
                j.is_loan_document_uptodate,
                j.is_labor_adjustment_correct,
                j.is_change_order_correct,
                j.is_coc_pdf_attached,
                j.updated_at
            FROM job j
            WHERE j.id > %s
            """
            
            params = [last_id]
            
            # Add date filter if provided
            if since:
                query += " AND j.updated_at >= %s"
                params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
            
            query += " ORDER BY j.id LIMIT %s"
            params.append(chunk_size)
            
            logger.debug(f"Cursor-based query: {query} with params: {params}")
            
            # Execute query
            chunk = self.execute_query(query, tuple(params))
            
            if not chunk:
                logger.debug("No more data found, ending pagination")
                break
            
            # Update cursor for next iteration
            last_id = chunk[-1][0]  # First field is ID
            total_fetched += len(chunk)
            
            logger.debug(f"Fetched chunk of {len(chunk)} items (total: {total_fetched})")
            
            yield chunk
    
    def get_total_count(self, since: Optional[datetime] = None) -> int:
        """
        Get total count of jobs matching the criteria
        
        Args:
            since: Optional datetime to filter records updated after this time
            
        Returns:
            Total count of matching records
        """
        query = "SELECT COUNT(*) FROM job j"
        params = []
        
        if since:
            query += " WHERE j.updated_at >= %s"
            params.append(since.strftime('%Y-%m-%d %H:%M:%S'))
        
        result = self.execute_query(query, tuple(params))
        return result[0][0] if result else 0
