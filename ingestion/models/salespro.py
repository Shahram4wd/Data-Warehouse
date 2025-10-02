from django.db import models
from django.utils import timezone

class SalesPro_Office(models.Model):
    """SalesPro office model based on SalesPro offices CSV export"""

    office_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    can_search_all_estimates = models.BooleanField(default=False)
    last_edit_user = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(blank=True, null=True, help_text="Original creation date from SalesPro")
    updated_at = models.DateTimeField(blank=True, null=True, help_text="Original last update date from SalesPro")
    
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)
    last_edit_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        db_table = 'salespro_office'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Office data stored in ingestion schema'
        verbose_name = 'SalesPro Office'
        verbose_name_plural = 'SalesPro Offices'
        indexes = [
            models.Index(fields=['company_id']),
            models.Index(fields=['name']),
        ]

    def __str__(self):
        return self.name or self.office_id

class SalesPro_User(models.Model):
    """SalesPro user model based on SalesPro export CSV
    Source CSV columns include: objectId, username, nameFirst, nameLast, isActive, isManager,
    createdAt, updatedAt, allowedOffices, canActivateUsers, canChangeSettings, canSubmitCreditApps,
    company, deactivatedDate, disableChangeCompany, email, identifier, isAvailableToCall,
    lastLoginDate, licenseNumber, phoneNumber, selectedOffice
    """

    user_object_id = models.CharField(max_length=50, primary_key=True)
    username = models.CharField(max_length=255, blank=True, null=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.EmailField(blank=True, null=True)
    phone_number = models.CharField(max_length=50, blank=True, null=True)

    # Status and roles
    is_active = models.BooleanField(default=True)
    is_manager = models.BooleanField(default=False)
    is_available_to_call = models.BooleanField(default=False)

    # Permissions
    can_activate_users = models.BooleanField(default=False)
    can_change_settings = models.BooleanField(default=False)
    can_submit_credit_apps = models.BooleanField(default=False)
    disable_change_company = models.BooleanField(default=False)

    # Organization
    company_id = models.CharField(max_length=50, blank=True, null=True)
    selected_office = models.CharField(max_length=50, blank=True, null=True)
    allowed_offices = models.TextField(blank=True, null=True, help_text="JSON array from CSV of Office pointers")

    # Identity and compliance
    identifier = models.CharField(max_length=255, blank=True, null=True)
    license_number = models.CharField(max_length=100, blank=True, null=True)

    # Timestamps from SalesPro
    created_at = models.DateTimeField(blank=True, null=True, help_text="Original creation date from SalesPro")
    updated_at = models.DateTimeField(blank=True, null=True, help_text="Original last update date from SalesPro")
    last_login_date = models.DateTimeField(blank=True, null=True)
    deactivated_date = models.DateTimeField(blank=True, null=True)
    
    # Sync tracking timestamps
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salespro_user'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro User data stored in ingestion schema'
        verbose_name = 'SalesPro User'
        verbose_name_plural = 'SalesPro Users'
        indexes = [
            models.Index(fields=['username']),
            models.Index(fields=['email']),
            models.Index(fields=['company_id']),
        ]

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        return name or (self.username or self.user_object_id)

class SalesPro_CreditApplication(models.Model):
    leap_credit_app_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    sales_rep_id = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    credit_app_vendor = models.CharField(max_length=255, blank=True, null=True)
    credit_app_vendor_id = models.CharField(max_length=255, blank=True, null=True)
    credit_app_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    credit_app_status = models.CharField(max_length=255, blank=True, null=True)
    credit_app_note = models.TextField(null=True, blank=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salespro_credit_application'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Credit Application data stored in ingestion schema'
        verbose_name = 'Credit Application'
        verbose_name_plural = 'Credit Applications'

    def __str__(self):
        return f"{self.customer_id} - {self.credit_app_vendor}"


class SalesPro_Customer(models.Model):
    customer_id = models.CharField(max_length=255, primary_key=True)
    estimate_id = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    customer_first_name = models.CharField(max_length=255, blank=True, null=True)
    customer_last_name = models.CharField(max_length=255, blank=True, null=True)
    crm_source = models.CharField(max_length=255, blank=True, null=True)
    crm_source_id = models.CharField(max_length=255, blank=True, null=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salespro_customer'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Customer data stored in ingestion schema'
        verbose_name = 'Customer'
        verbose_name_plural = 'Customers'

    def __str__(self):
        return f"{self.customer_first_name} {self.customer_last_name}"


class SalesPro_Estimate(models.Model):
    estimate_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    office_id = models.CharField(max_length=255, blank=True, null=True)
    office_name = models.CharField(max_length=255, blank=True, null=True)
    sales_rep_id = models.CharField(max_length=255, blank=True, null=True)
    sales_rep_first_name = models.CharField(max_length=255, blank=True, null=True)
    sales_rep_last_name = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    customer_first_name = models.CharField(max_length=255, blank=True, null=True)
    customer_last_name = models.CharField(max_length=255, blank=True, null=True)
    street_address = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=100, blank=True, null=True)
    zip_code = models.CharField(max_length=20, blank=True, null=True)
    sale_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    is_sale = models.BooleanField(default=False)
    job_type = models.CharField(max_length=100, blank=True, null=True)
    finance_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    bank_name = models.CharField(max_length=255, blank=True, null=True)
    loan_name = models.CharField(max_length=255, blank=True, null=True)
    down_payment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    has_credit_app = models.BooleanField(default=False)
    document_count = models.BigIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True, help_text="Original creation date from SalesPro")
    updated_at = models.DateTimeField(blank=True, null=True, help_text="Original last update date from SalesPro")
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salespro_estimate'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Estimate data stored in ingestion schema'
        verbose_name = 'Estimate'
        verbose_name_plural = 'Estimates'

    def __str__(self):
        return self.estimate_id


class SalesPro_LeadResult(models.Model):
    # Identity
    estimate_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True, db_index=True)

    # Result / reasons
    appointment_result = models.CharField(max_length=255, blank=True, null=True)
    result_reason_demo_not_sold = models.CharField(max_length=255, blank=True, null=True)  # "(objection)"
    result_reason_no_demo = models.CharField(max_length=255, blank=True, null=True)        # "(REQUIRES SALES MANGER APPROVAL)"

    # Presence
    both_homeowners_present = models.BooleanField(blank=True, null=True)
    sales_manager_present = models.BooleanField(blank=True, null=True)

    # Money / amounts
    job_size = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    total_job_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    one_year_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    last_price_offered = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    last_payment_offered = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    no_brainer_commitment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    deposit_type = models.CharField(max_length=255, blank=True, null=True)
    deposit_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    balance_type = models.CharField(max_length=255, blank=True, null=True)   # aka Balance Form Of Payment
    balance_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Financing / payment prefs
    preferred_payment = models.CharField(max_length=255, blank=True, null=True)
    financing = models.CharField(max_length=255, blank=True, null=True)
    financing_approved = models.BooleanField(blank=True, null=True)
    loan_docs_signed = models.BooleanField(blank=True, null=True)

    # Category / scheduling
    job_type = models.CharField(max_length=255, blank=True, null=True)
    services = models.CharField(max_length=255, blank=True, null=True)
    requested_start_month = models.CharField(max_length=255, blank=True, null=True)
    deadline = models.CharField(max_length=255, blank=True, null=True)
    timing = models.CharField(max_length=255, blank=True, null=True)  # e.g. "-RTG ..."
    scheduling_notes = models.TextField(blank=True, null=True)        # appears as "Scheduling Notes"

    # Process flags
    upload_estimate_sheet_company_cam = models.BooleanField(blank=True, null=True)  # "Did you Upload Estimate Sheet to Company Cam"
    st8_completed = models.BooleanField(blank=True, null=True)                      # "Did you complete your ST-8 Form Before leaving house?" / variant
    did_use_company_cam = models.BooleanField(blank=True, null=True)               # "Did you use company cam"
    client_most_likely_to_add_on = models.CharField(max_length=255, blank=True, null=True)  # "Client most likely to add on:"

    # Narrative / qualifiers
    warm_up_topic = models.CharField(max_length=255, blank=True, null=True)
    urgency_time_frame = models.CharField(max_length=255, blank=True, null=True)
    additional_services_demoed_priced = models.CharField(max_length=255, blank=True, null=True)

    describe_rapport_hot_button = models.TextField(blank=True, null=True)
    company_story_pain_point = models.TextField(blank=True, null=True)
    call_to_action = models.TextField(blank=True, null=True)
    price_conditioning_response = models.CharField(max_length=255, blank=True, null=True)
    customers_final_price_commitment = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    # Free-form notes seen in data
    notes = models.TextField(blank=True, null=True)                # "Notes", "Project Notes"
    closing_notes = models.TextField(blank=True, null=True)        # "Closing Notes (how could you have booked this job)"
    notes_for_install_team = models.TextField(blank=True, null=True)  # "Notes for Install Team"
    details_discussed_for_install = models.TextField(blank=True, null=True)  # "Details Discussed With Homeowner That Installation Needs To Know"

    # Misc selections / tools
    measurement_tool = models.CharField(max_length=255, blank=True, null=True)  # "Measurement Tool(s) Used"
    dumpster_preference = models.CharField(max_length=255, blank=True, null=True)
    color_selection = models.TextField(blank=True, null=True)

    # Other qualifiers
    has_consider_solar = models.CharField(max_length=64, blank=True, null=True)

    # Status bucket and raw data storage
    status_bucket = models.CharField(max_length=64, blank=True, null=True)  # e.g. "[HRE] Demo Sold", "[CC] Rescheduled"
    lead_results_raw = models.JSONField(blank=True, null=True)              # Original JSON data for reference

    # Optional: precomputed TSV for fast full-text search (manage via signal/trigger if you want it)
    # search = SearchVectorField(null=True, editable=False)

    # Sync stamps
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'salespro_lead_result'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Lead Result data stored in ingestion schema'
        verbose_name = 'Lead Result'
        verbose_name_plural = 'Lead Results'
        # No unique_together needed since estimate_id is primary key
        ordering = ['-sync_updated_at']
        indexes = [
            models.Index(fields=["company_id"]),
            models.Index(fields=["appointment_result"]),
            models.Index(fields=["status_bucket"]),
            models.Index(fields=["job_size"]),
            models.Index(fields=["sync_updated_at"]),
        ]

    def __str__(self):
        return f"{self.estimate_id} - {self.appointment_result}"


class SalesPro_LeadResultLineItem(models.Model):
    """Line items for SalesPro Lead Results (e.g., Job Type 1, Job Type 2, etc.)"""
    estimate = models.ForeignKey(
        SalesPro_LeadResult,
        on_delete=models.CASCADE,
        related_name="line_items",
        db_column="estimate_id",
    )
    job_type_number = models.PositiveSmallIntegerField()  # 1, 2, 3, 4, 5, 6
    job_type = models.CharField(max_length=255, blank=True, null=True)  # e.g., "-Roofing", "-Gutters and/or Guards"
    job_type_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)

    class Meta:
        db_table = 'salespro_lead_result_line_item'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Lead Result Line Items stored in ingestion schema'
        verbose_name = 'Lead Result Line Item'
        verbose_name_plural = 'Lead Result Line Items'
        unique_together = (("estimate", "job_type_number"),)
        indexes = [
            models.Index(fields=["estimate", "job_type_number"]),
        ]

    def __str__(self):
        return f"{self.estimate.estimate_id} - Job Type {self.job_type_number}: {self.job_type} ({self.job_type_amount})"