"""
Google Sheets Models

Django models for storing Google Sheets data following sync_crm_guide.md patterns.
Designed for flexibility to handle various sheet structures.
"""
from django.db import models
from django.utils import timezone


class GSheet_Lead(models.Model):
    """
    Google Sheets lead data model following sync_crm_guide.md patterns
    
    Designed to be flexible for various Google Sheets lead structures
    with common fields that typically appear in lead sheets.
    """
    
    # Primary identification
    sheet_row_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier: sheet_id + row_number"
    )
    sheet_id = models.CharField(
        max_length=100,
        help_text="Google Sheets document ID"
    )
    row_number = models.IntegerField(
        help_text="Row number in the sheet (1-based)"
    )
    
    # Standard lead fields (commonly found in lead sheets)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Contact information
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=50, blank=True, null=True)
    mobile = models.CharField(max_length=50, blank=True, null=True)
    
    # Address information
    address = models.TextField(blank=True, null=True)
    street = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Lead qualification
    lead_status = models.CharField(max_length=100, blank=True, null=True)
    lead_source = models.CharField(max_length=100, blank=True, null=True)
    lead_score = models.IntegerField(blank=True, null=True)
    
    # Business information
    company = models.CharField(max_length=255, blank=True, null=True)
    title = models.CharField(max_length=100, blank=True, null=True)
    industry = models.CharField(max_length=100, blank=True, null=True)
    
    # Financial information
    estimated_value = models.DecimalField(
        max_digits=15, decimal_places=2, 
        blank=True, null=True
    )
    budget = models.DecimalField(
        max_digits=15, decimal_places=2, 
        blank=True, null=True
    )
    
    # Dates
    created_date = models.DateTimeField(blank=True, null=True)
    updated_date = models.DateTimeField(blank=True, null=True)
    follow_up_date = models.DateTimeField(blank=True, null=True)
    
    # Notes and additional information
    notes = models.TextField(blank=True, null=True)
    comments = models.TextField(blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    
    # Campaign and tracking
    campaign = models.CharField(max_length=255, blank=True, null=True)
    utm_source = models.CharField(max_length=255, blank=True, null=True)
    utm_medium = models.CharField(max_length=255, blank=True, null=True)
    utm_campaign = models.CharField(max_length=255, blank=True, null=True)
    
    # Custom fields (for flexible sheet structures)
    custom_field_1 = models.TextField(blank=True, null=True)
    custom_field_2 = models.TextField(blank=True, null=True)
    custom_field_3 = models.TextField(blank=True, null=True)
    custom_field_4 = models.TextField(blank=True, null=True)
    custom_field_5 = models.TextField(blank=True, null=True)
    
    # Metadata for sync tracking
    raw_data = models.JSONField(
        default=dict,
        help_text="Complete raw row data from Google Sheets"
    )
    field_mappings = models.JSONField(
        default=dict,
        help_text="Column header to field mappings used during import"
    )
    
    # Sync management (following sync_crm_guide.md patterns)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_gsheet_lead'
        verbose_name = 'Google Sheets Lead'
        verbose_name_plural = 'Google Sheets Leads'
        
        indexes = [
            models.Index(fields=['sheet_id'], name='gsheet_lead_sheet_id_idx'),
            models.Index(fields=['email'], name='gsheet_lead_email_idx'),
            models.Index(fields=['phone'], name='gsheet_lead_phone_idx'),
            models.Index(fields=['lead_status'], name='gsheet_lead_status_idx'),
            models.Index(fields=['lead_source'], name='gsheet_lead_source_idx'),
            models.Index(fields=['created_date'], name='gsheet_lead_created_idx'),
            models.Index(fields=['imported_at'], name='gsheet_lead_imported_idx'),
        ]
        
        constraints = [
            models.UniqueConstraint(
                fields=['sheet_id', 'row_number'],
                name='unique_sheet_row'
            )
        ]
    
    def __str__(self):
        name = self.full_name or f"{self.first_name or ''} {self.last_name or ''}".strip()
        if name:
            return f"{name} (Row {self.row_number})"
        return f"Sheet Row {self.row_number}"
    
    def save(self, *args, **kwargs):
        """Override save to generate sheet_row_id"""
        if not self.sheet_row_id:
            self.sheet_row_id = f"{self.sheet_id}_{self.row_number}"
        super().save(*args, **kwargs)
    
    @property
    def display_name(self):
        """Get display name for the lead"""
        if self.full_name:
            return self.full_name
        
        parts = []
        if self.first_name:
            parts.append(self.first_name)
        if self.last_name:
            parts.append(self.last_name)
        
        if parts:
            return ' '.join(parts)
        
        return self.email or f"Row {self.row_number}"
    
    @property
    def contact_info(self):
        """Get primary contact information"""
        contacts = []
        if self.email:
            contacts.append(f"Email: {self.email}")
        if self.phone:
            contacts.append(f"Phone: {self.phone}")
        return " | ".join(contacts) if contacts else "No contact info"


class GSheet_Contact(models.Model):
    """
    Alternative model for contact-focused Google Sheets
    
    This model is optimized for sheets that primarily contain contact information
    rather than lead qualification data.
    """
    
    # Primary identification
    sheet_row_id = models.CharField(
        max_length=50,
        unique=True,
        help_text="Unique identifier: sheet_id + row_number"
    )
    sheet_id = models.CharField(max_length=100)
    row_number = models.IntegerField()
    
    # Core contact fields
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    display_name = models.CharField(max_length=200, blank=True, null=True)
    
    # Contact details
    email_primary = models.EmailField(max_length=254, blank=True, null=True)
    email_secondary = models.EmailField(max_length=254, blank=True, null=True)
    phone_primary = models.CharField(max_length=50, blank=True, null=True)
    phone_secondary = models.CharField(max_length=50, blank=True, null=True)
    
    # Professional information
    company_name = models.CharField(max_length=255, blank=True, null=True)
    job_title = models.CharField(max_length=100, blank=True, null=True)
    department = models.CharField(max_length=100, blank=True, null=True)
    
    # Address
    mailing_address = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state_province = models.CharField(max_length=50, blank=True, null=True)
    postal_code = models.CharField(max_length=20, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Metadata
    raw_data = models.JSONField(default=dict)
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_gsheet_contact'
        verbose_name = 'Google Sheets Contact'
        verbose_name_plural = 'Google Sheets Contacts'
        
        indexes = [
            models.Index(fields=['sheet_id'], name='gsheet_contact_sheet_id_idx'),
            models.Index(fields=['email_primary'], name='gsheet_contact_email_idx'),
            models.Index(fields=['company_name'], name='gsheet_contact_company_idx'),
        ]
    
    def save(self, *args, **kwargs):
        if not self.sheet_row_id:
            self.sheet_row_id = f"{self.sheet_id}_{self.row_number}"
        super().save(*args, **kwargs)


class GSheet_SheetInfo(models.Model):
    """
    Metadata about synced Google Sheets
    
    Tracks information about each sheet being synced for monitoring
    and configuration purposes.
    """
    
    sheet_id = models.CharField(max_length=100, unique=True)
    sheet_name = models.CharField(max_length=255)
    sheet_title = models.CharField(max_length=255, blank=True, null=True)
    
    # Sheet structure info
    total_rows = models.IntegerField(default=0)
    total_columns = models.IntegerField(default=0)
    header_row = models.IntegerField(default=1)
    data_start_row = models.IntegerField(default=2)
    
    # Column mappings
    column_headers = models.JSONField(
        default=list,
        help_text="List of column headers found in the sheet"
    )
    field_mappings = models.JSONField(
        default=dict,
        help_text="Mapping of sheet columns to model fields"
    )
    
    # Sync status
    last_sync_at = models.DateTimeField(blank=True, null=True)
    last_sync_rows = models.IntegerField(default=0)
    sync_enabled = models.BooleanField(default=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_gsheet_sheet_info'
        verbose_name = 'Google Sheet Info'
        verbose_name_plural = 'Google Sheets Info'
    
    def __str__(self):
        return f"{self.sheet_title or self.sheet_name} ({self.sheet_id[:8]}...)"
