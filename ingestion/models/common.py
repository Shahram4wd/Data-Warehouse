"""
Common models shared across all CRM integrations
"""
from django.db import models
from django.utils import timezone
from django_celery_beat.models import PeriodicTask

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
        # Use quoting hack so Django emits "orchestration"."sync_history" for PostgreSQL
        db_table = '"orchestration"."sync_history"'
        managed = True
        db_table_comment = 'Universal sync history for all CRM operations'
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
    
    @classmethod
    def get_last_sync_timestamp(cls, crm_source: str, sync_type: str):
        """Get last successful sync timestamp for delta sync - FRAMEWORK STANDARD"""
        last_sync = cls.objects.filter(
            crm_source=crm_source,
            sync_type=sync_type,
            status='success',
            end_time__isnull=False
        ).order_by('-end_time').first()
        
        return last_sync.end_time if last_sync else None

class SyncSchedule(models.Model):
    """Defines scheduled syncs (moved next to SyncHistory)."""

    MODE_CHOICES = [("delta", "Delta"), ("full", "Full")]
    RECURRENCE_CHOICES = [("interval", "Interval"), ("crontab", "Crontab")]

    source_key = models.CharField(max_length=64, db_index=True)
    name = models.CharField(max_length=128)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)

    recurrence_type = models.CharField(max_length=16, choices=RECURRENCE_CHOICES)
    # Interval
    every = models.PositiveIntegerField(null=True, blank=True)
    period = models.CharField(max_length=16, null=True, blank=True, choices=[
        ("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days")
    ])
    # Crontab
    minute = models.CharField(max_length=64, null=True, blank=True, default="0")
    hour = models.CharField(max_length=64, null=True, blank=True, default="*")
    day_of_week = models.CharField(max_length=64, null=True, blank=True, default="*")
    day_of_month = models.CharField(max_length=64, null=True, blank=True, default="*")
    month_of_year = models.CharField(max_length=64, null=True, blank=True, default="*")

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    enabled = models.BooleanField(default=True)
    options = models.JSONField(default=dict, blank=True)

    periodic_task = models.OneToOneField(PeriodicTask, null=True, blank=True, on_delete=models.SET_NULL)

    created_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name="created_schedules")
    updated_by = models.ForeignKey('auth.User', null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_schedules")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        # Use quoting hack so Django emits "orchestration"."sync_schedule" for PostgreSQL
        db_table = '"orchestration"."sync_schedule"'
        managed = True
        indexes = [models.Index(fields=["source_key", "mode"])]
        permissions = [("manage_schedules", "Can manage ingestion schedules")]

    def __str__(self):
        return f"{self.source_key}:{self.mode}:{self.name}"

    def get_recent_runs(self, limit=5):
        """Get recent SyncHistory records for this schedule."""
        return SyncHistory.objects.filter(
            crm_source=self.source_key,
            sync_type=f"{self.mode}_scheduled",
            configuration__schedule_id=self.id,
        ).order_by('-start_time')[:limit]

    def get_last_run(self):
        """Get the most recent SyncHistory record for this schedule."""
        recent_runs = self.get_recent_runs(limit=1)
        return recent_runs.first() if recent_runs else None

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
        managed = True
        db_table_comment = 'Dynamic sync configuration'
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
        managed = True
        db_table_comment = 'Encrypted API credentials'
        verbose_name = 'API Credential'
        verbose_name_plural = 'API Credentials'
    
    def __str__(self):
        return f"{self.crm_source} Credentials"
