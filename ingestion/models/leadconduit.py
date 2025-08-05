"""
LeadConduit data models

Models for storing LeadConduit event and lead data with proper indexing
and relationships for enterprise-scale data processing.
"""
from django.db import models
from django.utils import timezone
import json


class LeadConduit_Event(models.Model):
    """
    LeadConduit event records from the Events API
    
    Stores complete event data including outcomes, timing, and metadata
    """
    # Core identifiers
    event_id = models.CharField(max_length=100, unique=True, db_index=True)
    event_type = models.CharField(max_length=50, db_index=True)
    
    # Outcome and status
    outcome = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    outcome_combined = models.CharField(max_length=355, blank=True, null=True)
    
    # Flow and source names (extracted from vars)
    flow_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    source_name = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    
    # Timing data (UTC timestamps)
    start_timestamp = models.BigIntegerField(null=True, blank=True)
    end_timestamp = models.BigIntegerField(null=True, blank=True)
    submitted_utc = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # Performance metrics
    wait_ms = models.IntegerField(null=True, blank=True)
    overhead_ms = models.IntegerField(null=True, blank=True)
    lag_ms = models.IntegerField(null=True, blank=True)
    ms = models.IntegerField(null=True, blank=True)
    
    # Event metadata
    host = models.CharField(max_length=100, blank=True, null=True)
    handler_version = models.CharField(max_length=50, blank=True, null=True)
    cap_reached = models.BooleanField(default=False)
    ping_limit_reached = models.BooleanField(default=False)
    expires_at = models.BigIntegerField(null=True, blank=True)
    step_count = models.IntegerField(null=True, blank=True)
    module_id = models.CharField(max_length=100, blank=True, null=True)
    package_version = models.CharField(max_length=50, blank=True, null=True)
    
    # JSON data fields (store complete data for reference)
    raw_data = models.JSONField(default=dict, blank=True)
    vars_data = models.JSONField(default=dict, blank=True)
    appended_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps for tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_leadconduit_event'
        indexes = [
            models.Index(fields=['event_type', 'submitted_utc']),
            models.Index(fields=['outcome', 'submitted_utc']),
            models.Index(fields=['flow_name', 'source_name']),
            models.Index(fields=['submitted_utc']),
        ]
        verbose_name = 'LeadConduit Event'
        verbose_name_plural = 'LeadConduit Events'
        ordering = ['-submitted_utc']
    
    def __str__(self):
        return f"{self.event_type} - {self.event_id}"


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
    outcome = models.CharField(max_length=100, blank=True, null=True, db_index=True)
    reason = models.CharField(max_length=255, blank=True, null=True)
    
    # Timing
    submitted_utc = models.DateTimeField(null=True, blank=True, db_index=True)
    
    # JSON storage for complete data
    lead_data = models.JSONField(default=dict, blank=True)
    raw_data = models.JSONField(default=dict, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_leadconduit_lead'
        indexes = [
            models.Index(fields=['email', 'phone']),
            models.Index(fields=['state', 'zip_code']),
            models.Index(fields=['flow_name', 'source_name']),
            models.Index(fields=['outcome', 'submitted_utc']),
            models.Index(fields=['submitted_utc']),
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
