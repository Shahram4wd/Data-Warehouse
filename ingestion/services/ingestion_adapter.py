"""
Ingestion adapter service that maps source keys and modes to management commands.
"""
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def get_command_for_source(source_key: str, mode: str, model_name: str = None):
    """
    Get the command name and default arguments for a specific source and mode.
    This is a helper function that returns command info without executing it.
    
    Args:
        source_key: The source identifier (e.g., 'arrivy', 'hubspot', 'marketsharp')
        mode: The ingestion mode ('delta' or 'full')
        model_name: Optional specific model name for model-specific commands
        
    Returns:
        tuple: (command_name, default_args_dict)
        
    Raises:
        ValueError: If the source/mode combination is not supported
    """
    return _get_command_for_source(source_key, mode, model_name)

def run_source_ingestion(source_key: str, mode: str, model_name: str = None, **options):
    """
    Run ingestion for a specific source and mode.
    
    Args:
        source_key: The source identifier (e.g., 'arrivy', 'hubspot', 'marketsharp')
        mode: The ingestion mode ('delta' or 'full')
        model_name: Optional specific model name for model-specific commands
        **options: Additional options passed to the ingestion command
        
    Raises:
        ValueError: If the source/mode combination is not supported
        Exception: If the ingestion command fails
    """
    
    # Get the command for this source/model combination
    command, default_args = _get_command_for_source(source_key, mode, model_name)
    
    logger.info(f"Running ingestion command: {command} with args: {default_args}")
    
    # Merge default args with provided options
    final_args = default_args.copy()
    
    # Override with provided options, filtering out None values
    for k, v in options.items():
        if v is not None:
            final_args[k] = v
    
    try:
        # Execute the management command
        call_command(command, **final_args)
        logger.info(f"Successfully completed {command} for {source_key}/{mode}")
        
    except Exception as e:
        logger.error(f"Failed to execute {command} for {source_key}/{mode}: {e}")
        raise

def _get_command_for_source(source_key: str, mode: str, model_name: str = None):
    """Get the appropriate command and default args for a source/model combination"""
    from ingestion.models.common import SyncHistory
    from django.utils import timezone
    
    source_key = source_key.lower()
    mode = mode.lower()
    
    # Handle Genius models with specific commands
    if source_key == 'genius' and model_name:
        command = _get_genius_command(model_name)
        
        # If no command found (returns None), skip this sync
        if command is None:
            raise ValueError(f"No command mapping found for Genius model {model_name}, skipping sync")
        
        default_args = {}
        
        if mode == "full":
            default_args = {"full": True}
        elif mode == "delta":
            # For delta syncs, get the last sync timestamp
            sync_type = _get_genius_sync_type(model_name)
            if sync_type:
                last_sync_time = SyncHistory.get_last_sync_timestamp(source_key, sync_type)
                if last_sync_time:
                    # Format timestamp for the --since parameter
                    default_args = {"since": last_sync_time.isoformat()}
                # If no last sync time, do a full sync as fallback
                # (this handles the first run case)
        
        return command, default_args
    
    # Handle CallRail models with specific commands
    if source_key == 'callrail' and model_name:
        command = _get_callrail_command(model_name)
        
        # If no command found (returns None), skip this sync
        if command is None:
            raise ValueError(f"No command mapping found for CallRail model {model_name}, skipping sync")
        
        default_args = {"full": True} if mode == "full" else {}
        return command, default_args
    
    # Define the mapping between source/mode and management commands for other sources
    command_map = {
        # Arrivy source
        ("arrivy", "delta"): ("sync_arrivy_all", {}),
        ("arrivy", "full"): ("sync_arrivy_all", {"full": True}),
        
        # HubSpot source  
        ("hubspot", "delta"): ("sync_hubspot_all", {}),
        ("hubspot", "full"): ("sync_hubspot_all", {"full": True}),
        
        # MarketSharp source
        ("marketsharp", "delta"): ("sync_marketsharp_data", {}),
        ("marketsharp", "full"): ("sync_marketsharp_data", {"full": True}),
        
        # SalesPro source
        ("salespro", "delta"): ("db_salespro_all", {}),
        ("salespro", "full"): ("db_salespro_all", {"full": True}),
        
        # SalesRabbit source
        ("salesrabbit", "delta"): ("sync_salesrabbit_all", {}),
        ("salesrabbit", "full"): ("sync_salesrabbit_all", {"full": True}),
        
        # CallRail source
        ("callrail", "delta"): ("sync_callrail_all", {}),
        ("callrail", "full"): ("sync_callrail_all", {"full": True}),
        
        # Google Sheets source
        ("gsheet", "delta"): ("sync_gsheet_all", {}),
        ("gsheet", "full"): ("sync_gsheet_all", {"full": True}),
        
        # LeadConduit source
        ("leadconduit", "delta"): ("sync_leadconduit_all", {}),
        ("leadconduit", "full"): ("sync_leadconduit_all", {"full": True}),
        
        # Five9 source
        ("five9", "delta"): ("sync_five9_contacts", {}),
        ("five9", "full"): ("sync_five9_contacts", {"full": True}),
    }
    
    # Look up the command configuration
    key = (source_key, mode)
    if key in command_map:
        return command_map[key]
    
    # If no specific mapping found, raise error
    available_keys = list(command_map.keys())
    raise ValueError(
        f"Unsupported source/mode combination: {source_key}/{mode}. "
        f"Available combinations: {available_keys}"
    )

