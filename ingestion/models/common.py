"""
Common models shared across all CRM integrations
"""
from django.db import models
from django.utils import timezone

class SyncTracker(models.Model):
    """
    Tracks the last synchronization time for various data sources.
    Used by both Genius and Hubspot sync processes.
    """
    object_name = models.CharField(max_length=255, unique=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.object_name}: {self.last_synced_at}"

class SyncHistory(models.Model):
    """Universal sync history for all CRM operations"""
    
    # Sync identification
    crm_source = models.CharField(max_length=50)  # 'genius', 'hubspot', etc.
    sync_type = models.CharField(max_length=100)  # 'appointments', 'contacts', etc.
    endpoint = models.CharField(max_length=200, null=True, blank=True)
    
    # Timing
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True, blank=True)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ], default='running')
    
    # Metrics
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    records_failed = models.IntegerField(default=0)
    
    # Error handling
    error_message = models.TextField(null=True, blank=True)
    
    # Configuration and performance
    configuration = models.JSONField(default=dict)
    performance_metrics = models.JSONField(default=dict)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'sync_history'
        indexes = [
            models.Index(fields=['crm_source', 'sync_type']),
            models.Index(fields=['start_time']),
            models.Index(fields=['status']),
        ]
        verbose_name = 'Sync History'
        verbose_name_plural = 'Sync Histories'
        ordering = ['-start_time']
        
    def __str__(self):
        return f"{self.crm_source} {self.sync_type} - {self.status}"
    
    @property
    def duration_seconds(self):
        """Calculate sync duration in seconds"""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def records_per_second(self):
        """Calculate processing rate"""
        duration = self.duration_seconds
        if duration and duration > 0:
            return self.records_processed / duration
        return 0

class SyncConfiguration(models.Model):
    """Dynamic sync configuration"""
    
    crm_source = models.CharField(max_length=50)
    sync_type = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    
    # Sync settings
    batch_size = models.IntegerField(default=500)
    retry_count = models.IntegerField(default=3)
    retry_delay = models.IntegerField(default=1)  # seconds
    
    # Field mappings
    field_mappings = models.JSONField(default=dict)
    
    # API settings
    api_settings = models.JSONField(default=dict)
    
    # Scheduling
    schedule_enabled = models.BooleanField(default=False)
    schedule_cron = models.CharField(max_length=100, null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'sync_configuration'
        unique_together = ['crm_source', 'sync_type']
        verbose_name = 'Sync Configuration'
        verbose_name_plural = 'Sync Configurations'
        
    def __str__(self):
        return f"{self.crm_source} {self.sync_type} Config"

class APICredential(models.Model):
    """Encrypted API credentials"""
    
    crm_source = models.CharField(max_length=50, unique=True)
    credentials = models.JSONField()  # Store encrypted credentials
    is_active = models.BooleanField(default=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_credentials'
        verbose_name = 'API Credential'
        verbose_name_plural = 'API Credentials'
    
    def __str__(self):
        return f"{self.crm_source} Credentials"
