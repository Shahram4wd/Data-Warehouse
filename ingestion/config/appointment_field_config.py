"""
Configuration for HubSpot appointment field monitoring and validation
"""

# Field length limits based on the Hubspot_Appointment model
APPOINTMENT_FIELD_LIMITS = {
    # CharField(max_length=255) fields
    'appointment_id': 255,
    'genius_appointment_id': 255,
    'marketsharp_id': 255,
    'hs_appointment_name': 255,
    'hs_object_id': 255,
    'hs_pipeline': 255,
    'hs_pipeline_stage': 255,
    'hs_created_by_user_id': 255,
    'hs_object_source': 255,
    'hs_object_source_detail_1': 255,
    'hs_object_source_detail_2': 255,
    'hs_object_source_detail_3': 255,
    'hs_object_source_id': 255,
    'hs_object_source_label': 255,
    'hs_object_source_user_id': 255,
    'hs_unique_creation_key': 255,
    'hs_updated_by_user_id': 255,
    'first_name': 255,
    'last_name': 255,
    'address1': 255,
    'address2': 255,
    'product_interest_primary': 255,
    'product_interest_secondary': 255,
    'user_id': 255,
    'canvasser': 255,
    'canvasser_id': 255,
    'hubspot_owner_id': 255,
    'hubspot_team_id': 255,
    'division_id': 255,
    'division': 255,
    'primary_source': 255,
    'secondary_source': 255,
    'prospect_id': 255,
    'prospect_source_id': 255,
    'hscontact_id': 255,
    'sourcefield': 255,
    'type_id_text': 255,
    'marketsharp_appt_type': 255,
    'complete_outcome_id_text': 255,
    'confirm_with': 255,
    'cancel_reason': 255,
    'div_cancel_reasons': 255,
    'qc_cancel_reasons': 255,
    
    # Shorter specific length fields
    'phone1': 20,
    'phone2': 20,
    'city': 100,
    'state': 50,
    'zip': 20,
    'appointment_status': 100,
    'appointment_confirmed': 100,
    'appointment_response': 100,
    
    # URL fields (Django URLField default max_length=200)
    'salespro_fileurl_contract': 200,
    'salespro_fileurl_estimate': 200,
    
    # Email fields (Django EmailField default max_length=254)
    'email': 254,
    'canvasser_email': 254,
}

# Fields that should be monitored for frequent truncation
MONITORED_FIELDS = [
    'hs_appointment_name',
    'address1',
    'address2',
    'appointment_services',
    'lead_services',
    'notes',
    'arrivy_details',
    'arrivy_notes',
    'salespro_notes',
]

# Fields that are commonly problematic and should be validated extra carefully
PROBLEMATIC_FIELDS = [
    'email',  # Often contains invalid formats
    'phone1',  # Often contains invalid formats
    'phone2',  # Often contains invalid formats
    'zip',  # Often contains invalid formats
    'salespro_fileurl_estimate',  # Often contains 'N' instead of URL
    'salespro_fileurl_contract',  # Often contains 'N' instead of URL
]
