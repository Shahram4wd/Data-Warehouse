from django.db import models
from django.utils import timezone


class LeadConduit_Event(models.Model):
    """Model for LeadConduit event data - updated"""
    id = models.CharField(max_length=24, primary_key=True)  # 24 character BSON identifier
    outcome = models.CharField(max_length=50)  # success, failure, error
    reason = models.TextField(null=True, blank=True)  # reason for failure or error
    event_type = models.CharField(max_length=50)  # source, recipient, filter, etc.
    host = models.CharField(max_length=255, null=True, blank=True)
    
    # Timestamps
    start_timestamp = models.BigIntegerField(null=True, blank=True)  # milliseconds since epoch
    end_timestamp = models.BigIntegerField(null=True, blank=True)    # milliseconds since epoch
    expires_at = models.DateTimeField(null=True, blank=True)
    
    # Processing metrics
    ms = models.IntegerField(null=True, blank=True)  # processing time in ms
    wait_ms = models.IntegerField(null=True, blank=True)  # wait time in ms
    overhead_ms = models.IntegerField(null=True, blank=True)  # overhead time in ms
    lag_ms = models.IntegerField(null=True, blank=True)  # lag time in ms
    total_ms = models.IntegerField(null=True, blank=True)  # total time in ms
    
    # Lead data (stored as JSON)
    vars_data = models.JSONField(null=True, blank=True)  # All lead variables
    appended_data = models.JSONField(null=True, blank=True)  # Appended data
    
    # Version info
    handler_version = models.CharField(max_length=50, null=True, blank=True)
    version = models.CharField(max_length=50, null=True, blank=True)
    package_version = models.CharField(max_length=50, null=True, blank=True)
    
    # Capacity and limits
    cap_reached = models.BooleanField(default=False)
    ping_limit_reached = models.BooleanField(default=False)
    
    # Step info
    step_count = models.IntegerField(null=True, blank=True)
    module_id = models.CharField(max_length=255, null=True, blank=True)
    
    # HTTP request/response data
    request_data = models.JSONField(null=True, blank=True)
    response_data = models.JSONField(null=True, blank=True)
    
    # Metadata
    imported_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_leadconduit_event'
        verbose_name = 'LeadConduit Event'
        verbose_name_plural = 'LeadConduit Events'
        ordering = ['-start_timestamp', '-imported_at']
        indexes = [
            models.Index(fields=['outcome']),
            models.Index(fields=['event_type']),
            models.Index(fields=['start_timestamp']),
            models.Index(fields=['imported_at']),
        ]
    
    def __str__(self):
        return f"Event {self.id} - {self.outcome} ({self.event_type})"
    
    @property
    def start_datetime(self):
        """Convert start_timestamp to datetime"""
        if self.start_timestamp:
            return timezone.datetime.fromtimestamp(self.start_timestamp / 1000, tz=timezone.utc)
        return None
    
    @property
    def end_datetime(self):
        """Convert end_timestamp to datetime"""
        if self.end_timestamp:
            return timezone.datetime.fromtimestamp(self.end_timestamp / 1000, tz=timezone.utc)
        return None


