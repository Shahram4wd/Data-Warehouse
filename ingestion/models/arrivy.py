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
        db_table = 'ingestion_arrivy_customer'
        verbose_name = 'Arrivy Customer'
        verbose_name_plural = 'Arrivy Customers'

    def __str__(self):
        if self.company_name:
            return f"{self.company_name} ({self.id})"
        return f"{self.first_name} {self.last_name} ({self.id})" if self.first_name or self.last_name else f"Customer {self.id}"


class Arrivy_Booking(models.Model):
    """Arrivy Booking model"""
    id = models.CharField(max_length=50, primary_key=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
      # Customer relationship - no foreign key constraint
    customer_id = models.CharField(max_length=50, null=True, blank=True, help_text="Customer ID from API - no foreign key constraint")
    customer_id_raw = models.CharField(max_length=50, null=True, blank=True, help_text="Raw customer ID from API for debugging")
    
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
        db_table = 'ingestion_arrivy_booking'
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
        db_table = 'ingestion_arrivy_sync_history'
        verbose_name = 'Arrivy Sync History'
        verbose_name_plural = 'Arrivy Sync Histories'

    def __str__(self):
        return f"{self.endpoint} - {self.last_synced_at}"


class Arrivy_Entity(models.Model):
    """Arrivy Entity model - represents individual crew members from Arrivy entities endpoint"""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    type = models.CharField(max_length=100, null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    external_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Contact information
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Visual and identification
    image_id = models.CharField(max_length=50, null=True, blank=True)
    image_path = models.URLField(null=True, blank=True)
    color = models.CharField(max_length=50, null=True, blank=True)
    url_safe_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Status and permissions
    is_active = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)
    is_default = models.BooleanField(default=False)
    user_type = models.CharField(max_length=50, null=True, blank=True)
    invite_status = models.CharField(max_length=50, null=True, blank=True)
    
    # Group and organizational structure
    group_id = models.CharField(max_length=50, null=True, blank=True)
    owner = models.CharField(max_length=50, null=True, blank=True)
    additional_group_ids = models.JSONField(null=True, blank=True)
    
    # Location and address
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    complete_address = models.TextField(null=True, blank=True)
    exact_location = models.JSONField(null=True, blank=True)
    is_address_geo_coded = models.BooleanField(default=False)
    use_lat_lng_address = models.BooleanField(default=False)
    
    # Settings and preferences
    allow_login_in_kiosk_mode_only = models.BooleanField(default=False)
    can_turnoff_location = models.BooleanField(default=True)
    can_view_customers_of_all_groups = models.BooleanField(default=False)
    is_status_priority_notifications_disabled = models.BooleanField(default=False)
    is_included_in_billing = models.BooleanField(default=True)
    force_stop_billing = models.BooleanField(default=False)
    
    # Skills and capabilities
    skill_ids = models.JSONField(null=True, blank=True)
    skill_details = models.JSONField(null=True, blank=True)
    
    # Additional data
    details = models.TextField(null=True, blank=True)
    extra_fields = models.JSONField(null=True, blank=True)
    visible_bookings = models.JSONField(null=True, blank=True)
    visible_routing_forms = models.JSONField(null=True, blank=True)
    notifications = models.JSONField(null=True, blank=True)
    allow_status_notifications = models.JSONField(null=True, blank=True)
    permission_groups = models.JSONField(null=True, blank=True)
    template_id = models.CharField(max_length=50, null=True, blank=True)
    template_extra_fields = models.JSONField(null=True, blank=True)
    
    # Audit trail
    created_by = models.CharField(max_length=50, null=True, blank=True)
    created_by_user = models.CharField(max_length=255, null=True, blank=True)
    created_time = models.DateTimeField(null=True, blank=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)
    updated_by_user = models.CharField(max_length=255, null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)
    joined_datetime = models.DateTimeField(null=True, blank=True)
    
    # Last location reading
    last_reading = models.JSONField(null=True, blank=True)
    
    # SSO integration
    okta_user_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_arrivy_entity'
        verbose_name = 'Arrivy Entity'
        verbose_name_plural = 'Arrivy Entities'

    def __str__(self):
        return f"{self.name} ({self.type}) - {self.id}" if self.name and self.type else f"Entity {self.id}"


class Arrivy_Group(models.Model):
    """Arrivy Group model - represents groups/locations from official Arrivy groups endpoint"""
    id = models.CharField(max_length=50, primary_key=True)
    url_safe_id = models.CharField(max_length=255, null=True, blank=True)
    owner = models.CharField(max_length=50, null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    
    # Contact information
    email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    mobile_number = models.CharField(max_length=20, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    emergency = models.CharField(max_length=255, null=True, blank=True)
    
    # Address information
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    complete_address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=20, null=True, blank=True)
    exact_location = models.JSONField(null=True, blank=True)
    use_lat_lng_address = models.BooleanField(default=False)
    is_address_geo_coded = models.BooleanField(default=False)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    
    # Visual and organizational
    image_id = models.CharField(max_length=50, null=True, blank=True)
    image_path = models.URLField(null=True, blank=True)
    
    # Status and settings
    is_default = models.BooleanField(default=False)
    is_disabled = models.BooleanField(default=False)
    is_implicit = models.BooleanField(default=False)
    
    # Additional data
    social_links = models.JSONField(null=True, blank=True)
    additional_addresses = models.JSONField(null=True, blank=True)
    territory_ids = models.JSONField(null=True, blank=True)
    extra_fields = models.JSONField(null=True, blank=True)
    
    # Audit trail
    created_by = models.CharField(max_length=50, null=True, blank=True)
    created_time = models.DateTimeField(null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    synced_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_arrivy_group'
        verbose_name = 'Arrivy Group'
        verbose_name_plural = 'Arrivy Groups'

    def __str__(self):
        return f"{self.name} ({self.id})" if self.name else f"Group {self.id}"
