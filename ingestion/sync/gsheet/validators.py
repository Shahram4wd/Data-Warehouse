"""
Google Sheets Validation Rules
"""
import re
from typing import Any, Dict, List, Optional
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class GoogleSheetsValidator:
    """
    Validation rules for Google Sheets data
    """
    
    @staticmethod
    def is_valid_date(date_value: Any) -> bool:
        """
        Validate if a value represents a valid date
        
        Args:
            date_value: Value to validate
            
        Returns:
            True if valid date format
        """
        if not date_value:
            return False
        
        date_str = str(date_value).strip()
        
        # Common date formats
        date_patterns = [
            r'^\d{4}-\d{2}-\d{2}$',  # YYYY-MM-DD
            r'^\d{1,2}/\d{1,2}/\d{4}$',  # M/D/YYYY or MM/DD/YYYY
            r'^\d{1,2}-\d{1,2}-\d{4}$',  # M-D-YYYY or MM-DD-YYYY
            r'^\d{4}/\d{1,2}/\d{1,2}$',  # YYYY/M/D or YYYY/MM/DD
        ]
        
        for pattern in date_patterns:
            if re.match(pattern, date_str):
                return True
        
        return False
    
    @staticmethod
    def is_valid_numeric(numeric_value: Any) -> bool:
        """
        Validate if a value represents a valid number
        
        Args:
            numeric_value: Value to validate
            
        Returns:
            True if valid numeric format
        """
        if not numeric_value:
            return False
        
        numeric_str = str(numeric_value).strip()
        
        # Remove common formatting
        cleaned = numeric_str.replace(',', '').replace('$', '').replace('%', '').strip()
        
        try:
            float(cleaned)
            return True
        except (ValueError, TypeError):
            return False
    
    @staticmethod
    def validate_marketing_lead_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a marketing lead record
        
        Args:
            record: Record to validate
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check for required fields
        if not record.get('date'):
            validation_result['warnings'].append('Missing date field')
        elif not GoogleSheetsValidator.is_valid_date(record['date']):
            validation_result['warnings'].append(f'Invalid date format: {record["date"]}')
        
        # Validate numeric fields
        for field in ['leads', 'cost']:
            if record.get(field):
                if not GoogleSheetsValidator.is_valid_numeric(record[field]):
                    validation_result['warnings'].append(f'Invalid numeric format for {field}: {record[field]}')
        
        # Check for empty record
        has_data = any(
            record.get(field) and str(record[field]).strip()
            for field in ['date', 'source', 'medium', 'campaign', 'leads', 'cost']
        )
        
        if not has_data:
            validation_result['is_valid'] = False
            validation_result['errors'].append('Record appears to be empty')
        
        return validation_result
    
    @staticmethod
    def validate_sheet_structure(headers: List[str]) -> Dict[str, Any]:
        """
        Validate Google Sheets structure
        
        Args:
            headers: List of header column names
            
        Returns:
            Dict with validation results
        """
        validation_result = {
            'is_valid': True,
            'errors': [],
            'warnings': [],
            'suggestions': []
        }
        
        if not headers:
            validation_result['is_valid'] = False
            validation_result['errors'].append('No headers found in sheet')
            return validation_result
        
        # Check for common expected headers
        expected_headers = ['date', 'source', 'medium', 'campaign', 'leads', 'cost']
        header_lower = [h.lower() for h in headers]
        
        missing_headers = []
        for expected in expected_headers:
            found = False
            for header in header_lower:
                if expected in header or header in expected:
                    found = True
                    break
            if not found:
                missing_headers.append(expected)
        
        if missing_headers:
            validation_result['warnings'].append(f'Missing expected headers: {missing_headers}')
            validation_result['suggestions'].append(
                'Consider adding columns for: ' + ', '.join(missing_headers)
            )
        
        # Check for duplicate headers
        seen_headers = set()
        duplicates = []
        for header in headers:
            if header.lower() in seen_headers:
                duplicates.append(header)
            else:
                seen_headers.add(header.lower())
        
        if duplicates:
            validation_result['warnings'].append(f'Duplicate headers found: {duplicates}')
        
        # Check for empty headers
        empty_headers = [i for i, header in enumerate(headers) if not header or not header.strip()]
        if empty_headers:
            validation_result['warnings'].append(f'Empty headers found at positions: {empty_headers}')
        
        return validation_result


