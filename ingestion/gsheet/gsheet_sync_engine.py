"""
Google Sheets Sync Engine

Core sync engine for Google Sheets data following sync_crm_guide.md patterns.
Handles data transformation, deduplication, and database operations.
"""
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from django.db import transaction
from django.utils import timezone

from ingestion.base.sync_engine import BaseSyncEngine
from ingestion.base.exceptions import SyncError, ValidationError
from ingestion.gsheet.gsheet_client import GSheetClient
from ingestion.models.gsheet import GSheet_Lead, GSheet_Contact, GSheet_SheetInfo
from ingestion.config.gsheet_config import GSheetConfig


logger = logging.getLogger(__name__)


class GSheetSyncEngine(BaseSyncEngine):
    """
    Google Sheets sync engine following sync_crm_guide.md patterns
    
    Handles:
    - Data extraction from Google Sheets
    - Data transformation and mapping
    - Database synchronization
    - Deduplication and conflict resolution
    """
    
    def __init__(self, config: GSheetConfig = None):
        """
        Initialize Google Sheets sync engine
        
        Args:
            config: GSheetConfig instance
        """
        super().__init__()
        self.config = config or GSheetConfig()
        self.client = GSheetClient(self.config)
        self.sheet_id = None
        self.sheet_metadata = None
        self.field_mappings = {}
        
    def configure_sheet(self, sheet_url_or_id: str, model_type: str = 'lead',
                       custom_mappings: Dict[str, str] = None) -> Dict[str, Any]:
        """
        Configure sync for a specific Google Sheet
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            model_type: 'lead' or 'contact' - determines target model
            custom_mappings: Custom field mappings (header -> field_name)
            
        Returns:
            Configuration summary
        """
        try:
            # Extract sheet ID and get metadata
            self.sheet_id = self.client._extract_sheet_id(sheet_url_or_id)
            self.sheet_metadata = self.client.get_sheet_metadata(sheet_url_or_id)
            
            # Analyze sheet structure
            structure = self.client.get_sheet_structure(sheet_url_or_id)
            
            # Set up field mappings
            if custom_mappings:
                self.field_mappings = custom_mappings
            else:
                self.field_mappings = structure['suggested_mappings']
            
            # Store or update sheet info
            sheet_info, created = GSheet_SheetInfo.objects.get_or_create(
                sheet_id=self.sheet_id,
                defaults={
                    'sheet_name': self.sheet_metadata['sheets'][0]['title'],
                    'sheet_title': self.sheet_metadata['title'],
                    'total_rows': structure['total_rows'],
                    'total_columns': structure['total_columns'],
                    'column_headers': structure['headers'],
                    'field_mappings': self.field_mappings,
                }
            )
            
            if not created:
                # Update existing info
                sheet_info.sheet_title = self.sheet_metadata['title']
                sheet_info.total_rows = structure['total_rows']
                sheet_info.total_columns = structure['total_columns']
                sheet_info.column_headers = structure['headers']
                sheet_info.field_mappings = self.field_mappings
                sheet_info.save()
            
            config_summary = {
                'sheet_id': self.sheet_id,
                'sheet_title': self.sheet_metadata['title'],
                'model_type': model_type,
                'total_rows': structure['total_rows'],
                'headers': structure['headers'],
                'field_mappings': self.field_mappings,
                'mapped_fields': len(self.field_mappings),
                'unmapped_headers': [h for h in structure['headers'] if h not in self.field_mappings]
            }
            
            logger.info(f"Configured sheet sync: {config_summary['sheet_title']}")
            return config_summary
            
        except Exception as e:
            logger.error(f"Failed to configure sheet: {e}")
            raise SyncError(f"Sheet configuration failed: {e}")
    
    def sync_leads(self, batch_size: int = 1000, start_row: int = 2,
                  dry_run: bool = False) -> Dict[str, Any]:
        """
        Sync lead data from Google Sheets
        
        Args:
            batch_size: Number of rows to process per batch
            start_row: Row number to start sync from (1-based)
            dry_run: If True, validate but don't save to database
            
        Returns:
            Sync results summary
        """
        if not self.sheet_id:
            raise SyncError("Sheet not configured. Call configure_sheet() first.")
        
        sync_stats = {
            'total_processed': 0,
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': [],
            'start_time': timezone.now(),
            'dry_run': dry_run
        }
        
        try:
            # Get headers
            headers = self.client.get_sheet_values(
                self.sheet_id, 
                range_name='1:1'
            )[0]
            
            # Process data in batches
            for batch_data in self.client.get_batch_data(
                self.sheet_id, 
                batch_size=batch_size,
                start_row=start_row
            ):
                batch_stats = self._process_lead_batch(
                    headers, batch_data, dry_run, start_row + sync_stats['total_processed']
                )
                
                # Update cumulative stats
                for key in ['created', 'updated', 'skipped', 'errors']:
                    sync_stats[key] += batch_stats[key]
                
                sync_stats['total_processed'] += len(batch_data)
                sync_stats['error_details'].extend(batch_stats['error_details'])
                
                logger.info(f"Processed batch: {len(batch_data)} rows, "
                          f"Total: {sync_stats['total_processed']}")
            
            # Update sheet info
            if not dry_run:
                sheet_info = GSheet_SheetInfo.objects.get(sheet_id=self.sheet_id)
                sheet_info.last_sync_at = timezone.now()
                sheet_info.last_sync_rows = sync_stats['total_processed']
                sheet_info.save()
            
            sync_stats['end_time'] = timezone.now()
            sync_stats['duration'] = (sync_stats['end_time'] - sync_stats['start_time']).total_seconds()
            
            logger.info(f"Sync completed: {sync_stats}")
            return sync_stats
            
        except Exception as e:
            logger.error(f"Sync failed: {e}")
            sync_stats['end_time'] = timezone.now()
            sync_stats['fatal_error'] = str(e)
            raise SyncError(f"Lead sync failed: {e}")
    
    def _process_lead_batch(self, headers: List[str], batch_data: List[List[str]],
                           dry_run: bool, start_row_num: int) -> Dict[str, Any]:
        """
        Process a batch of lead data
        
        Args:
            headers: Column headers
            batch_data: Rows of data
            dry_run: If True, don't save to database
            start_row_num: Starting row number for this batch
            
        Returns:
            Batch processing stats
        """
        batch_stats = {
            'created': 0,
            'updated': 0,
            'skipped': 0,
            'errors': 0,
            'error_details': []
        }
        
        for row_index, row_data in enumerate(batch_data):
            row_num = start_row_num + row_index
            
            try:
                # Transform row data to lead object
                lead_data = self._transform_row_to_lead(headers, row_data, row_num)
                
                if not lead_data:
                    batch_stats['skipped'] += 1
                    continue
                
                if dry_run:
                    # Validate without saving
                    lead = GSheet_Lead(**lead_data)
                    lead.full_clean()  # Django validation
                    batch_stats['created'] += 1
                else:
                    # Save to database
                    lead, created = GSheet_Lead.objects.update_or_create(
                        sheet_row_id=lead_data['sheet_row_id'],
                        defaults=lead_data
                    )
                    
                    if created:
                        batch_stats['created'] += 1
                    else:
                        batch_stats['updated'] += 1
            
            except Exception as e:
                batch_stats['errors'] += 1
                error_detail = {
                    'row_number': row_num,
                    'error': str(e),
                    'row_data': row_data[:5]  # First 5 columns for context
                }
                batch_stats['error_details'].append(error_detail)
                logger.warning(f"Error processing row {row_num}: {e}")
        
        return batch_stats
    
    def _transform_row_to_lead(self, headers: List[str], row_data: List[str],
                              row_num: int) -> Optional[Dict[str, Any]]:
        """
        Transform a sheet row to lead model data
        
        Args:
            headers: Column headers
            row_data: Row cell values
            row_num: Row number
            
        Returns:
            Lead model data dict or None if row should be skipped
        """
        # Skip empty rows
        if not any(str(cell).strip() for cell in row_data):
            return None
        
        # Create row data dict
        row_dict = {}
        for i, header in enumerate(headers):
            if i < len(row_data):
                row_dict[header] = str(row_data[i]).strip() if row_data[i] else ''
            else:
                row_dict[header] = ''
        
        # Transform to lead data
        lead_data = {
            'sheet_id': self.sheet_id,
            'row_number': row_num,
            'sheet_row_id': f"{self.sheet_id}_{row_num}",
            'raw_data': row_dict,
            'field_mappings': self.field_mappings,
        }
        
        # Map fields based on field_mappings
        for header, field_name in self.field_mappings.items():
            if header in row_dict and hasattr(GSheet_Lead, field_name):
                value = row_dict[header]
                
                # Apply field-specific transformations
                transformed_value = self._transform_field_value(field_name, value)
                if transformed_value is not None:
                    lead_data[field_name] = transformed_value
        
        # Handle unmapped fields in custom fields
        unmapped_headers = [h for h in headers if h not in self.field_mappings]
        custom_field_num = 1
        
        for header in unmapped_headers[:5]:  # Up to 5 custom fields
            if header in row_dict and row_dict[header]:
                custom_field_name = f"custom_field_{custom_field_num}"
                lead_data[custom_field_name] = f"{header}: {row_dict[header]}"
                custom_field_num += 1
        
        # Generate full_name if not mapped but first/last names are available
        if ('full_name' not in lead_data and 
            'first_name' in lead_data and 'last_name' in lead_data):
            first = lead_data.get('first_name', '').strip()
            last = lead_data.get('last_name', '').strip()
            if first or last:
                lead_data['full_name'] = f"{first} {last}".strip()
        
        return lead_data
    
    def _transform_field_value(self, field_name: str, value: str) -> Any:
        """
        Transform field value based on field type
        
        Args:
            field_name: Target model field name
            value: Raw value from sheet
            
        Returns:
            Transformed value or None if invalid
        """
        if not value or not str(value).strip():
            return None
        
        value = str(value).strip()
        
        # Email validation
        if field_name == 'email':
            if '@' in value and '.' in value:
                return value.lower()
            return None
        
        # Phone number cleaning
        if 'phone' in field_name:
            # Remove non-digit characters except + and -
            import re
            cleaned = re.sub(r'[^\d+\-\(\)\s]', '', value)
            if len(re.sub(r'[^\d]', '', cleaned)) >= 7:  # At least 7 digits
                return cleaned
            return None
        
        # Numeric fields
        if field_name in ['lead_score', 'estimated_value', 'budget']:
            try:
                # Remove currency symbols and commas
                import re
                numeric_str = re.sub(r'[^\d.-]', '', value)
                if '.' in numeric_str:
                    return float(numeric_str)
                else:
                    return int(numeric_str)
            except ValueError:
                return None
        
        # Date fields
        if 'date' in field_name:
            return self._parse_date(value)
        
        # String fields with length limits
        string_field_limits = {
            'first_name': 100,
            'last_name': 100,
            'full_name': 200,
            'city': 100,
            'state': 50,
            'zip_code': 20,
            'country': 100,
            'company': 255,
            'title': 100,
            'industry': 100,
            'lead_status': 100,
            'lead_source': 100,
            'campaign': 255,
            'utm_source': 255,
            'utm_medium': 255,
            'utm_campaign': 255,
        }
        
        if field_name in string_field_limits:
            max_length = string_field_limits[field_name]
            return value[:max_length] if len(value) > max_length else value
        
        # Default: return as string
        return value
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """
        Parse date string to datetime object
        
        Args:
            date_str: Date string in various formats
            
        Returns:
            Parsed datetime or None if invalid
        """
        if not date_str:
            return None
        
        # Common date formats
        date_formats = [
            '%Y-%m-%d',
            '%m/%d/%Y',
            '%d/%m/%Y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%dT%H:%M:%SZ',
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
        
        # Try to parse with dateutil if available
        try:
            from dateutil.parser import parse
            return parse(date_str)
        except:
            return None
    
    def get_sync_status(self) -> Dict[str, Any]:
        """
        Get current sync status for configured sheet
        
        Returns:
            Sync status information
        """
        if not self.sheet_id:
            return {'error': 'No sheet configured'}
        
        try:
            sheet_info = GSheet_SheetInfo.objects.get(sheet_id=self.sheet_id)
            lead_count = GSheet_Lead.objects.filter(sheet_id=self.sheet_id).count()
            
            return {
                'sheet_id': self.sheet_id,
                'sheet_title': sheet_info.sheet_title,
                'total_sheet_rows': sheet_info.total_rows,
                'synced_leads': lead_count,
                'last_sync': sheet_info.last_sync_at,
                'sync_enabled': sheet_info.sync_enabled,
                'field_mappings': sheet_info.field_mappings,
            }
        except GSheet_SheetInfo.DoesNotExist:
            return {'error': 'Sheet not found in database'}
    
    def validate_sheet_access(self, sheet_url_or_id: str) -> Tuple[bool, str]:
        """
        Validate access to a Google Sheet
        
        Args:
            sheet_url_or_id: Google Sheets URL or ID
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        try:
            metadata = self.client.get_sheet_metadata(sheet_url_or_id)
            structure = self.client.get_sheet_structure(sheet_url_or_id)
            
            if structure['total_rows'] == 0:
                return False, "Sheet appears to be empty"
            
            if len(structure['headers']) == 0:
                return False, "No headers found in first row"
            
            return True, f"Successfully accessed sheet: {metadata['title']}"
            
        except Exception as e:
            return False, f"Access validation failed: {e}"
