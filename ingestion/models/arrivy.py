from django.db import models
from django.utils import timezone


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
    zipcode = models.CharField(max_length=50, null=True, blank=True)
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
    mobile_number = models.CharField(max_length=50, null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    emergency = models.CharField(max_length=255, null=True, blank=True)
    
    # Address information
    address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    complete_address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=100, null=True, blank=True)
    country = models.CharField(max_length=100, null=True, blank=True)
    zipcode = models.CharField(max_length=50, null=True, blank=True)
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


class Arrivy_Task(models.Model):
    task_id = models.CharField(max_length=255, unique=True)
    task_title = models.CharField(max_length=255)
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    mobile_number = models.CharField(max_length=50, null=True, blank=True)
    address = models.TextField(null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    zipcode = models.CharField(max_length=50, null=True, blank=True)
    country = models.CharField(max_length=255, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    start_time = models.TimeField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    end_time = models.TimeField(null=True, blank=True)
    template = models.CharField(max_length=255, null=True, blank=True)
    group = models.CharField(max_length=255, null=True, blank=True)
    status = models.CharField(max_length=255, null=True, blank=True)
    timezone = models.CharField(max_length=255, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)
    forms = models.TextField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    created_by = models.CharField(max_length=255, null=True, blank=True)
    created_on = models.DateTimeField(null=True, blank=True)
    scheduled_by = models.CharField(max_length=255, null=True, blank=True)
    rescheduled_count = models.IntegerField(null=True, blank=True)
    crew_assigned_by = models.CharField(max_length=255, null=True, blank=True)
    booking_id = models.CharField(max_length=255, null=True, blank=True)
    booking_name = models.CharField(max_length=255, null=True, blank=True)
    route_name = models.CharField(max_length=255, null=True, blank=True)
    assignees = models.TextField(null=True, blank=True)
    resources = models.TextField(null=True, blank=True)
    resource_template = models.TextField(null=True, blank=True)
    employee_ids = models.TextField(null=True, blank=True)
    customer_id = models.CharField(max_length=255, null=True, blank=True)
    company = models.CharField(max_length=255, null=True, blank=True)
    customer_type = models.CharField(max_length=255, null=True, blank=True)
    address_2 = models.TextField(null=True, blank=True)
    start_timezone = models.CharField(max_length=255, null=True, blank=True)
    end_timezone = models.CharField(max_length=255, null=True, blank=True)
    duration = models.CharField(max_length=255, null=True, blank=True)
    unscheduled = models.BooleanField(default=False)
    expected_start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    travel_time = models.CharField(max_length=255, null=True, blank=True)
    wait_time = models.CharField(max_length=255, null=True, blank=True)
    task_time = models.CharField(max_length=255, null=True, blank=True)
    total_time = models.CharField(max_length=255, null=True, blank=True)
    mileage = models.FloatField(null=True, blank=True)
    rating = models.FloatField(null=True, blank=True)
    rating_text = models.TextField(null=True, blank=True)
    outbound_sms_count = models.IntegerField(null=True, blank=True)
    inbound_sms_count = models.IntegerField(null=True, blank=True)
    outbound_email_count = models.IntegerField(null=True, blank=True)
    inbound_email_count = models.IntegerField(null=True, blank=True)
    template_extra_field_product_interest_primary = models.TextField(null=True, blank=True)
    template_extra_field_product_interest_secondary = models.TextField(null=True, blank=True)
    template_extra_field_primary_source = models.TextField(null=True, blank=True)
    template_extra_field_secondary_source = models.TextField(null=True, blank=True)
    complete = models.BooleanField(default=False)
    cancel = models.BooleanField(default=False)
    custom_cancel_test = models.BooleanField(default=False)
    appointment_confirmed = models.BooleanField(default=False)
    demo_sold = models.BooleanField(default=False)
    on_our_way = models.BooleanField(default=False)
    start = models.BooleanField(default=False)
    exception = models.BooleanField(default=False)
    customer_extra_fields = models.TextField(null=True, blank=True)
    task_extra_fields = models.TextField(null=True, blank=True)
    resource_template_extra_field = models.TextField(null=True, blank=True)
    resource_extra_field = models.TextField(null=True, blank=True)

    class Meta:
        db_table = 'ingestion_arrivy_task'
        verbose_name = 'Arrivy Task'
        verbose_name_plural = 'Arrivy Tasks'

    def __str__(self):
        return f"{self.task_title} ({self.task_id})"


class Arrivy_TaskStatus(models.Model):
    """Represents the status of a task in Arrivy."""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_time = models.DateTimeField(null=True, blank=True)
    updated_time = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ingestion_arrivy_task_status'
        verbose_name = 'Arrivy Task Status'
        verbose_name_plural = 'Arrivy Task Statuses'

    def __str__(self):
        return self.name or f"Task Status {self.id}"


class Arrivy_LocationReport(models.Model):
    """Represents a location report in Arrivy."""
    id = models.CharField(max_length=50, primary_key=True)
    task_id = models.CharField(max_length=50, null=True, blank=True)
    entity_id = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.FloatField(null=True, blank=True)
    longitude = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = 'ingestion_arrivy_location_report'
        verbose_name = 'Arrivy Location Report'
        verbose_name_plural = 'Arrivy Location Reports'

    def __str__(self):
        return f"Location Report {self.id} for Task {self.task_id}"


class Arrivy_SyncHistory(models.Model):
    """Tracks the synchronization history for Arrivy data."""
    id = models.AutoField(primary_key=True)
    sync_type = models.CharField(max_length=50, default='tasks')  # e.g., 'tasks', 'entities', 'task_statuses', etc.
    last_synced_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_arrivy_sync_history'
        verbose_name = 'Arrivy Sync History'
        verbose_name_plural = 'Arrivy Sync Histories'

    def __str__(self):
        return f"{self.sync_type} last synced at {self.last_synced_at}"
