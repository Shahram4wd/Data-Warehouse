"""
CallRail CRM models for phone call tracking and analytics
"""
from django.db import models


class CallRail_Account(models.Model):
    """CallRail account model"""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    outbound_recording_enabled = models.BooleanField(default=False)
    hipaa_account = models.BooleanField(default=False)
    numeric_id = models.BigIntegerField(null=True, blank=True)
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_callrail_account'
        verbose_name = 'CallRail Account'
        verbose_name_plural = 'CallRail Accounts'

    def __str__(self):
        return self.name


class CallRail_Company(models.Model):
    """CallRail company model"""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    status = models.CharField(max_length=50)
    time_zone = models.CharField(max_length=100)
    dni_active = models.BooleanField(null=True, blank=True)
    script_url = models.TextField(null=True, blank=True)
    callscribe_enabled = models.BooleanField(default=False)
    lead_scoring_enabled = models.BooleanField(default=False)
    swap_exclude_jquery = models.BooleanField(null=True, blank=True)
    swap_ppc_override = models.BooleanField(null=True, blank=True)
    swap_landing_override = models.CharField(max_length=255, null=True, blank=True)
    swap_cookie_duration = models.IntegerField(default=6)
    swap_cookie_duration_unit = models.CharField(max_length=20, default="months")
    callscore_enabled = models.BooleanField(default=False)
    keyword_spotting_enabled = models.BooleanField(default=False)
    form_capture = models.BooleanField(default=False)
    disabled_at = models.DateTimeField(null=True, blank=True)
    
    # Sync tracking
    api_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_company'
        verbose_name = 'CallRail Company'
        verbose_name_plural = 'CallRail Companies'
        indexes = [
            models.Index(fields=['status']),
            models.Index(fields=['time_zone']),
        ]

    def __str__(self):
        return f"{self.name} ({self.status})"


