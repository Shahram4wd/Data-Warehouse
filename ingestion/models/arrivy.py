from django.db import models
from django.utils import timezone


class Arrivy_Customer(models.Model):
    """Arrivy Customer model"""
    id = models.CharField(max_length=50, primary_key=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    company_name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    extra_fields = models.JSONField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_time = models.DateTimeField(null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arrivy_customer'
        verbose_name = 'Arrivy Customer'
        verbose_name_plural = 'Arrivy Customers'

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.id})"
        return f"{self.first_name} {self.last_name} ({self.id})" if self.first_name or self.last_name else f"Customer {self.id}"


class Arrivy_TeamMember(models.Model):
    """Arrivy Team Member model"""
    id = models.CharField(max_length=50, primary_key=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    image_path = models.URLField(null=True, blank=True)
    image_id = models.CharField(max_length=50, null=True, blank=True)
    
    # Profile information
    username = models.CharField(max_length=255, null=True, blank=True)
    role = models.CharField(max_length=100, null=True, blank=True)
    permission = models.CharField(max_length=100, null=True, blank=True)
    group_id = models.CharField(max_length=50, null=True, blank=True)
    group_name = models.CharField(max_length=255, null=True, blank=True)
    
    # Location and timezone
    timezone = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    
    # Status and settings
    is_active = models.BooleanField(default=True)
    is_online = models.BooleanField(default=False)
    can_turnon_location = models.BooleanField(default=False)
    support_sms = models.BooleanField(default=True)
    support_phone = models.BooleanField(default=True)
    
    # Timestamps
    created_time = models.DateTimeField(null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)
    last_location_time = models.DateTimeField(null=True, blank=True)
    
    # Extra fields and metadata
    extra_fields = models.JSONField(null=True, blank=True)
    skills = models.JSONField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arrivy_team_member'
        verbose_name = 'Arrivy Team Member'
        verbose_name_plural = 'Arrivy Team Members'

    def __str__(self):
        return f"{self.name or f'{self.first_name} {self.last_name}'} ({self.id})"


class Arrivy_Booking(models.Model):
    """Arrivy Booking model"""
    id = models.CharField(max_length=50, primary_key=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
      # Customer relationship
    customer = models.ForeignKey(Arrivy_Customer, on_delete=models.SET_NULL, null=True, blank=True, related_name='bookings')
    
    # Basic booking information
    title = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    
    # Scheduling
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    start_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    end_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    
    # Status and type
    status = models.CharField(max_length=50, null=True, blank=True)
    status_id = models.IntegerField(null=True, blank=True)
    task_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Location information
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    exact_location = models.JSONField(null=True, blank=True)  # lat, lng
    
    # Team assignment
    assigned_team_members = models.JSONField(null=True, blank=True)  # List of team member IDs
    team_member_ids = models.TextField(null=True, blank=True)  # Comma-separated IDs for easier querying
    
    # Additional fields
    template_id = models.CharField(max_length=50, null=True, blank=True)
    template_extra_fields = models.JSONField(null=True, blank=True)
    extra_fields = models.JSONField(null=True, blank=True)
    custom_fields = models.JSONField(null=True, blank=True)
    
    # Time tracking
    actual_start_datetime = models.DateTimeField(null=True, blank=True)
    actual_end_datetime = models.DateTimeField(null=True, blank=True)
    duration_estimate = models.IntegerField(null=True, blank=True)  # in minutes
    
    # Flags and settings
    is_recurring = models.BooleanField(default=False)
    is_all_day = models.BooleanField(default=False)
    enable_time_window_display = models.BooleanField(default=False)
    unscheduled = models.BooleanField(default=False)
    
    # Notifications
    notifications = models.JSONField(null=True, blank=True)
    
    # Timestamps
    created_time = models.DateTimeField(null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'arrivy_booking'
        verbose_name = 'Arrivy Booking'
        verbose_name_plural = 'Arrivy Bookings'

    def __str__(self):
        return f"{self.title or 'Booking'} ({self.id})"


class Arrivy_SyncHistory(models.Model):
    """Track sync history for Arrivy endpoints"""
    endpoint = models.CharField(max_length=100, unique=True)
    last_synced_at = models.DateTimeField()
    total_records = models.IntegerField(default=0)
    success_count = models.IntegerField(default=0)
    error_count = models.IntegerField(default=0)
    notes = models.TextField(null=True, blank=True)
    
    class Meta:
        db_table = 'arrivy_sync_history'
        verbose_name = 'Arrivy Sync History'
        verbose_name_plural = 'Arrivy Sync Histories'

    def __str__(self):
        return f"{self.endpoint} - {self.last_synced_at}"
