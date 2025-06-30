from django.db import models
from django.utils import timezone

class Hubspot_Contact(models.Model):  # Updated table name
    id = models.CharField(max_length=50, primary_key=True)
    address = models.TextField(null=True, blank=True)
    adgroupid = models.CharField(max_length=255, null=True, blank=True)
    ap_leadid = models.CharField(max_length=255, null=True, blank=True)
    campaign_content = models.CharField(max_length=255, null=True, blank=True)
    campaign_name = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    clickcheck = models.CharField(max_length=255, null=True, blank=True)
    clicktype = models.CharField(max_length=255, null=True, blank=True)
    comments = models.TextField(null=True, blank=True)
    createdate = models.DateTimeField(null=True, blank=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    firstname = models.CharField(max_length=255, null=True, blank=True)
    hs_google_click_id = models.CharField(max_length=255, null=True, blank=True)
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    lastmodifieddate = models.DateTimeField(null=True, blank=True)
    lastname = models.CharField(max_length=255, null=True, blank=True)
    lead_salesrabbit_lead_id = models.CharField(max_length=255, null=True, blank=True)
    marketsharp_id = models.CharField(max_length=255, null=True, blank=True)
    msm_source = models.CharField(max_length=255, null=True, blank=True)
    original_lead_source = models.TextField(null=True, blank=True)
    original_lead_source_created = models.DateTimeField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    reference_code = models.CharField(max_length=255, null=True, blank=True)
    search_terms = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=255, null=True, blank=True)
    tier = models.CharField(max_length=255, null=True, blank=True)
    trustedform_cert_url = models.URLField(null=True, blank=True)
    vendorleadid = models.CharField(max_length=255, null=True, blank=True)
    vertical = models.CharField(max_length=255, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    
    def __str__(self):
        return f"{self.firstname} {self.lastname} ({self.email})"

class Hubspot_Deal(models.Model):  # Updated table name
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

class Hubspot_SyncHistory(models.Model):  # Updated table name
    endpoint = models.CharField(max_length=100)
    last_synced_at = models.DateTimeField(null=True, blank=True)
    
    def __str__(self):
        return f"{self.endpoint} - {self.last_synced_at}"
    
    class Meta:
        verbose_name_plural = "Hubspot Sync Histories"

class Hubspot_Appointment(models.Model):
    """HubSpot Appointment model for custom object 0-421"""
    id = models.CharField(max_length=50, primary_key=True)  # hs_object_id
    
    # Basic appointment info
    appointment_id = models.CharField(max_length=255, null=True, blank=True)
    genius_appointment_id = models.CharField(max_length=255, null=True, blank=True)
    marketsharp_id = models.CharField(max_length=255, null=True, blank=True)
      # HubSpot specific fields
    hs_appointment_name = models.CharField(max_length=255, null=True, blank=True)
    hs_appointment_start = models.DateTimeField(null=True, blank=True)
    hs_appointment_end = models.DateTimeField(null=True, blank=True)
    hs_duration = models.IntegerField(null=True, blank=True)
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    hs_createdate = models.DateTimeField(null=True, blank=True)
    hs_lastmodifieddate = models.DateTimeField(null=True, blank=True)
    hs_pipeline = models.CharField(max_length=255, null=True, blank=True)
    hs_pipeline_stage = models.CharField(max_length=255, null=True, blank=True)
    
    # HubSpot system fields
    hs_all_accessible_team_ids = models.JSONField(null=True, blank=True)
    hs_all_assigned_business_unit_ids = models.JSONField(null=True, blank=True)
    hs_all_owner_ids = models.JSONField(null=True, blank=True)
    hs_all_team_ids = models.JSONField(null=True, blank=True)
    hs_created_by_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_merged_object_ids = models.JSONField(null=True, blank=True)
    hs_object_source = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_1 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_2 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_3 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_id = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_label = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_owning_teams = models.JSONField(null=True, blank=True)
    hs_read_only = models.BooleanField(null=True, blank=True)
    hs_shared_team_ids = models.JSONField(null=True, blank=True)
    hs_shared_user_ids = models.JSONField(null=True, blank=True)
    hs_unique_creation_key = models.CharField(max_length=255, null=True, blank=True)
    hs_updated_by_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_user_ids_of_all_notification_followers = models.JSONField(null=True, blank=True)
    hs_user_ids_of_all_notification_unfollowers = models.JSONField(null=True, blank=True)
    hs_user_ids_of_all_owners = models.JSONField(null=True, blank=True)
    hs_was_imported = models.BooleanField(null=True, blank=True)
    
    # Contact information
    first_name = models.CharField(max_length=255, null=True, blank=True)
    last_name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    phone1 = models.CharField(max_length=20, null=True, blank=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    
    # Address information
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    
    # Appointment scheduling
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    duration = models.IntegerField(null=True, blank=True)  # in minutes
    
    # Appointment status and response
    appointment_status = models.CharField(max_length=100, null=True, blank=True)
    appointment_response = models.CharField(max_length=100, null=True, blank=True)
    is_complete = models.BooleanField(default=False)
    
    # Services and interests
    appointment_services = models.TextField(null=True, blank=True)
    lead_services = models.TextField(null=True, blank=True)
    product_interest_primary = models.CharField(max_length=255, null=True, blank=True)
    product_interest_secondary = models.CharField(max_length=255, null=True, blank=True)
    
    # User and assignment info
    user_id = models.CharField(max_length=255, null=True, blank=True)
    canvasser = models.CharField(max_length=255, null=True, blank=True)
    canvasser_id = models.CharField(max_length=255, null=True, blank=True)
    canvasser_email = models.EmailField(null=True, blank=True)
    hubspot_owner_id = models.CharField(max_length=255, null=True, blank=True)
    hubspot_owner_assigneddate = models.DateTimeField(null=True, blank=True)
    hubspot_team_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Division and organizational info
    division_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Source tracking
    primary_source = models.CharField(max_length=255, null=True, blank=True)
    secondary_source = models.CharField(max_length=255, null=True, blank=True)
    prospect_id = models.CharField(max_length=255, null=True, blank=True)
    prospect_source_id = models.CharField(max_length=255, null=True, blank=True)
    hscontact_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Appointment type and completion
    type_id = models.CharField(max_length=255, null=True, blank=True)
    type_id_text = models.CharField(max_length=255, null=True, blank=True)
    marketsharp_appt_type = models.CharField(max_length=255, null=True, blank=True)
    
    # Completion details
    complete_date = models.DateTimeField(null=True, blank=True)
    complete_outcome_id = models.CharField(max_length=255, null=True, blank=True)
    complete_outcome_id_text = models.CharField(max_length=255, null=True, blank=True)
    complete_user_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Confirmation details
    confirm_date = models.DateTimeField(null=True, blank=True)
    confirm_user_id = models.CharField(max_length=255, null=True, blank=True)
    confirm_with = models.CharField(max_length=255, null=True, blank=True)
    
    # Assignment details
    assign_date = models.DateTimeField(null=True, blank=True)
    add_date = models.DateTimeField(null=True, blank=True)
    add_user_id = models.CharField(max_length=255, null=True, blank=True)
    
    # Arrivy integration fields
    arrivy_appt_date = models.DateTimeField(null=True, blank=True)
    arrivy_confirm_date = models.DateTimeField(null=True, blank=True)
    arrivy_confirm_user = models.CharField(max_length=255, null=True, blank=True)
    arrivy_created_by = models.CharField(max_length=255, null=True, blank=True)
    arrivy_object_id = models.CharField(max_length=255, null=True, blank=True)
    arrivy_status = models.CharField(max_length=255, null=True, blank=True)
    arrivy_user = models.CharField(max_length=255, null=True, blank=True)
    arrivy_user_divison_id = models.CharField(max_length=255, null=True, blank=True)
    arrivy_user_external_id = models.CharField(max_length=255, null=True, blank=True)
    arrivy_username = models.CharField(max_length=255, null=True, blank=True)
    
    # SalesPro integration fields
    salespro_both_homeowners = models.BooleanField(null=True, blank=True)
    salespro_deadline = models.DateField(null=True, blank=True)
    salespro_deposit_type = models.CharField(max_length=255, null=True, blank=True)
    salespro_fileurl_contract = models.URLField(null=True, blank=True)
    salespro_fileurl_estimate = models.URLField(null=True, blank=True)
    salespro_financing = models.CharField(max_length=255, null=True, blank=True)
    salespro_job_size = models.CharField(max_length=255, null=True, blank=True)
    salespro_job_type = models.CharField(max_length=255, null=True, blank=True)
    salespro_last_price_offered = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    salespro_notes = models.TextField(null=True, blank=True)
    salespro_one_year_price = models.DecimalField(max_digits=15, decimal_places=2, null=True, blank=True)
    salespro_preferred_payment = models.CharField(max_length=255, null=True, blank=True)
    salespro_requested_start = models.DateField(null=True, blank=True)
    salespro_result = models.CharField(max_length=255, null=True, blank=True)
    salespro_result_notes = models.TextField(null=True, blank=True)
    salespro_result_reason_demo = models.CharField(max_length=255, null=True, blank=True)
    salespro_result_reason_no_demo = models.CharField(max_length=255, null=True, blank=True)
    
    # Additional fields
    notes = models.TextField(null=True, blank=True)
    log = models.TextField(null=True, blank=True)
    title = models.CharField(max_length=255, null=True, blank=True)
    marketing_task_id = models.CharField(max_length=255, null=True, blank=True)
    leap_estimate_id = models.CharField(max_length=255, null=True, blank=True)
    spouses_present = models.BooleanField(null=True, blank=True)
    year_built = models.IntegerField(null=True, blank=True)
    error_details = models.TextField(null=True, blank=True)
    tester_test = models.CharField(max_length=255, null=True, blank=True)
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ingestion_hubspot_appointment'
        verbose_name = 'HubSpot Appointment'
        verbose_name_plural = 'HubSpot Appointments'
        ordering = ['-hs_appointment_start', '-hs_createdate']
        indexes = [
            models.Index(fields=['appointment_id']),
            models.Index(fields=['genius_appointment_id']),
            models.Index(fields=['marketsharp_id']),
            models.Index(fields=['email']),
            models.Index(fields=['hs_appointment_start']),
            models.Index(fields=['appointment_status']),
            models.Index(fields=['is_complete']),
            models.Index(fields=['hubspot_owner_id']),
            models.Index(fields=['division_id']),
        ]
    
    def __str__(self):
        name = f"{self.first_name} {self.last_name}".strip()
        if name:
            return f"{name} - {self.hs_appointment_start or self.date}"
        return f"Appointment {self.id} - {self.hs_appointment_start or self.date}"
    
    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
    
    @property
    def full_address(self):
        parts = [
            self.address1,
            self.address2,
            self.city,
            f"{self.state} {self.zip}".strip()
        ]
        return ", ".join(filter(None, parts))

class Hubspot_AppointmentContactAssociation(models.Model):
    """Direct mapping of appointment to contact associations"""
    appointment_id = models.CharField(max_length=50, null=True, blank=True)
    contact_id = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_hubspot_appointment_contact_assoc'
        unique_together = ('appointment_id', 'contact_id')

    def __str__(self):
        return f"{self.appointment_id} -> {self.contact_id}"

class Hubspot_ContactDivisionAssociation(models.Model):
    """Direct mapping of contact to division associations via custom object 2-37778609"""
    contact_id = models.CharField(max_length=50, null=True, blank=True)
    division_id = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'ingestion_hubspot_contact_division_assoc'
        unique_together = ('contact_id', 'division_id')

    def __str__(self):
        return f"{self.contact_id} -> {self.division_id}"

class Hubspot_Division(models.Model):
    """HubSpot Division model for custom object 2-37778609"""
    id = models.CharField(max_length=50, primary_key=True)  # hs_object_id
    
    # Basic division info
    division_name = models.CharField(max_length=255, null=True, blank=True)
    division_label = models.CharField(max_length=255, null=True, blank=True)
    division_code = models.CharField(max_length=100, null=True, blank=True)
    
    # HubSpot specific fields
    hs_object_id = models.CharField(max_length=255, null=True, blank=True)
    hs_createdate = models.DateTimeField(null=True, blank=True)
    hs_lastmodifieddate = models.DateTimeField(null=True, blank=True)
    hs_pipeline = models.CharField(max_length=255, null=True, blank=True)
    hs_pipeline_stage = models.CharField(max_length=255, null=True, blank=True)
    
    # HubSpot system fields
    hs_all_accessible_team_ids = models.JSONField(null=True, blank=True)
    hs_all_assigned_business_unit_ids = models.JSONField(null=True, blank=True)
    hs_all_owner_ids = models.JSONField(null=True, blank=True)
    hs_all_team_ids = models.JSONField(null=True, blank=True)
    hs_created_by_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_merged_object_ids = models.JSONField(null=True, blank=True)
    hs_object_source = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_1 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_2 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_detail_3 = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_id = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_label = models.CharField(max_length=255, null=True, blank=True)
    hs_object_source_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_owning_teams = models.JSONField(null=True, blank=True)
    hs_read_only = models.BooleanField(null=True, blank=True)
    hs_shared_team_ids = models.JSONField(null=True, blank=True)
    hs_shared_user_ids = models.JSONField(null=True, blank=True)
    hs_unique_creation_key = models.CharField(max_length=255, null=True, blank=True)
    hs_updated_by_user_id = models.CharField(max_length=255, null=True, blank=True)
    hs_user_ids_of_all_notification_followers = models.JSONField(null=True, blank=True)
    hs_user_ids_of_all_notification_unfollowers = models.JSONField(null=True, blank=True)
    hs_user_ids_of_all_owners = models.JSONField(null=True, blank=True)
    hs_was_imported = models.BooleanField(null=True, blank=True)
    
    # Division properties
    status = models.CharField(max_length=100, null=True, blank=True)
    region = models.CharField(max_length=100, null=True, blank=True)
    manager_name = models.CharField(max_length=255, null=True, blank=True)
    manager_email = models.EmailField(null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    
    # Address information
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=10, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ingestion_hubspot_division'
        verbose_name = 'HubSpot Division'
        verbose_name_plural = 'HubSpot Divisions'
    
    def __str__(self):
        return f"{self.division_name or self.division_label or self.id}"


class Hubspot_ZipCode(models.Model):
    zipcode = models.CharField(max_length=10, primary_key=True)
    division = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=255, null=True, blank=True)
    county = models.CharField(max_length=255, null=True, blank=True)
    state = models.CharField(max_length=10, null=True, blank=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    archived = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'ingestion_hubspot_zipcode'
        verbose_name = 'HubSpot ZipCode'
        verbose_name_plural = 'HubSpot ZipCodes'
    
    def __str__(self):
        return f"{self.zipcode} - {self.city}, {self.state}"