class MarketingLeadsValidator(GoogleSheetsValidator):
    """
    Specific validator for Marketing Leads sheet
    """
    
    @staticmethod
    def validate_record(record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate a marketing leads record with specific business rules
        
        Args:
            record: Marketing leads record
            
        Returns:
            Validation result
        """
        # Start with base validation
        result = GoogleSheetsValidator.validate_marketing_lead_record(record)
        
        # Additional marketing-specific validation
        try:
            # Check leads count is reasonable
            if record.get('leads'):
                try:
                    leads_num = float(str(record['leads']).replace(',', ''))
                    if leads_num < 0:
                        result['warnings'].append('Negative leads count')
                    elif leads_num > 10000:  # Arbitrary high threshold
                        result['warnings'].append(f'Very high leads count: {leads_num}')
                except (ValueError, TypeError):
                    pass
            
            # Check cost is reasonable
            if record.get('cost'):
                try:
                    cost_num = float(str(record['cost']).replace(',', '').replace('$', ''))
                    if cost_num < 0:
                        result['warnings'].append('Negative cost')
                    elif cost_num > 100000:  # Arbitrary high threshold
                        result['warnings'].append(f'Very high cost: ${cost_num:,.2f}')
                except (ValueError, TypeError):
                    pass
            
            # Check for suspicious data patterns
            if record.get('source') and len(str(record['source'])) > 100:
                result['warnings'].append('Very long source name')
            
            if record.get('campaign') and len(str(record['campaign'])) > 200:
                result['warnings'].append('Very long campaign name')
        
        except Exception as e:
            logger.error(f"Error in marketing leads validation: {e}")
            result['warnings'].append(f'Validation error: {e}')
        
        return result
    
    @staticmethod
    def get_data_quality_report(records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a data quality report for marketing leads
        
        Args:
            records: List of marketing leads records
            
        Returns:
            Data quality report
        """
        try:
            total_records = len(records)
            
            if total_records == 0:
                return {
                    'total_records': 0,
                    'quality_score': 0,
                    'issues': ['No records to analyze']
                }
            
            # Track various quality metrics
            valid_dates = 0
            valid_sources = 0
            valid_leads = 0
            valid_costs = 0
            complete_records = 0
            
            issues = []
            date_formats = set()
            sources = set()
            
            for i, record in enumerate(records):
                # Check completeness
                required_fields = ['date', 'source', 'leads']
                if all(record.get(field) for field in required_fields):
                    complete_records += 1
                
                # Validate individual fields
                if record.get('date'):
                    if GoogleSheetsValidator.is_valid_date(record['date']):
                        valid_dates += 1
                        date_formats.add(str(record['date'])[:10])  # Store format sample
                
                if record.get('source') and str(record['source']).strip():
                    valid_sources += 1
                    sources.add(str(record['source']).strip())
                
                if record.get('leads'):
                    if GoogleSheetsValidator.is_valid_numeric(record['leads']):
                        valid_leads += 1
                
                if record.get('cost'):
                    if GoogleSheetsValidator.is_valid_numeric(record['cost']):
                        valid_costs += 1
            
            # Calculate quality score (0-100)
            quality_metrics = [
                valid_dates / total_records,
                valid_sources / total_records,
                valid_leads / total_records,
                complete_records / total_records
            ]
            quality_score = int(sum(quality_metrics) / len(quality_metrics) * 100)
            
            # Generate issues list
            if valid_dates / total_records < 0.9:
                issues.append(f'Only {valid_dates}/{total_records} records have valid dates')
            
            if valid_sources / total_records < 0.9:
                issues.append(f'Only {valid_sources}/{total_records} records have valid sources')
            
            if valid_leads / total_records < 0.8:
                issues.append(f'Only {valid_leads}/{total_records} records have valid leads counts')
            
            if complete_records / total_records < 0.8:
                issues.append(f'Only {complete_records}/{total_records} records are complete')
            
            return {
                'total_records': total_records,
                'complete_records': complete_records,
                'quality_score': quality_score,
                'field_validity': {
                    'dates': f'{valid_dates}/{total_records} ({valid_dates/total_records*100:.1f}%)',
                    'sources': f'{valid_sources}/{total_records} ({valid_sources/total_records*100:.1f}%)',
                    'leads': f'{valid_leads}/{total_records} ({valid_leads/total_records*100:.1f}%)',
                    'costs': f'{valid_costs}/{total_records} ({valid_costs/total_records*100:.1f}%)'
                },
                'unique_sources': len(sources),
                'date_range': f'{min(date_formats)} to {max(date_formats)}' if date_formats else 'No valid dates',
                'issues': issues if issues else ['No significant data quality issues found']
            }
            
        except Exception as e:
            logger.error(f"Error generating data quality report: {e}")
            return {
                'total_records': len(records),
                'quality_score': 0,
                'error': str(e)
            }
