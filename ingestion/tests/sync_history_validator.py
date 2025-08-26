"""
Sync History validation utilities for CRM command testing.
Provides validation patterns and analysis for sync operation results.
"""

from datetime import datetime, timedelta
from django.utils import timezone
from ingestion.models import SyncHistory
from typing import List, Dict, Optional


class SyncHistoryValidator:
    """Validates sync history records for consistency and completeness"""
    
    def __init__(self, command_name: str = None):
        self.command_name = command_name
    
    def get_recent_syncs(self, hours: int = 24) -> List[SyncHistory]:
        """Get recent sync records for analysis"""
        since = timezone.now() - timedelta(hours=hours)
        queryset = SyncHistory.objects.filter(start_time__gte=since)
        
        if self.command_name:
            queryset = queryset.filter(command_name=self.command_name)
        
        return list(queryset.order_by('-start_time'))
    
    def validate_sync_sequence(self, syncs: List[SyncHistory]) -> Dict[str, any]:
        """Validate a sequence of sync operations"""
        if not syncs:
            return {'valid': False, 'errors': ['No sync records found']}
        
        errors = []
        warnings = []
        
        # Check for proper ordering
        for i in range(len(syncs) - 1):
            if syncs[i].start_time < syncs[i + 1].start_time:
                errors.append(f"Sync order inconsistency at index {i}")
        
        # Check for overlapping syncs
        for i, sync in enumerate(syncs):
            if sync.end_time and sync.end_time < sync.start_time:
                errors.append(f"Sync {i} has end_time before start_time")
        
        # Check for reasonable execution times
        for i, sync in enumerate(syncs):
            if sync.end_time:
                duration = (sync.end_time - sync.start_time).total_seconds()
                if duration > 3600:  # More than 1 hour
                    warnings.append(f"Sync {i} took {duration/60:.1f} minutes")
                elif duration < 1:  # Less than 1 second
                    warnings.append(f"Sync {i} completed suspiciously quickly")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings,
            'total_syncs': len(syncs),
            'success_rate': len([s for s in syncs if s.status == 'SUCCESS']) / len(syncs)
        }
    
    def validate_record_counts(self, syncs: List[SyncHistory]) -> Dict[str, any]:
        """Validate record processing counts"""
        if not syncs:
            return {'valid': True, 'total_records': 0}
        
        errors = []
        total_records = 0
        
        for i, sync in enumerate(syncs):
            if sync.records_processed is None:
                errors.append(f"Sync {i} missing records_processed count")
            elif sync.records_processed < 0:
                errors.append(f"Sync {i} has negative record count: {sync.records_processed}")
            else:
                total_records += sync.records_processed
        
        # Check for unusual patterns
        if syncs:
            avg_records = total_records / len(syncs)
            for i, sync in enumerate(syncs):
                if sync.records_processed and sync.records_processed > avg_records * 10:
                    errors.append(f"Sync {i} processed unusually high record count: {sync.records_processed}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'total_records': total_records,
            'average_per_sync': total_records / len(syncs) if syncs else 0
        }
    
    def validate_status_patterns(self, syncs: List[SyncHistory]) -> Dict[str, any]:
        """Validate status patterns for anomalies"""
        if not syncs:
            return {'valid': True, 'patterns': {}}
        
        status_counts = {}
        consecutive_failures = 0
        max_consecutive_failures = 0
        
        for sync in syncs:
            status = sync.status or 'UNKNOWN'
            status_counts[status] = status_counts.get(status, 0) + 1
            
            if status == 'FAILED':
                consecutive_failures += 1
                max_consecutive_failures = max(max_consecutive_failures, consecutive_failures)
            else:
                consecutive_failures = 0
        
        # Identify concerning patterns
        warnings = []
        if max_consecutive_failures >= 3:
            warnings.append(f"Found {max_consecutive_failures} consecutive failures")
        
        failure_rate = status_counts.get('FAILED', 0) / len(syncs)
        if failure_rate > 0.5:
            warnings.append(f"High failure rate: {failure_rate:.1%}")
        
        return {
            'valid': max_consecutive_failures < 5,  # 5+ consecutive failures is invalid
            'warnings': warnings,
            'status_counts': status_counts,
            'failure_rate': failure_rate,
            'max_consecutive_failures': max_consecutive_failures
        }
    
    def validate_log_data_completeness(self, syncs: List[SyncHistory]) -> Dict[str, any]:
        """Validate that log data contains expected information"""
        if not syncs:
            return {'valid': True, 'missing_logs': 0}
        
        missing_logs = 0
        incomplete_logs = 0
        expected_fields = ['command_options', 'start_timestamp', 'records_processed']
        
        for sync in syncs:
            if not sync.log_data:
                missing_logs += 1
                continue
            
            missing_fields = []
            for field in expected_fields:
                if field not in sync.log_data:
                    missing_fields.append(field)
            
            if missing_fields:
                incomplete_logs += 1
        
        completeness_rate = (len(syncs) - missing_logs - incomplete_logs) / len(syncs)
        
        return {
            'valid': missing_logs == 0 and incomplete_logs < len(syncs) * 0.2,  # < 20% incomplete
            'missing_logs': missing_logs,
            'incomplete_logs': incomplete_logs,
            'completeness_rate': completeness_rate
        }
    
    def generate_comprehensive_report(self, hours: int = 24) -> Dict[str, any]:
        """Generate a comprehensive validation report"""
        syncs = self.get_recent_syncs(hours)
        
        sequence_validation = self.validate_sync_sequence(syncs)
        count_validation = self.validate_record_counts(syncs)
        status_validation = self.validate_status_patterns(syncs)
        log_validation = self.validate_log_data_completeness(syncs)
        
        overall_valid = all([
            sequence_validation['valid'],
            count_validation['valid'],
            status_validation['valid'],
            log_validation['valid']
        ])
        
        return {
            'command_name': self.command_name,
            'analysis_period_hours': hours,
            'overall_valid': overall_valid,
            'sequence_validation': sequence_validation,
            'count_validation': count_validation,
            'status_validation': status_validation,
            'log_validation': log_validation,
            'summary': {
                'total_syncs': len(syncs),
                'success_rate': sequence_validation.get('success_rate', 0),
                'total_records_processed': count_validation.get('total_records', 0),
                'average_records_per_sync': count_validation.get('average_per_sync', 0)
            }
        }


