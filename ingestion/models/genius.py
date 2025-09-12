from django.db import models
from django.utils import timezone
from decimal import Decimal

# SyncTracker has been moved to common.py

class Genius_DivisionGroup(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    group_label = models.CharField(max_length=64, null=True, blank=True)
    region = models.IntegerField(default=1)
    default_time_zone_name = models.CharField(max_length=64, default='US/Pacific')
    intern_payroll_start = models.IntegerField(null=True, blank=True)
    painter_payroll_start = models.IntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    cc_profile_id = models.CharField(max_length=32, blank=True, null=True)
    mes_profile_id = models.CharField(max_length=25, null=True, blank=True)
    mes_profile_key = models.CharField(max_length=50, null=True, blank=True)
    docusign_acct_id = models.CharField(max_length=50, null=True, blank=True)
    paysimple_username = models.CharField(max_length=20, null=True, blank=True)
    paysimple_secret = models.CharField(max_length=150, null=True, blank=True)
    hub_account_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_division_group'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Division Group data stored in ingestion schema'
        verbose_name = 'Genius Division Group'
        verbose_name_plural = 'Genius Division Groups'

    def __str__(self):
        return self.group_label or f"DivisionGroup {self.id}"

class Genius_DivisionRegion(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    name = models.CharField(max_length=64, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_division_region'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Division Region data stored in ingestion schema'
        verbose_name = 'Genius Division Region'
        verbose_name_plural = 'Genius Division Regions'

    def __str__(self):
        return self.name or f"DivisionRegion {self.id}"


class Genius_Division(models.Model):
    id = models.IntegerField(primary_key=True)
    group_id = models.SmallIntegerField(null=True, blank=True)
    region_id = models.SmallIntegerField(null=True, blank=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    abbreviation = models.CharField(max_length=50, null=True, blank=True)
    is_utility = models.BooleanField(default=False)
    is_corp = models.BooleanField(default=False)
    is_omniscient = models.BooleanField(default=False)
    is_inactive = models.IntegerField(default=0)
    account_scheduler_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_division'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Division data stored in ingestion schema'
        verbose_name = 'Genius Division'
        verbose_name_plural = 'Genius Divisions'

    def __str__(self):
        return self.label or f"Division {self.id}"


class Genius_UserData(models.Model):
    id = models.IntegerField(primary_key=True, db_column='user_id')
    division_id = models.IntegerField(null=False, blank=False)
    title_id = models.SmallIntegerField(null=True, blank=True)
    manager_user_id = models.IntegerField(null=True, blank=True)
    first_name = models.CharField(max_length=100, null=True, blank=True)
    first_name_alt = models.CharField(max_length=100, null=True, blank=True)
    last_name = models.CharField(max_length=100, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    personal_email = models.EmailField(null=True, blank=True)
    birth_date = models.DateField(null=True, blank=True)
    gender_id = models.IntegerField(null=True, blank=True)
    marital_status_id = models.IntegerField(null=True, blank=True)
    time_zone_name = models.CharField(max_length=50, null=False, blank=True, default='')
    hired_on = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    add_user_id = models.IntegerField(null=True, blank=True)
    add_datetime = models.DateTimeField(null=True, blank=True)
    is_inactive = models.BooleanField(default=False)
    inactive_on = models.DateTimeField(null=True, blank=True)
    inactive_reason_id = models.SmallIntegerField(null=True, blank=True)
    inactive_reason_other = models.CharField(max_length=255, null=True, blank=True)
    primary_user_id = models.IntegerField(null=True, blank=True)
    inactive_transfer_division_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_userdata'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius UserData stored in ingestion schema'
        verbose_name = 'Genius User Data'
        verbose_name_plural = 'Genius User Data'

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Genius_Prospect(models.Model):
    id = models.IntegerField(primary_key=True)
    division_id = models.IntegerField(null=False, blank=False)
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
    hubspot_contact_id = models.BigIntegerField(null=True, blank=True)
    is_address_valid = models.SmallIntegerField(default=0) 
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)
    user_id = models.IntegerField(null=True, blank=True)
    year_built = models.SmallIntegerField(null=True, blank=True)

    class Meta:
        db_table = 'genius_prospect'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Prospect data stored in ingestion schema'
        verbose_name = 'Genius Prospect'
        verbose_name_plural = 'Genius Prospects'

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


class Genius_ProspectSource(models.Model):
    id = models.AutoField(primary_key=True)
    prospect_id = models.IntegerField(null=False, blank=False)
    marketing_source_id = models.IntegerField(null=False, blank=False)
    source_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_prospect_source'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Prospect Source data stored in ingestion schema'
        verbose_name = 'Genius Prospect Source'
        verbose_name_plural = 'Genius Prospect Sources'

    def __str__(self):
        return f"Source {self.marketing_source_id or 'N/A'} for Prospect {self.prospect_id or 'N/A'}"


class Genius_AppointmentType(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_appointment_type'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Appointment Type data stored in ingestion schema'
        verbose_name = 'Genius Appointment Type'
        verbose_name_plural = 'Genius Appointment Types'

    def __str__(self):
        return self.label or f"AppointmentType {self.id}"


class Genius_AppointmentOutcomeType(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=50, blank=True, null=True)
    sort_idx = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_appointment_outcome_type'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Appointment Outcome Type data stored in ingestion schema'
        verbose_name = 'Genius Appointment Outcome Type'
        verbose_name_plural = 'Genius Appointment Outcome Types'

    def __str__(self):
        return self.label or f"Appointment Outcome Type {self.id}"


class Genius_UserAssociation(models.Model):
    id = models.AutoField(primary_key=True)
    definition_id = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    division_id = models.IntegerField(null=True, blank=True)
    field_value = models.CharField(max_length=128, null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_user_association'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius User Association data stored in ingestion schema'
        verbose_name = 'Genius User Association'
        verbose_name_plural = 'Genius User Associations'

    def __str__(self):
        return f"User Association {self.id} - User: {self.user_id}, Division: {self.division_id}"


class Genius_AppointmentOutcome(models.Model):
    id = models.AutoField(primary_key=True)
    type_id = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_appointment_outcome'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius AppointmentOutcome data stored in ingestion schema'
        verbose_name = 'Genius AppointmentOutcome'
        verbose_name_plural = 'Genius AppointmentOutcomes'

    def __str__(self):
        return self.label or f"Appointment Outcome {self.id}"


class Genius_Appointment(models.Model):
    id = models.IntegerField(primary_key=True)
    prospect_id = models.IntegerField(null=False, blank=False)
    prospect_source_id = models.IntegerField(null=True, blank=True)
    user_id = models.IntegerField(null=True, blank=True)
    type_id = models.IntegerField(null=False, blank=False)
    date = models.DateField(null=True, blank=True)
    time = models.TimeField(null=True, blank=True)
    duration = models.DurationField(null=True, blank=True)
    address1 = models.CharField(max_length=255, null=True, blank=True)
    address2 = models.CharField(max_length=255, null=True, blank=True)
    city = models.CharField(max_length=100, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    zip = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(null=False, blank=False, default=timezone.now)
    assign_date = models.DateTimeField(null=True, blank=True)
    confirm_user_id = models.IntegerField(null=True, blank=True)
    confirm_date = models.DateTimeField(null=True, blank=True)
    confirm_with = models.CharField(max_length=100, null=True, blank=True)
    spouses_present = models.IntegerField(default=0)
    is_complete = models.IntegerField(default=0)
    complete_outcome_id = models.IntegerField(null=True, blank=True)
    complete_user_id = models.IntegerField(null=True, blank=True)
    complete_date = models.DateTimeField(null=True, blank=True)
    marketsharp_id = models.CharField(max_length=100, null=True, blank=True)
    marketsharp_appt_type = models.CharField(max_length=100, null=True, blank=True)
    leap_estimate_id = models.CharField(max_length=100, null=True, blank=True)
    hubspot_appointment_id = models.BigIntegerField(null=True, blank=True)
    marketing_task_id = models.IntegerField(default=0)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_appointment'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Appointment data stored in ingestion schema'
        verbose_name = 'Genius Appointment'
        verbose_name_plural = 'Genius Appointments'

    def __str__(self):
        return f"Appointment {self.id} for Prospect {self.prospect_id}"


class Genius_Service(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    label = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_lead_required = models.BooleanField(default=False)
    order_number = models.SmallIntegerField(default=0)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_service'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Service data stored in ingestion schema'
        verbose_name = 'Genius Service'
        verbose_name_plural = 'Genius Services'

    def __str__(self):
        return self.label or f"Service {self.id}"


class Genius_AppointmentService(models.Model):
    appointment_id = models.IntegerField(null=False, blank=False)
    service_id = models.SmallIntegerField(null=False, blank=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_appointment_service'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius AppointmentService data stored in ingestion schema'
        verbose_name = 'Genius AppointmentService'
        verbose_name_plural = 'Genius AppointmentServices'
        unique_together = ('appointment_id', 'service_id')


class Genius_Quote(models.Model):
    id = models.IntegerField(primary_key=True)
    prospect_id = models.IntegerField(null=False, blank=False)
    appointment_id = models.IntegerField(null=False, blank=False)
    job_id = models.IntegerField(null=True, blank=True)
    client_cid = models.IntegerField(null=True, blank=True)
    service_id = models.SmallIntegerField(null=False, blank=False)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    amount = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    expire_date = models.DateField(null=True, blank=True)
    status_id = models.IntegerField(default=1)
    contract_file_id = models.IntegerField(null=True, blank=True)
    estimate_file_id = models.IntegerField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_quote'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Quote data stored in ingestion schema'
        verbose_name = 'Genius Quote'
        verbose_name_plural = 'Genius Quotes'

    def __str__(self):
        return f"Quote {self.id} – ${self.amount:.2f}"


class Genius_MarketingSourceType(models.Model):
    id = models.IntegerField(primary_key=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    list_order = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_marketing_source_type'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius MarketingSourceType data stored in ingestion schema'
        verbose_name = 'Genius MarketingSourceType'
        verbose_name_plural = 'Genius MarketingSourceTypes'

    def __str__(self):
        return self.label or f"Marketing Source Type {self.id}"


class Genius_MarketingSource(models.Model):
    id = models.IntegerField(primary_key=True)
    type_id = models.IntegerField(null=False, blank=True, default=0)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_allow_lead_modification = models.BooleanField(default=False)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_marketing_source'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius MarketingSource data stored in ingestion schema'
        verbose_name = 'Genius MarketingSource'
        verbose_name_plural = 'Genius MarketingSources'

    def __str__(self):
        return self.label or f"Marketing Source {self.id}"


class Genius_UserTitle(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    abbreviation = models.CharField(max_length=10, null=True, blank=True)
    roles = models.CharField(max_length=256, null=True, blank=True)
    type_id = models.SmallIntegerField(null=False, blank=True, default=0)
    section_id = models.SmallIntegerField(null=True, blank=True)
    sort = models.SmallIntegerField(null=False, blank=True, default=0)
    pay_component_group_id = models.SmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_unique_per_division = models.BooleanField(default=False)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_user_title'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius UserTitle data stored in ingestion schema'
        verbose_name = 'Genius UserTitle'
        verbose_name_plural = 'Genius UserTitles'

    def __str__(self):
        return self.title or f"Title {self.id}"

class Genius_Lead(models.Model):
    lead_id = models.IntegerField(primary_key=True)
    contact = models.IntegerField(null=False, blank=True, default=0)
    division_id = models.IntegerField(null=False, blank=True, db_column='division', default=0)
    first_name = models.CharField(max_length=50, null=True, blank=True)
    last_name = models.CharField(max_length=50, null=True, blank=True)
    address1 = models.CharField(max_length=50, null=True, blank=True)
    address2 = models.CharField(max_length=50, null=True, blank=True)
    city = models.CharField(max_length=50, null=True, blank=True)
    state = models.CharField(max_length=2, null=True, blank=True)
    zip = models.CharField(max_length=7, null=True, blank=True)
    cdyne_county = models.CharField(max_length=25, null=True, blank=True)
    is_valid_address = models.SmallIntegerField(default=0) 
    email = models.CharField(max_length=100, null=True, blank=True)
    phone1 = models.CharField(max_length=12, null=True, blank=True)
    type1 = models.SmallIntegerField(null=False, blank=True, default=0)
    phone2 = models.CharField(max_length=12, null=True, blank=True)
    type2 = models.SmallIntegerField(null=False, blank=True, default=0)
    phone3 = models.CharField(max_length=12, null=True, blank=True)
    type3 = models.SmallIntegerField(null=False, blank=True, default=0)
    phone4 = models.CharField(max_length=12, null=True, blank=True)
    type4 = models.SmallIntegerField(null=False, blank=True, default=0)
    source = models.SmallIntegerField(null=False, blank=True, default=0)
    source_notes = models.CharField(max_length=64, null=True, blank=True)
    sourced_on = models.DateTimeField(null=True, blank=True)
    job_type = models.SmallIntegerField(null=False, blank=True, default=2)
    rating = models.SmallIntegerField(null=True, blank=True)
    year_built = models.CharField(max_length=4, null=True, blank=True)
    is_year_built_verified = models.SmallIntegerField(default=0) 
    is_zillow = models.SmallIntegerField(default=0) 
    is_express_consent = models.SmallIntegerField(default=0) 
    express_consent_set_by = models.IntegerField(null=True, blank=True)
    express_consent_set_on = models.DateTimeField(null=True, blank=True)
    express_consent_source = models.SmallIntegerField(null=True, blank=True)
    express_consent_upload_file_id = models.IntegerField(null=True, blank=True)
    is_express_consent_being_reviewed = models.SmallIntegerField(default=0) 
    express_consent_being_reviewed_by = models.IntegerField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    status = models.SmallIntegerField(null=True, blank=True)
    substatus = models.SmallIntegerField(null=True, blank=True)
    substatus_reason = models.IntegerField(null=True, blank=True)
    alternate_id = models.IntegerField(null=True, blank=True)
    added_by = models.IntegerField(null=False, blank=True, default=0)
    added_on = models.DateTimeField(null=True, blank=True)
    viewed_on = models.DateTimeField(null=True, blank=True)
    is_estimate_set = models.SmallIntegerField(default=0) 
    estimate_set_by = models.IntegerField(null=True, blank=True)
    estimate_set_on = models.DateTimeField(null=True, blank=True)
    dead_on = models.DateTimeField(null=True, blank=True)
    dead_by = models.IntegerField(null=True, blank=True)
    dead_note = models.CharField(max_length=100, null=True, blank=True)
    is_credit_request = models.SmallIntegerField(null=True, blank=True) 
    credit_request_by = models.IntegerField(null=True, blank=True)
    credit_request_on = models.DateTimeField(null=True, blank=True)
    credit_request_reason = models.TextField(null=True, blank=True)
    credit_request_status = models.SmallIntegerField(null=True, blank=True)
    credit_request_update_on = models.DateTimeField(null=True, blank=True)
    credit_request_update_by = models.IntegerField(null=True, blank=True)
    credit_request_note = models.TextField(null=True, blank=True)
    lead_cost = models.FloatField(default=20.00) 
    import_source = models.CharField(max_length=100, null=True, blank=True)
    call_screen_viewed_on = models.DateTimeField(null=True, blank=True)
    call_screen_viewed_by = models.IntegerField(null=True, blank=True)
    copied_to_id = models.IntegerField(null=True, blank=True)
    copied_to_on = models.DateTimeField(null=True, blank=True)
    copied_from_id = models.IntegerField(null=True, blank=True)
    copied_from_on = models.DateTimeField(null=True, blank=True)
    cwp_client = models.IntegerField(default=0)
    cwp_referral = models.IntegerField(null=True, blank=True)
    rc_paid_to = models.IntegerField(null=True, blank=True)
    rc_paid_on = models.DateTimeField(null=True, blank=True)
    with_dm = models.SmallIntegerField(default=-1) 
    voicemail_file = models.CharField(max_length=124, null=True, blank=True)
    agent_id = models.CharField(max_length=48, null=True, blank=True)
    agent_name = models.CharField(max_length=124, null=True, blank=True)
    invalid_address = models.SmallIntegerField(default=0) 
    is_valid_email = models.SmallIntegerField(default=0) 
    is_high_potential = models.SmallIntegerField(default=0) 
    is_mobile_lead = models.SmallIntegerField(default=0) 
    is_dnc = models.SmallIntegerField(null=True, blank=True, default=0) 
    is_dummy = models.SmallIntegerField(default=0) 
    lead_central_estimate_date = models.DateTimeField(null=True, blank=True)
    do_not_call_before = models.DateTimeField(null=True, blank=True)
    is_estimate_confirmed = models.SmallIntegerField(null=True, blank=True) 
    estimate_confirmed_by = models.IntegerField(null=True, blank=True)
    estimate_confirmed_on = models.DateTimeField(null=True, blank=True)
    added_by_latitude = models.DecimalField(max_digits=9, decimal_places=7, null=True, blank=True)
    added_by_longitude = models.DecimalField(max_digits=10, decimal_places=7, null=True, blank=True)
    is_carpentry_followup = models.SmallIntegerField(default=0) 
    carpentry_followup_notes = models.TextField(null=True, blank=True)
    marketing_source = models.IntegerField(null=True, blank=True)
    prospect_id = models.IntegerField(null=True, blank=True)
    added_by_supervisor = models.IntegerField(null=True, blank=True)
    salesrabbit_lead_id = models.IntegerField(null=True, blank=True)
    third_party_source_id = models.IntegerField(null=True, blank=True)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_lead'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Lead data stored in ingestion schema'
        verbose_name = 'Genius Lead'
        verbose_name_plural = 'Genius Leads'

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip() or f"Lead {self.lead_id}"


class Genius_MarketSharpSource(models.Model):
    id = models.AutoField(primary_key=True)
    marketsharp_id = models.CharField(max_length=256, null=False, blank=True, default='')
    source_name = models.CharField(max_length=128, null=False, blank=True, default='')
    inactive = models.SmallIntegerField(default=0) 
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_marketsharp_source'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius MarketSharpSource data stored in ingestion schema'
        verbose_name = 'Genius MarketSharpSource'
        verbose_name_plural = 'Genius MarketSharpSources'

    def __str__(self):
        return self.source_name or f"MarketSharp Source {self.id}"


class Genius_MarketSharpMarketingSourceMap(models.Model):
    marketsharp_id = models.CharField(max_length=128, primary_key=True)
    marketing_source_id = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_marketsharp_marketing_source_map'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius MarketSharpMarketingSourceMap data stored in ingestion schema'
        verbose_name = 'Genius MarketSharpMarketingSourceMap'
        verbose_name_plural = 'Genius MarketSharpMarketingSourceMaps'

    def __str__(self):
        return f"MarketSharp ID: {self.marketsharp_id}, Marketing Source ID: {self.marketing_source_id}"


class Genius_Job(models.Model):
    id = models.AutoField(primary_key=True)
    client_cid = models.IntegerField(null=True, blank=True)
    prospect_id = models.IntegerField(null=False, blank=False)
    division_id = models.IntegerField(null=False, blank=False)
    user_id = models.IntegerField(null=True, blank=True)
    production_user_id = models.IntegerField(null=True, blank=True)
    project_coordinator_user_id = models.IntegerField(null=True, blank=True)
    production_month = models.IntegerField(null=True, blank=True)
    subcontractor_id = models.IntegerField(null=True, blank=True)
    subcontractor_status_id = models.SmallIntegerField(null=True, blank=True)
    subcontractor_confirmed = models.SmallIntegerField(default=0)
    status = models.IntegerField(default=10)
    is_in_progress = models.SmallIntegerField(default=0)
    ready_status = models.SmallIntegerField(null=True, blank=True)
    prep_status_id = models.SmallIntegerField(null=True, blank=True)
    prep_status_set_date = models.DateTimeField(null=True, blank=True)
    prep_status_is_reset = models.SmallIntegerField(default=0)
    prep_status_notes = models.TextField(null=True, blank=True)
    prep_issue_id = models.CharField(max_length=32, null=True, blank=True)
    service_id = models.SmallIntegerField(null=False, blank=False)
    is_lead_pb = models.SmallIntegerField(default=0)
    contract_number = models.CharField(max_length=50, null=True, blank=True)
    contract_date = models.DateField(null=True, blank=True)
    contract_amount = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    contract_amount_difference = models.TextField(null=True, blank=True)
    contract_hours = models.IntegerField(default=0)
    contract_file_id = models.IntegerField(null=True, blank=True)
    job_value = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    deposit_amount = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    deposit_type_id = models.SmallIntegerField(null=True, blank=True)
    is_financing = models.SmallIntegerField(default=0)
    sales_tax_rate = models.DecimalField(max_digits=7, decimal_places=5, default=Decimal('0.00000'))
    is_sales_tax_exempt = models.SmallIntegerField(default=0)
    commission_payout = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    accrued_commission_payout = models.DecimalField(max_digits=11, decimal_places=2, default=Decimal('0.00'))
    sold_user_id = models.IntegerField(null=True, blank=True)
    sold_date = models.DateField(null=True, blank=True)
    start_request_date = models.DateField(null=True, blank=True)
    deadline_date = models.DateField(null=True, blank=True)
    ready_date = models.DateField(null=True, blank=True)
    jsa_sent = models.SmallIntegerField(null=True, blank=True)
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(default=timezone.now)
    cancel_date = models.DateField(null=True, blank=True)
    cancel_user_id = models.IntegerField(null=True, blank=True)
    cancel_reason_id = models.SmallIntegerField(null=True, blank=True)
    is_refund = models.SmallIntegerField(default=0)
    refund_date = models.DateField(null=True, blank=True)
    refund_user_id = models.IntegerField(null=True, blank=True)
    finish_date = models.DateField(null=True, blank=True)
    is_earned_not_paid = models.SmallIntegerField(default=0)
    materials_arrival_date = models.DateField(null=True, blank=True)
    measure_date = models.DateField(null=True, blank=True)
    measure_time = models.TimeField(null=True, blank=True)
    measure_user_id = models.IntegerField(null=True, blank=True)
    time_format = models.SmallIntegerField(null=True, blank=True)
    materials_estimated_arrival_date = models.DateField(null=True, blank=True)
    materials_ordered = models.DateTimeField(null=True, blank=True)
    price_level = models.CharField(max_length=32, null=True, blank=True)
    price_level_goal = models.SmallIntegerField(null=True, blank=True)
    price_level_commission = models.DecimalField(max_digits=3, decimal_places=1, null=True, blank=True)
    price_level_commission_reduction = models.SmallIntegerField(null=True, blank=True)
    is_reviewed = models.SmallIntegerField(default=0)
    reviewed_by = models.IntegerField(null=True, blank=True)
    pp_id_updated = models.SmallIntegerField(default=0)
    hoa = models.SmallIntegerField(null=True, blank=True)
    hoa_approved = models.SmallIntegerField(null=True, blank=True)
    install_date = models.DateField(null=True, blank=True)
    install_time = models.TimeField(null=True, blank=True)
    install_time_format = models.SmallIntegerField(null=True, blank=True)
    materials_ordered_old = models.SmallIntegerField(null=True, blank=True)
    start_month_old = models.SmallIntegerField(null=True, blank=True)
    cogs_report_month = models.CharField(max_length=50, null=True, blank=True)
    is_cogs_report_month_updated = models.SmallIntegerField(default=0)
    forecast_month = models.CharField(max_length=50, null=True, blank=True)
    coc_sent_on = models.DateTimeField(null=True, blank=True)
    coc_sent_by = models.IntegerField(null=True, blank=True)
    company_cam_link = models.CharField(max_length=256, null=True, blank=True)
    pm_finished_on = models.DateField(null=True, blank=True)
    estimate_job_duration = models.SmallIntegerField(null=True, blank=True)
    payment_not_finalized_reason = models.IntegerField(null=True, blank=True)
    reasons_other = models.CharField(max_length=255, null=True, blank=True)
    payment_type = models.IntegerField(null=True, blank=True)
    payment_amount = models.DecimalField(max_digits=11, decimal_places=2, null=True, blank=True)
    is_payment_finalized = models.SmallIntegerField(null=True, blank=True)
    is_company_cam = models.SmallIntegerField(null=True, blank=True)
    is_five_star_review = models.SmallIntegerField(null=True, blank=True)
    projected_end_date = models.DateField(null=True, blank=True)
    is_company_cam_images_correct = models.SmallIntegerField(null=True, blank=True)
    post_pm_closeout_date = models.DateField(null=True, blank=True)
    pre_pm_closeout_date = models.DateField(null=True, blank=True)
    actual_install_date = models.DateTimeField(null=True, blank=True)
    in_progress_substatus_id = models.IntegerField(null=True, blank=True)
    is_loan_document_uptodate = models.SmallIntegerField(null=True, blank=True)
    is_labor_adjustment_correct = models.SmallIntegerField(null=True, blank=True)
    is_change_order_correct = models.SmallIntegerField(null=True, blank=True)
    is_coc_pdf_attached = models.SmallIntegerField(default=0)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Job data stored in ingestion schema'
        verbose_name = 'Genius Job'
        verbose_name_plural = 'Genius Jobs'

    def __str__(self):
        return f"Job {self.id} for Prospect {self.prospect_id}"


class Genius_JobChangeOrder(models.Model):
    id = models.AutoField(primary_key=True)
    job_id = models.IntegerField(null=False, blank=False)
    number = models.CharField(max_length=20)
    status_id = models.SmallIntegerField(default=1)
    type_id = models.SmallIntegerField(default=1)
    adjustment_change_order_id = models.IntegerField(null=True, blank=True)
    effective_date = models.DateField()
    total_amount = models.DecimalField(max_digits=9, decimal_places=2)
    add_user_id = models.IntegerField(null=True, blank=True)
    add_date = models.DateTimeField()
    sold_user_id = models.IntegerField(null=True, blank=True)
    sold_date = models.DateTimeField(null=True, blank=True)
    cancel_user_id = models.IntegerField(null=True, blank=True)
    cancel_date = models.DateTimeField(null=True, blank=True)
    reason_id = models.SmallIntegerField(null=True, blank=True)
    envelope_id = models.CharField(max_length=64, null=True, blank=True)
    total_contract_amount = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    total_pre_change_orders_amount = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    signer_name = models.CharField(max_length=100, null=True, blank=True)
    signer_email = models.CharField(max_length=100, null=True, blank=True)
    financing_note = models.CharField(max_length=255, null=True, blank=True)
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_change_order'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobChangeOrder data stored in ingestion schema'
        verbose_name = 'Genius JobChangeOrder'
        verbose_name_plural = 'Genius JobChangeOrders'

    def __str__(self):
        return f"ChangeOrder {self.id} for Job {self.job_id}"


class Genius_JobChangeOrderItem(models.Model):
    id = models.AutoField(primary_key=True)
    change_order_id = models.IntegerField(null=False, blank=False)
    description = models.CharField(max_length=256, null=True, blank=True)
    amount = models.DecimalField(max_digits=8, decimal_places=2)
    created_at = models.DateTimeField()
    updated_at = models.DateTimeField()
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_change_order_item'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobChangeOrderItem data stored in ingestion schema'
        verbose_name = 'Genius JobChangeOrderItem'
        verbose_name_plural = 'Genius JobChangeOrderItems'

    def __str__(self):
        return f"CO Item {self.id} for ChangeOrder {self.change_order_id}"


class Genius_JobChangeOrderReason(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=100, null=True, blank=True)
    description = models.CharField(max_length=255, null=True, blank=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_change_order_reason'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobChangeOrderReason data stored in ingestion schema'
        verbose_name = 'Genius JobChangeOrderReason'
        verbose_name_plural = 'Genius JobChangeOrderReasons'

    def __str__(self):
        return self.label or f"CO Reason {self.id}"


class Genius_JobChangeOrderStatus(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=32)
    is_selectable = models.SmallIntegerField(default=1)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_change_order_status'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobChangeOrderStatus data stored in ingestion schema'
        verbose_name = 'Genius JobChangeOrderStatus'
        verbose_name_plural = 'Genius JobChangeOrderStatuss'

    def __str__(self):
        return self.label


class Genius_JobChangeOrderType(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=32, null=True, blank=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_change_order_type'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobChangeOrderType data stored in ingestion schema'
        verbose_name = 'Genius JobChangeOrderType'
        verbose_name_plural = 'Genius JobChangeOrderTypes'

    def __str__(self):
        return self.label or f"CO Type {self.id}"


class Genius_JobStatus(models.Model):
    id = models.IntegerField(primary_key=True)
    label = models.CharField(max_length=50, null=True, blank=True)
    is_system = models.SmallIntegerField(default=0)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'genius_job_status'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius JobStatus data stored in ingestion schema'
        verbose_name = 'Genius JobStatus'
        verbose_name_plural = 'Genius JobStatuss'

    def __str__(self):
        return self.label or f"Job Status {self.id}"


class Genius_JobFinancing(models.Model):
    job_id = models.IntegerField(primary_key=True)
    term_id = models.IntegerField(null=True, blank=True)
    financed_amount = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    max_financed_amount = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal('0.00'))
    bid_rate = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    commission_reduction = models.DecimalField(max_digits=5, decimal_places=3, null=True, blank=True)
    signed_on = models.DateTimeField(null=True, blank=True)
    cancellation_period_expires_on = models.DateTimeField(null=True, blank=True)
    app_submission_date = models.DateTimeField(null=True, blank=True)
    is_joint_application = models.SmallIntegerField(default=0)
    applicant = models.CharField(max_length=50, null=True, blank=True)
    co_applicant = models.CharField(max_length=50, null=True, blank=True)
    status = models.SmallIntegerField(default=1)
    approved_on = models.DateTimeField(null=True, blank=True)
    loan_expiration_date = models.DateTimeField(null=True, blank=True)
    denied_on = models.DateTimeField(null=True, blank=True)
    denied_by = models.IntegerField(null=True, blank=True)
    why_book = models.TextField(null=True, blank=True)
    would_book = models.SmallIntegerField(null=True, blank=True)
    is_financing_factor = models.SmallIntegerField(null=True, blank=True)
    satisfied = models.TextField(null=True, blank=True)
    docs_completed = models.DateTimeField(null=True, blank=True)
    active_stipulation_notes = models.TextField(null=True, blank=True)
    is_active_stipulations_cleared = models.SmallIntegerField(default=0)
    legal_app_name = models.CharField(max_length=100, null=True, blank=True)
    sync_created_at = models.DateTimeField(auto_now_add=True)
    sync_updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = '"genius_job_financing"'
        managed = True
        app_label = 'ingestion'
        db_table_comment = 'Genius Job Financing data stored in ingestion schema'
        verbose_name = 'Genius Job Financing'
        verbose_name_plural = 'Genius Job Financings'

    def __str__(self):
        return f"Job Financing {self.job_id} - Term {self.term_id}"