def normalize_sync_type(crm_source: str, sync_type: str) -> str:
    """
    Normalize sync_type to standardized format for any CRM system.
    This is the main function that should be used across the entire application.
    
    Args:
        crm_source: The CRM source (e.g., 'genius', 'callrail', 'five9', 'arrivy')
        sync_type: The sync_type to normalize
        
    Returns:
        Normalized sync_type in standardized format
    """
    if not sync_type:
        return 'all'
    
    # Route to appropriate normalizer based on CRM source
    if crm_source == 'genius':
        return _get_genius_sync_type(sync_type) or sync_type
    elif crm_source == 'callrail':
        return _get_callrail_sync_type(sync_type) or sync_type
    elif crm_source == 'five9':
        return _get_five9_sync_type(sync_type) or sync_type
    elif crm_source == 'arrivy':
        return _get_arrivy_sync_type(sync_type) or sync_type
    elif crm_source == 'hubspot':
        return _get_hubspot_sync_type(sync_type) or sync_type
    
    return sync_type

def _get_callrail_sync_type(sync_type: str) -> str:
    """Normalize CallRail sync_type from legacy format"""
    if not sync_type or not sync_type.startswith('CallRail_'):
        return None
        
    base_name = sync_type.replace('CallRail_', '').lower()
    pluralization_map = {
        'account': 'accounts',
        'call': 'calls',
        'company': 'companies', 
        'tag': 'tags',
        'tracker': 'trackers',
        'user': 'users'
    }
    return pluralization_map.get(base_name, base_name)

def _get_five9_sync_type(sync_type: str) -> str:
    """Normalize Five9 sync_type from legacy format"""
    if not sync_type or not sync_type.startswith('Five9'):
        return None
        
    base_name = sync_type.replace('Five9', '').lower()
    pluralization_map = {
        'contact': 'contacts'
    }
    return pluralization_map.get(base_name, base_name)

def _get_arrivy_sync_type(sync_type: str) -> str:
    """Normalize Arrivy sync_type from legacy format"""
    if not sync_type or not sync_type.startswith('Arrivy_'):
        return None
        
    base_name = sync_type.replace('Arrivy_', '').lower()
    pluralization_map = {
        'booking': 'bookings',
        'group': 'groups',
        'status': 'statuses'
    }
    return pluralization_map.get(base_name, base_name)

def _get_hubspot_sync_type(sync_type: str) -> str:
    """Normalize HubSpot sync_type from legacy format"""
    if not sync_type or not sync_type.startswith('HubSpot_'):
        return None
        
    base_name = sync_type.replace('HubSpot_', '').lower()
    
    # Handle special HubSpot naming conventions
    conversion_map = {
        'associationscontactappointment': 'associations_contact_appointment',
        'contact': 'contacts',
        'deal': 'deals',
        'appointment': 'appointments',
        'division': 'divisions',
        'geniususer': 'genius_users'
    }
    return conversion_map.get(base_name, base_name)

