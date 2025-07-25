from django.db import models

# SyncTracker has been moved to common.py

class Genius_DivisionGroup(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    group_label = models.CharField(max_length=255, null=True, blank=True)
    region = models.IntegerField(default=1)
    default_time_zone_name = models.CharField(max_length=64, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    hub_account_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.group_label or f"DivisionGroup {self.id}"


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

    def __str__(self):
        return self.label or f"Division {self.id}"


class Genius_UserData(models.Model):
    id = models.IntegerField(primary_key=True)
    division = models.ForeignKey('Genius_Division', on_delete=models.SET_NULL, null=True, related_name='users')
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
    time_zone_name = models.CharField(max_length=50, null=True, blank=True)
    hired_on = models.DateTimeField(null=True, blank=True)
    start_date = models.DateTimeField(null=True, blank=True)
    add_user_id = models.IntegerField(null=True, blank=True)
    add_datetime = models.DateTimeField(null=True, blank=True)
    is_inactive = models.BooleanField(default=False)
    inactive_on = models.DateTimeField(null=True, blank=True)
    inactive_reason_id = models.SmallIntegerField(null=True, blank=True)
    inactive_reason_other = models.CharField(max_length=255, null=True, blank=True)
    primary_user_id = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}".strip()


class Genius_Prospect(models.Model):
    id = models.IntegerField(primary_key=True)
    division = models.ForeignKey('Genius_Division', on_delete=models.SET_NULL, null=True, related_name='prospects')
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

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip()


class Genius_ProspectSource(models.Model):
    id = models.AutoField(primary_key=True)
    prospect = models.ForeignKey('Genius_Prospect', on_delete=models.CASCADE, related_name='sources')
    marketing_source = models.ForeignKey('Genius_MarketingSource', on_delete=models.SET_NULL, null=True, blank=True, related_name='prospect_sources')
    source_date = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    add_user_id = models.IntegerField()
    add_date = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Source {self.marketing_source_id or 'N/A'} for Prospect {self.prospect_id or 'N/A'}"


class Genius_AppointmentType(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label or f"AppointmentType {self.id}"


class Genius_AppointmentOutcomeType(models.Model):
    id = models.AutoField(primary_key=True)
    label = models.CharField(max_length=50, blank=True, null=True)
    sort_idx = models.PositiveSmallIntegerField()
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label or f"Appointment Outcome Type {self.id}"


class Genius_AppointmentOutcome(models.Model):
    id = models.AutoField(primary_key=True)
    type_id = models.PositiveSmallIntegerField(default=0)
    label = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.label or f"Appointment Outcome {self.id}"


class Genius_Appointment(models.Model):
    id = models.BigIntegerField(primary_key=True)
    prospect = models.ForeignKey('Genius_Prospect', on_delete=models.CASCADE, related_name='appointments')
    prospect_source = models.ForeignKey('Genius_ProspectSource', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    user_id = models.BigIntegerField(null=True, blank=True)
    type = models.ForeignKey('Genius_AppointmentType', on_delete=models.PROTECT, related_name='appointments')
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
    add_user_id = models.BigIntegerField()
    add_date = models.DateTimeField(null=True, blank=True)
    assign_date = models.DateTimeField(null=True, blank=True)
    confirm_user_id = models.BigIntegerField(null=True, blank=True)
    confirm_date = models.DateTimeField(null=True, blank=True)
    confirm_with = models.CharField(max_length=100, null=True, blank=True)
    spouses_present = models.IntegerField(default=0)
    is_complete = models.IntegerField(default=0)
    complete_outcome = models.ForeignKey('Genius_AppointmentOutcome', on_delete=models.SET_NULL, null=True, blank=True, related_name='appointments')
    complete_user_id = models.BigIntegerField(null=True, blank=True)
    complete_date = models.DateTimeField(null=True, blank=True)
    marketsharp_id = models.CharField(max_length=100, null=True, blank=True)
    marketsharp_appt_type = models.CharField(max_length=100, null=True, blank=True)
    leap_estimate_id = models.CharField(max_length=100, null=True, blank=True)
    hubspot_appointment_id = models.BigIntegerField(null=True, blank=True)

    def __str__(self):
        return f"Appointment {self.id} for Prospect {self.prospect_id}"


class Genius_Service(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    label = models.CharField(max_length=100, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_lead_required = models.BooleanField(default=False)
    order_number = models.SmallIntegerField(default=0)

    def __str__(self):
        return self.label or f"Service {self.id}"


class Genius_AppointmentService(models.Model):
    appointment = models.ForeignKey('Genius_Appointment', on_delete=models.CASCADE)
    service = models.ForeignKey('Genius_Service', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('appointment', 'service')


class Genius_Quote(models.Model):
    id = models.IntegerField(primary_key=True)
    prospect = models.ForeignKey('Genius_Prospect', on_delete=models.CASCADE, related_name='quotes')
    appointment = models.ForeignKey('Genius_Appointment', on_delete=models.CASCADE, related_name='quotes')
    job_id = models.IntegerField(null=True, blank=True)
    client_cid = models.IntegerField(null=True, blank=True)
    service = models.ForeignKey('Genius_Service', on_delete=models.PROTECT, related_name='quotes')
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


class Genius_MarketingSourceType(models.Model):
    id = models.IntegerField(primary_key=True)
    label = models.CharField(max_length=255, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    list_order = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return self.label or f"Marketing Source Type {self.id}"


class Genius_MarketingSource(models.Model):
    id = models.IntegerField(primary_key=True)
    type_id = models.IntegerField(null=True, blank=True)
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


class Genius_UserTitle(models.Model):
    id = models.SmallIntegerField(primary_key=True)
    title = models.CharField(max_length=100, null=True, blank=True)
    abbreviation = models.CharField(max_length=10, null=True, blank=True)
    roles = models.CharField(max_length=256, null=True, blank=True)
    type_id = models.SmallIntegerField(null=True, blank=True)
    section_id = models.SmallIntegerField(null=True, blank=True)
    sort = models.SmallIntegerField(null=True, blank=True)
    pay_component_group_id = models.SmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_unique_per_division = models.BooleanField(default=False)

    def __str__(self):
        return self.title or f"Title {self.id}"

class Genius_Lead(models.Model):
    lead_id = models.IntegerField(primary_key=True)
    contact = models.IntegerField(null=True, blank=True)
    division_id = models.IntegerField(null=True, blank=True, db_column='division')
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
    type1 = models.SmallIntegerField(null=True, blank=True)
    phone2 = models.CharField(max_length=12, null=True, blank=True)
    type2 = models.SmallIntegerField(null=True, blank=True)
    phone3 = models.CharField(max_length=12, null=True, blank=True)
    type3 = models.SmallIntegerField(null=True, blank=True)
    phone4 = models.CharField(max_length=12, null=True, blank=True)
    type4 = models.SmallIntegerField(null=True, blank=True)
    source = models.SmallIntegerField(null=True, blank=True)
    source_notes = models.CharField(max_length=64, null=True, blank=True)
    sourced_on = models.DateTimeField(null=True, blank=True)
    job_type = models.SmallIntegerField(null=True, blank=True, default=2)
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
    added_by = models.IntegerField(null=True, blank=True)
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

    def __str__(self):
        return f"{self.first_name} {self.last_name or ''}".strip() or f"Lead {self.lead_id}"


class Genius_MarketSharpSource(models.Model):
    id = models.AutoField(primary_key=True)
    marketsharp_id = models.CharField(max_length=256, null=True, blank=True)
    source_name = models.CharField(max_length=128, null=True, blank=True)
    inactive = models.SmallIntegerField(default=0) 

    def __str__(self):
        return self.source_name or f"MarketSharp Source {self.id}"


class Genius_MarketSharpMarketingSourceMap(models.Model):
    marketsharp_id = models.CharField(max_length=128, unique=True)
    marketing_source_id = models.IntegerField(default=-1)

    def __str__(self):
        return f"MarketSharp ID: {self.marketsharp_id}, Marketing Source ID: {self.marketing_source_id}"

