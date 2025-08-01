from django.db import models

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
        db_table = 'ingestion_salespro_credit_application'
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
    # Use estimate_id as primary key to keep only latest version
    estimate_id = models.CharField(max_length=255, primary_key=True)
    company_id = models.CharField(max_length=255, blank=True, null=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    
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
        db_table = 'ingestion_salespro_lead_result'
        verbose_name = 'Lead Result'
        verbose_name_plural = 'Lead Results'
        # No unique_together needed since estimate_id is primary key
        ordering = ['-updated_at']

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
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()

    class Meta:
        db_table = 'ingestion_salespro_payment'
        verbose_name = 'Payment'
        verbose_name_plural = 'Payments'

    def __str__(self):
        return self.payment_id


class SalesPro_UserActivity(models.Model):
    # Add a proper primary key for framework compliance
    id = models.AutoField(primary_key=True)
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
