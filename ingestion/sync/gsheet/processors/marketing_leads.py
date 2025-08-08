"""
Marketing Leads Google Sheets Processor
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import BaseGoogleSheetsProcessor

logger = logging.getLogger(__name__)


class MarketingLeadsProcessor(BaseGoogleSheetsProcessor):
    """
    Processor for Marketing Source Leads Google Sheet data
    
    Handles transformation and validation of marketing leads data
    from Google Sheets to the database model.
    """
    
    def get_field_mappings(self) -> Dict[str, str]:
        """
        Field mappings specific to Marketing Leads sheet
        
        Returns:
            Dict mapping Google Sheets columns to model fields
        """
        base_mappings = super().get_field_mappings()
        
        # Marketing leads specific mappings
        marketing_mappings = {
            # Common variations of field names we might see
            'Date': 'date',
            'Source': 'source',
            'Medium': 'medium',
            'Campaign': 'campaign',
            'Leads': 'leads',
            'Cost': 'cost',
            
            # Alternative column names
            'Marketing Source': 'source',
            'Marketing Medium': 'medium',
            'Campaign Name': 'campaign',
            'Lead Count': 'leads',
            'Total Cost': 'cost',
            'Spend': 'cost',
            'Ad Spend': 'cost',
            
            # Date variations
            'Report Date': 'date',
            'Campaign Date': 'date',
        }
        
        # Merge with base mappings
        base_mappings.update(marketing_mappings)
        return base_mappings
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform marketing leads record with specific business logic
        
        Args:
            record: Raw record from Google Sheets
            
        Returns:
            Transformed record
        """
        # Start with base transformation
        transformed = super().transform_record(record)
        
        try:
            # Specific transformations for marketing data
            
            # Normalize date format
            if 'date' in transformed:
                transformed['date'] = self._normalize_date(transformed['date'])
            
            # Clean and validate numeric fields
            for field in ['leads', 'cost']:
                if field in transformed:
                    transformed[field] = self._normalize_numeric(transformed[field])
            
            # Clean text fields
            for field in ['source', 'medium', 'campaign']:
                if field in transformed:
                    transformed[field] = self._normalize_text(transformed[field])
            
            return transformed
            
        except Exception as e:
            logger.error(f"Error in marketing leads transformation: {e}")
            return transformed  # Return partially transformed data
    
    def validate_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate marketing leads record with business rules
        
        Args:
            record: Transformed record
            
        Returns:
            Validated record
        """
        # Start with base validation
        validated = super().validate_record(record)
        
        try:
            # Marketing-specific validation
            
            # Validate required fields (based on what we expect)
            if not validated.get('date'):
                logger.warning(f"Record missing date: {validated.get('raw_data', {})}")
            
            # Validate numeric fields are reasonable
            if validated.get('leads'):
                try:
                    leads_num = float(validated['leads'].replace(',', '') if isinstance(validated['leads'], str) else validated['leads'])
                    if leads_num < 0:
                        logger.warning(f"Negative leads count: {leads_num}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid leads value: {validated.get('leads')}")
            
            if validated.get('cost'):
                try:
                    cost_num = float(validated['cost'].replace(',', '').replace('$', '') if isinstance(validated['cost'], str) else validated['cost'])
                    if cost_num < 0:
                        logger.warning(f"Negative cost: {cost_num}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid cost value: {validated.get('cost')}")
            
            return validated
            
        except Exception as e:
            logger.error(f"Error in marketing leads validation: {e}")
            return validated
    
    def _normalize_date(self, date_value: Any) -> str:
        """
        Normalize date field to consistent format
        
        Args:
            date_value: Raw date value
            
        Returns:
            Normalized date string
        """
        if not date_value:
            return ''
        
        date_str = str(date_value).strip()
        
        if not date_str:
            return ''
        
        # Try to parse and reformat common date formats
        try:
            # Handle various date formats
            for date_format in ['%Y-%m-%d', '%m/%d/%Y', '%d/%m/%Y', '%Y/%m/%d', '%m-%d-%Y']:
                try:
                    parsed_date = datetime.strptime(date_str, date_format)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # If no format matches, return as-is
            logger.debug(f"Could not parse date format: {date_str}")
            return date_str
            
        except Exception as e:
            logger.warning(f"Error normalizing date {date_value}: {e}")
            return date_str
    
    def _normalize_numeric(self, numeric_value: Any) -> str:
        """
        Normalize numeric field (leads, cost) to consistent format
        
        Args:
            numeric_value: Raw numeric value
            
        Returns:
            Normalized numeric string
        """
        if not numeric_value:
            return ''
        
        numeric_str = str(numeric_value).strip()
        
        if not numeric_str:
            return ''
        
        try:
            # Remove common formatting characters
            cleaned = numeric_str.replace(',', '').replace('$', '').replace('%', '').strip()
            
            # Try to convert to float and back to remove extra formatting
            if cleaned:
                num = float(cleaned)
                # Keep original format for display but ensure it's valid
                return str(num) if num == int(num) else str(num)
            
            return ''
            
        except (ValueError, TypeError):
            # If can't convert to number, return as-is
            logger.debug(f"Could not normalize numeric value: {numeric_value}")
            return numeric_str
    
    def _normalize_text(self, text_value: Any) -> str:
        """
        Normalize text field to consistent format
        
        Args:
            text_value: Raw text value
            
        Returns:
            Normalized text string
        """
        if not text_value:
            return ''
        
        text_str = str(text_value).strip()
        
        # Basic text cleaning
        # Remove extra whitespace
        text_str = ' '.join(text_str.split())
        
        # Convert to title case for consistency (optional)
        # text_str = text_str.title()
        
        return text_str
    
    def get_summary_stats(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Get summary statistics for processed marketing leads data
        
        Args:
            records: List of processed records
            
        Returns:
            Summary statistics
        """
        try:
            if not records:
                return {
                    'total_records': 0,
                    'date_range': None,
                    'sources': [],
                    'total_leads': 0,
                    'total_cost': 0
                }
            
            # Extract summary info
            dates = []
            sources = set()
            total_leads = 0
            total_cost = 0
            
            for record in records:
                # Collect dates
                if record.get('date'):
                    dates.append(record['date'])
                
                # Collect sources
                if record.get('source'):
                    sources.add(record['source'])
                
                # Sum leads
                if record.get('leads'):
                    try:
                        leads_num = float(str(record['leads']).replace(',', ''))
                        total_leads += leads_num
                    except (ValueError, TypeError):
                        pass
                
                # Sum cost
                if record.get('cost'):
                    try:
                        cost_num = float(str(record['cost']).replace(',', '').replace('$', ''))
                        total_cost += cost_num
                    except (ValueError, TypeError):
                        pass
            
            # Date range
            date_range = None
            if dates:
                sorted_dates = sorted(dates)
                if len(sorted_dates) == 1:
                    date_range = sorted_dates[0]
                else:
                    date_range = f"{sorted_dates[0]} to {sorted_dates[-1]}"
            
            return {
                'total_records': len(records),
                'date_range': date_range,
                'unique_sources': list(sources),
                'source_count': len(sources),
                'total_leads': total_leads,
                'total_cost': total_cost,
                'avg_cost_per_lead': total_cost / total_leads if total_leads > 0 else 0
            }
            
        except Exception as e:
            logger.error(f"Error calculating summary stats: {e}")
            return {
                'total_records': len(records),
                'error': str(e)
            }
