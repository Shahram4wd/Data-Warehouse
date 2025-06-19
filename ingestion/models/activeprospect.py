from django.db import models
from django.contrib.postgres.fields import JSONField


class ActiveProspect_Event(models.Model):
    """ActiveProspect Event model - represents events from LeadConduit API"""
    # Core fields
    id = models.CharField(max_length=50, primary_key=True)
    outcome = models.CharField(max_length=50, null=True, blank=True)
    reason = models.TextField(null=True, blank=True)
    event_type = models.CharField(max_length=50, null=True, blank=True)  # source, recipient, filter, etc.
    host = models.CharField(max_length=255, null=True, blank=True)
    
    # Timing fields
    start_timestamp = models.BigIntegerField(null=True, blank=True)
    end_timestamp = models.BigIntegerField(null=True, blank=True)
    ms = models.IntegerField(null=True, blank=True)
    wait_ms = models.IntegerField(null=True, blank=True)
    overhead_ms = models.IntegerField(null=True, blank=True)
    lag_ms = models.IntegerField(null=True, blank=True)
    total_ms = models.IntegerField(null=True, blank=True)
    
    # Version and handler info
    handler_version = models.CharField(max_length=50, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    module_id = models.CharField(max_length=255, null=True, blank=True)
    package_version = models.CharField(max_length=50, null=True, blank=True)
    
    # Flow and step info
    step_id = models.CharField(max_length=50, null=True, blank=True)
    step_count = models.IntegerField(null=True, blank=True)
    
    # Caps and limits
    cap_reached = models.BooleanField(default=False)
    ping_limit_reached = models.BooleanField(default=False)
    
    # Pricing and revenue
    cost = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    purchase_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    revenue = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    
    # JSON fields for complex data
    vars = models.JSONField(null=True, blank=True)  # All lead data at time of event
    appended = models.JSONField(null=True, blank=True)  # Data appended during processing
    firehose = models.JSONField(null=True, blank=True)  # Firehose configuration
    flow_ping_limits = models.JSONField(null=True, blank=True)
    source_ping_limits = models.JSONField(null=True, blank=True)
    acceptance_criteria = models.JSONField(null=True, blank=True)
    caps = models.JSONField(null=True, blank=True)
    
    # HTTP request/response data
    request_method = models.CharField(max_length=10, null=True, blank=True)
    request_uri = models.URLField(null=True, blank=True)
    request_version = models.CharField(max_length=10, null=True, blank=True)
    request_headers = models.JSONField(null=True, blank=True)
    request_body = models.TextField(null=True, blank=True)
    request_timestamp = models.BigIntegerField(null=True, blank=True)
    
    response_status = models.IntegerField(null=True, blank=True)
    response_status_text = models.CharField(max_length=100, null=True, blank=True)
    response_version = models.CharField(max_length=10, null=True, blank=True)
    response_headers = models.JSONField(null=True, blank=True)
    response_body = models.TextField(null=True, blank=True)
    response_timestamp = models.BigIntegerField(null=True, blank=True)
    
    # Expiration
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_activeprospect_event'
        verbose_name = 'ActiveProspect Event'
        verbose_name_plural = 'ActiveProspect Events'
        indexes = [
            models.Index(fields=['outcome']),
            models.Index(fields=['event_type']),
            models.Index(fields=['start_timestamp']),
            models.Index(fields=['expires_at']),
        ]

    def __str__(self):
        return f"Event {self.id} - {self.event_type} ({self.outcome})"


class ActiveProspect_Lead(models.Model):
    """ActiveProspect Lead model - represents lead search results from LeadConduit API"""
    # Core identification
    lead_id = models.CharField(max_length=50, primary_key=True)
    flow_id = models.CharField(max_length=50, null=True, blank=True)
    flow_name = models.CharField(max_length=255, null=True, blank=True)
    source_id = models.CharField(max_length=50, null=True, blank=True)
    source_name = models.CharField(max_length=255, null=True, blank=True)
    reference = models.CharField(max_length=255, null=True, blank=True)
    
    # Contact information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone_1 = models.CharField(max_length=20, null=True, blank=True)
    phone_2 = models.CharField(max_length=20, null=True, blank=True)
    
    # Address information
    address_1 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    
    # Timestamps
    submission_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Search metadata
    highlight = models.JSONField(null=True, blank=True)
    
    # Latest event reference
    latest_event_id = models.CharField(max_length=50, null=True, blank=True)
    latest_event_outcome = models.CharField(max_length=50, null=True, blank=True)
    latest_event_data = models.JSONField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_activeprospect_lead'
        verbose_name = 'ActiveProspect Lead'
        verbose_name_plural = 'ActiveProspect Leads'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_1']),
            models.Index(fields=['submission_timestamp']),
            models.Index(fields=['flow_id']),
            models.Index(fields=['source_id']),
            models.Index(fields=['state']),
        ]

    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        if name:
            return f"{name} ({self.lead_id})"
        elif self.email:
            return f"{self.email} ({self.lead_id})"
        else:
            return f"Lead {self.lead_id}"


class ActiveProspect_SyncHistory(models.Model):
    """Track sync history for ActiveProspect endpoints"""
    endpoint = models.CharField(max_length=100, unique=True)
    last_synced_at = models.DateTimeField()
    total_records = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'ingestion_activeprospect_sync_history'
        verbose_name = 'ActiveProspect Sync History'
        verbose_name_plural = 'ActiveProspect Sync Histories'

    def __str__(self):
        return f"{self.endpoint} - {self.last_synced_at}"
