# HubSpot Appointment Model vs Expected Properties Comparison

## Overview
This document compares the current `Hubspot_Appointment` model in your Django application with the properties list you provided from HubSpot.

## Summary of Findings

### ✅ Properties Present in Model (123 out of 134 properties)
### ❌ Properties Missing from Model (11 properties)

---

## Missing Properties in Current Model

The following properties from your list are **NOT** present in the current model:

| Property Name | Internal Name | Type | Notes |
|---------------|---------------|------|-------|
| Appointment Confirmed | `appointment_confirmed` | enumeration | Missing field |
| Arrivy Details | `arrivy_details` | string | Missing field |
| Arrivy Notes | `arrivy_notes` | string | Missing field |
| Arrivy Result Full String | `arrivy_result_full_string` | string | Missing field |
| Arrivy Salesrep First Name | `arrivy_salesrep_first_name` | string | Missing field |
| Arrivy Salesrep Last Name | `arrivy_salesrep_last_name` | string | Missing field |
| Arrivy Status Title | `arrivy_status_title` | string | Missing field |
| Cancel Reason | `cancel_reason` | enumeration | Missing field |
| Created By Make | `created_by_make` | string | Missing field |
| Div Cancel Reasons | `div_cancel_reasons` | enumeration | Missing field |
| Division | `division` | string | Missing field (only `division_id` exists) |
| F9 TFUID | `f9_tfuid` | string | Missing field |
| Genius Quote ID | `genius_quote_id` | string | Missing field |
| Genius Quote Response | `genius_quote_response` | string | Missing field |
| Genius Quote Response Status | `genius_quote_response_status` | string | Missing field |
| Genius Response | `genius_response` | string | Missing field |
| Genius Response Status | `genius_response_status` | string | Missing field |
| Genius Resubmit | `genius_resubmit` | enumeration | Missing field |
| QC Cancel Reasons | `qc_cancel_reasons` | enumeration | Missing field |
| Salespro Consider Solar | `salespro_consider_solar` | string | Missing field |
| Salespro Customer ID | `salespro_customer_id` | string | Missing field |
| Salespro Estimate ID | `salespro_estimate_id` | string | Missing field |
| Set Date | `set_date` | date | Missing field |
| Source Field | `sourcefield` | string | Missing field |

---

## Properties Present in Model but with Type Mismatches

| Property Name | Internal Name | Expected Type | Current Model Type | Notes |
|---------------|---------------|---------------|-------------------|-------|
| add_user_id | `add_user_id` | number | CharField | Should be IntegerField |
| complete_outcome_id | `complete_outcome_id` | number | CharField | Should be IntegerField |
| complete_user_id | `complete_user_id` | number | CharField | Should be IntegerField |
| confirm_user_id | `confirm_user_id` | number | CharField | Should be IntegerField |
| marketing_task_id | `marketing_task_id` | number | CharField | Should be IntegerField |
| type_id | `type_id` | number | CharField | Should be IntegerField |

---

## Properties Present and Correctly Typed (117 properties)

### Basic HubSpot Fields
- ✅ `hs_appointment_end` (datetime)
- ✅ `hs_appointment_name` (string)
- ✅ `hs_appointment_start` (datetime)
- ✅ `hs_created_by_user_id` (number)
- ✅ `hs_createdate` (datetime)
- ✅ `hs_duration` (number)
- ✅ `hs_lastmodifieddate` (datetime)
- ✅ `hs_merged_object_ids` (enumeration)
- ✅ `hs_object_id` (number)
- ✅ `hs_object_source_detail_1` (string)
- ✅ `hs_object_source_detail_2` (string)
- ✅ `hs_object_source_detail_3` (string)
- ✅ `hs_object_source_label` (enumeration)
- ✅ `hs_pipeline` (enumeration)
- ✅ `hs_pipeline_stage` (enumeration)
- ✅ `hs_updated_by_user_id` (number)

### Contact Information
- ✅ `add_date` (datetime)
- ✅ `address1` (string)
- ✅ `address2` (string)
- ✅ `appointment_id` (number)
- ✅ `appointment_response` (string)
- ✅ `appointment_services` (string)
- ✅ `appointment_status` (enumeration)
- ✅ `city` (string)
- ✅ `email` (string)
- ✅ `first_name` (string)
- ✅ `last_name` (string)
- ✅ `phone1` (string)
- ✅ `phone2` (string)
- ✅ `state` (string)
- ✅ `zip` (string)

