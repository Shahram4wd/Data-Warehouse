from django.db import models
from django.utils import timezone
from ..config.five9_config import field_mapper, DELTA_SYNC_CONFIG


class Five9Contact(models.Model):
    """Five9 Contact Model - Preserves all original field names"""
    
    # Standard Contact Fields
    number1 = models.CharField(max_length=20, blank=True, null=True)
    number2 = models.CharField(max_length=20, blank=True, null=True)
    number3 = models.CharField(max_length=20, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    company = models.CharField(max_length=255, blank=True, null=True)
    street = models.TextField(blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip = models.CharField(max_length=20, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    
    # System Fields
    contactID = models.CharField(max_length=100, blank=True, null=True)
    sys_created_date = models.DateTimeField(blank=True, null=True)
    sys_last_agent = models.CharField(max_length=255, blank=True, null=True)
    sys_last_disposition = models.CharField(max_length=255, blank=True, null=True)
    sys_last_disposition_time = models.DateTimeField(blank=True, null=True)
    last_campaign = models.CharField(max_length=255, blank=True, null=True)
    attempts = models.CharField(max_length=50, blank=True, null=True)
    last_list = models.CharField(max_length=255, blank=True, null=True)
    
    # Custom UUID Fields (preserve original names)
    # Note: Using field_ prefix for UUID fields to make them valid Python identifiers
    f65d759a_2250_4b2d_89a9_60796f624f72 = models.CharField(max_length=20, blank=True, null=True)  # PHONE
    field_4f347541_7c4d_4812_9190_e8dea6c0eb49 = models.DateTimeField(blank=True, null=True)  # DATE_TIME
    field_80cf8462_cc10_41b8_a68a_5898cdba1e11 = models.CharField(max_length=255, blank=True, null=True)  # STRING
    
    # Additional Custom Fields (replace spaces with underscores for valid field names)
    New_Contact_Field = models.DateTimeField(blank=True, null=True)
    lead_source = models.CharField(max_length=255, blank=True, null=True)
    DialAttempts = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True)
    XCounter = models.CharField(max_length=255, blank=True, null=True)
    F9_list = models.CharField(max_length=255, blank=True, null=True)
    DoNotDial = models.BooleanField(blank=True, null=True)
    ggg = models.CharField(max_length=255, blank=True, null=True)
    lead_prioritization = models.DecimalField(max_digits=2, decimal_places=0, blank=True, null=True)
    metal_count = models.DecimalField(max_digits=5, decimal_places=0, blank=True, null=True)
    
    # Agent Disposition Fields (replace spaces with underscores)
    Last_Agent_Disposition = models.CharField(max_length=255, blank=True, null=True)
    Last_Agent_Disposition_Date_Time = models.DateTimeField(blank=True, null=True)
    
    # Business Fields (replace spaces with underscores)
    Market = models.CharField(max_length=255, blank=True, null=True)
    Secondary_Lead_Source = models.CharField(max_length=255, blank=True, null=True)
    HubSpot_ContactID = models.CharField(max_length=255, blank=True, null=True)
    Result = models.CharField(max_length=255, blank=True, null=True)
    Product = models.CharField(max_length=255, blank=True, null=True)
    Appointment_Date_and_Time = models.DateTimeField(blank=True, null=True)
    Carrier = models.CharField(max_length=255, blank=True, null=True)
    TFUID = models.CharField(max_length=255, blank=True, null=True)
    Lead_Status = models.CharField(max_length=255, blank=True, null=True)
    PC_Work_Finished = models.DateField(blank=True, null=True)
    Total_Job_Amount = models.DecimalField(max_digits=7, decimal_places=2, blank=True, null=True)
    Position = models.CharField(max_length=255, blank=True, null=True)
    Appointment_Date = models.DateField(blank=True, null=True)
    
    # List Tracking (as requested)
    list_name = models.CharField(max_length=255)
    
    # Internal Sync Fields (as requested)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'five9_contact'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Five9 Contact data stored in ingestion schema'
        verbose_name = 'Five9 Contact'
        verbose_name_plural = 'Five9 Contacts'
        # Composite primary key: number1 + list_name (phone number can appear in multiple lists)
        unique_together = [['number1', 'list_name']]
        indexes = [
            models.Index(fields=['number1']),
            models.Index(fields=['contactID']),
            models.Index(fields=['list_name']),
            models.Index(fields=['sys_last_disposition_time']),
            models.Index(fields=['sync_updated_at']),
        ]
    
    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.list_name})"
