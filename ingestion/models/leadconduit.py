"""
LeadConduit data models

Models for storing LeadConduit event and lead data with proper indexing
and relationships for enterprise-scale data processing.
"""
from django.db import models
from django.utils import timezone
import json

class LeadConduit_Lead(models.Model):
    """
    Lead data extracted from LeadConduit source events
    
    Normalized contact information and lead metadata
    """
    # Core identifiers
    lead_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_id = models.CharField(max_length=100, db_index=True)
    
    # Contact information
    first_name = models.CharField(max_length=200, blank=True, null=True)
    last_name = models.CharField(max_length=200, blank=True, null=True)
    email = models.EmailField(blank=True, null=True, db_index=True)
    phone = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    
    # Address information
    address = models.CharField(max_length=500, blank=True, null=True)
    city = models.CharField(max_length=200, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    zip_code = models.CharField(max_length=50, blank=True, null=True, db_index=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    
    # Lead metadata
    flow_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    source_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    outcome = models.CharField(max_length=255, blank=True, null=True, db_index=True)
    reason = models.TextField(blank=True, null=True)
    
    # Timing
    submitted_utc = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # HGE-specific fields (discovered from API analysis)
    note_hge = models.TextField(blank=True, null=True, help_text="HGE lead notes")
    owner_hge = models.CharField(max_length=100, blank=True, null=True, help_text="HGE lead owner name")
    owneremail_hge = models.EmailField(blank=True, null=True, help_text="HGE lead owner email")
    ownerid_hge = models.CharField(max_length=50, blank=True, null=True, db_index=True, help_text="HGE lead owner ID")
    salesrabbit_lead_id_hge = models.CharField(max_length=50, blank=True, null=True, db_index=True, help_text="SalesRabbit lead ID")
    
    # Metadata storage for complex API structures
    phone_metadata = models.JSONField(default=dict, blank=True, help_text="Phone validation metadata from API")
    email_metadata = models.JSONField(default=dict, blank=True, help_text="Email validation metadata from API")
    address_metadata = models.JSONField(default=dict, blank=True, help_text="Address validation metadata from API")
    
    # JSON storage for complete data
    lead_data = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'leadconduit_lead'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'LeadConduit Lead data stored in ingestion schema'
        indexes = [
            models.Index(fields=['email', 'phone']),
            models.Index(fields=['state', 'zip_code']),
            models.Index(fields=['flow_name', 'source_name']),
            models.Index(fields=['outcome', 'submitted_utc']),
            models.Index(fields=['submitted_utc']),
            # New indexes for HGE-specific fields
            models.Index(fields=['ownerid_hge']),
            models.Index(fields=['salesrabbit_lead_id_hge']),
            models.Index(fields=['owner_hge', 'submitted_utc']),
        ]
        verbose_name = 'LeadConduit Lead'
        verbose_name_plural = 'LeadConduit Leads'
        ordering = ['-submitted_utc']
    
    def __str__(self):
        name_parts = [self.first_name, self.last_name]
        name = ' '.join([part for part in name_parts if part])
        return name or self.email or self.lead_id
    
    @property
    def full_name(self):
        """Get full name from first and last name"""
        name_parts = [self.first_name, self.last_name]
        return ' '.join([part for part in name_parts if part])
    
    @property
    def contact_info(self):
        """Get primary contact information"""
        return self.email or self.phone or "No contact info"