def _get_genius_sync_type(model_name: str) -> str:
    """Get the sync_type for a Genius model by checking if it follows common patterns"""
    # Most genius sync types follow a simple pattern: 
    # 'Genius_Appointment' -> 'appointments'
    # 'Genius_Lead' -> 'leads' 
    # 'Genius_Prospect' -> 'prospects'
    
    if not model_name or not model_name.startswith('Genius_'):
        return None
        
    # Remove 'Genius_' prefix and convert to lowercase
    base_name = model_name.replace('Genius_', '').lower()
    
    # Handle pluralization and special mappings - most sync types are plural
    pluralization_map = {
        'appointment': 'appointments',
        'appointmentoutcome': 'appointment_outcomes',
        'appointmentoutcometype': 'appointment_outcome_types', 
        'appointmentservice': 'appointment_services',
        'appointmenttype': 'appointment_types',
        'lead': 'leads',
        'prospect': 'prospects', 
        'quote': 'quotes',
        'job': 'jobs',
        'jobfinancing': 'job_financings',
        'jobstatus': 'job_statuses',
        'jobchangeorder': 'job_change_orders',
        'jobchangeorderitem': 'job_change_order_items',
        'jobchangeordertype': 'job_change_order_types',
        'jobchangeorderreason': 'job_change_order_reasons',
        'division': 'divisions',
        'divisiongroup': 'division_groups',
        'divisionregion': 'division_regions',
        'user': 'users',
        'userdata': 'users',  # Genius_UserData -> users
        'usertitle': 'user_titles',
        'userassociation': 'user_associations',
        'service': 'services',
        # Keep as-is (already correct format)
        'marketingsourcetype': 'marketing_source_types',
        'marketingsource': 'marketing_sources',
        'marketsharp': 'marketsharp_sources',
        'prospectssource': 'prospect_sources',
    }
    
    return pluralization_map.get(base_name, base_name)

def _get_genius_command(model_name: str) -> str:
    """Get the specific command for a Genius model"""
    # Map both full model names and sync types to their specific commands
    genius_commands = {
        # Full model names (all 28 models from genius.py)
        'Genius_Appointment': 'db_genius_appointments',
        'Genius_AppointmentOutcome': 'db_genius_appointment_outcomes', 
        'Genius_AppointmentOutcomeType': 'db_genius_appointment_outcome_types',
        'Genius_AppointmentService': 'db_genius_appointment_services',
        'Genius_AppointmentType': 'db_genius_appointment_types',
        'Genius_Division': 'db_genius_divisions',
        'Genius_DivisionGroup': 'db_genius_division_groups',
        'Genius_DivisionRegion': 'db_genius_division_regions',
        'Genius_Job': 'db_genius_jobs',
        'Genius_JobChangeOrder': 'db_genius_job_change_orders',
        'Genius_JobChangeOrderItem': 'db_genius_job_change_order_items',
        'Genius_JobChangeOrderReason': 'db_genius_job_change_order_reasons',
        'Genius_JobChangeOrderStatus': 'db_genius_job_change_order_statuses',
        'Genius_JobChangeOrderType': 'db_genius_job_change_order_types',
        'Genius_JobFinancing': 'db_genius_job_financings',
        'Genius_JobStatus': 'db_genius_job_statuses',
        'Genius_Lead': 'db_genius_leads',
        'Genius_Location': 'db_genius_locations',
        'Genius_MarketingSource': 'db_genius_marketing_sources',
        'Genius_MarketingSourceType': 'db_genius_marketing_source_types',
        'Genius_MarketSharpMarketingSourceMap': 'db_genius_marketsharp_marketing_source_maps',
        'Genius_MarketSharpSource': 'db_genius_marketsharp_sources',
        'Genius_Person': 'db_genius_people',
        'Genius_Product': 'db_genius_products',
        'Genius_Prospect': 'db_genius_prospects',
        'Genius_ProspectSource': 'db_genius_prospect_sources',
        'Genius_Quote': 'db_genius_quotes',
        'Genius_SalesRep': 'db_genius_sales_reps',
        'Genius_Service': 'db_genius_services',
        'Genius_Unit': 'db_genius_units',
        'Genius_UnitType': 'db_genius_unit_types',
        'Genius_UserAssociation': 'db_genius_user_associations',
        'Genius_UserData': 'db_genius_users',
        'Genius_UserTitle': 'db_genius_user_titles',
        
        # Sync types (matching JavaScript modelNameToSyncType function behavior)
        # JavaScript strips 'Genius_' (7 chars) and converts to lowercase + pluralization
        'appointments': 'db_genius_appointments',
        'appointmentoutcomes': 'db_genius_appointment_outcomes',
        'appointmentoutcometypes': 'db_genius_appointment_outcome_types', 
        'appointmentservices': 'db_genius_appointment_services',
        'appointmenttypes': 'db_genius_appointment_types',
        'divisiongroups': 'db_genius_division_groups',
        'divisionregions': 'db_genius_division_regions',
        'divisions': 'db_genius_divisions',
        'jobs': 'db_genius_jobs',
        'jobchangeorders': 'db_genius_job_change_orders',
        'jobchangeorderitems': 'db_genius_job_change_order_items',
        'jobchangeorderreasons': 'db_genius_job_change_order_reasons',
        'jobchangeorderstatuses': 'db_genius_job_change_order_statuses',
        'jobchangeorderstatus': 'db_genius_job_change_order_statuses',  # JavaScript: 'JobChangeOrderStatus' -> 'jobchangeorderstatus' (singular ends with 's')
        'jobchangeordertypes': 'db_genius_job_change_order_types',
        'jobfinancings': 'db_genius_job_financings',
        'jobstatuses': 'db_genius_job_statuses',
        'jobstatus': 'db_genius_job_statuses',  # JavaScript: 'JobStatus' -> 'jobstatus' (singular ends with 's')
        'leads': 'db_genius_leads',
        'locations': 'db_genius_locations',
        'marketingsources': 'db_genius_marketing_sources',
        'marketingsourcetypes': 'db_genius_marketing_source_types',
        'marketsharpsources': 'db_genius_marketsharp_sources',
        'marketsharpmarketingsourcemaps': 'db_genius_marketsharp_marketing_source_maps',
        'people': 'db_genius_people',
        'products': 'db_genius_products',
        'prospects': 'db_genius_prospects',
        'prospectsources': 'db_genius_prospect_sources',
        'quotes': 'db_genius_quotes',
        'salesreps': 'db_genius_sales_reps',
        'services': 'db_genius_services',
        'units': 'db_genius_units',
        'unittypes': 'db_genius_unit_types',
        'userassociations': 'db_genius_user_associations',
        'userdatas': 'db_genius_users',  # JavaScript: 'UserData' -> 'userdatas'
        'usertitles': 'db_genius_user_titles',
    }
    
    if model_name in genius_commands:
        return genius_commands[model_name]
    
    # If no specific command found, log and return None to skip
    logger.warning(f"No specific command found for {model_name}, skipping sync")
    return None

