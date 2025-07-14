from django.db import models


class SalesPro_Users(models.Model):
    user_object_id = models.CharField(max_length=50, primary_key=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    username = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    last_login = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    send_credit_apps = models.BooleanField(default=False)
    search_other_users_estimates = models.BooleanField(default=False)
    assigned_office = models.CharField(max_length=255, null=True, blank=True)
    office_id = models.CharField(max_length=50, null=True, blank=True)
    license_number = models.CharField(max_length=100, null=True, blank=True)
    additional_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True, default=0)
    unique_identifier = models.CharField(max_length=255, null=True, blank=True)
    job_representative_id = models.CharField(max_length=50, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'ingestion_salespro_users'
        verbose_name = "SalesPro User"
        verbose_name_plural = "SalesPro Users"

    def __str__(self):
        return f"{self.first_name} {self.last_name} ({self.email})"
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}".strip()


class SalesPro_Appointment(models.Model):
    """Model for SalesPro appointment/sales data from CSV export"""
    id = models.CharField(max_length=50, primary_key=True)  # _id field from CSV
    created_at = models.DateTimeField(null=True, blank=True)  # _created_at
    updated_at = models.DateTimeField(null=True, blank=True)  # _updated_at
    is_sale = models.BooleanField(default=False)  # isSale
    result_full_string = models.TextField(null=True, blank=True)  # resultFullString
    
    # Customer information
    customer_last_name = models.CharField(max_length=100, null=True, blank=True)  # customer.nameLast
    customer_first_name = models.CharField(max_length=100, null=True, blank=True)  # customer.nameFirst
    customer_estimate_name = models.CharField(max_length=255, null=True, blank=True)  # customer.estimateName
    
    # Sales rep information
    salesrep_email = models.EmailField(null=True, blank=True)  # salesrep.email
    salesrep_first_name = models.CharField(max_length=100, null=True, blank=True)  # salesrep.nameFirst
    salesrep_last_name = models.CharField(max_length=100, null=True, blank=True)  # salesrep.nameLast
      # Sale information
    sale_amount = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)  # saleAmount
    
    # Metadata
    imported_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'ingestion_salespro_appointment'
        verbose_name = 'SalesPro Appointment'
        verbose_name_plural = 'SalesPro Appointments'
        ordering = ['-created_at']
    
    def __str__(self):
        if self.salesrep_first_name and self.salesrep_last_name:
            return f"{self.salesrep_first_name} {self.salesrep_last_name} - {self.id}"
        return f"SalesPro Appointment {self.id}"


class SalesPro_SyncHistory(models.Model):
    """Track SalesPro import history"""
    sync_type = models.CharField(max_length=50)  # e.g., 'csv_appointments'
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    records_processed = models.IntegerField(default=0)
    records_created = models.IntegerField(default=0)
    records_updated = models.IntegerField(default=0)
    status = models.CharField(max_length=20, default='in_progress')  # in_progress, completed, failed
    error_message = models.TextField(null=True, blank=True)
    file_path = models.CharField(max_length=500, null=True, blank=True)  # For CSV imports
    
    class Meta:
        db_table = 'ingestion_salespro_sync_history'
        verbose_name = 'SalesPro Sync History'
        verbose_name_plural = 'SalesPro Sync Histories'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"

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
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_credit_applications'
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
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_customer'
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
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_estimate'
        verbose_name = 'Estimate'
        verbose_name_plural = 'Estimates'

    def __str__(self):
        return self.estimate_id


class SalesPro_LeadResult(models.Model):
    estimate_id = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    lead_results = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_lead_results'
        verbose_name = 'Lead Result'
        verbose_name_plural = 'Lead Results'

    def __str__(self):
        return self.estimate_id


class SalesPro_MeasureSheet(models.Model):
    # Remove auto-incrementing ID since this is a measure sheet items table
    id = None
    
    estimate_id = models.CharField(max_length=255, blank=True, null=True)
    office_id = models.CharField(max_length=255, blank=True, null=True)
    office_name = models.CharField(max_length=255, blank=True, null=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    measure_sheet_item_id = models.CharField(max_length=255, blank=True, null=True)
    quantity = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    category = models.CharField(max_length=255, blank=True, null=True)
    measurement_type = models.CharField(max_length=255, blank=True, null=True)
    measure_sheet_item_name = models.CharField(max_length=255, blank=True, null=True)
    measure_sheet_item_price = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_measure_sheet'
        verbose_name = 'Measure Sheet'
        verbose_name_plural = 'Measure Sheets'
        unique_together = [['created_at', 'updated_at', 'estimate_id', 'measure_sheet_item_name']]
        # Order by created_at by default
        ordering = ['created_at']

    def __str__(self):
        return f"{self.estimate_id} - {self.measure_sheet_item_name}"


class SalesPro_Payment(models.Model):
    payment_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    company_name = models.CharField(max_length=255, blank=True, null=True)
    customer_id = models.CharField(max_length=255, blank=True, null=True)
    payment_amount = models.DecimalField(max_digits=12, decimal_places=2, blank=True, null=True)
    payment_type = models.CharField(max_length=100, blank=True, null=True)
    payment_description = models.CharField(max_length=255, blank=True, null=True)
    payment_success = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_payments'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return self.payment_id


class SalesPro_UserActivity(models.Model):
    created_at = models.DateTimeField()
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
        db_table = 'ingestion_salespro_user_activity'
        verbose_name = 'User Activity'
        verbose_name_plural = 'User Activities'
        # Use combination of created_at, user_id, and activity_note as unique constraint
        unique_together = [['created_at', 'user_id', 'activity_note']]
        # Order by created_at by default
        ordering = ['created_at']

    def __str__(self):
        return f"{self.user_id} - {self.activity_identifier}"


class SalesPro_EstimatePriceBreakdown(models.Model):
    estimate_date = models.DateTimeField(blank=True, null=True)