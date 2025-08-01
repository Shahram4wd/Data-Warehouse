from django.db import models
from django.utils import timezone
from .common import SyncHistory


class SalesRabbit_Lead(models.Model):
    """Model representing a SalesRabbit lead"""
    id = models.BigIntegerField(primary_key=True)
    
    # Name fields
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    business_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Contact fields
    email = models.EmailField(null=True, blank=True)
    phone_primary = models.CharField(max_length=20, null=True, blank=True)
    phone_alternate = models.CharField(max_length=20, null=True, blank=True)
    
    # Address fields
    street1 = models.CharField(max_length=255, null=True, blank=True)
    street2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=50, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    
    # Location fields
    latitude = models.DecimalField(max_digits=10, decimal_places=8, null=True, blank=True)
    longitude = models.DecimalField(max_digits=11, decimal_places=8, null=True, blank=True)
    
    # Status and tracking
    status = models.CharField(max_length=100, null=True, blank=True)
    status_modified = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    appointment = models.TextField(null=True, blank=True)  # Appointment details from API
    
    # Files and attachments
    files = models.JSONField(null=True, blank=True)  # Array of file objects from API
    
    # Campaign and ownership
    campaign_id = models.BigIntegerField(null=True, blank=True)
    user_id = models.BigIntegerField(null=True, blank=True)
    user_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Dates
    date_created = models.DateTimeField(null=True, blank=True)
    date_modified = models.DateTimeField(null=True, blank=True)
    owner_modified = models.DateTimeField(null=True, blank=True)
    date_of_birth = models.DateField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    
    # Raw data backup
    data = models.JSONField()  # Raw lead data from API
    custom_fields = models.JSONField(null=True, blank=True)  # Custom fields from API
    
    # Sync tracking - STANDARDIZED to match other CRM models
    created_at = models.DateTimeField(auto_now_add=True)  # When record was first created in our DB
    updated_at = models.DateTimeField(auto_now=True)      # When record was last updated in our DB

    class Meta:
        db_table = 'ingestion_salesrabbit_lead'
        verbose_name = "SalesRabbit Lead"
        verbose_name_plural = "SalesRabbit Leads"
        indexes = [
            models.Index(fields=['date_modified']),  # For delta sync
            models.Index(fields=['email']),
            models.Index(fields=['status']),
            models.Index(fields=['campaign_id']),
            models.Index(fields=['user_id']),
        ]

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or self.business_name or f"Lead {self.id}"
    
    @property
    def full_name(self):
        """Return full name or business name"""
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or self.business_name
    
    @property
    def full_address(self):
        """Return formatted full address"""
        parts = [self.street1, self.city, self.state, self.zip]
        return ", ".join(part for part in parts if part)
