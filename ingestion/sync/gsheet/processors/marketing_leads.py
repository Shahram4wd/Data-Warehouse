"""
Marketing Leads Google Sheets Processor
"""
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from django.utils import timezone

from .base import BaseGoogleSheetsProcessor

logger = logging.getLogger(__name__)


class MarketingLeadsProcessor(BaseGoogleSheetsProcessor):
    """
    Processor for Marketing Source Leads Google Sheet data
    
    Handles transformation and validation of marketing leads data
    from Google Sheets to the database model.
    """
    def __init__(self, *args, **kwargs):
        """Initialize processor and cache expensive metadata."""
        super().__init__(*args, **kwargs)
        self._cached_field_max_lengths: Optional[Dict[str, int]] = None
    
    def get_field_mappings(self) -> Dict[str, str]:
        """
        Field mappings specific to Marketing Leads sheet
        Maps Google Sheet column names to Django model field names
        """
        return {
            # Contact Information
            'first_name': 'first_name',
            'last_name': 'last_name', 
            'phone_number': 'phone_number',
            'email_address': 'email_address',
            
            # Timestamp
            # Map the sheet's `created_at` column into the model `lead_created_at`
            # to avoid clobbering the DB-created `created_at` timestamp.
            'created_at': 'lead_created_at',
            
            # UTM Campaign Data
            'utm_campaign': 'utm_campaign',
            'utm_term': 'utm_term',
            'utm_content': 'utm_content',
            
            # Page and Source Information
            'page_source_name': 'page_source_name',
            'page_url': 'page_url',
            'variant': 'variant',
            
            # Click and Tracking Data
            'click_id': 'click_id',
            'click_type': 'click_type',
            
            # Geographic and Division
            'division': 'division',
            'form_submit_zipcode': 'form_submit_zipcode',
            'marketing_zip_check': 'marketing_zip_check',
            
            # Lead Classification
            'lead_type': 'lead_type',
            'connection_status': 'connection_status',
            'contact_reason': 'contact_reason',
            
            # Lead Setting Status
            'lead_set': 'lead_set',
            'no_set_reason': 'no_set_reason',
            
            # Call Details
            'recording_duration': 'recording_duration',
            'hold_time': 'hold_time',
            'first_call_date_time': 'first_call_date_time',
            'call_attempts': 'call_attempts',
            'after_hours': 'after_hours',
            'call_notes': 'call_notes',
            'call_recording': 'call_recording',
            
            # Management and Follow-up
            'manager_followup': 'manager_followup',
            'callback_review': 'callback_review',
            'call_center': 'call_center',
            'Multiple Inquiry': 'multiple_inquiry',
            
            # Appointment Information
            'preferred_appt_date': 'preferred_appt_date',
            'Appt Set By': 'appt_set_by',
            'Set Appt Date': 'set_appt_date',
            'Appt Date-Time': 'appt_date_time',
            'Appt Result': 'appt_result',
            'Appt Result Reason': 'appt_result_reason',
            'Appt Attempts': 'appt_attempts',
            'appointment_outcome': 'appointment_outcome',
            'appointment_outcome_type': 'appointment_outcome_type',
            'spouses_present': 'spouses_present',
            
            # Marketing Keywords and Ad Groups
            'keyword': 'keyword',
            'adgroup_name': 'adgroup_name',
            'adgroup_id': 'adgroup_id',
            
            # CSR and Disposition
            'csr_disposition': 'csr_disposition',
            
            # F9 System Data
            'f9_list_name': 'f9_list_name',
            'f9_last_campaign': 'f9_last_campaign',
            'f9_sys_created_date': 'f9_sys_created_date',
            
            # Address and Job Information
            'MarketSharp Address': 'marketsharp_address',
            'Total Job Value': 'total_job_value',
            'Cancel Job Value': 'cancel_job_value',
            
            # System Integration Fields
            'Genius Division': 'genius_division',
            'Genius Marketing Source': 'genius_marketing_source',
            'MarketSharp Source': 'marketsharp_source',
            
            # Event Information
            'event_show_type': 'event_show_type',
            'event_show_name': 'event_show_name',
            
            # Campaign Rename
            'google_ads_campaign_rename': 'google_ads_campaign_rename',
            
            # Marketing Channel
            'marketing_channel': 'marketing_channel',
        }
    
    def process_row_sync(self, row_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a single row from Google Sheets synchronously
        
        Args:
            row_data: Raw row data from Google Sheets
            
        Returns:
            Processed data ready for model creation
        """
        try:
            processed_data = {}
            field_mappings = self.get_field_mappings()
            
            # Map fields from sheet columns to model fields
            for sheet_col, model_field in field_mappings.items():
                if sheet_col in row_data and model_field:
                    value = row_data[sheet_col]
                    
                    # Skip empty values
                    if value is None or (isinstance(value, str) and value.strip() == ''):
                        continue
                        
                    # Process value based on field type
                    processed_value = self._process_field_value(model_field, value)
                    if processed_value is not None:
                        processed_data[model_field] = processed_value
            
            # Add metadata
            processed_data['sheet_row_number'] = row_data.get('sheet_row_number', 0)
            processed_data['sheet_last_modified'] = timezone.now()
            processed_data['raw_data'] = row_data
            
            # Use the existing transform_record method but indicate this is already field-mapped
            processed_data['_already_field_mapped'] = True
            processed_data = self.transform_record(processed_data)
            del processed_data['_already_field_mapped']  # Remove the flag
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing row: {e}")
            logger.error(f"Row data: {row_data}")
            return None
    
    def _process_field_value(self, field_name: str, value: Any) -> Any:
        """
        Process individual field values based on their expected type
        """
        if value is None or (isinstance(value, str) and value.strip() == ''):
            return None
            
        try:
            # Handle boolean fields early to avoid extra transform passes
            if field_name in ['lead_set', 'manager_followup', 'multiple_inquiry', 'spouses_present']:
                return self._parse_boolean(value)

            # Handle datetime fields
            if field_name in ['lead_created_at', 'first_call_date_time', 'appt_date_time', 'f9_sys_created_date']:
                return self._parse_datetime(value)
            
            # Handle date fields
            elif field_name in ['preferred_appt_date', 'set_appt_date']:
                return self._parse_date(value)
            
            # Handle integer fields
            elif field_name in ['recording_duration', 'hold_time', 'call_attempts', 'appt_attempts', 'sheet_row_number']:
                return self._parse_integer(value)
            
            # Handle decimal fields
            elif field_name in ['total_job_value', 'cancel_job_value']:
                return self._parse_decimal(value)
            
            # Handle string fields (default) with length validation
            else:
                processed_value = str(value).strip() if value else None
                if processed_value:
                    # Check for common field length limits and truncate if necessary
                    max_lengths = self._get_field_max_lengths()
                    if field_name in max_lengths:
                        max_length = max_lengths[field_name]
                        if len(processed_value) > max_length:
                            logger.warning(f"Field '{field_name}' value truncated from {len(processed_value)} to {max_length} chars. "
                                         f"Original: '{processed_value[:100]}...'")
                            processed_value = processed_value[:max_length]
                    
                return processed_value
                
        except Exception as e:
            logger.warning(f"Error processing field {field_name} with value {value}: {e}")
            return None

    def _get_field_max_lengths(self) -> Dict[str, int]:
        """
        Get maximum field lengths from the model
        
        Returns:
            Dictionary mapping field names to max lengths
        """
        # Cache the result to avoid per-field introspection overhead
        if self._cached_field_max_lengths is not None:
            return self._cached_field_max_lengths

        from ingestion.models.gsheet import GoogleSheetMarketingLead

        max_lengths: Dict[str, int] = {}
        for field in GoogleSheetMarketingLead._meta.fields:
            if hasattr(field, 'max_length') and field.max_length:
                max_lengths[field.name] = field.max_length

        self._cached_field_max_lengths = max_lengths
        return self._cached_field_max_lengths
    
    def _parse_datetime(self, value: Any) -> Optional[datetime]:
        """Parse datetime from various formats"""
        if not value:
            return None

        try:
            if isinstance(value, datetime):
                return timezone.make_aware(value) if timezone.is_naive(value) else value

            # Normalize to string once
            s = str(value).strip()

            # Fast path: ISO 8601 via fromisoformat, with 'Z' handling
            try:
                iso_str = s[:-1] + '+00:00' if s.endswith('Z') else s
                dt = datetime.fromisoformat(iso_str)
                return timezone.make_aware(dt) if timezone.is_naive(dt) else dt
            except Exception:
                pass

            # Try common datetime formats (ordered by likelihood) with minimal throws
            formats = [
                '%Y-%m-%d %H:%M:%S',       # 2023-11-01 07:40:08
                '%m/%d/%Y %H:%M:%S',       # 11/1/2023 7:40:08
                '%Y-%m-%d %H:%M:%S',       # 2023-11-01 07:40:08
                '%Y-%m-%dT%H:%M:%S%z',     # 2023-11-01T07:40:08+00:00 (ISO format with timezone)
                '%Y-%m-%dT%H:%M:%S.%f%z',  # 2023-11-01T07:40:08.123456+00:00 (ISO with microseconds)
                '%Y-%m-%dT%H:%M:%S',       # 2023-11-01T07:40:08 (ISO without timezone)
                '%m/%d/%Y %H:%M',          # 11/1/2023 7:40
                '%Y-%m-%d',                # 2023-11-01
                '%m/%d/%Y',                # 11/1/2023
            ]

            for fmt in formats:
                try:
                    dt = datetime.strptime(s, fmt)
                    # If the datetime already has timezone info (from %z), don't make it aware
                    if dt.tzinfo is not None:
                        return dt
                    else:
                        return timezone.make_aware(dt)
                except ValueError:
                    continue

        except Exception as e:
            logger.warning(f"Could not parse datetime: {value} - {e}")

        return None
    
    def _parse_date(self, value: Any) -> Optional[datetime]:
        """Parse date from various formats"""
        dt = self._parse_datetime(value)
        return dt.date() if dt else None
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """Parse integer values"""
        if not value:
            return None
            
        try:
            # Remove any non-numeric characters except minus
            clean_value = str(value).replace(',', '').replace('$', '').strip()
            return int(float(clean_value))  # Convert to float first to handle "123.0"
        except (ValueError, TypeError):
            return None
    
    def _parse_decimal(self, value: Any) -> Optional[float]:
        """Parse decimal values"""
        if not value:
            return None
            
        try:
            # Remove any non-numeric characters except decimal point and minus
            clean_value = str(value).replace(',', '').replace('$', '').strip()
            return float(clean_value)
        except (ValueError, TypeError):
            return None
    
    def _parse_boolean(self, value: Any) -> Optional[bool]:
        """Parse boolean values from Google Sheets string values"""
        if value is None or value == '':
            return None
            
        # Convert to string and normalize
        str_value = str(value).strip().lower()
        
        # Common true values
        if str_value in ['yes', 'y', 'true', '1', 'on']:
            return True
        
        # Common false values
        if str_value in ['no', 'n', 'false', '0', 'off']:
            return False
        
        # For numeric values like spouses_present
        try:
            numeric_value = int(float(str_value))
            return numeric_value > 0
        except (ValueError, TypeError):
            pass
        
        # Default to None for unknown values
        logger.warning(f"Unknown boolean value: {value}, treating as None")
        return None
    
    def _serialize_for_json(self, obj: Any) -> Any:
        """Convert objects to JSON-serializable format"""
        from datetime import datetime, date
        import decimal
        
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, decimal.Decimal):
            return float(obj)
        elif isinstance(obj, dict):
            return {k: self._serialize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, (list, tuple)):
            return [self._serialize_for_json(item) for item in obj]
        else:
            return obj
    
    def transform_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform marketing leads record with specific business logic
        
        Args:
            record: Raw record from Google Sheets or already field-mapped data
            
        Returns:
            Transformed record
        """
        # Check if this data is already field-mapped (from process_row_sync)
        if record.get('_already_field_mapped'):
            # Fast path: values already parsed field-by-field in process_row_sync.
            # Avoid re-parsing to reduce per-row overhead.
            transformed = record.copy()
            if 'raw_data' in transformed:
                transformed['raw_data'] = self._serialize_for_json(transformed['raw_data'])
            return transformed
        else:
            # Raw data from Google Sheets, apply base transformation first
            transformed = super().transform_record(record)
        
        try:
            # Define Boolean fields that need special conversion
            boolean_fields = [
                'lead_set',
                'manager_followup', 
                'multiple_inquiry',
                'spouses_present'
            ]
            
            # Convert Boolean fields
            for field in boolean_fields:
                if field in transformed:
                    transformed[field] = self._parse_boolean(transformed[field])
            
            # Parse datetime fields
            datetime_fields = [
                'lead_created_at',
                'first_call_date_time',
                'appt_date_time',
                'f9_sys_created_date'
            ]
            
            for field in datetime_fields:
                if field in transformed:
                    transformed[field] = self._parse_datetime(transformed[field])
            
            # Parse date fields
            date_fields = [
                'preferred_appt_date',
                'set_appt_date'
            ]
            
            for field in date_fields:
                if field in transformed:
                    transformed[field] = self._parse_date(transformed[field])
            
            # Parse integer fields
            integer_fields = [
                'recording_duration',
                'hold_time',
                'call_attempts',
                'appt_attempts'
            ]
            
            for field in integer_fields:
                if field in transformed:
                    transformed[field] = self._parse_integer(transformed[field])
            
            # Parse decimal fields
            decimal_fields = [
                'total_job_value',
                'cancel_job_value'
            ]
            
            for field in decimal_fields:
                if field in transformed:
                    transformed[field] = self._parse_decimal(transformed[field])
            
            # Ensure raw_data is JSON serializable
            if 'raw_data' in transformed:
                transformed['raw_data'] = self._serialize_for_json(transformed['raw_data'])
            
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