class CallRail_Call(models.Model):
    """CallRail call tracking model"""
    id = models.CharField(max_length=50, primary_key=True)
    answered = models.BooleanField(default=False)
    business_phone_number = models.CharField(max_length=20, null=True, blank=True)
    customer_city = models.CharField(max_length=100, null=True, blank=True)
    customer_country = models.CharField(max_length=100, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_phone_number = models.CharField(max_length=20)
    customer_state = models.CharField(max_length=50, null=True, blank=True)
    direction = models.CharField(max_length=20)  # inbound/outbound
    duration = models.IntegerField(default=0)  # in seconds
    recording = models.URLField(null=True, blank=True)
    recording_duration = models.CharField(max_length=20, null=True, blank=True)
    recording_player = models.URLField(null=True, blank=True)
    start_time = models.DateTimeField()
    tracking_phone_number = models.CharField(max_length=20)
    voicemail = models.BooleanField(default=False)
    agent_email = models.EmailField(null=True, blank=True)
    call_type = models.CharField(max_length=50, null=True, blank=True)
    campaign = models.CharField(max_length=255, null=True, blank=True)
    company_id = models.CharField(max_length=50, null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    note = models.TextField(null=True, blank=True)
    lead_status = models.CharField(max_length=100, null=True, blank=True)
    value = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    
    # Tags (stored as JSON array)
    tags = models.JSONField(null=True, blank=True)
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_call'
        verbose_name = 'CallRail Call'
        verbose_name_plural = 'CallRail Calls'
        indexes = [
            models.Index(fields=['start_time']),  # For delta sync
            models.Index(fields=['customer_phone_number']),
            models.Index(fields=['tracking_phone_number']),
            models.Index(fields=['answered']),
            models.Index(fields=['direction']),
            models.Index(fields=['company_id']),
            models.Index(fields=['lead_status']),
        ]

    def __str__(self):
        status = "Answered" if self.answered else "Missed"
        return f"{self.customer_phone_number} → {self.tracking_phone_number} ({status})"


class CallRail_Tracker(models.Model):
    """CallRail phone number tracker model"""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    type = models.CharField(max_length=50)  # pool, source, etc.
    status = models.CharField(max_length=50)
    destination_number = models.CharField(max_length=20)
    whisper_message = models.TextField(null=True, blank=True)
    sms_enabled = models.BooleanField(default=False)
    sms_supported = models.BooleanField(default=False)
    disabled_at = models.DateTimeField(null=True, blank=True)
    
    # Tracking numbers (stored as JSON array)
    tracking_numbers = models.JSONField(default=list)
    
    # Company info (stored as JSON object)
    company = models.JSONField(null=True, blank=True)
    
    # Call flow configuration (stored as JSON object)
    call_flow = models.JSONField(null=True, blank=True)
    
    # Source configuration (stored as JSON object)
    source = models.JSONField(null=True, blank=True)
    
    # Sync tracking
    api_created_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_tracker'
        verbose_name = 'CallRail Tracker'
        verbose_name_plural = 'CallRail Trackers'
        indexes = [
            models.Index(fields=['type']),
            models.Index(fields=['status']),
            models.Index(fields=['destination_number']),
        ]

    def __str__(self):
        numbers = ", ".join(self.tracking_numbers) if self.tracking_numbers else "No numbers"
        return f"{self.name} ({self.type}): {numbers}"


class CallRail_FormSubmission(models.Model):
    """CallRail form submission tracking model"""
    id = models.CharField(max_length=50, primary_key=True)
    company_id = models.CharField(max_length=50)
    person_id = models.CharField(max_length=50, null=True, blank=True)
    form_url = models.URLField()
    landing_page_url = models.URLField(null=True, blank=True)
    
    # Form data (stored as JSON object)
    form_data = models.JSONField()
    
    # Timestamps
    submission_time = models.DateTimeField()
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_form_submission'
        verbose_name = 'CallRail Form Submission'
        verbose_name_plural = 'CallRail Form Submissions'
        indexes = [
            models.Index(fields=['submission_time']),  # For delta sync
            models.Index(fields=['company_id']),
            models.Index(fields=['person_id']),
        ]

    def __str__(self):
        return f"Form submission {self.id} - {self.submission_time}"


class CallRail_TextMessage(models.Model):
    """CallRail text message tracking model"""
    id = models.CharField(max_length=50, primary_key=True)
    company_id = models.CharField(max_length=50, null=True, blank=True)
    direction = models.CharField(max_length=20)  # inbound/outbound
    tracking_phone_number = models.CharField(max_length=20)
    customer_phone_number = models.CharField(max_length=20)
    message = models.TextField()
    sent_at = models.DateTimeField()
    
    # Message status
    status = models.CharField(max_length=50, null=True, blank=True)
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_text_message'
        verbose_name = 'CallRail Text Message'
        verbose_name_plural = 'CallRail Text Messages'
        indexes = [
            models.Index(fields=['sent_at']),  # For delta sync
            models.Index(fields=['direction']),
            models.Index(fields=['customer_phone_number']),
            models.Index(fields=['tracking_phone_number']),
            models.Index(fields=['company_id']),
        ]

    def __str__(self):
        return f"SMS {self.direction} - {self.customer_phone_number} ({self.sent_at})"


class CallRail_Tag(models.Model):
    """CallRail tag model for call categorization"""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255)
    color = models.CharField(max_length=20, null=True, blank=True)
    company_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Tag configuration (stored as JSON object)
    configuration = models.JSONField(null=True, blank=True)
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_tag'
        verbose_name = 'CallRail Tag'
        verbose_name_plural = 'CallRail Tags'
        indexes = [
            models.Index(fields=['name']),
            models.Index(fields=['company_id']),
        ]

    def __str__(self):
        return f"{self.name} ({self.color})" if self.color else self.name


class CallRail_User(models.Model):
    """CallRail user model"""
    id = models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    email = models.EmailField()
    role = models.CharField(max_length=100, null=True, blank=True)
    
    # User configuration (stored as JSON object)
    permissions = models.JSONField(null=True, blank=True)
    
    # Status
    is_active = models.BooleanField(default=True)
    
    # Sync tracking
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    synced_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_CallRail_user'
        verbose_name = 'CallRail User'
        verbose_name_plural = 'CallRail Users'
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active']),
        ]

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
