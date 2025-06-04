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