class LeadConduit_Lead(models.Model):
    """Model for LeadConduit lead data extracted from events and CSV imports"""
    lead_id = models.CharField(max_length=50, primary_key=True)  # Increased length for various ID formats
    flow_id = models.CharField(max_length=50, null=True, blank=True)
    flow_name = models.CharField(max_length=255, null=True, blank=True)
    source_id = models.CharField(max_length=50, null=True, blank=True)
    source_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Lead contact information
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone_1 = models.CharField(max_length=20, null=True, blank=True)
    phone_2 = models.CharField(max_length=20, null=True, blank=True)
    
    # Address information
    address_1 = models.CharField(max_length=255, null=True, blank=True)
    address_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    postal_code = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=50, null=True, blank=True)
    
    # Additional lead data
    reference = models.CharField(max_length=255, null=True, blank=True)
    submission_timestamp = models.DateTimeField(null=True, blank=True)
    
    # Marketing and campaign information (common in LeadConduit exports)
    campaign = models.CharField(max_length=255, null=True, blank=True)
    ad_group = models.CharField(max_length=255, null=True, blank=True)
    keyword = models.CharField(max_length=255, null=True, blank=True)
    utm_source = models.CharField(max_length=255, null=True, blank=True)
    utm_medium = models.CharField(max_length=255, null=True, blank=True)
    utm_campaign = models.CharField(max_length=255, null=True, blank=True)
    utm_content = models.CharField(max_length=255, null=True, blank=True)
    utm_term = models.CharField(max_length=255, null=True, blank=True)
    
    # Lead quality and scoring
    quality_score = models.FloatField(null=True, blank=True)
    lead_score = models.IntegerField(null=True, blank=True)
    is_duplicate = models.BooleanField(default=False)
    
    # Geographic and demographic data
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(null=True, blank=True)
    referring_url = models.URLField(max_length=500, null=True, blank=True)
    landing_page = models.URLField(max_length=500, null=True, blank=True)
      # Lead status and disposition
    status = models.CharField(max_length=50, null=True, blank=True)
    disposition = models.CharField(max_length=100, null=True, blank=True)
      # HubSpot properties (when LeadConduit exports include HubSpot data)
    hs_createdate = models.DateTimeField(null=True, blank=True)
    hs_lastmodifieddate = models.DateTimeField(null=True, blank=True)
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    hs_lead_status = models.CharField(max_length=100, null=True, blank=True)
    hs_lifecyclestage = models.CharField(max_length=100, null=True, blank=True)
    hs_analytics_source = models.CharField(max_length=255, null=True, blank=True)
    hs_analytics_source_data_1 = models.CharField(max_length=255, null=True, blank=True)
    hs_analytics_source_data_2 = models.CharField(max_length=255, null=True, blank=True)
    
    # SalesRabbit integration fields (common in LeadConduit exports)
    salesrabbit_lead_id = models.CharField(max_length=100, null=True, blank=True)
    salesrabbit_rep_id = models.CharField(max_length=100, null=True, blank=True)
    salesrabbit_rep_name = models.CharField(max_length=255, null=True, blank=True)
    salesrabbit_area_id = models.CharField(max_length=100, null=True, blank=True)
    salesrabbit_area_name = models.CharField(max_length=255, null=True, blank=True)
    salesrabbit_status = models.CharField(max_length=100, null=True, blank=True)
    salesrabbit_disposition = models.CharField(max_length=255, null=True, blank=True)
    salesrabbit_notes = models.TextField(null=True, blank=True)
    salesrabbit_created_at = models.DateTimeField(null=True, blank=True)
    salesrabbit_updated_at = models.DateTimeField(null=True, blank=True)
    salesrabbit_appointment_date = models.DateTimeField(null=True, blank=True)
    salesrabbit_sale_amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    salesrabbit_commission = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    
    # Import source tracking
    import_source = models.CharField(max_length=50, default='api', choices=[
        ('api', 'API Import'),
        ('csv', 'CSV Import'),
        ('events', 'Events Extract'),
    ])
    # Full lead data (JSON)
    full_data = models.JSONField(null=True, blank=True)  # Complete lead variables
    
    # Latest event info
    latest_event_id = models.CharField(max_length=50, null=True, blank=True)
    latest_outcome = models.CharField(max_length=50, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_leadconduit_lead'
        verbose_name = 'LeadConduit Lead'
        verbose_name_plural = 'LeadConduit Leads'
        ordering = ['-submission_timestamp', '-updated_at']
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['phone_1']),
            models.Index(fields=['state']),
            models.Index(fields=['submission_timestamp']),
            models.Index(fields=['latest_outcome']),
            models.Index(fields=['import_source']),
            models.Index(fields=['status']),
            models.Index(fields=['campaign']),
            models.Index(fields=['utm_source']),
            models.Index(fields=['flow_name']),
            models.Index(fields=['source_name']),
        ]
    
    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        if name:
            return f"{name} ({self.lead_id})"
        return f"Lead {self.lead_id}"
    
    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
    
    @property
    def full_address(self):
        parts = [
            self.address_1,
            self.city,
            f"{self.state} {self.postal_code}".strip()
        ]
        return ", ".join(filter(None, parts))


class LeadConduit_SyncHistory(models.Model):
    """Track LeadConduit import history"""
    sync_type = models.CharField(max_length=50)  # e.g., 'events', 'leads'
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='in_progress')  # in_progress, completed, failed
    error_message = models.TextField(null=True, blank=True)
    
    # API request parameters
    api_endpoint = models.CharField(max_length=255, null=True, blank=True)
    query_params = models.JSONField(null=True, blank=True)
    
    # Pagination info
    start_id = models.CharField(max_length=24, null=True, blank=True)  # for pagination
    end_id = models.CharField(max_length=24, null=True, blank=True)
    
    class Meta:
        db_table = 'ingestion_leadconduit_sync_history'
        verbose_name = 'LeadConduit Sync History'
        verbose_name_plural = 'LeadConduit Sync Histories'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