def _get_callrail_command(model_name: str) -> str:
    """Get the specific command for a CallRail model"""
    # Map both full model names and sync types to their specific commands
    callrail_commands = {
        # Full model names
        'CallRail_Account': 'sync_callrail_accounts',
        'CallRail_Call': 'sync_callrail_calls',
        'CallRail_Company': 'sync_callrail_companies',
        'CallRail_FormSubmission': 'sync_callrail_form_submissions',
        'CallRail_Tag': 'sync_callrail_tags',
        'CallRail_TextMessage': 'sync_callrail_text_messages',
        'CallRail_Tracker': 'sync_callrail_trackers',
        'CallRail_User': 'sync_callrail_users',
        
        # Sync types (from JavaScript modelNameToSyncType)
        'accounts': 'sync_callrail_accounts',
        'calls': 'sync_callrail_calls',
        'companies': 'sync_callrail_companies',
        'form_submissions': 'sync_callrail_form_submissions',
        'tags': 'sync_callrail_tags',
        'text_messages': 'sync_callrail_text_messages',
        'trackers': 'sync_callrail_trackers',
        'users': 'sync_callrail_users',
    }
    
    if model_name in callrail_commands:
        return callrail_commands[model_name]
    
    # If no specific command found, log and return None to skip
    logger.warning(f"No specific command found for {model_name}, skipping sync")
    return None

def get_available_sources():
    """
    Get a list of all available source keys.
    
    Returns:
        list: List of available source key strings
    """
    available_sources = [
        "arrivy", "hubspot", "marketsharp", "genius", "salespro", 
        "salesrabbit", "callrail", "gsheet", "leadconduit", "five9"
    ]
    
    return sorted(available_sources)

def get_available_modes():
    """
    Get a list of all available ingestion modes.
    
    Returns:
        list: List of available mode strings
    """
    return ["delta", "full"]

def validate_source_mode(source_key: str, mode: str):
    """
    Validate if a source/mode combination is supported.
    
    Args:
        source_key: The source identifier
        mode: The ingestion mode
        
    Returns:
        bool: True if the combination is supported, False otherwise
    """
    available_sources = [
        "arrivy", "hubspot", "marketsharp", "genius", "salespro", 
        "salesrabbit", "callrail", "gsheet", "leadconduit", "five9"
    ]
    available_modes = ["delta", "full"]
    
    return source_key.lower() in available_sources and mode.lower() in available_modes
