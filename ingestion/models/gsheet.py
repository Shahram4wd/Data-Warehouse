"""
Google Sheets Models

Following CRM sync guide - using global SyncHistory table for sync tracking.
Configuration is hardcoded in engines, not stored in database.
"""
from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone
from decimal import Decimal
import json


class GoogleSheetMarketingLead(models.Model):
    """Marketing leads data from Google Sheets - Complete column mapping"""
    
    # Primary key - using sheet row number as natural primary key
    sheet_row_number = models.PositiveIntegerField(primary_key=True)
    
    # System timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Sheet metadata
    sheet_last_modified = models.DateTimeField(
        null=True, blank=True,
        help_text="Sheet last modification time"
    )
    
    # Lead creation timestamp from sheet
    lead_created_at = models.DateTimeField(null=True, blank=True, help_text="created_at from sheet")
    
    # Contact Information
    first_name = models.CharField(max_length=200, null=True, blank=True)  # was 168, rounded to 200
    last_name = models.CharField(max_length=512, null=True, blank=True)   # was 305, rounded to 512
    phone_number = models.CharField(max_length=20, null=True, blank=True)  # Keep as CharField for phone numbers
    email_address = models.EmailField(null=True, blank=True)
    
    # UTM Campaign Data
    utm_campaign = models.CharField(max_length=200, null=True, blank=True)  # was 142, rounded to 200
    utm_term = models.CharField(max_length=100, null=True, blank=True)      # was 89, rounded to 100
    utm_content = models.CharField(max_length=100, null=True, blank=True)   # was 86, rounded to 100
    
    # Page and Source Information
    page_source_name = models.CharField(max_length=128, null=True, blank=True)  # was 122, power of 2
    page_url = models.URLField(max_length=512, null=True, blank=True)           # was 511, power of 2
    variant = models.CharField(max_length=100, null=True, blank=True)           # was 69, rounded to 100
    
    # Click and Tracking Data
    click_id = models.CharField(max_length=256, null=True, blank=True)   # was 220, power of 2
    click_type = models.CharField(max_length=100, null=True, blank=True) # was 65, rounded to 100
    
    # Geographic and Division
    division = models.CharField(max_length=100, null=True, blank=True)          # was 63, rounded to 100
    form_submit_zipcode = models.CharField(max_length=10, null=True, blank=True) # Keep for zipcodes
    marketing_zip_check = models.CharField(max_length=100, null=True, blank=True) # was 65, rounded to 100
    
    # Lead Classification
    lead_type = models.CharField(max_length=50, null=True, blank=True)           # was 10, rounded to 50
    connection_status = models.CharField(max_length=100, null=True, blank=True)  # was 74, rounded to 100
    contact_reason = models.CharField(max_length=100, null=True, blank=True)     # was 87, rounded to 100
    
    # Lead Setting Status
    lead_set = models.BooleanField(null=True, blank=True)  # Changed to Boolean as per analysis
    no_set_reason = models.CharField(max_length=100, null=True, blank=True)  # was 86, rounded to 100
    
    # Call Details
    recording_duration = models.IntegerField(null=True, blank=True, help_text="Duration in seconds")
    hold_time = models.IntegerField(null=True, blank=True, help_text="Hold time in seconds")
    first_call_date_time = models.DateTimeField(null=True, blank=True)
    call_attempts = models.IntegerField(null=True, blank=True)  # Keep as Integer for counting
    after_hours = models.CharField(max_length=50, null=True, blank=True)  # was 10, rounded to 50
    call_notes = models.TextField(null=True, blank=True)
    call_recording = models.URLField(max_length=200, null=True, blank=True)  # was 167, rounded to 200
    
    # Management and Follow-up
    manager_followup = models.BooleanField(null=True, blank=True)  # Changed to Boolean as per analysis
    callback_review = models.CharField(max_length=100, null=True, blank=True)  # was 80, rounded to 100
    call_center = models.CharField(max_length=100, null=True, blank=True)      # was 61, rounded to 100
    multiple_inquiry = models.BooleanField(null=True, blank=True)  # Changed to Boolean, fixed field name
    
    # Appointment Information
    preferred_appt_date = models.DateField(null=True, blank=True)  # Keep as DateField for dates
    appt_set_by = models.CharField(max_length=100, null=True, blank=True)      # was 86, rounded to 100
    set_appt_date = models.DateField(null=True, blank=True)                   # Keep as DateField for dates
    appt_date_time = models.DateTimeField(null=True, blank=True)
    appt_result = models.CharField(max_length=100, null=True, blank=True)      # was 78, rounded to 100
    appt_result_reason = models.CharField(max_length=100, null=True, blank=True) # was 71, rounded to 100
    appt_attempts = models.IntegerField(null=True, blank=True)                 # Changed to Integer for counting
    appointment_outcome = models.CharField(max_length=100, null=True, blank=True)      # was 72, rounded to 100
    appointment_outcome_type = models.CharField(max_length=100, null=True, blank=True) # was 63, rounded to 100
    spouses_present = models.BooleanField(null=True, blank=True)  # Changed to Boolean for Yes/No values
    
    # Marketing Keywords and Ad Groups
    keyword = models.CharField(max_length=100, null=True, blank=True)     # was 96, rounded to 100
    adgroup_name = models.CharField(max_length=100, null=True, blank=True) # was 89, rounded to 100
    adgroup_id = models.CharField(max_length=100, null=True, blank=True)   # Keep as CharField for IDs
    
    # CSR and Disposition
    csr_disposition = models.CharField(max_length=100, null=True, blank=True)  # was 78, rounded to 100
    
    # F9 System Data
    f9_list_name = models.CharField(max_length=100, null=True, blank=True)     # was 70, rounded to 100
    f9_last_campaign = models.CharField(max_length=100, null=True, blank=True) # was 80, rounded to 100
    f9_sys_created_date = models.DateTimeField(null=True, blank=True)
    
    # Address and Job Information
    marketsharp_address = models.CharField(max_length=200, null=True, blank=True) # was 152, rounded to 200
    total_job_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    cancel_job_value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # System Integration Fields
    genius_division = models.CharField(max_length=100, null=True, blank=True)          # was 63, rounded to 100
    genius_marketing_source = models.CharField(max_length=100, null=True, blank=True)  # was 86, rounded to 100
    marketsharp_source = models.CharField(max_length=128, null=True, blank=True)       # was 109, power of 2
    
    # Event Information
    event_show_type = models.CharField(max_length=50, null=True, blank=True)    # was 10, rounded to 50
    event_show_name = models.CharField(max_length=128, null=True, blank=True)   # was 109, power of 2
    
    # Campaign Rename
    google_ads_campaign_rename = models.CharField(max_length=128, null=True, blank=True)  # was 114, power of 2
    
    # Metadata - preserve original raw data
    raw_data = models.JSONField(
        default=dict,
        help_text="Complete row data from sheet"
    )
    
    
    class Meta:
        db_table = 'ingestion_gsheet_marketing_lead'
        verbose_name = 'Google Sheet Marketing Lead'
        verbose_name_plural = 'Google Sheet Marketing Leads'
        ordering = ['-lead_created_at', '-created_at']
        indexes = [
            # Core lead identification
            models.Index(fields=['phone_number', 'lead_created_at']),
            models.Index(fields=['email_address', 'lead_created_at']),
            models.Index(fields=['first_name', 'last_name']),
            
            # Marketing attribution
            models.Index(fields=['utm_campaign', 'division']),
            models.Index(fields=['genius_marketing_source', 'division']),
            models.Index(fields=['lead_created_at', 'utm_campaign']),
            
            # Lead management
            models.Index(fields=['lead_set', 'division']),
            models.Index(fields=['connection_status', 'lead_type']),
            models.Index(fields=['appt_result', 'appointment_outcome']),
            
            # System fields
            models.Index(fields=['sheet_row_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['lead_created_at']),
            
            # Performance tracking
            models.Index(fields=['division', 'lead_created_at', 'lead_set']),
        ]

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        if name:
            return f"Row {self.sheet_row_number}: {name} - {self.lead_created_at or 'No Date'}"
        else:
            return f"Row {self.sheet_row_number}: {self.phone_number or 'No Phone'} - {self.lead_created_at or 'No Date'}"

    def save(self, *args, **kwargs):
        # Ensure raw_data is properly formatted
        if not isinstance(self.raw_data, dict):
            self.raw_data = {}
        super().save(*args, **kwargs)

    @property
    def full_name(self):
        """Get full name from first and last name"""
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
    
    @property
    def is_appointment_set(self):
        """Check if appointment was successfully set"""
        return bool(self.lead_set)
    
    @property
    def has_contact_info(self):
        """Check if lead has usable contact information"""
        return bool(self.phone_number or self.email_address)


class GoogleSheetMarketingSpend(models.Model):
    """Marketing spends data from Google Sheets"""
    
    # Primary key - using sheet row number as natural primary key
    sheet_row_number = models.PositiveIntegerField(primary_key=True)
    
    # System timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Sheet metadata
    sheet_last_modified = models.DateTimeField(
        null=True, blank=True,
        help_text="Sheet last modification time"
    )
    
    # Marketing spend data
    spend_date = models.DateField(null=True, blank=True, help_text="Date of marketing spend")
    cost = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True, help_text="Marketing cost amount")
    division = models.CharField(max_length=50, null=True, blank=True, help_text="Marketing division")
    channel = models.CharField(max_length=50, null=True, blank=True, help_text="Marketing channel")
    campaign = models.CharField(max_length=100, null=True, blank=True, help_text="Marketing campaign name")
    event_start_date = models.DateField(null=True, blank=True, help_text="Event start date")
    event_end_date = models.DateField(null=True, blank=True, help_text="Event end date")
    
    # Metadata - preserve original raw data
    raw_data = models.JSONField(
        default=dict,
        help_text="Complete row data from sheet"
    )
    
    class Meta:
        db_table = 'ingestion_gsheet_marketing_spend'
        verbose_name = 'Google Sheet Marketing Spend'
        verbose_name_plural = 'Google Sheet Marketing Spends'
        ordering = ['-spend_date', '-created_at']
        indexes = [
            # Core spend identification
            models.Index(fields=['spend_date', 'division']),
            models.Index(fields=['division', 'channel']),
            models.Index(fields=['campaign', 'spend_date']),
            
            # Marketing attribution
            models.Index(fields=['channel', 'campaign']),
            models.Index(fields=['spend_date', 'channel']),
            
            # System fields
            models.Index(fields=['sheet_row_number']),
            models.Index(fields=['created_at']),
            models.Index(fields=['spend_date']),
            
            # Performance tracking
            models.Index(fields=['division', 'spend_date', 'cost']),
        ]

    def __str__(self):
        return f"Row {self.sheet_row_number}: {self.division or 'No Division'} - {self.channel or 'No Channel'} - ${self.cost or 0} on {self.spend_date or 'No Date'}"

    def save(self, *args, **kwargs):
        # Ensure raw_data is properly formatted
        if not isinstance(self.raw_data, dict):
            self.raw_data = {}
        super().save(*args, **kwargs)

    @property
    def cost_formatted(self):
        """Get formatted cost as currency string"""
        if self.cost:
            return f"${self.cost:,.2f}"
        return "$0.00"
    
    @property
    def has_event_dates(self):
        """Check if spend has event date information"""
        return bool(self.event_start_date or self.event_end_date)
