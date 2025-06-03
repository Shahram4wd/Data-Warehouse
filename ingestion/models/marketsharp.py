from django.db import models
from datetime import datetime
import uuid

class MarketSharp_Activity(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    due_date = models.DateTimeField(blank=True, null=True)
    reminder_minutes = models.IntegerField(blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    appointment_id = models.UUIDField(blank=True, null=True)
    assign_to_employee_id = models.UUIDField(blank=True, null=True)
    scheduled_by_employee_id = models.UUIDField(blank=True, null=True)
    reminder_dismissed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_updated_by = models.CharField(max_length=255)
    last_update = models.DateTimeField()
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()
    inquiry_id = models.UUIDField(blank=True, null=True)
    activity_result_id = models.IntegerField(blank=True, null=True)
    activity_reference_id = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Activity"
        verbose_name_plural = "Activities"

    def __str__(self):
        return f"{self.type} - {self.contact_id}"


class MarketSharp_ActivityReference(models.Model):
    id = models.IntegerField(primary_key=True)
    company_id = models.IntegerField()
    name = models.CharField(max_length=255)
    inquiry_required = models.BooleanField(default=False)
    appointment_required = models.BooleanField(default=False)
    is_active = models.BooleanField(default=False)
    created_by = models.CharField(max_length=255)
    created_date_utc = models.DateTimeField()
    last_update_by = models.UUIDField(blank=True, null=True)
    last_update_utc = models.DateTimeField()

    class Meta:
        verbose_name = "Activity Reference"
        verbose_name_plural = "Activity References"

    def __str__(self):
        return self.name


class MarketSharp_ActivityResult(models.Model):
    id = models.IntegerField(primary_key=True)  # Integer field for ID
    company_id = models.IntegerField()
    name = models.CharField(max_length=255)
    email_success = models.BooleanField(default=False)
    email_failure = models.BooleanField(default=False)
    confirmed = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_update_by = models.UUIDField(blank=True, null=True)
    last_update = models.DateTimeField()
    created_by = models.CharField(max_length=255)
    created_date = models.DateTimeField()
    count_as_appt_confirmed = models.BooleanField(default=False)
    count_as_appt_created = models.BooleanField(default=False)
    count_as_contacted = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Activity Result"
        verbose_name_plural = "Activity Results"

    def __str__(self):
        return self.name
    

class MarketSharp_Address(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    line1 = models.CharField(max_length=255, blank=True, null=True)
    line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=20, blank=True, null=True)
    county = models.CharField(max_length=255, blank=True, null=True)
    zip = models.CharField(max_length=10, blank=True, null=True)
    country = models.CharField(max_length=100, blank=True, null=True)
    carrier_route = models.CharField(max_length=50, blank=True, null=True)
    cass = models.CharField(max_length=50, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    zip4 = models.CharField(max_length=10, blank=True, null=True)
    dpbc2 = models.CharField(max_length=10, blank=True, null=True)
    bar_code = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Address"
        verbose_name_plural = "Addresses"

    def __str__(self):
        return f"{self.line1}, {self.city}, {self.state}, {self.zip}"


class MarketSharp_Appointment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry_id = models.UUIDField(blank=True, null=True)
    salesperson1_id = models.UUIDField(blank=True, null=True)
    salesperson2_id = models.UUIDField(blank=True, null=True)
    set_by_id = models.UUIDField(blank=True, null=True)
    result_id = models.UUIDField(blank=True, null=True)
    last_update_by = models.UUIDField(blank=True, null=True)
    created_by = models.UUIDField(blank=True, null=True)
    appointment_date = models.DateTimeField(blank=True, null=True)
    set_date = models.DateTimeField(blank=True, null=True)
    issued_date = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    subject = models.CharField(max_length=255, blank=True, null=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    result_reason = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    created_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Appointment"
        verbose_name_plural = "Appointments"

    def __str__(self):
        return f"Appointment {self.id}"
    
    
class MarketSharp_AppointmentResult(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    presentation = models.BooleanField(default=False)
    sold = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Appointment Result"
        verbose_name_plural = "Appointment Results"

    def __str__(self):
        return self.name or str(self.id)
    
class MarketSharp_Company(models.Model):
    id = models.IntegerField(primary_key=True)
    number = models.IntegerField(null=True, blank=True)
    name = models.CharField(max_length=255, null=True, blank=True)
    owner = models.CharField(max_length=255, null=True, blank=True)
    address_line1 = models.CharField(max_length=255, null=True, blank=True)
    address_line2 = models.CharField(max_length=255, null=True, blank=True)
    address_city = models.CharField(max_length=255, null=True, blank=True)
    address_state = models.CharField(max_length=255, null=True, blank=True)
    address_zip = models.CharField(max_length=20, null=True, blank=True)
    email = models.EmailField(null=True, blank=True)
    website = models.URLField(null=True, blank=True)
    contact_name = models.CharField(max_length=255, null=True, blank=True)
    contact_title = models.CharField(max_length=255, null=True, blank=True)
    phone = models.CharField(max_length=20, null=True, blank=True)
    fax = models.CharField(max_length=20, null=True, blank=True)
    time_zone = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        verbose_name = "Company"
        verbose_name_plural = "Companies"

    def __str__(self):
        return self.name

class MarketSharp_Contact(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.IntegerField()
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_initial = models.CharField(max_length=1, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    income_code = models.CharField(max_length=100, blank=True, null=True)
    age_code = models.CharField(max_length=100, blank=True, null=True)
    structure_age_code = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone_id = models.UUIDField(blank=True, null=True)
    primary_address_id = models.UUIDField(blank=True, null=True)
    website1 = models.URLField(blank=True, null=True)
    website2 = models.URLField(blank=True, null=True)
    website3 = models.URLField(blank=True, null=True)
    email1 = models.EmailField(blank=True, null=True)
    email1_can_mail = models.BooleanField(default=False)
    email2 = models.EmailField(blank=True, null=True)
    email2_can_mail = models.BooleanField(default=False)
    email3 = models.EmailField(blank=True, null=True)
    email3_can_mail = models.BooleanField(default=False)
    is_tagged = models.BooleanField(blank=True, null=True)
    structure_value_code = models.CharField(max_length=100, blank=True, null=True)
    do_not_mail = models.BooleanField(default=False)
    year_home_built = models.CharField(max_length=4, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    length_of_residence = models.CharField(max_length=50, blank=True, null=True)
    style_of_home = models.CharField(max_length=100, blank=True, null=True)
    mail_merge_name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    creation_date = models.DateTimeField()
    qb_sync_date = models.DateTimeField(blank=True, null=True)
    qb_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    has_dnc_phone = models.BooleanField(default=False)
    has_dne_email = models.BooleanField(default=False)
    qb_edit_sequence = models.CharField(max_length=255, blank=True, null=True)
    qb_sync_data = models.BooleanField(blank=True, null=True)
    qb_name = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()

    class Meta:
        verbose_name = "Contact"
        verbose_name_plural = "Contacts"

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else str(self.id)


class MarketSharp_ContactPhone(models.Model):
    contact_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    assistant_phone = models.CharField(max_length=50, blank=True, null=True)
    work_fax = models.CharField(max_length=50, blank=True, null=True)
    cell_phone = models.CharField(max_length=50, blank=True, null=True)
    company_phone = models.CharField(max_length=50, blank=True, null=True)
    home_phone2 = models.CharField(max_length=50, blank=True, null=True)
    home_fax = models.CharField(max_length=50, blank=True, null=True)
    pager = models.CharField(max_length=50, blank=True, null=True)
    work_phone2 = models.CharField(max_length=50, blank=True, null=True)
    company_fax = models.CharField(max_length=50, blank=True, null=True)
    home_phone = models.CharField(max_length=50, blank=True, null=True)
    work_phone = models.CharField(max_length=50, blank=True, null=True)
    other_phone = models.CharField(max_length=50, blank=True, null=True)
    cell_phone2 = models.CharField(max_length=50, blank=True, null=True)
    other_phone2 = models.CharField(max_length=50, blank=True, null=True)

    class Meta:
        verbose_name = "Contact Phone"
        verbose_name_plural = "Contact Phones"

    def __str__(self):
        return f"ContactPhone {self.contact_id}"


class MarketSharp_ContactType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField(blank=True, null=True)
    contact_type = models.CharField(max_length=50, blank=True, null=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Contact Type"
        verbose_name_plural = "Contact Types"

    def __str__(self):
        return f"ContactType {self.id} - {self.contact_type}"
 
    
class MarketSharp_CustomField(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    value = models.CharField(max_length=500, blank=True, null=True)
    contact_id = models.UUIDField(blank=True, null=True)

    class Meta:
        verbose_name = "Custom Field"
        verbose_name_plural = "Custom Fields"

    def __str__(self):
        return f"{self.name} - {self.value}"
    

class MarketSharp_Customer(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.IntegerField()
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_initial = models.CharField(max_length=1, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    income_code = models.CharField(max_length=100, blank=True, null=True)
    age_code = models.CharField(max_length=100, blank=True, null=True)
    structure_age_code = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone_id = models.UUIDField(blank=True, null=True)
    primary_address_id = models.UUIDField(blank=True, null=True)
    website1 = models.URLField(blank=True, null=True)
    website2 = models.URLField(blank=True, null=True)
    website3 = models.URLField(blank=True, null=True)
    email1 = models.EmailField(blank=True, null=True)
    email1_can_mail = models.BooleanField(default=False)
    email2 = models.EmailField(blank=True, null=True)
    email2_can_mail = models.BooleanField(default=False)
    email3 = models.EmailField(blank=True, null=True)
    email3_can_mail = models.BooleanField(default=False)
    is_tagged = models.BooleanField(blank=True, null=True)
    structure_value_code = models.CharField(max_length=100, blank=True, null=True)
    do_not_mail = models.BooleanField(default=False)
    year_home_built = models.CharField(max_length=4, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    length_of_residence = models.CharField(max_length=50, blank=True, null=True)
    style_of_home = models.CharField(max_length=100, blank=True, null=True)
    mail_merge_name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    qb_sync_date = models.DateTimeField(blank=True, null=True)
    qb_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    has_dnc_phone = models.BooleanField(default=False)
    has_dne_email = models.BooleanField(default=False)
    qb_edit_sequence = models.CharField(max_length=255, blank=True, null=True)
    qb_sync_data = models.BooleanField(blank=True, null=True)
    qb_name = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()

    class Meta:
        verbose_name = "Customer"
        verbose_name_plural = "Customers"

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else str(self.id)
  
      
class MarketSharp_Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    company_id = models.IntegerField()

    class Meta:
        verbose_name = "Employee"
        verbose_name_plural = "Employees"

    def __str__(self):
        return f"{self.name} - {self.company_id}"

  
class MarketSharp_Inquiry(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField()
    description = models.CharField(max_length=255, blank=True, null=True)
    inquiry_source_primary_id = models.UUIDField(blank=True, null=True)
    inquiry_source_secondary_id = models.UUIDField(blank=True, null=True)
    creation_date = models.DateTimeField(blank=True, null=True)
    inquiry_date = models.DateTimeField(blank=True, null=True)
    set_date = models.DateTimeField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    promoter_id = models.UUIDField(blank=True, null=True)
    canvasser_id = models.UUIDField(blank=True, null=True)
    telemarketer_id = models.UUIDField(blank=True, null=True)
    job_site_address_line1 = models.CharField(max_length=255, blank=True, null=True)
    job_site_address_line2 = models.CharField(max_length=255, blank=True, null=True)
    job_site_city = models.CharField(max_length=100, blank=True, null=True)
    job_site_state = models.CharField(max_length=20, blank=True, null=True)
    job_site_zip = models.CharField(max_length=10, blank=True, null=True)
    job_site_directions = models.TextField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    set_by_id = models.UUIDField(blank=True, null=True)
    division = models.CharField(max_length=255, blank=True, null=True)
    inquiry_status_id = models.IntegerField(blank=True, null=True)
    last_update_by = models.UUIDField(blank=True, null=True)
    last_update = models.DateTimeField()
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField(blank=True, null=True)

    class Meta:
        verbose_name = "Inquiry"
        verbose_name_plural = "Inquiries"

    def __str__(self):
        return self.description or str(self.id)


class MarketSharp_InquirySourcePrimary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    company_id = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Inquiry Source Primary"
        verbose_name_plural = "Inquiry Source Primaries"

    def __str__(self):
        return f"{self.name or 'Unnamed'} - {self.id}"


class MarketSharp_InquirySourceSecondary(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry_source_primary_id = models.UUIDField(blank=True, null=True)
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    company_id = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Inquiry Source Secondary"
        verbose_name_plural = "Inquiry Source Secondaries"

    def __str__(self):
        return self.name or str(self.id)
    

class MarketSharp_InquiryStatus(models.Model):
    id = models.IntegerField(primary_key=True)
    company_id = models.IntegerField()
    name = models.CharField(max_length=255, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update_by = models.UUIDField(blank=True, null=True)
    last_update_utc = models.DateTimeField()
    created_by = models.CharField(max_length=255, blank=True, null=True)
    created_date_utc = models.DateTimeField()

    class Meta:
        verbose_name = "Inquiry Status"
        verbose_name_plural = "Inquiry Statuses"

    def __str__(self):
        return f"{self.name} ({self.id})"

    
class MarketSharp_Job(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    contact_id = models.UUIDField(blank=True, null=True)
    inquiry_id = models.UUIDField(blank=True, null=True)
    site = models.CharField(max_length=255, blank=True, null=True)
    number = models.CharField(max_length=100, blank=True, null=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    type = models.CharField(max_length=100, blank=True, null=True)
    status = models.CharField(max_length=100, blank=True, null=True)
    address_line1 = models.CharField(max_length=255, blank=True, null=True)
    address_line2 = models.CharField(max_length=255, blank=True, null=True)
    city = models.CharField(max_length=100, blank=True, null=True)
    state = models.CharField(max_length=50, blank=True, null=True)
    zip = models.CharField(max_length=20, blank=True, null=True)
    structure_value_code = models.CharField(max_length=100, blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    start_date = models.DateTimeField(blank=True, null=True)
    sale_date = models.DateTimeField(blank=True, null=True)
    completed_date = models.DateTimeField(blank=True, null=True)
    appointment_id = models.UUIDField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    created_date = models.DateTimeField()
    exported_to_guild_quality = models.BooleanField(default=False)

    class Meta:
        verbose_name = "Job"
        verbose_name_plural = "Jobs"

    def __str__(self):
        return self.name


class MarketSharp_Lead(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.IntegerField()
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_initial = models.CharField(max_length=1, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    income_code = models.CharField(max_length=100, blank=True, null=True)
    age_code = models.CharField(max_length=100, blank=True, null=True)
    structure_age_code = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone_id = models.UUIDField(blank=True, null=True)
    primary_address_id = models.UUIDField(blank=True, null=True)
    website1 = models.URLField(blank=True, null=True)
    website2 = models.URLField(blank=True, null=True)
    website3 = models.URLField(blank=True, null=True)
    email1 = models.EmailField(blank=True, null=True)
    email1_can_mail = models.BooleanField(default=False)
    email2 = models.EmailField(blank=True, null=True)
    email2_can_mail = models.BooleanField(default=False)
    email3 = models.EmailField(blank=True, null=True)
    email3_can_mail = models.BooleanField(default=False)
    is_tagged = models.BooleanField(blank=True, null=True)
    structure_value_code = models.CharField(max_length=100, blank=True, null=True)
    do_not_mail = models.BooleanField(default=False)
    year_home_built = models.CharField(max_length=4, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    length_of_residence = models.CharField(max_length=50, blank=True, null=True)
    style_of_home = models.CharField(max_length=100, blank=True, null=True)
    mail_merge_name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255, blank=True, null=True)
    creation_date = models.DateTimeField()
    qb_sync_date = models.DateTimeField(blank=True, null=True)
    qb_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    has_dnc_phone = models.BooleanField(default=False)
    has_dne_email = models.BooleanField(default=False)
    qb_edit_sequence = models.CharField(max_length=255, blank=True, null=True)
    qb_sync_data = models.BooleanField(blank=True, null=True)
    qb_name = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()

    class Meta:
        verbose_name = "Lead"
        verbose_name_plural = "Leads"

    def __str__(self):
        return f"{self.first_name} {self.last_name}" if self.first_name and self.last_name else str(self.id)


class MarketSharp_ProductDetail(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    product_type_id = models.UUIDField(blank=True, null=True)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    company_id = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Product Detail"
        verbose_name_plural = "Product Details"

    def __str__(self):
        return f"{self.name} - {self.id}"


class MarketSharp_ProductInterest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    inquiry_id = models.UUIDField(blank=True, null=True)
    product_type_id = models.UUIDField(blank=True, null=True)
    product_detail_id = models.UUIDField(blank=True, null=True)
    price_quoted = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()

    class Meta:
        verbose_name = "Product Interest"
        verbose_name_plural = "Product Interests"

    def __str__(self):
        return f"{self.id} - {self.product_type_id}"


class MarketSharp_ProductType(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    company_id = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = "Product Type"
        verbose_name_plural = "Product Types"

    def __str__(self):
        return f"{self.name} - {self.id}"


class MarketSharp_Prospect(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company_id = models.IntegerField()
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    middle_initial = models.CharField(max_length=1, blank=True, null=True)
    title = models.CharField(max_length=255, blank=True, null=True)
    income_code = models.CharField(max_length=100, blank=True, null=True)
    age_code = models.CharField(max_length=100, blank=True, null=True)
    structure_age_code = models.CharField(max_length=100, blank=True, null=True)
    reference = models.CharField(max_length=255, blank=True, null=True)
    business_name = models.CharField(max_length=255, blank=True, null=True)
    contact_phone_id = models.UUIDField(blank=True, null=True)
    primary_address_id = models.UUIDField(blank=True, null=True)
    website1 = models.URLField(blank=True, null=True)
    website2 = models.URLField(blank=True, null=True)
    website3 = models.URLField(blank=True, null=True)
    email1 = models.EmailField(blank=True, null=True)
    email1_can_mail = models.BooleanField(default=False)
    email2 = models.EmailField(blank=True, null=True)
    email2_can_mail = models.BooleanField(default=False)
    email3 = models.EmailField(blank=True, null=True)
    email3_can_mail = models.BooleanField(default=False)
    is_tagged = models.BooleanField(blank=True, null=True)
    structure_value_code = models.CharField(max_length=100, blank=True, null=True)
    do_not_mail = models.BooleanField(default=False)
    year_home_built = models.CharField(max_length=4, blank=True, null=True)
    marital_status = models.CharField(max_length=50, blank=True, null=True)
    length_of_residence = models.CharField(max_length=50, blank=True, null=True)
    style_of_home = models.CharField(max_length=100, blank=True, null=True)
    mail_merge_name = models.CharField(max_length=255, blank=True, null=True)
    source = models.CharField(max_length=255)
    creation_date = models.DateTimeField()
    qb_sync_date = models.DateTimeField(blank=True, null=True)
    qb_id = models.CharField(max_length=100, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    last_update = models.DateTimeField()
    has_dnc_phone = models.BooleanField(default=False)
    has_dne_email = models.BooleanField(default=False)
    qb_edit_sequence = models.CharField(max_length=255, blank=True, null=True)
    qb_sync_data = models.BooleanField(blank=True, null=True)
    qb_name = models.CharField(max_length=255, blank=True, null=True)
    created_date = models.DateTimeField()

    class Meta:
        verbose_name = "Prospect"
        verbose_name_plural = "Prospects"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"