class SyncHistoryTestAssertions:
    """Assertion helpers for testing sync history validation"""
    
    @staticmethod
    def assert_sync_valid(validator_result: Dict[str, any], test_case):
        """Assert that sync validation passed"""
        if not validator_result['valid']:
            errors = validator_result.get('errors', [])
            test_case.fail(f"Sync validation failed: {'; '.join(errors)}")
    
    @staticmethod
    def assert_success_rate_above(validator_result: Dict[str, any], min_rate: float, test_case):
        """Assert that success rate is above threshold"""
        actual_rate = validator_result.get('success_rate', 0)
        test_case.assertGreaterEqual(
            actual_rate, min_rate,
            f"Success rate {actual_rate:.1%} is below required {min_rate:.1%}"
        )
    
    @staticmethod
    def assert_record_count_positive(validator_result: Dict[str, any], test_case):
        """Assert that total records processed is positive"""
        total_records = validator_result.get('total_records', 0)
        test_case.assertGreater(
            total_records, 0,
            "No records were processed across all syncs"
        )
    
    @staticmethod
    def assert_no_consecutive_failures(validator_result: Dict[str, any], max_allowed: int, test_case):
        """Assert that consecutive failures don't exceed threshold"""
        max_consecutive = validator_result.get('max_consecutive_failures', 0)
        test_case.assertLessEqual(
            max_consecutive, max_allowed,
            f"Too many consecutive failures: {max_consecutive} > {max_allowed}"
        )


# Example usage patterns for different CRM systems
class CRMSyncPatterns:
    """Common sync patterns for different CRM types"""
    
    @staticmethod
    def api_based_crm_pattern():
        """Expected pattern for API-based CRMs like HubSpot, SalesRabbit"""
        return {
            'expected_duration_range': (30, 300),  # 30 seconds to 5 minutes
            'expected_record_range': (0, 10000),   # 0 to 10k records per sync
            'acceptable_failure_rate': 0.1,        # 10% failure rate acceptable
            'required_log_fields': [
                'api_endpoint', 'batch_size', 'total_pages', 'rate_limit_remaining'
            ]
        }
    
    @staticmethod
    def database_crm_pattern():
        """Expected pattern for database CRMs like Genius, SalesPro"""
        return {
            'expected_duration_range': (10, 600),  # 10 seconds to 10 minutes
            'expected_record_range': (0, 50000),   # 0 to 50k records per sync
            'acceptable_failure_rate': 0.05,       # 5% failure rate acceptable
            'required_log_fields': [
                'database_host', 'query_execution_time', 'connection_pool_size'
            ]
        }
    
    @staticmethod
    def webhook_crm_pattern():
        """Expected pattern for webhook-based CRMs like CallRail"""
        return {
            'expected_duration_range': (5, 120),   # 5 seconds to 2 minutes
            'expected_record_range': (0, 5000),    # 0 to 5k records per sync
            'acceptable_failure_rate': 0.15,       # 15% failure rate acceptable (webhooks can be flaky)
            'required_log_fields': [
                'webhook_url', 'payload_size', 'response_status'
            ]
        }


def create_validator_for_command(command_name: str) -> SyncHistoryValidator:
    """Factory function to create appropriate validator for command"""
    return SyncHistoryValidator(command_name)
