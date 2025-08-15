from django.db import models
from django.utils import timezone


class Arrivy_Entity(models.Model):
    """Arrivy Entity model - represents individual crew members from Arrivy entities endpoint"""
    # Note: Cons    customer_mobile_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Customer address informationnging to BigIntegerField in future migration if needed
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
    # Note: Consider changing to BigIntegerField in future migration
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
    
    # New management permissions (from API data)
    can_manage_resources = models.JSONField(null=True, blank=True)
    can_manage_crews = models.JSONField(null=True, blank=True)
    can_manage_entities = models.JSONField(null=True, blank=True)
    
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
    # Note: Consider changing to BigIntegerField in future migration
    template_id = models.CharField(max_length=50, null=True, blank=True)
    template_extra_fields = models.JSONField(null=True, blank=True)
    
    # Email invitation data (from API)
    email_invitation = models.JSONField(null=True, blank=True)
    
    # Audit trail
    # Note: Consider changing to BigIntegerField in future migration
    created_by = models.CharField(max_length=50, null=True, blank=True)
    created_by_user = models.CharField(max_length=255, null=True, blank=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)
    updated_by_user = models.CharField(max_length=255, null=True, blank=True)
    joined_datetime = models.DateTimeField(null=True, blank=True)
    
    # API timestamp fields (parsed from 'created' and 'updated' in API)
    created = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    
    # Last location reading (renamed from lastreading in API)
    last_reading = models.JSONField(null=True, blank=True)
    
    # SSO integration
    okta_user_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Tracking fields
    updated_at = models.DateTimeField(auto_now=True)
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
    
    # API timestamp fields (parsed from 'created' and 'updated' in API)
    created = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_arrivy_group'
        verbose_name = 'Arrivy Group'
        verbose_name_plural = 'Arrivy Groups'

    def __str__(self):
        return f"{self.name} ({self.id})" if self.name else f"Group {self.id}"


