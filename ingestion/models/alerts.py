"""
Alert models for the monitoring system
"""
from django.db import models
from django.utils import timezone
import json

class AlertModel(models.Model):
    """Database model for storing system alerts"""
    
    # Alert identification
    alert_id = models.CharField(max_length=255, unique=True, help_text="Unique identifier for the alert")
    alert_type = models.CharField(max_length=50, help_text="Type of alert (performance, error_rate, etc.)")
    severity = models.CharField(max_length=20, help_text="Alert severity level")
    
    # Alert content
    title = models.CharField(max_length=255, help_text="Alert title")
    message = models.TextField(help_text="Alert message")
    details = models.JSONField(default=dict, help_text="Additional alert details")
    
    # Metadata
    timestamp = models.DateTimeField(help_text="When the alert was created")
    source = models.CharField(max_length=100, default="monitoring", help_text="Source of the alert")
    resolved = models.BooleanField(default=False, help_text="Whether the alert has been resolved")
    
    # Resolution tracking
    resolution_time = models.DateTimeField(null=True, blank=True, help_text="When the alert was resolved")
    resolution_notes = models.TextField(null=True, blank=True, help_text="Notes about the resolution")
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'ingestion_alerts'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['alert_type']),
            models.Index(fields=['severity']),
            models.Index(fields=['resolved']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['source']),
        ]
    
    def __str__(self):
        return f"{self.alert_type} - {self.title} ({self.severity})"
    
    def get_details_display(self):
        """Get formatted details for display"""
        if isinstance(self.details, dict):
            return json.dumps(self.details, indent=2)
        return str(self.details)
    
    def resolve(self, notes=None):
        """Mark alert as resolved"""
        self.resolved = True
        self.resolution_time = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save()
    
    def to_dict(self):
        """Convert alert to dictionary"""
        return {
            'id': self.alert_id,
            'type': self.alert_type,
            'severity': self.severity,
            'title': self.title,
            'message': self.message,
            'details': self.details,
            'timestamp': self.timestamp.isoformat(),
            'source': self.source,
            'resolved': self.resolved,
            'resolution_time': self.resolution_time.isoformat() if self.resolution_time else None,
            'resolution_notes': self.resolution_notes,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
        }

class AlertRule(models.Model):
    """Database model for alert rules configuration"""
    
    name = models.CharField(max_length=255, unique=True, help_text="Rule name")
    alert_type = models.CharField(max_length=50, help_text="Type of alert this rule generates")
    severity = models.CharField(max_length=20, help_text="Severity level for alerts from this rule")
    message_template = models.TextField(help_text="Template for alert messages")
    
    # Rule configuration
    condition_config = models.JSONField(default=dict, help_text="Condition configuration")
    cooldown_minutes = models.IntegerField(default=60, help_text="Cooldown period in minutes")
    max_alerts_per_hour = models.IntegerField(default=5, help_text="Maximum alerts per hour")
    enabled = models.BooleanField(default=True, help_text="Whether the rule is enabled")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        indexes = [
            models.Index(fields=['alert_type']),
            models.Index(fields=['enabled']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.alert_type})"
