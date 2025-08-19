from django.db import models

class SalesPro_Office(models.Model):
    """SalesPro office model based on SalesPro offices CSV export"""

    office_id = models.CharField(max_length=50, primary_key=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=50, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)

    can_search_all_estimates = models.BooleanField(default=False)
    last_edit_user = models.CharField(max_length=255, blank=True, null=True)

    sync_created_at = models.DateTimeField(blank=True, null=True)
    sync_updated_at = models.DateTimeField(blank=True, null=True)
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

    # Timestamps
    sync_created_at = models.DateTimeField(blank=True, null=True)
    sync_updated_at = models.DateTimeField(blank=True, null=True)
    last_login_date = models.DateTimeField(blank=True, null=True)
    deactivated_date = models.DateTimeField(blank=True, null=True)

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
    sync_created_at = models.DateTimeField()
    sync_updated_at = models.DateTimeField()

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
    sync_created_at = models.DateTimeField()
    sync_updated_at = models.DateTimeField()

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
    sync_created_at = models.DateTimeField()
    sync_updated_at = models.DateTimeField()

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
    # Use estimate_id as primary key to keep only latest version
    estimate_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    sync_created_at = models.DateTimeField()
    sync_updated_at = models.DateTimeField()
    
    # Normalized lead result fields based on the sample data
    appointment_result = models.CharField(max_length=255, blank=True, null=True)  # "Appointment Result"
    result_reason_demo_not_sold = models.CharField(max_length=255, blank=True, null=True)  # "Result Reason - Demo Not Sold (objection)"
    result_reason_no_demo = models.CharField(max_length=255, blank=True, null=True)  # "Result Reason - No Demo (REQUIRES SALES MANGER APPROVAL)"
    both_homeowners_present = models.CharField(max_length=10, blank=True, null=True)  # "Both Homeowners Present?" (Yes/No)
    one_year_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # "One Year Price"
    last_price_offered = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)  # "Last Price Offered"
    preferred_payment = models.CharField(max_length=255, blank=True, null=True)  # "Preferred Payment"
    notes = models.TextField(blank=True, null=True)  # "Notes"
    
    # Keep the original JSON field as backup/reference during transition
    lead_results_raw = models.TextField(blank=True, null=True, help_text="Original JSON data for reference")

    class Meta:
        db_table = 'salespro_lead_result'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Lead Result data stored in ingestion schema'
        verbose_name = 'Lead Result'
        verbose_name_plural = 'Lead Results'
        # No unique_together needed since estimate_id is primary key
        ordering = ['-sync_updated_at']

    def __str__(self):
        return f"{self.estimate_id} - {self.appointment_result}"


class SalesPro_Payment(models.Model):
    payment_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_type = models.CharField(max_length=100, blank=True, null=True)
    payment_description = models.CharField(max_length=255, blank=True, null=True)
    payment_success = models.BooleanField(default=False)
    sync_created_at = models.DateTimeField()
    sync_updated_at = models.DateTimeField()

    class Meta:
        db_table = 'salespro_payment'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro Payment data stored in ingestion schema'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return self.payment_id


class SalesPro_UserActivity(models.Model):
    # Add a proper primary key for framework compliance
    id = models.AutoField(primary_key=True)
    sync_created_at = models.DateTimeField()
    user_id = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    local_customer_uuid = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    activity_note = models.TextField(blank=True, null=True)
    key_metric = models.CharField(max_length=255, blank=True, null=True)
    activity_identifier = models.CharField(max_length=255, blank=True, null=True)
    price_type = models.CharField(max_length=255, blank=True, null=True)
    price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    original_row_num = models.BigIntegerField(blank=True, null=True)

    class Meta:
        db_table = 'salespro_user_activity'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'SalesPro User Activity data stored in ingestion schema'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        # Use combination of sync_created_at, user_id, and activity_note as unique constraint
        unique_together = [['sync_created_at', 'user_id', 'activity_note']]
        # Order by sync_created_at by default
        ordering = ['sync_created_at']

    def __str__(self):
        return f"{self.user_id} - {self.activity_identifier}"
