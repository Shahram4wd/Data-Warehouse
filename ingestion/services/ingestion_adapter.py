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
    
    # Handle pluralization - most sync types are plural
    pluralization_map = {
        'appointment': 'appointments',
        'lead': 'leads',
        'prospect': 'prospects', 
        'quote': 'quotes',
        'job': 'jobs',
        'division': 'divisions',
        'user': 'users',
        'service': 'services',
        # Add other irregular plurals as needed
    }
    
    return pluralization_map.get(base_name, base_name)

def _get_genius_command(model_name: str) -> str:
    """Get the specific command for a Genius model"""
    # Map both full model names and sync types to their specific commands
    genius_commands = {
        # Full model names
        'Genius_Appointment': 'db_genius_appointments',
        'Genius_AppointmentOutcome': 'db_genius_appointment_outcomes', 
        'Genius_AppointmentOutcomeType': 'db_genius_appointment_outcome_types',
        'Genius_AppointmentService': 'db_genius_appointment_services',
        'Genius_AppointmentType': 'db_genius_appointment_types',
        'Genius_Division': 'db_genius_divisions',
        'Genius_DivisionGroup': 'db_genius_division_groups',
        'Genius_Job': 'db_genius_jobs',
        'Genius_JobChangeOrder': 'db_genius_job_change_orders',
        'Genius_Lead': 'db_genius_leads',
        'Genius_Location': 'db_genius_locations',
        'Genius_Person': 'db_genius_people',
        'Genius_Product': 'db_genius_products',
        'Genius_SalesRep': 'db_genius_sales_reps',
        'Genius_Unit': 'db_genius_units',
        'Genius_UnitType': 'db_genius_unit_types',
        
        # Sync types (from JavaScript modelNameToSyncType)
        'appointments': 'db_genius_appointments',
        'appointmentoutcomes': 'db_genius_appointment_outcomes',
        'appointmentoutcometypes': 'db_genius_appointment_outcome_types', 
        'appointmentservices': 'db_genius_appointment_services',
        'appointmenttypes': 'db_genius_appointment_types',
        'divisions': 'db_genius_divisions',
        'divisiongroups': 'db_genius_division_groups',
        'jobs': 'db_genius_jobs',
        'jobchangeorders': 'db_genius_job_change_orders',
        'leads': 'db_genius_leads',
        'locations': 'db_genius_locations',
        'people': 'db_genius_people',
        'products': 'db_genius_products',
        'salesreps': 'db_genius_sales_reps',
        'units': 'db_genius_units',
        'unittypes': 'db_genius_unit_types',
    }
    
    if model_name in genius_commands:
        return genius_commands[model_name]
    
    # If no specific command found, default to db_genius_all
    logger.warning(f"No specific command found for {model_name}, using db_genius_all")
    return 'db_genius_all'

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
    
    # If no specific command found, default to sync_callrail_all
    logger.warning(f"No specific command found for {model_name}, using sync_callrail_all")
    return 'sync_callrail_all'

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
