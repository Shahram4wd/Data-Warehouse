
from django.db import models

class DivisionGroup(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    group_label = models.CharField(max_length=255, null=True, blank=True)
    region = models.IntegerField(default=1)
    default_time_zone_name = models.CharField(max_length=64, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    hub_account_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.group_label or f"DivisionGroup {self.id}"


class Division(models.Model):
    id = models.IntegerField(primary_key=True)
    group_id = models.SmallIntegerField(null=True, blank=True)
    region_id = models.SmallIntegerField(null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    abbreviation = models.CharField(max_length=50, null=True, blank=True)
    is_utility = models.BooleanField(default=False)
    is_corp = models.BooleanField(default=False)
    is_omniscient = models.BooleanField(default=False)

    def __str__(self):
        return self.label or f"Division {self.id}"


class UserData(models.Model):
    user_id = models.IntegerField(primary_key=True)
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, related_name='users')
    first_name = models.CharField(max_length=100, null=True, blank=True)
    first_name_alt = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    personal_email = models.EmailField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender_id = models.IntegerField(null=True, blank=True)
    marital_status_id = models.IntegerField(null=True, blank=True)
    time_zone_name = models.CharField(max_length=50)
    lead_radius_zip = models.CharField(max_length=20, null=True, blank=True)
    lead_radius_distance = models.FloatField(null=True, blank=True)
    lead_types = models.IntegerField(null=True, blank=True)
    lead_call_center = models.BooleanField(default=True)
    title_id = models.SmallIntegerField(null=True, blank=True)
    manager_user_id = models.IntegerField(null=True, blank=True)
    hired_on = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    add_user_id = models.IntegerField(null=True, blank=True)
    add_datetime = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    user_associations_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Prospect(models.Model):
    id = models.IntegerField(primary_key=True)
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, related_name='prospects')
    first_name = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    alt_first_name = models.CharField(max_length=100, null=True, blank=True)
    alt_last_name = models.CharField(max_length=100, null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    county = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    phone1 = models.CharField(max_length=20, null=True, blank=True)
    phone2 = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(null=True, blank=True, auto_now_add=True)
    marketsharp_id = models.CharField(max_length=100, null=True, blank=True)
    leap_customer_id = models.CharField(max_length=100, null=True, blank=True)
    third_party_source_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


class ProspectSource(models.Model):
    id = models.AutoField(primary_key=True)
    prospect = models.ForeignKey('Prospect', on_delete=models.CASCADE, related_name='sources')
    marketing_source = models.ForeignKey('MarketingSource', on_delete=models.SET_NULL, null=True, blank=True, related_name='prospect_sources')
    source_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Source {self.marketing_source_id} for Prospect {self.prospect_id}"


class AppointmentType(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    label = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label or f"AppointmentType {self.id}"


class AppointmentOutcome(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    type_id = models.SmallIntegerField(default=0)
    label = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label or f"Outcome {self.id}"


class Appointment(models.Model):
    id = models.IntegerField(primary_key=True)
    prospect = models.ForeignKey('Prospect', on_delete=models.CASCADE, related_name='appointments')
    prospect_source = models.ForeignKey('ProspectSource', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    user_id = models.IntegerField(null=True, blank=True)
    type = models.ForeignKey('AppointmentType', on_delete=models.PROTECT, related_name='appointments')
    marketing_task_id = models.IntegerField()
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    duration = models.TimeField(null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)
    assign_date = models.DateTimeField(null=True, blank=True)
    confirm_user_id = models.IntegerField(null=True, blank=True)
    confirm_date = models.DateTimeField(null=True, blank=True)
    confirm_with = models.CharField(max_length=100, null=True, blank=True)
    spouses_present = models.BooleanField(default=False)
    is_complete = models.BooleanField(default=False)
    complete_outcome = models.ForeignKey('AppointmentOutcome', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    complete_user_id = models.IntegerField(null=True, blank=True)
    complete_date = models.DateTimeField(null=True, blank=True)
    marketsharp_id = models.CharField(max_length=100, null=True, blank=True)
    marketsharp_appt_type = models.CharField(max_length=100, null=True, blank=True)
    leap_estimate_id = models.CharField(max_length=100, null=True, blank=True)
    third_party_source_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Appointment {self.id} for Prospect {self.prospect_id}"


class Service(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    label = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_lead_required = models.BooleanField(default=False)
    order_number = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.label or f"Service {self.id}"


class AppointmentService(models.Model):
    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE)
    service = models.ForeignKey('Service', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('appointment', 'service')


class Quote(models.Model):
    id = models.IntegerField(primary_key=True)
    prospect = models.ForeignKey('Prospect', on_delete=models.CASCADE, related_name='quotes')
    appointment = models.ForeignKey('Appointment', on_delete=models.CASCADE, related_name='quotes')
    job_id = models.IntegerField(null=True, blank=True)
    client_cid = models.IntegerField(null=True, blank=True)
    service = models.ForeignKey('Service', on_delete=models.PROTECT, related_name='quotes')
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    expire_date = models.DateField(null=True, blank=True)
    status_id = models.IntegerField(default=1)
    contract_file_id = models.IntegerField(null=True, blank=True)
    estimate_file_id = models.IntegerField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Quote {self.id} – ${self.amount:.2f}"


class MarketingSourceType(models.Model):
    id = models.IntegerField(primary_key=True)
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, blank=True, related_name='marketing_source_types')
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    list_order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.label or f"Marketing Source Type {self.id}"


class MarketingSource(models.Model):
    id = models.IntegerField(primary_key=True)
    type = models.ForeignKey('MarketingSourceType', on_delete=models.PROTECT, related_name='marketing_sources')
    division = models.ForeignKey('Division', on_delete=models.SET_NULL, null=True, blank=True, related_name='marketing_sources')
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    is_allow_lead_modification = models.BooleanField(default=False)

    def __str__(self):
        return self.label or f"Marketing Source {self.id}"
