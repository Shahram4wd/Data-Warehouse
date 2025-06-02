from django.db import models
from django.utils import timezone

class HubspotContact(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    address = models.TextField(null=True, blank=True)
    campaign_name = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    createdate = models.DateTimeField(null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    firstname = models.CharField(max_length=255, null=True, blank=True)
    hs_google_click_id = models.CharField(max_length=255, null=True, blank=True)
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    lastmodifieddate = models.DateTimeField(null=True, blank=True)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    marketsharp_id = models.CharField(max_length=255, null=True, blank=True)
    original_lead_source = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.email})"

class HubspotDeal(models.Model):
    id = models.CharField(max_length=50, primary_key=True)
    deal_name = models.CharField(max_length=255, null=True, blank=True)
    amount = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    closedate = models.DateTimeField(null=True, blank=True)
    createdate = models.DateTimeField(null=True, blank=True)
    dealstage = models.CharField(max_length=255, null=True, blank=True)
    dealtype = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    hubspot_owner_id = models.CharField(max_length=255, null=True, blank=True)
    pipeline = models.CharField(max_length=255, null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    priority = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.deal_name} ({self.amount})"

class HubspotSyncHistory(models.Model):
    endpoint = models.CharField(max_length=100)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.endpoint} - {self.last_synced_at}"
    
    class Meta:
        verbose_name_plural = "Hubspot Sync Histories"
