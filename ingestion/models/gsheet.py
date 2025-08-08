"""
Google Sheets Models

Following CRM sync guide - using global SyncHistory table for sync tracking.
Configuration is hardcoded in engines, not stored in database.
"""
from django.db import models
from django.utils import timezone


class GoogleSheetMarketingLead(models.Model):
    """Marketing leads data from Google Sheets"""
    
    # Primary key
    id = models.AutoField(primary_key=True)
    
    # Timestamps
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Sheet metadata
    sheet_row_number = models.IntegerField(
        null=True, blank=True,
        help_text="Original row number in sheet"
    )
    sheet_last_modified = models.DateTimeField(
        null=True, blank=True,
        help_text="Sheet last modification time"
    )
    
    # Marketing data fields (auto-detected from sheet headers)
    date = models.CharField(max_length=255, null=True, blank=True)
    source = models.CharField(max_length=255, null=True, blank=True)
    medium = models.CharField(max_length=255, null=True, blank=True)
    campaign = models.CharField(max_length=255, null=True, blank=True)
    leads = models.CharField(max_length=255, null=True, blank=True)
    cost = models.CharField(max_length=255, null=True, blank=True)
    
    # Store complete raw data for flexibility
    raw_data = models.JSONField(
        default=dict,
        help_text="Complete row data from sheet"
    )
    
    class Meta:
        db_table = 'ingestion_gsheet_marketing_lead'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Marketing Lead {self.id} - {self.source} ({self.date})"