class Arrivy_Task(models.Model):
    """Arrivy Task model - represents tasks/appointments from official Arrivy tasks endpoint"""
    # Primary identification
    id = models.CharField(max_length=50, primary_key=True)
    url_safe_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    
    # Audit trail
    owner = models.CharField(max_length=50, null=True, blank=True)
    created_by = models.CharField(max_length=50, null=True, blank=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)
    created_by_user = models.CharField(max_length=255, null=True, blank=True)
    updated_by_user = models.CharField(max_length=255, null=True, blank=True)
    
    # API timestamp fields
    created = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    
    # Scheduling - datetime fields (combined date/time from API)
    start_datetime = models.DateTimeField(null=True, blank=True)
    start_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    start_datetime_timezone = models.CharField(max_length=50, null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    end_datetime_timezone = models.CharField(max_length=50, null=True, blank=True)
    due_datetime = models.DateTimeField(null=True, blank=True)
    due_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    
    # Status and workflow
    status = models.CharField(max_length=255, null=True, blank=True)
    status_title = models.CharField(max_length=255, null=True, blank=True)
    template_type = models.CharField(max_length=50, null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # Changed to IntegerField for minutes
    unscheduled = models.BooleanField(default=False)
    self_scheduling = models.BooleanField(default=False)
    
    # Customer information (flattened from nested API structure)
    customer_id = models.CharField(max_length=50, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_first_name = models.CharField(max_length=255, null=True, blank=True)
    customer_last_name = models.CharField(max_length=255, null=True, blank=True)
    customer_company_name = models.CharField(max_length=255, null=True, blank=True)
    customer_notes = models.TextField(null=True, blank=True)
    customer_timezone = models.CharField(max_length=50, null=True, blank=True)
    
    # Customer contact information
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_mobile_number = models.CharField(max_length=20, null=True, blank=True)
    
    # Customer address information
    customer_address_line_1 = models.CharField(max_length=255, null=True, blank=True)
    customer_address_line_2 = models.CharField(max_length=255, null=True, blank=True)
    customer_address = models.TextField(null=True, blank=True)  # Complete address
    customer_city = models.CharField(max_length=100, null=True, blank=True)
    customer_state = models.CharField(max_length=100, null=True, blank=True)
    customer_country = models.CharField(max_length=100, null=True, blank=True)
    customer_zipcode = models.CharField(max_length=50, null=True, blank=True)
    customer_exact_location = models.JSONField(null=True, blank=True)
    is_customer_address_geo_coded = models.BooleanField(default=False)
    use_lat_lng_address = models.BooleanField(default=False)
    
    # Assignment and resources
    entity_ids = models.JSONField(null=True, blank=True)
    crew_ids = models.JSONField(null=True, blank=True)
    worker_ids = models.JSONField(null=True, blank=True)
    number_of_workers_required = models.IntegerField(null=True, blank=True)
    resource_ids = models.JSONField(null=True, blank=True)
    
    # External integration
    external_type = models.CharField(max_length=100, null=True, blank=True)
    external_resource_type = models.CharField(max_length=100, null=True, blank=True)
    linked_internal_ref = models.CharField(max_length=50, null=True, blank=True)
    linked_external_ref = models.CharField(max_length=255, null=True, blank=True)
    is_linked = models.BooleanField(default=False)
    
    # Supply and logistics
    is_supply_provided_locked = models.BooleanField(default=False)
    is_supply_returned_locked = models.BooleanField(default=False)
    
    # Routing and navigation
    route_id = models.CharField(max_length=50, null=True, blank=True)
    internal_route_id = models.CharField(max_length=50, null=True, blank=True)
    routes = models.JSONField(null=True, blank=True)
    entity_routes = models.JSONField(null=True, blank=True)
    mileage_data = models.JSONField(null=True, blank=True)  # Array in API (renamed to avoid conflict)
    additional_addresses = models.JSONField(null=True, blank=True)
    current_destination = models.JSONField(null=True, blank=True)
    
    # Time tracking
    travel_time = models.CharField(max_length=255, null=True, blank=True)
    wait_time = models.CharField(max_length=255, null=True, blank=True)
    task_time = models.CharField(max_length=255, null=True, blank=True)
    total_time = models.CharField(max_length=255, null=True, blank=True)
    
    # Performance metrics
    rating = models.FloatField(null=True, blank=True)
    rating_text = models.TextField(null=True, blank=True)
    
    # Communication tracking
    outbound_sms_count = models.IntegerField(null=True, blank=True)
    inbound_sms_count = models.IntegerField(null=True, blank=True)
    outbound_email_count = models.IntegerField(null=True, blank=True)
    inbound_email_count = models.IntegerField(null=True, blank=True)
    
    # Documents and files
    document_ids = models.JSONField(null=True, blank=True)
    file_ids = models.JSONField(null=True, blank=True)
    files = models.JSONField(null=True, blank=True)
    forms = models.JSONField(null=True, blank=True)
    
    # Additional data
    extra_fields = models.JSONField(null=True, blank=True)
    template_extra_fields = models.JSONField(null=True, blank=True)
    entity_confirmation_statuses = models.JSONField(null=True, blank=True)
    items = models.JSONField(null=True, blank=True)
    series_id = models.CharField(max_length=50, null=True, blank=True)
    skill_details = models.JSONField(null=True, blank=True)
    
    # Legacy fields (kept for backward compatibility)
    # Note: These may be deprecated in future versions
    task_id = models.CharField(max_length=255, null=True, blank=True)  # Mapped from id
    task_title = models.CharField(max_length=255, null=True, blank=True)  # Mapped from title
    first_name = models.CharField(max_length=255, null=True, blank=True)  # Mapped from customer_first_name
    last_name = models.CharField(max_length=255, null=True, blank=True)  # Mapped from customer_last_name
    email = models.EmailField(null=True, blank=True)  # Could be from customer data
    mobile_number = models.CharField(max_length=50, null=True, blank=True)  # Could be from customer data
    address = models.TextField(null=True, blank=True)  # Mapped from customer_address
    city = models.CharField(max_length=255, null=True, blank=True)  # Mapped from customer_city
    state = models.CharField(max_length=255, null=True, blank=True)  # Mapped from customer_state
    zipcode = models.CharField(max_length=50, null=True, blank=True)  # Mapped from customer_zipcode
    country = models.CharField(max_length=255, null=True, blank=True)  # Mapped from customer_country
    latitude = models.FloatField(null=True, blank=True)  # From customer_exact_location
    longitude = models.FloatField(null=True, blank=True)  # From customer_exact_location
    start_date = models.DateField(null=True, blank=True)  # Derived from start_datetime
    start_time = models.TimeField(null=True, blank=True)  # Derived from start_datetime
    end_date = models.DateField(null=True, blank=True)  # Derived from end_datetime
    end_time = models.TimeField(null=True, blank=True)  # Derived from end_datetime
    template = models.CharField(max_length=255, null=True, blank=True)
    group = models.CharField(max_length=255, null=True, blank=True)
    timezone = models.CharField(max_length=255, null=True, blank=True)
    instructions = models.TextField(null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    created_on = models.DateTimeField(null=True, blank=True)  # Mapped from created
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
    company = models.CharField(max_length=255, null=True, blank=True)
    customer_type = models.CharField(max_length=255, null=True, blank=True)
    address_2 = models.TextField(null=True, blank=True)
    start_timezone = models.CharField(max_length=255, null=True, blank=True)
    end_timezone = models.CharField(max_length=255, null=True, blank=True)
    expected_start_date = models.DateField(null=True, blank=True)
    expected_end_date = models.DateField(null=True, blank=True)
    actual_start_time = models.DateTimeField(null=True, blank=True)
    actual_end_time = models.DateTimeField(null=True, blank=True)
    mileage = models.FloatField(null=True, blank=True)  # Legacy field - keep as FloatField for now
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
    
    # Tracking fields
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_arrivy_task'
        verbose_name = 'Arrivy Task'
        verbose_name_plural = 'Arrivy Tasks'

    def __str__(self):
        return f"{self.title or self.task_title} ({self.id})"


class Arrivy_TaskStatus(models.Model):
    """Represents the status of a task in Arrivy."""
    id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    
    # API timestamp fields (consistent with other models)
    created = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    
    # Tracking fields
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

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


class Arrivy_Booking(models.Model):
    """Arrivy Booking model - represents bookings from official Arrivy bookings endpoint"""
    
    # Primary identification
    id = models.CharField(max_length=50, primary_key=True)
    url_safe_id = models.CharField(max_length=255, null=True, blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    title = models.CharField(max_length=500, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    details = models.TextField(null=True, blank=True)
    
    # Audit trail
    owner = models.CharField(max_length=50, null=True, blank=True)
    created_by = models.CharField(max_length=50, null=True, blank=True)
    updated_by = models.CharField(max_length=50, null=True, blank=True)
    created_by_user = models.CharField(max_length=255, null=True, blank=True)
    updated_by_user = models.CharField(max_length=255, null=True, blank=True)
    
    # API timestamp fields
    created = models.DateTimeField(null=True, blank=True)
    updated = models.DateTimeField(null=True, blank=True)
    created_time = models.DateTimeField(null=True, blank=True)  # Alternative timestamp field
    updated_time = models.DateTimeField(null=True, blank=True)  # Alternative timestamp field
    
    # Scheduling - datetime fields (combined date/time from API)
    start_datetime = models.DateTimeField(null=True, blank=True)
    end_datetime = models.DateTimeField(null=True, blank=True)
    start_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    end_datetime_original_iso_str = models.CharField(max_length=50, null=True, blank=True)
    
    # Derived scheduling fields (for easier querying)
    start_date = models.DateField(null=True, blank=True)  # Derived from start_datetime
    start_time = models.TimeField(null=True, blank=True)  # Derived from start_datetime
    end_date = models.DateField(null=True, blank=True)  # Derived from end_datetime
    end_time = models.TimeField(null=True, blank=True)  # Derived from end_datetime
    
    # Status and workflow
    status = models.CharField(max_length=50, null=True, blank=True)
    status_id = models.IntegerField(null=True, blank=True)
    task_type = models.CharField(max_length=100, null=True, blank=True)
    
    # Duration and timing
    duration_estimate = models.IntegerField(null=True, blank=True)  # in minutes
    actual_start_datetime = models.DateTimeField(null=True, blank=True)
    actual_end_datetime = models.DateTimeField(null=True, blank=True)
    timezone = models.CharField(max_length=50, null=True, blank=True)
    
    # Boolean flags
    is_recurring = models.BooleanField(default=False)
    is_all_day = models.BooleanField(default=False)
    enable_time_window_display = models.BooleanField(default=False)
    unscheduled = models.BooleanField(default=False)
    
    # Customer information
    customer_id = models.CharField(max_length=50, null=True, blank=True)
    customer_name = models.CharField(max_length=255, null=True, blank=True)
    customer_first_name = models.CharField(max_length=255, null=True, blank=True)
    customer_last_name = models.CharField(max_length=255, null=True, blank=True)
    customer_company_name = models.CharField(max_length=255, null=True, blank=True)
    customer_email = models.EmailField(null=True, blank=True)
    customer_phone = models.CharField(max_length=20, null=True, blank=True)
    customer_mobile_number = models.CharField(max_length=20, null=True, blank=True)
    customer_notes = models.TextField(null=True, blank=True)
    customer_timezone = models.CharField(max_length=50, null=True, blank=True)
    
    # Address information
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
    
    # Derived location fields (for easier querying)
    latitude = models.FloatField(null=True, blank=True)  # From exact_location
    longitude = models.FloatField(null=True, blank=True)  # From exact_location
    
    # Team and resource assignment
    assigned_team_members = models.JSONField(null=True, blank=True)
    team_member_ids = models.TextField(null=True, blank=True)
    entity_ids = models.JSONField(null=True, blank=True)
    crew_ids = models.JSONField(null=True, blank=True)
    worker_ids = models.JSONField(null=True, blank=True)
    number_of_workers_required = models.IntegerField(null=True, blank=True)
    resource_ids = models.JSONField(null=True, blank=True)
    
    # Template and configuration
    template_id = models.CharField(max_length=50, null=True, blank=True)
    template = models.CharField(max_length=255, null=True, blank=True)
    template_extra_fields = models.JSONField(null=True, blank=True)
    extra_fields = models.JSONField(null=True, blank=True)
    custom_fields = models.JSONField(null=True, blank=True)
    
    # Group and organizational
    group = models.CharField(max_length=255, null=True, blank=True)
    group_id = models.CharField(max_length=50, null=True, blank=True)
    
    # External integration
    external_type = models.CharField(max_length=100, null=True, blank=True)
    external_resource_type = models.CharField(max_length=100, null=True, blank=True)
    linked_internal_ref = models.CharField(max_length=50, null=True, blank=True)
    linked_external_ref = models.CharField(max_length=255, null=True, blank=True)
    is_linked = models.BooleanField(default=False)
    
    # Routing and navigation
    route_id = models.CharField(max_length=50, null=True, blank=True)
    route_name = models.CharField(max_length=255, null=True, blank=True)
    internal_route_id = models.CharField(max_length=50, null=True, blank=True)
    routes = models.JSONField(null=True, blank=True)
    entity_routes = models.JSONField(null=True, blank=True)
    additional_addresses = models.JSONField(null=True, blank=True)
    current_destination = models.JSONField(null=True, blank=True)
    
    # Communication and notifications
    notifications = models.JSONField(null=True, blank=True)
    outbound_sms_count = models.IntegerField(null=True, blank=True)
    inbound_sms_count = models.IntegerField(null=True, blank=True)
    outbound_email_count = models.IntegerField(null=True, blank=True)
    inbound_email_count = models.IntegerField(null=True, blank=True)
    
    # Performance and tracking
    rating = models.FloatField(null=True, blank=True)
    rating_text = models.TextField(null=True, blank=True)
    travel_time = models.CharField(max_length=255, null=True, blank=True)
    wait_time = models.CharField(max_length=255, null=True, blank=True)
    task_time = models.CharField(max_length=255, null=True, blank=True)
    total_time = models.CharField(max_length=255, null=True, blank=True)
    mileage = models.FloatField(null=True, blank=True)
    
    # Documents and files
    document_ids = models.JSONField(null=True, blank=True)
    file_ids = models.JSONField(null=True, blank=True)
    files = models.JSONField(null=True, blank=True)
    forms = models.JSONField(null=True, blank=True)
    
    # Instructions and workflow
    instructions = models.TextField(null=True, blank=True)
    
    # Additional tracking
    items = models.JSONField(null=True, blank=True)
    entity_confirmation_statuses = models.JSONField(null=True, blank=True)
    
    # Tracking fields
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_arrivy_booking'
        verbose_name = 'Arrivy Booking'
        verbose_name_plural = 'Arrivy Bookings'

    def __str__(self):
        return f"{self.title} ({self.id})" if self.title else f"Booking {self.id}"


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
