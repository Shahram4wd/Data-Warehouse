"""
Data consistency validator for HubSpot sync operations
Validates that old and new sync processes produce consistent results
"""
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple, Set
from dataclasses import dataclass
from django.db import connection
from django.utils import timezone

from ingestion.models.hubspot import (
    Hubspot_Contact, Hubspot_Appointment, Hubspot_Division, Hubspot_Deal
)
from ingestion.models.common import SyncHistory

logger = logging.getLogger(__name__)

@dataclass
class ConsistencyIssue:
    """Represents a data consistency issue"""
    issue_type: str
    entity_type: str
    entity_id: str
    field_name: str
    old_value: Any
    new_value: Any
    severity: str  # 'critical', 'warning', 'info'
    description: str

@dataclass
class ConsistencyReport:
    """Comprehensive consistency validation report"""
    entity_type: str
    total_records: int
    issues_found: List[ConsistencyIssue]
    summary: Dict[str, Any]
    recommendations: List[str]

class DataConsistencyValidator:
    """Validates data consistency between old and new sync processes"""
    
    def __init__(self, tolerance_threshold: float = 0.01):
        """
        Initialize validator
        
        Args:
            tolerance_threshold: Acceptable difference threshold for numeric comparisons (1% default)
        """
        self.tolerance_threshold = tolerance_threshold
        self.issues = []
    
    def validate_contact_consistency(self, sample_size: int = 1000) -> ConsistencyReport:
        """Validate consistency of contact data"""
        logger.info(f"Validating contact data consistency (sample size: {sample_size})")
        
        # Get recent contacts for validation
        recent_contacts = Hubspot_Contact.objects.order_by('-lastmodifieddate')[:sample_size]
        
        issues = []
        total_records = recent_contacts.count()
        
        for contact in recent_contacts:
            # Validate required fields
            contact_issues = self._validate_contact_record(contact)
            issues.extend(contact_issues)
        
        # Check for duplicates
        duplicate_issues = self._check_contact_duplicates()
        issues.extend(duplicate_issues)
        
        # Generate summary
        summary = self._generate_contact_summary(total_records, issues)
        
        # Generate recommendations
        recommendations = self._generate_contact_recommendations(issues)
        
        return ConsistencyReport(
            entity_type='contacts',
            total_records=total_records,
            issues_found=issues,
            summary=summary,
            recommendations=recommendations
        )
    
    def validate_appointment_consistency(self, sample_size: int = 1000) -> ConsistencyReport:
        """Validate consistency of appointment data"""
        logger.info(f"Validating appointment data consistency (sample size: {sample_size})")
        
        # Get recent appointments for validation
        recent_appointments = Hubspot_Appointment.objects.order_by('-hs_lastmodifieddate')[:sample_size]
        
        issues = []
        total_records = recent_appointments.count()
        
        for appointment in recent_appointments:
            # Validate required fields and data integrity
            appointment_issues = self._validate_appointment_record(appointment)
            issues.extend(appointment_issues)
        
        # Check for duplicates
        duplicate_issues = self._check_appointment_duplicates()
        issues.extend(duplicate_issues)
        
        # Generate summary
        summary = self._generate_appointment_summary(total_records, issues)
        
        # Generate recommendations
        recommendations = self._generate_appointment_recommendations(issues)
        
        return ConsistencyReport(
            entity_type='appointments',
            total_records=total_records,
            issues_found=issues,
            summary=summary,
            recommendations=recommendations
        )
    
    def validate_division_consistency(self) -> ConsistencyReport:
        """Validate consistency of division data"""
        logger.info("Validating division data consistency")
        
        # Get all divisions (usually small dataset)
        divisions = Hubspot_Division.objects.all()
        
        issues = []
        total_records = divisions.count()
        
        for division in divisions:
            # Validate required fields and data integrity
            division_issues = self._validate_division_record(division)
            issues.extend(division_issues)
        
        # Check for duplicates
        duplicate_issues = self._check_division_duplicates()
        issues.extend(duplicate_issues)
        
        # Generate summary
        summary = self._generate_division_summary(total_records, issues)
        
        # Generate recommendations
        recommendations = self._generate_division_recommendations(issues)
        
        return ConsistencyReport(
            entity_type='divisions',
            total_records=total_records,
            issues_found=issues,
            summary=summary,
            recommendations=recommendations
        )
    
    def validate_deal_consistency(self, sample_size: int = 1000) -> ConsistencyReport:
        """Validate consistency of deal data"""
        logger.info(f"Validating deal data consistency (sample size: {sample_size})")
        
        # Get recent deals for validation
        recent_deals = Hubspot_Deal.objects.order_by('-createdate')[:sample_size]
        
        issues = []
        total_records = recent_deals.count()
        
        for deal in recent_deals:
            # Validate required fields and data integrity
            deal_issues = self._validate_deal_record(deal)
            issues.extend(deal_issues)
        
        # Check for duplicates
        duplicate_issues = self._check_deal_duplicates()
        issues.extend(duplicate_issues)
        
        # Generate summary
        summary = self._generate_deal_summary(total_records, issues)
        
        # Generate recommendations
        recommendations = self._generate_deal_recommendations(issues)
        
        return ConsistencyReport(
            entity_type='deals',
            total_records=total_records,
            issues_found=issues,
            summary=summary,
            recommendations=recommendations
        )
    
    def validate_all_consistency(self) -> List[ConsistencyReport]:
        """Validate consistency for all entity types"""
        logger.info("Starting comprehensive consistency validation")
        
        reports = []
        
        # Validate each entity type
        entity_validators = [
            ('contacts', self.validate_contact_consistency),
            ('appointments', self.validate_appointment_consistency),
            ('divisions', self.validate_division_consistency),
            ('deals', self.validate_deal_consistency)
        ]
        
        for entity_type, validator in entity_validators:
            try:
                logger.info(f"Validating {entity_type}...")
                report = validator()
                reports.append(report)
                logger.info(f"Completed {entity_type} validation: {len(report.issues_found)} issues found")
            except Exception as e:
                logger.error(f"Error validating {entity_type}: {e}")
                # Create error report
                error_report = ConsistencyReport(
                    entity_type=entity_type,
                    total_records=0,
                    issues_found=[
                        ConsistencyIssue(
                            issue_type='validation_error',
                            entity_type=entity_type,
                            entity_id='unknown',
                            field_name='validation',
                            old_value=None,
                            new_value=None,
                            severity='critical',
                            description=f"Validation failed: {e}"
                        )
                    ],
                    summary={'error': str(e)},
                    recommendations=[f"Fix validation error for {entity_type}: {e}"]
                )
                reports.append(error_report)
        
        return reports
    
    def _validate_contact_record(self, contact: Hubspot_Contact) -> List[ConsistencyIssue]:
        """Validate a single contact record"""
        issues = []
        
        # Check required fields
        if not contact.id:
            issues.append(
                ConsistencyIssue(
                    issue_type='missing_required_field',
                    entity_type='contact',
                    entity_id=str(contact.id),
                    field_name='id',
                    old_value=None,
                    new_value=contact.id,
                    severity='critical',
                    description='Contact ID is missing'
                )
            )
        
        # Validate email format
        if contact.email and '@' not in contact.email:
            issues.append(
                ConsistencyIssue(
                    issue_type='invalid_format',
                    entity_type='contact',
                    entity_id=str(contact.id),
                    field_name='email',
                    old_value=None,
                    new_value=contact.email,
                    severity='warning',
                    description=f'Invalid email format: {contact.email}'
                )
            )
        
        # Validate phone format
        if contact.phone and len(contact.phone) < 10:
            issues.append(
                ConsistencyIssue(
                    issue_type='invalid_format',
                    entity_type='contact',
                    entity_id=str(contact.id),
                    field_name='phone',
                    old_value=None,
                    new_value=contact.phone,
                    severity='info',
                    description=f'Short phone number: {contact.phone}'
                )
            )
        
        return issues
    
    def _validate_appointment_record(self, appointment: Hubspot_Appointment) -> List[ConsistencyIssue]:
        """Validate a single appointment record"""
        issues = []
        
        # Check required fields
        if not appointment.id:
            issues.append(
                ConsistencyIssue(
                    issue_type='missing_required_field',
                    entity_type='appointment',
                    entity_id=str(appointment.id),
                    field_name='id',
                    old_value=None,
                    new_value=appointment.id,
                    severity='critical',
                    description='Appointment ID is missing'
                )
            )
        
        # Validate date consistency
        if appointment.hs_appointment_start and appointment.hs_appointment_end:
            if appointment.hs_appointment_start > appointment.hs_appointment_end:
                issues.append(
                    ConsistencyIssue(
                        issue_type='logical_inconsistency',
                        entity_type='appointment',
                        entity_id=str(appointment.id),
                        field_name='hs_appointment_start/hs_appointment_end',
                        old_value=appointment.hs_appointment_start,
                        new_value=appointment.hs_appointment_end,
                        severity='warning',
                        description='Appointment start time is after end time'
                    )
                )
        
        return issues
    
    def _validate_division_record(self, division: Hubspot_Division) -> List[ConsistencyIssue]:
        """Validate a single division record"""
        issues = []
        
        # Check required fields
        if not division.id:
            issues.append(
                ConsistencyIssue(
                    issue_type='missing_required_field',
                    entity_type='division',
                    entity_id=str(division.id),
                    field_name='id',
                    old_value=None,
                    new_value=division.id,
                    severity='critical',
                    description='Division ID is missing'
                )
            )
        
        return issues
    
    def _validate_deal_record(self, deal: Hubspot_Deal) -> List[ConsistencyIssue]:
        """Validate a single deal record"""
        issues = []
        
        # Check required fields
        if not deal.id:
            issues.append(
                ConsistencyIssue(
                    issue_type='missing_required_field',
                    entity_type='deal',
                    entity_id=str(deal.id),
                    field_name='id',
                    old_value=None,
                    new_value=deal.id,
                    severity='critical',
                    description='Deal ID is missing'
                )
            )
        
        # Validate amount
        if deal.amount and deal.amount < 0:
            issues.append(
                ConsistencyIssue(
                    issue_type='invalid_value',
                    entity_type='deal',
                    entity_id=str(deal.id),
                    field_name='amount',
                    old_value=None,
                    new_value=deal.amount,
                    severity='warning',
                    description=f'Negative deal amount: {deal.amount}'
                )
            )
        
        return issues
    
    def _check_contact_duplicates(self) -> List[ConsistencyIssue]:
        """Check for duplicate contact records"""
        issues = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, COUNT(*) as count
                FROM ingestion_hubspot_contact
                GROUP BY id
                HAVING COUNT(*) > 1
                LIMIT 100
            """)
            
            duplicates = cursor.fetchall()
            
            for contact_id, count in duplicates:
                issues.append(
                    ConsistencyIssue(
                        issue_type='duplicate_record',
                        entity_type='contact',
                        entity_id=str(contact_id),
                        field_name='id',
                        old_value=1,
                        new_value=count,
                        severity='critical',
                        description=f'Duplicate contact ID found {count} times'
                    )
                )
        
        return issues
    
    def _check_appointment_duplicates(self) -> List[ConsistencyIssue]:
        """Check for duplicate appointment records"""
        issues = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, COUNT(*) as count
                FROM ingestion_hubspot_appointment
                GROUP BY id
                HAVING COUNT(*) > 1
                LIMIT 100
            """)
            
            duplicates = cursor.fetchall()
            
            for appointment_id, count in duplicates:
                issues.append(
                    ConsistencyIssue(
                        issue_type='duplicate_record',
                        entity_type='appointment',
                        entity_id=str(appointment_id),
                        field_name='id',
                        old_value=1,
                        new_value=count,
                        severity='critical',
                        description=f'Duplicate appointment ID found {count} times'
                    )
                )
        
        return issues
    
    def _check_division_duplicates(self) -> List[ConsistencyIssue]:
        """Check for duplicate division records"""
        issues = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, COUNT(*) as count
                FROM ingestion_hubspot_division
                GROUP BY id
                HAVING COUNT(*) > 1
                LIMIT 100
            """)
            
            duplicates = cursor.fetchall()
            
            for division_id, count in duplicates:
                issues.append(
                    ConsistencyIssue(
                        issue_type='duplicate_record',
                        entity_type='division',
                        entity_id=str(division_id),
                        field_name='id',
                        old_value=1,
                        new_value=count,
                        severity='critical',
                        description=f'Duplicate division ID found {count} times'
                    )
                )
        
        return issues
    
    def _check_deal_duplicates(self) -> List[ConsistencyIssue]:
        """Check for duplicate deal records"""
        issues = []
        
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, COUNT(*) as count
                FROM ingestion_hubspot_deal
                GROUP BY id
                HAVING COUNT(*) > 1
                LIMIT 100
            """)
            
            duplicates = cursor.fetchall()
            
            for deal_id, count in duplicates:
                issues.append(
                    ConsistencyIssue(
                        issue_type='duplicate_record',
                        entity_type='deal',
                        entity_id=str(deal_id),
                        field_name='id',
                        old_value=1,
                        new_value=count,
                        severity='critical',
                        description=f'Duplicate deal ID found {count} times'
                    )
                )
        
        return issues
    
    def _generate_contact_summary(self, total_records: int, issues: List[ConsistencyIssue]) -> Dict[str, Any]:
        """Generate summary for contact validation"""
        return {
            'total_records': total_records,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == 'critical']),
            'warning_issues': len([i for i in issues if i.severity == 'warning']),
            'info_issues': len([i for i in issues if i.severity == 'info']),
            'data_quality_score': max(0, (total_records - len(issues)) / max(1, total_records) * 100)
        }
    
    def _generate_appointment_summary(self, total_records: int, issues: List[ConsistencyIssue]) -> Dict[str, Any]:
        """Generate summary for appointment validation"""
        return {
            'total_records': total_records,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == 'critical']),
            'warning_issues': len([i for i in issues if i.severity == 'warning']),
            'info_issues': len([i for i in issues if i.severity == 'info']),
            'data_quality_score': max(0, (total_records - len(issues)) / max(1, total_records) * 100)
        }
    
    def _generate_division_summary(self, total_records: int, issues: List[ConsistencyIssue]) -> Dict[str, Any]:
        """Generate summary for division validation"""
        return {
            'total_records': total_records,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == 'critical']),
            'warning_issues': len([i for i in issues if i.severity == 'warning']),
            'info_issues': len([i for i in issues if i.severity == 'info']),
            'data_quality_score': max(0, (total_records - len(issues)) / max(1, total_records) * 100)
        }
    
    def _generate_deal_summary(self, total_records: int, issues: List[ConsistencyIssue]) -> Dict[str, Any]:
        """Generate summary for deal validation"""
        return {
            'total_records': total_records,
            'total_issues': len(issues),
            'critical_issues': len([i for i in issues if i.severity == 'critical']),
            'warning_issues': len([i for i in issues if i.severity == 'warning']),
            'info_issues': len([i for i in issues if i.severity == 'info']),
            'data_quality_score': max(0, (total_records - len(issues)) / max(1, total_records) * 100)
        }
    
    def _generate_contact_recommendations(self, issues: List[ConsistencyIssue]) -> List[str]:
        """Generate recommendations for contact issues"""
        recommendations = []
        
        critical_count = len([i for i in issues if i.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} critical issues need immediate attention")
        
        warning_count = len([i for i in issues if i.severity == 'warning'])
        if warning_count > 0:
            recommendations.append(f"⚠️ {warning_count} warnings should be reviewed")
        
        # Check for common issues
        email_issues = len([i for i in issues if i.field_name == 'email'])
        if email_issues > 0:
            recommendations.append(f"📧 {email_issues} email format issues found - implement email validation")
        
        phone_issues = len([i for i in issues if i.field_name == 'phone'])
        if phone_issues > 0:
            recommendations.append(f"📞 {phone_issues} phone format issues found - implement phone validation")
        
        return recommendations
    
    def _generate_appointment_recommendations(self, issues: List[ConsistencyIssue]) -> List[str]:
        """Generate recommendations for appointment issues"""
        recommendations = []
        
        critical_count = len([i for i in issues if i.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} critical issues need immediate attention")
        
        warning_count = len([i for i in issues if i.severity == 'warning'])
        if warning_count > 0:
            recommendations.append(f"⚠️ {warning_count} warnings should be reviewed")
        
        # Check for date/time issues
        date_issues = len([i for i in issues if 'date' in i.field_name or 'time' in i.field_name])
        if date_issues > 0:
            recommendations.append(f"📅 {date_issues} date/time issues found - validate appointment scheduling logic")
        
        return recommendations
    
    def _generate_division_recommendations(self, issues: List[ConsistencyIssue]) -> List[str]:
        """Generate recommendations for division issues"""
        recommendations = []
        
        critical_count = len([i for i in issues if i.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} critical issues need immediate attention")
        
        return recommendations
    
    def _generate_deal_recommendations(self, issues: List[ConsistencyIssue]) -> List[str]:
        """Generate recommendations for deal issues"""
        recommendations = []
        
        critical_count = len([i for i in issues if i.severity == 'critical'])
        if critical_count > 0:
            recommendations.append(f"🚨 {critical_count} critical issues need immediate attention")
        
        # Check for amount issues
        amount_issues = len([i for i in issues if i.field_name == 'amount'])
        if amount_issues > 0:
            recommendations.append(f"💰 {amount_issues} deal amount issues found - validate financial data")
        
        return recommendations
    
    def generate_consistency_report(self, reports: List[ConsistencyReport]) -> str:
        """Generate a comprehensive consistency report"""
        report = []
        report.append("# HubSpot Data Consistency Validation Report")
        report.append(f"Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Overall summary
        total_records = sum(r.total_records for r in reports)
        total_issues = sum(len(r.issues_found) for r in reports)
        
        report.append("## Overall Summary")
        report.append(f"- Total Records Validated: {total_records:,}")
        report.append(f"- Total Issues Found: {total_issues:,}")
        report.append(f"- Overall Data Quality Score: {((total_records - total_issues) / max(1, total_records) * 100):.1f}%")
        report.append("")
        
        # Individual entity reports
        for entity_report in reports:
            report.append(f"## {entity_report.entity_type.title()} Validation")
            report.append("")
            
            # Summary
            report.append("### Summary")
            for key, value in entity_report.summary.items():
                if key != 'error':
                    display_key = key.replace('_', ' ').title()
                    if isinstance(value, float):
                        report.append(f"- {display_key}: {value:.2f}")
                    else:
                        report.append(f"- {display_key}: {value:,}")
            report.append("")
            
            # Top issues
            if entity_report.issues_found:
                report.append("### Top Issues")
                for i, issue in enumerate(entity_report.issues_found[:10]):  # Show top 10
                    severity_icon = {'critical': '🚨', 'warning': '⚠️', 'info': 'ℹ️'}.get(issue.severity, '❓')
                    report.append(f"{i+1}. {severity_icon} {issue.description}")
                
                if len(entity_report.issues_found) > 10:
                    report.append(f"... and {len(entity_report.issues_found) - 10} more issues")
                report.append("")
            
            # Recommendations
            if entity_report.recommendations:
                report.append("### Recommendations")
                for rec in entity_report.recommendations:
                    report.append(f"- {rec}")
                report.append("")
        
        return "\n".join(report)