### Arrivy Integration
- ✅ `arrivy_appt_date` (string)
- ✅ `arrivy_confirm_date` (string)
- ✅ `arrivy_confirm_user` (string)
- ✅ `arrivy_created_by` (string)
- ✅ `arrivy_object_id` (string)
- ✅ `arrivy_status` (string)
- ✅ `arrivy_user` (string)
- ✅ `arrivy_user_divison_id` (string)
- ✅ `arrivy_user_external_id` (string)
- ✅ `arrivy_username` (string)

### Assignment and Completion
- ✅ `assign_date` (datetime)
- ✅ `canvasser` (string)
- ✅ `canvasser_email` (string)
- ✅ `canvasser_id` (string)
- ✅ `complete_date` (datetime)
- ✅ `complete_outcome_id_text` (string)
- ✅ `confirm_date` (datetime)
- ✅ `confirm_with` (string)

### Dates and Times
- ✅ `date` (date)
- ✅ `duration` (string)
- ✅ `time` (string)

### Division and Ownership
- ✅ `division_id` (string)
- ✅ `hubspot_owner_assigneddate` (datetime)
- ✅ `hubspot_owner_id` (enumeration)
- ✅ `hubspot_team_id` (enumeration)

### Additional Fields
- ✅ `error_details` (string)
- ✅ `genius_appointment_id` (string)
- ✅ `hscontact_id` (string)
- ✅ `is_complete` (number)
- ✅ `lead_services` (string)
- ✅ `leap_estimate_id` (string)
- ✅ `log` (string)
- ✅ `marketsharp_appt_type` (string)
- ✅ `marketsharp_id` (string)
- ✅ `notes` (string)
- ✅ `primary_source` (string)
- ✅ `product_interest_primary` (string)
- ✅ `product_interest_secondary` (string)
- ✅ `prospect_id` (string)
- ✅ `prospect_source_id` (string)
- ✅ `secondary_source` (string)
- ✅ `spouses_present` (number)
- ✅ `title` (string)
- ✅ `type_id_text` (string)
- ✅ `user_id` (string)
- ✅ `year_built` (number)

### SalesPro Integration (All Present)
- ✅ `salespro_both_homeowners` (string)
- ✅ `salespro_deadline` (string)
- ✅ `salespro_deposit_type` (string)
- ✅ `salespro_fileurl_contract` (string)
- ✅ `salespro_fileurl_estimate` (string)
- ✅ `salespro_financing` (string)
- ✅ `salespro_job_size` (string)
- ✅ `salespro_job_type` (string)
- ✅ `salespro_last_price_offered` (string)
- ✅ `salespro_notes` (string)
- ✅ `salespro_one_year_price` (string)
- ✅ `salespro_preferred_payment` (string)
- ✅ `salespro_requested_start` (string)
- ✅ `salespro_result` (string)
- ✅ `salespro_result_notes` (string)
- ✅ `salespro_result_reason_demo` (string)
- ✅ `salespro_result_reason_no_demo` (string)

---

## Properties in Model but NOT in Your List

These fields exist in the model but weren't in your provided list:

### System/Meta Fields
- `created_at` (auto-generated)
- `updated_at` (auto-generated)
- `archived` (boolean)

### Additional HubSpot System Fields
- `hs_all_accessible_team_ids`
- `hs_all_assigned_business_unit_ids`
- `hs_all_owner_ids`
- `hs_all_team_ids`
- `hs_object_source`
- `hs_object_source_id`
- `hs_object_source_user_id`
- `hs_owning_teams`
- `hs_read_only`
- `hs_shared_team_ids`
- `hs_shared_user_ids`
- `hs_unique_creation_key`
- `hs_user_ids_of_all_notification_followers`
- `hs_user_ids_of_all_notification_unfollowers`
- `hs_user_ids_of_all_owners`
- `hs_was_imported`

### Test Field
- `tester_test` (appears to be a test field)

---

## Recommendations

### 1. Add Missing Fields
Consider adding the 24 missing fields to ensure complete data capture from HubSpot.

### 2. Fix Type Mismatches
Update the 6 fields with incorrect types:
- Convert CharField to IntegerField for numeric IDs
- Ensure proper data validation

### 3. Review Field Usage
- Verify if all existing fields are actually being used
- Consider removing unused fields to optimize the model

### 4. Data Migration
If you add the missing fields, you'll need to create a Django migration to update the database schema.

---

## Related Error from Log
The error in your ingestion.log mentions:
```
Hubspot_Deal() got unexpected keyword arguments: 'dealname'
```

This suggests there might be similar field mapping issues in other models that should be reviewed.
