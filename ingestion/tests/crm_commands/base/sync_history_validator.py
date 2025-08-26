"""
SyncHistory Compliance Validator

CRITICAL: Validates that all CRM sync commands comply with the mandatory
SyncHistory framework requirements from crm_sync_guide.md

🔴 MANDATORY COMPLIANCE REQUIREMENTS:
- All CRM sync commands MUST use SyncHistory table
- NO custom sync tracking solutions allowed  
- Proper delta sync timestamp handling required
- Centralized monitoring and audit trails required
"""
import logging
from typing import Dict, Any, List, Optional, Type
from unittest.mock import patch
from datetime import datetime, timedelta

from django.db import models
from django.utils import timezone

from ingestion.models.common import SyncHistory


class SyncHistoryComplianceValidator:
    """
    Validates SyncHistory compliance for CRM sync commands
    
    This is a MANDATORY validation as per crm_sync_guide.md
    All CRM integrations must pass these compliance tests
    """
    
    FORBIDDEN_PATTERNS = [
        # Patterns that violate SyncHistory compliance
        'synced_at',  # Custom timestamp fields
        'last_sync',  # Custom sync tracking
        'sync_timestamp',  # Custom timestamp tracking
        '_sync_',  # Any custom sync fields
    ]
    
    def __init__(self, command_runner):
        self.command_runner = command_runner
        self.logger = logging.getLogger('sync_history_compliance')
    
    def validate_sync_history_usage(self, command_name: str, crm_source: str, 
                                   operation_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        🔴 CRITICAL: Validate that command uses SyncHistory properly
        
        Args:
            command_name: Management command to test
            crm_source: CRM source name (e.g., 'hubspot', 'callrail')
            operation_name: Operation name (e.g., 'contacts', 'deals')
            *args: Command arguments
            **kwargs: Command options
            
        Returns:
            Validation results dict
        """
        validation_results = {
            'compliant': True,
            'violations': [],
            'warnings': [],
            'sync_history_created': False,
            'sync_history_records': [],
        }
        
        # Clear existing sync history for clean test
        initial_count = SyncHistory.objects.filter(
            crm_source=crm_source,
            sync_type=operation_name
        ).count()
        
        # Run command and check SyncHistory usage
        try:
            result = self.command_runner.run_command_in_docker(
                command_name, *args, **kwargs
            )
            
            # Check if SyncHistory records were created
            final_count = SyncHistory.objects.filter(
                source=crm_source,
                operation_name=operation_name
            ).count()
            
            new_records = SyncHistory.objects.filter(
                crm_source=crm_source,
                sync_type=operation_name
            ).count() - initial_count
            
            if new_records > 0:
                validation_results['sync_history_created'] = True
                validation_results['sync_history_records'] = list(
                    SyncHistory.objects.filter(
                        source=crm_source,
                        operation_name=operation_name
                    ).order_by('-started_at')[:new_records]
                )
                
                # Validate record structure
                for record in validation_results['sync_history_records']:
                    record_validation = self._validate_sync_history_record(record)
                    validation_results['violations'].extend(record_validation['violations'])
                    validation_results['warnings'].extend(record_validation['warnings'])
            
            else:
                # CRITICAL VIOLATION: No SyncHistory record created
                if not kwargs.get('dry_run', False):  # Dry-run may not create records
                    validation_results['compliant'] = False
                    validation_results['violations'].append(
                        f"🔴 CRITICAL: Command {command_name} did not create SyncHistory record"
                    )
        
        except Exception as e:
            validation_results['compliant'] = False
            validation_results['violations'].append(
                f"🔴 CRITICAL: Command {command_name} failed during SyncHistory validation: {e}"
            )
        
        return validation_results
    
    def _validate_sync_history_record(self, record: SyncHistory) -> Dict[str, Any]:
        """Validate individual SyncHistory record structure"""
        validation = {
            'violations': [],
            'warnings': []
        }
        
        # Required field validation
        if not record.source:
            validation['violations'].append("SyncHistory.source is empty")
        
        if not record.operation_name:
            validation['violations'].append("SyncHistory.operation_name is empty")
        
        if not record.started_at:
            validation['violations'].append("SyncHistory.started_at is empty")
        
        # Timestamp validation
        if record.started_at and record.completed_at:
            if record.completed_at < record.started_at:
                validation['violations'].append("SyncHistory.completed_at is before started_at")
        
        # Configuration validation
        if not isinstance(record.configuration, dict):
            validation['warnings'].append("SyncHistory.configuration is not a dict")
        
        return validation
    
    def validate_no_custom_sync_tracking(self, model_classes: List[Type[models.Model]]) -> Dict[str, Any]:
        """
        🔴 CRITICAL: Validate that models don't use forbidden custom sync tracking
        
        Args:
            model_classes: Django model classes to check
            
        Returns:
            Validation results dict
        """
        validation_results = {
            'compliant': True,
            'violations': [],
            'models_checked': []
        }
        
        for model_class in model_classes:
            model_validation = self._check_model_for_forbidden_patterns(model_class)
            validation_results['models_checked'].append({
                'model': model_class.__name__,
                'violations': model_validation['violations']
            })
            
            if model_validation['violations']:
                validation_results['compliant'] = False
                validation_results['violations'].extend(model_validation['violations'])
        
        return validation_results
    
    def _check_model_for_forbidden_patterns(self, model_class: Type[models.Model]) -> Dict[str, Any]:
        """Check a single model for forbidden sync tracking patterns"""
        validation = {'violations': []}
        
        # Check field names for forbidden patterns
        for field in model_class._meta.get_fields():
            field_name = field.name.lower()
            
            for forbidden_pattern in self.FORBIDDEN_PATTERNS:
                if forbidden_pattern in field_name:
                    validation['violations'].append(
                        f"🔴 FORBIDDEN: Model {model_class.__name__} has field '{field.name}' "
                        f"containing forbidden pattern '{forbidden_pattern}'. "
                        f"Use SyncHistory table instead."
                    )
        
        return validation
    
    def validate_delta_sync_compliance(self, command_name: str, crm_source: str,
                                     operation_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Validate that command properly implements delta sync using SyncHistory
        
        Args:
            command_name: Management command to test
            crm_source: CRM source name
            operation_name: Operation name
            *args: Command arguments
            **kwargs: Command options
            
        Returns:
            Validation results dict
        """
        validation_results = {
            'compliant': True,
            'violations': [],
            'delta_sync_working': False,
            'last_sync_timestamp_used': False
        }
        
        try:
            # Create a fake previous sync record
            previous_sync = SyncHistory.objects.create(
                source=crm_source,
                operation_name=operation_name,
                started_at=timezone.now() - timedelta(hours=1),
                completed_at=timezone.now() - timedelta(hours=1),
                status='completed',
                records_processed=10,
                configuration={'test': 'previous_sync'}
            )
            
            # Mock API client to track what timestamp is used
            api_calls_made = []
            
            def mock_api_call(*args, **kwargs):
                api_calls_made.append(kwargs)
                return {'results': [], 'total': 0}
            
            # This will need to be customized per CRM
            with patch('requests.get', side_effect=mock_api_call):
                result = self.command_runner.run_command_in_docker(
                    command_name, '--dry-run', *args, **kwargs
                )
                
                # Check if API was called with timestamp from previous sync
                for call_kwargs in api_calls_made:
                    # Look for timestamp parameters that match previous sync
                    if self._contains_timestamp_near(call_kwargs, previous_sync.completed_at):
                        validation_results['last_sync_timestamp_used'] = True
                        validation_results['delta_sync_working'] = True
                        break
        
        except Exception as e:
            validation_results['violations'].append(
                f"Delta sync validation failed: {e}"
            )
            validation_results['compliant'] = False
        
        return validation_results
    
    def _contains_timestamp_near(self, params: Dict[str, Any], target_time: datetime, 
                                tolerance_minutes: int = 5) -> bool:
        """Check if parameters contain a timestamp near the target time"""
        for key, value in params.items():
            if isinstance(value, str):
                # Try to parse as timestamp
                try:
                    parsed_time = datetime.fromisoformat(value.replace('Z', '+00:00'))
                    if abs((parsed_time - target_time).total_seconds()) < (tolerance_minutes * 60):
                        return True
                except:
                    continue
        return False
    
    def validate_audit_trail_completeness(self, command_name: str, crm_source: str,
                                        operation_name: str, *args, **kwargs) -> Dict[str, Any]:
        """
        Validate that SyncHistory provides complete audit trail
        
        Args:
            command_name: Management command to test
            crm_source: CRM source name
            operation_name: Operation name
            *args: Command arguments
            **kwargs: Command options
            
        Returns:
            Validation results dict
        """
        validation_results = {
            'compliant': True,
            'violations': [],
            'audit_trail_complete': False
        }
        
        try:
            # Run command and check audit trail completeness
            result = self.command_runner.run_command_in_docker(
                command_name, *args, **kwargs
            )
            
            # Get the created sync history record
            sync_record = SyncHistory.objects.filter(
                source=crm_source,
                operation_name=operation_name
            ).order_by('-started_at').first()
            
            if sync_record:
                audit_validation = self._validate_audit_trail_fields(sync_record)
                validation_results.update(audit_validation)
            else:
                validation_results['violations'].append(
                    "No SyncHistory record found for audit trail validation"
                )
                validation_results['compliant'] = False
        
        except Exception as e:
            validation_results['violations'].append(f"Audit trail validation failed: {e}")
            validation_results['compliant'] = False
        
        return validation_results
    
    def _validate_audit_trail_fields(self, record: SyncHistory) -> Dict[str, Any]:
        """Validate that SyncHistory record has complete audit trail"""
        validation = {
            'compliant': True,
            'violations': [],
            'audit_trail_complete': True
        }
        
        # Required audit fields
        required_fields = [
            'source', 'operation_name', 'started_at', 'status'
        ]
        
        for field in required_fields:
            if not getattr(record, field, None):
                validation['violations'].append(f"Missing audit field: {field}")
                validation['compliant'] = False
                validation['audit_trail_complete'] = False
        
        # Recommended audit fields
        recommended_fields = [
            'completed_at', 'records_processed', 'configuration'
        ]
        
        for field in recommended_fields:
            if not getattr(record, field, None):
                validation['violations'].append(f"Missing recommended audit field: {field}")
        
        return validation
    
    def generate_compliance_report(self, validations: List[Dict[str, Any]]) -> str:
        """
        Generate a comprehensive compliance report
        
        Args:
            validations: List of validation result dicts
            
        Returns:
            Formatted compliance report string
        """
        report_lines = [
            "=" * 70,
            "🔴 SYNCHISTORY COMPLIANCE REPORT",
            "=" * 70,
            ""
        ]
        
        total_tests = len(validations)
        compliant_tests = sum(1 for v in validations if v.get('compliant', False))
        
        report_lines.extend([
            f"📊 SUMMARY: {compliant_tests}/{total_tests} tests passed",
            f"✅ Compliant: {compliant_tests}",
            f"❌ Non-compliant: {total_tests - compliant_tests}",
            ""
        ])
        
        if compliant_tests == total_tests:
            report_lines.extend([
                "🎉 ALL TESTS PASSED - SYNCHISTORY COMPLIANT",
                "✅ This CRM integration follows crm_sync_guide.md requirements",
                ""
            ])
        else:
            report_lines.extend([
                "🚨 COMPLIANCE VIOLATIONS FOUND",
                "❌ This CRM integration violates crm_sync_guide.md requirements",
                "🔧 Fix violations before deployment",
                ""
            ])
        
        # Detail each validation
        for i, validation in enumerate(validations, 1):
            status = "✅ PASS" if validation.get('compliant', False) else "❌ FAIL"
            report_lines.append(f"{i}. {status} - {validation.get('test_name', 'Test')}")
            
            for violation in validation.get('violations', []):
                report_lines.append(f"   🔴 {violation}")
            
            for warning in validation.get('warnings', []):
                report_lines.append(f"   ⚠️  {warning}")
            
            report_lines.append("")
        
        report_lines.append("=" * 70)
        
        return "\n".join(report_lines)
