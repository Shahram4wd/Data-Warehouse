"""
Parallel testing framework for HubSpot sync commands
Runs both old and new commands and compares results
"""
import asyncio
import logging
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, asdict
from django.core.management import call_command
from django.utils import timezone
from django.db import connection
from io import StringIO

from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

@dataclass
class SyncTestResult:
    """Result of a sync command test"""
    command: str
    success: bool
    duration: float
    records_processed: int
    records_created: int
    records_updated: int
    records_failed: int
    error_message: Optional[str] = None
    output: Optional[str] = None
    memory_usage: Optional[float] = None

@dataclass
class ComparisonResult:
    """Result of comparing old vs new sync commands"""
    entity_type: str
    old_result: SyncTestResult
    new_result: SyncTestResult
    data_consistency: Dict[str, Any]
    performance_comparison: Dict[str, Any]
    recommendations: List[str]

class ParallelSyncTester:
    """Framework for testing old vs new sync commands in parallel"""
    
    def __init__(self, dry_run: bool = True, debug: bool = False):
        self.dry_run = dry_run
        self.debug = debug
        self.results = []
        
    def run_command_test(self, command: str, *args, **kwargs) -> SyncTestResult:
        """Run a single command and capture results"""
        start_time = time.time()
        stdout = StringIO()
        stderr = StringIO()
        
        try:
            # Capture memory usage before
            memory_before = self._get_memory_usage()
            
            # Run the command
            call_command(command, *args, stdout=stdout, stderr=stderr, **kwargs)
            
            # Capture memory usage after
            memory_after = self._get_memory_usage()
            memory_usage = memory_after - memory_before
            
            duration = time.time() - start_time
            
            # Get sync history for metrics
            sync_history = self._get_latest_sync_history(command)
            
            return SyncTestResult(
                command=command,
                success=True,
                duration=duration,
                records_processed=sync_history.records_processed if sync_history else 0,
                records_created=sync_history.records_created if sync_history else 0,
                records_updated=sync_history.records_updated if sync_history else 0,
                records_failed=sync_history.records_failed if sync_history else 0,
                output=stdout.getvalue(),
                memory_usage=memory_usage
            )
            
        except Exception as e:
            duration = time.time() - start_time
            return SyncTestResult(
                command=command,
                success=False,
                duration=duration,
                records_processed=0,
                records_created=0,
                records_updated=0,
                records_failed=0,
                error_message=str(e),
                output=stdout.getvalue()
            )
    
    def compare_contact_syncs(self, limit: int = 100) -> ComparisonResult:
        """Compare old vs new contact sync commands"""
        logger.info("Starting contact sync comparison...")
        
        # Get baseline record count
        baseline_count = Hubspot_Contact.objects.count()
        
        # Run old command
        old_result = self.run_command_test(
            'sync_hubspot_contacts',
            dry_run=self.dry_run,
            debug=self.debug,
            pages=1  # Limit to prevent long runs
        )
        
        # Run new command
        new_result = self.run_command_test(
            'sync_hubspot_contacts_new',
            dry_run=self.dry_run,
            debug=self.debug,
            batch_size=limit
        )
        
        # Compare data consistency
        data_consistency = self._compare_contact_data()
        
        # Compare performance
        performance_comparison = self._compare_performance(old_result, new_result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(old_result, new_result, data_consistency)
        
        return ComparisonResult(
            entity_type='contacts',
            old_result=old_result,
            new_result=new_result,
            data_consistency=data_consistency,
            performance_comparison=performance_comparison,
            recommendations=recommendations
        )
    
    def compare_appointment_syncs(self, limit: int = 100) -> ComparisonResult:
        """Compare old vs new appointment sync commands"""
        logger.info("Starting appointment sync comparison...")
        
        # Run old command
        old_result = self.run_command_test(
            'sync_hubspot_appointments',
            dry_run=self.dry_run,
            debug=self.debug,
            pages=1
        )
        
        # Run new command
        new_result = self.run_command_test(
            'sync_hubspot_appointments_new',
            dry_run=self.dry_run,
            debug=self.debug,
            batch_size=limit
        )
        
        # Compare data consistency
        data_consistency = self._compare_appointment_data()
        
        # Compare performance
        performance_comparison = self._compare_performance(old_result, new_result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(old_result, new_result, data_consistency)
        
        return ComparisonResult(
            entity_type='appointments',
            old_result=old_result,
            new_result=new_result,
            data_consistency=data_consistency,
            performance_comparison=performance_comparison,
            recommendations=recommendations
        )
    
    def compare_division_syncs(self, limit: int = 50) -> ComparisonResult:
        """Compare old vs new division sync commands"""
        logger.info("Starting division sync comparison...")
        
        # Run old command
        old_result = self.run_command_test(
            'sync_hubspot_divisions',
            dry_run=self.dry_run,
            debug=self.debug
        )
        
        # Run new command
        new_result = self.run_command_test(
            'sync_hubspot_divisions_new',
            dry_run=self.dry_run,
            debug=self.debug,
            batch_size=limit
        )
        
        # Compare data consistency
        data_consistency = self._compare_division_data()
        
        # Compare performance
        performance_comparison = self._compare_performance(old_result, new_result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(old_result, new_result, data_consistency)
        
        return ComparisonResult(
            entity_type='divisions',
            old_result=old_result,
            new_result=new_result,
            data_consistency=data_consistency,
            performance_comparison=performance_comparison,
            recommendations=recommendations
        )
    
    def compare_deal_syncs(self, limit: int = 100) -> ComparisonResult:
        """Compare old vs new deal sync commands"""
        logger.info("Starting deal sync comparison...")
        
        # Run old command
        old_result = self.run_command_test(
            'sync_hubspot_deals',
            dry_run=self.dry_run,
            debug=self.debug,
            pages=1
        )
        
        # Run new command
        new_result = self.run_command_test(
            'sync_hubspot_deals_new',
            dry_run=self.dry_run,
            debug=self.debug,
            batch_size=limit
        )
        
        # Compare data consistency
        data_consistency = self._compare_deal_data()
        
        # Compare performance
        performance_comparison = self._compare_performance(old_result, new_result)
        
        # Generate recommendations
        recommendations = self._generate_recommendations(old_result, new_result, data_consistency)
        
        return ComparisonResult(
            entity_type='deals',
            old_result=old_result,
            new_result=new_result,
            data_consistency=data_consistency,
            performance_comparison=performance_comparison,
            recommendations=recommendations
        )
    
    def run_comprehensive_comparison(self) -> List[ComparisonResult]:
        """Run comprehensive comparison of all sync commands"""
        logger.info("Starting comprehensive sync comparison...")
        
        comparisons = []
        
        # Test each entity type
        entity_tests = [
            ('contacts', self.compare_contact_syncs),
            ('appointments', self.compare_appointment_syncs),
            ('divisions', self.compare_division_syncs),
            ('deals', self.compare_deal_syncs)
        ]
        
        for entity_type, test_func in entity_tests:
            try:
                logger.info(f"Testing {entity_type} sync...")
                result = test_func()
                comparisons.append(result)
                logger.info(f"Completed {entity_type} sync test")
            except Exception as e:
                logger.error(f"Error testing {entity_type} sync: {e}")
                # Create error result
                error_result = ComparisonResult(
                    entity_type=entity_type,
                    old_result=SyncTestResult(
                        command=f'sync_hubspot_{entity_type}',
                        success=False,
                        duration=0,
                        records_processed=0,
                        records_created=0,
                        records_updated=0,
                        records_failed=0,
                        error_message=str(e)
                    ),
                    new_result=SyncTestResult(
                        command=f'sync_hubspot_{entity_type}_new',
                        success=False,
                        duration=0,
                        records_processed=0,
                        records_created=0,
                        records_updated=0,
                        records_failed=0,
                        error_message=str(e)
                    ),
                    data_consistency={},
                    performance_comparison={},
                    recommendations=[f"Fix error in {entity_type} sync: {e}"]
                )
                comparisons.append(error_result)
        
        return comparisons
    
    def _get_memory_usage(self) -> float:
        """Get current memory usage in MB"""
        try:
            import psutil
            import os
            process = psutil.Process(os.getpid())
            return process.memory_info().rss / 1024 / 1024  # MB
        except ImportError:
            return 0.0
    
    def _get_latest_sync_history(self, command: str) -> Optional[SyncHistory]:
        """Get the latest sync history record for a command"""
        try:
            # Map command names to sync types
            sync_type_map = {
                'sync_hubspot_contacts': 'contacts',
                'sync_hubspot_contacts_new': 'contacts',
                'sync_hubspot_appointments': 'appointments',
                'sync_hubspot_appointments_new': 'appointments',
                'sync_hubspot_divisions': 'divisions',
                'sync_hubspot_divisions_new': 'divisions',
                'sync_hubspot_deals': 'deals',
                'sync_hubspot_deals_new': 'deals'
            }
            
            sync_type = sync_type_map.get(command)
            if not sync_type:
                return None
            
            return SyncHistory.objects.filter(
                crm_source='hubspot',
                sync_type=sync_type
            ).order_by('-start_time').first()
        except Exception:
            return None
    
    def _compare_contact_data(self) -> Dict[str, Any]:
        """Compare contact data consistency"""
        try:
            total_contacts = Hubspot_Contact.objects.count()
            recent_contacts = Hubspot_Contact.objects.filter(
                lastmodifieddate__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            return {
                'total_records': total_contacts,
                'recent_records': recent_contacts,
                'data_quality_score': self._calculate_data_quality_score(Hubspot_Contact),
                'duplicate_check': self._check_for_duplicates(Hubspot_Contact, 'id')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _compare_appointment_data(self) -> Dict[str, Any]:
        """Compare appointment data consistency"""
        try:
            total_appointments = Hubspot_Appointment.objects.count()
            recent_appointments = Hubspot_Appointment.objects.filter(
                hs_lastmodifieddate__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            return {
                'total_records': total_appointments,
                'recent_records': recent_appointments,
                'data_quality_score': self._calculate_data_quality_score(Hubspot_Appointment),
                'duplicate_check': self._check_for_duplicates(Hubspot_Appointment, 'id')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _compare_division_data(self) -> Dict[str, Any]:
        """Compare division data consistency"""
        try:
            total_divisions = Hubspot_Division.objects.count()
            
            return {
                'total_records': total_divisions,
                'data_quality_score': self._calculate_data_quality_score(Hubspot_Division),
                'duplicate_check': self._check_for_duplicates(Hubspot_Division, 'id')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _compare_deal_data(self) -> Dict[str, Any]:
        """Compare deal data consistency"""
        try:
            total_deals = Hubspot_Deal.objects.count()
            recent_deals = Hubspot_Deal.objects.filter(
                createdate__gte=timezone.now() - timedelta(days=1)
            ).count()
            
            return {
                'total_records': total_deals,
                'recent_records': recent_deals,
                'data_quality_score': self._calculate_data_quality_score(Hubspot_Deal),
                'duplicate_check': self._check_for_duplicates(Hubspot_Deal, 'id')
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _calculate_data_quality_score(self, model_class) -> float:
        """Calculate a data quality score for a model"""
        try:
            total_records = model_class.objects.count()
            if total_records == 0:
                return 0.0
            
            # Count records with null IDs (shouldn't happen but check anyway)
            null_ids = model_class.objects.filter(id__isnull=True).count()
            
            # Calculate score (simple implementation)
            score = max(0.0, (total_records - null_ids) / total_records * 100)
            return score
        except Exception:
            return 0.0
    
    def _check_for_duplicates(self, model_class, field_name: str) -> Dict[str, Any]:
        """Check for duplicate records"""
        try:
            with connection.cursor() as cursor:
                table_name = model_class._meta.db_table
                cursor.execute(f"""
                    SELECT {field_name}, COUNT(*) as count
                    FROM {table_name}
                    GROUP BY {field_name}
                    HAVING COUNT(*) > 1
                    LIMIT 10
                """)
                duplicates = cursor.fetchall()
                
                return {
                    'duplicate_count': len(duplicates),
                    'sample_duplicates': duplicates[:5] if duplicates else []
                }
        except Exception as e:
            return {'error': str(e)}
    
    def _compare_performance(self, old_result: SyncTestResult, new_result: SyncTestResult) -> Dict[str, Any]:
        """Compare performance metrics between old and new results"""
        comparison = {}
        
        # Duration comparison
        if old_result.duration > 0 and new_result.duration > 0:
            speed_improvement = (old_result.duration - new_result.duration) / old_result.duration * 100
            comparison['speed_improvement_percent'] = speed_improvement
        
        # Memory usage comparison
        if old_result.memory_usage and new_result.memory_usage:
            memory_improvement = (old_result.memory_usage - new_result.memory_usage) / old_result.memory_usage * 100
            comparison['memory_improvement_percent'] = memory_improvement
        
        # Records per second
        if old_result.duration > 0:
            comparison['old_records_per_second'] = old_result.records_processed / old_result.duration
        if new_result.duration > 0:
            comparison['new_records_per_second'] = new_result.records_processed / new_result.duration
        
        # Success rate
        comparison['old_success_rate'] = old_result.success
        comparison['new_success_rate'] = new_result.success
        
        return comparison
    
    def _generate_recommendations(self, old_result: SyncTestResult, new_result: SyncTestResult, 
                                data_consistency: Dict[str, Any]) -> List[str]:
        """Generate recommendations based on test results"""
        recommendations = []
        
        # Performance recommendations
        if new_result.success and old_result.success:
            if new_result.duration < old_result.duration:
                recommendations.append(f"✅ New command is {((old_result.duration - new_result.duration) / old_result.duration * 100):.1f}% faster")
            elif new_result.duration > old_result.duration:
                recommendations.append(f"⚠️ New command is {((new_result.duration - old_result.duration) / old_result.duration * 100):.1f}% slower - investigate performance")
        
        # Success rate recommendations
        if new_result.success and not old_result.success:
            recommendations.append("✅ New command succeeded where old command failed")
        elif not new_result.success and old_result.success:
            recommendations.append("❌ New command failed where old command succeeded - needs investigation")
        elif not new_result.success and not old_result.success:
            recommendations.append("❌ Both commands failed - investigate underlying issues")
        
        # Data consistency recommendations
        if 'error' in data_consistency:
            recommendations.append(f"⚠️ Data consistency check failed: {data_consistency['error']}")
        else:
            quality_score = data_consistency.get('data_quality_score', 0)
            if quality_score < 95:
                recommendations.append(f"⚠️ Data quality score is {quality_score:.1f}% - investigate data issues")
            else:
                recommendations.append(f"✅ Data quality score is {quality_score:.1f}%")
        
        return recommendations
    
    def generate_report(self, comparisons: List[ComparisonResult]) -> str:
        """Generate a comprehensive test report"""
        report = []
        report.append("# HubSpot Sync Commands - Parallel Testing Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Test Mode: {'Dry Run' if self.dry_run else 'Live Run'}")
        report.append("")
        
        # Summary
        report.append("## Summary")
        successful_tests = sum(1 for comp in comparisons if comp.old_result.success and comp.new_result.success)
        report.append(f"- Total Tests: {len(comparisons)}")
        report.append(f"- Successful Tests: {successful_tests}")
        report.append(f"- Failed Tests: {len(comparisons) - successful_tests}")
        report.append("")
        
        # Detailed results
        for comp in comparisons:
            report.append(f"## {comp.entity_type.title()} Sync Comparison")
            report.append("")
            
            # Old command results
            report.append("### Old Command Results")
            report.append(f"- Command: {comp.old_result.command}")
            report.append(f"- Success: {'✅' if comp.old_result.success else '❌'}")
            report.append(f"- Duration: {comp.old_result.duration:.2f}s")
            report.append(f"- Records Processed: {comp.old_result.records_processed}")
            report.append(f"- Records Created: {comp.old_result.records_created}")
            report.append(f"- Records Updated: {comp.old_result.records_updated}")
            report.append(f"- Records Failed: {comp.old_result.records_failed}")
            if comp.old_result.error_message:
                report.append(f"- Error: {comp.old_result.error_message}")
            report.append("")
            
            # New command results
            report.append("### New Command Results")
            report.append(f"- Command: {comp.new_result.command}")
            report.append(f"- Success: {'✅' if comp.new_result.success else '❌'}")
            report.append(f"- Duration: {comp.new_result.duration:.2f}s")
            report.append(f"- Records Processed: {comp.new_result.records_processed}")
            report.append(f"- Records Created: {comp.new_result.records_created}")
            report.append(f"- Records Updated: {comp.new_result.records_updated}")
            report.append(f"- Records Failed: {comp.new_result.records_failed}")
            if comp.new_result.error_message:
                report.append(f"- Error: {comp.new_result.error_message}")
            report.append("")
            
            # Performance comparison
            report.append("### Performance Comparison")
            for key, value in comp.performance_comparison.items():
                if isinstance(value, float):
                    report.append(f"- {key.replace('_', ' ').title()}: {value:.2f}")
                else:
                    report.append(f"- {key.replace('_', ' ').title()}: {value}")
            report.append("")
            
            # Data consistency
            report.append("### Data Consistency")
            for key, value in comp.data_consistency.items():
                if key != 'error':
                    report.append(f"- {key.replace('_', ' ').title()}: {value}")
            report.append("")
            
            # Recommendations
            report.append("### Recommendations")
            for rec in comp.recommendations:
                report.append(f"- {rec}")
            report.append("")
        
        return "\n".join(report)
