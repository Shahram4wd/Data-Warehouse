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
        db_table = 'salespro_appointment'
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
        db_table = 'salespro_sync_history'
        verbose_name = 'SalesPro Sync History'
        verbose_name_plural = 'SalesPro Sync Histories'
        ordering = ['-started_at']
    
    def __str__(self):
        return f"{self.sync_type} - {self.started_at.strftime('%Y-%m-%d %H:%M')}"
