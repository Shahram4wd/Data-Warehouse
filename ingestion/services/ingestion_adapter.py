"""
Ingestion adapter service that maps source keys and modes to management commands.
"""
from django.core.management import call_command
import logging

logger = logging.getLogger(__name__)

def run_source_ingestion(source_key: str, mode: str, **options):
    """
    Run ingestion for a specific source and mode.
    
    Args:
        source_key: The source identifier (e.g., 'arrivy', 'hubspot', 'marketsharp')
        mode: The ingestion mode ('delta' or 'full')
        **options: Additional options passed to the ingestion command
        
    Raises:
        ValueError: If the source/mode combination is not supported
        Exception: If the ingestion command fails
    """
    
    # Define the mapping between source/mode and management commands
    # Based on actual commands in ingestion/management/commands/
    command_map = {
        # Arrivy source
        ("arrivy", "delta"): {
            "command": "sync_arrivy_all", 
            "default_args": {}
        },
        ("arrivy", "full"): {
            "command": "sync_arrivy_all", 
            "default_args": {"full": True}
        },
        
        # HubSpot source
        ("hubspot", "delta"): {
            "command": "sync_hubspot_all", 
            "default_args": {}
        },
        ("hubspot", "full"): {
            "command": "sync_hubspot_all", 
            "default_args": {"full": True}
        },
        
        # MarketSharp source
        ("marketsharp", "delta"): {
            "command": "sync_marketsharp_data", 
            "default_args": {}
        },
        ("marketsharp", "full"): {
            "command": "sync_marketsharp_data", 
            "default_args": {"full": True}
        },
        
        # Genius source
        ("genius", "delta"): {
            "command": "db_genius_appointments", 
            "default_args": {}
        },
        ("genius", "full"): {
            "command": "db_genius_appointments", 
            "default_args": {"full": True}
        },
        
        # SalesPro source
        ("salespro", "delta"): {
            "command": "db_salespro_all", 
            "default_args": {}
        },
        ("salespro", "full"): {
            "command": "db_salespro_all", 
            "default_args": {"full": True}
        },
        
        # SalesRabbit source
        ("salesrabbit", "delta"): {
            "command": "sync_salesrabbit_all", 
            "default_args": {}
        },
        ("salesrabbit", "full"): {
            "command": "sync_salesrabbit_all", 
            "default_args": {"full": True}
        },
        
        # CallRail source
        ("callrail", "delta"): {
            "command": "sync_callrail_all", 
            "default_args": {}
        },
        ("callrail", "full"): {
            "command": "sync_callrail_all", 
            "default_args": {"full": True}
        },
        
        # Google Sheets source
        ("gsheet", "delta"): {
            "command": "sync_gsheet_all", 
            "default_args": {}
        },
        ("gsheet", "full"): {
            "command": "sync_gsheet_all", 
            "default_args": {"full": True}
        },
        
        # LeadConduit source
        ("leadconduit", "delta"): {
            "command": "sync_leadconduit_all", 
            "default_args": {}
        },
        ("leadconduit", "full"): {
            "command": "sync_leadconduit_all", 
            "default_args": {"full": True}
        },
        
        # Five9 source
        ("five9", "delta"): {
            "command": "sync_five9_contacts", 
            "default_args": {}
        },
        ("five9", "full"): {
            "command": "sync_five9_contacts", 
            "default_args": {"full": True}
        },
        
        # Add more sources as needed
    }
    
    # Look up the command configuration
    key = (source_key.lower(), mode.lower())
    if key not in command_map:
        available_keys = list(command_map.keys())
        raise ValueError(
            f"Unsupported source/mode combination: {source_key}/{mode}. "
            f"Available combinations: {available_keys}"
        )
    
    config = command_map[key]
    command = config["command"]
    default_args = config["default_args"].copy()
    
    # Merge default args with provided options
    # Provided options take precedence over defaults
    final_args = {}
    
    # Start with defaults
    for k, v in default_args.items():
        final_args[k] = v
    
    # Override with provided options, filtering out None values
    for k, v in options.items():
        if v is not None:
            final_args[k] = v
    
    logger.info(f"Running ingestion command: {command} with args: {final_args}")
    
    try:
        # Execute the management command
        call_command(command, **final_args)
        logger.info(f"Successfully completed {command} for {source_key}/{mode}")
        
    except Exception as e:
        logger.error(f"Failed to execute {command} for {source_key}/{mode}: {e}")
        raise

def get_available_sources():
    """
    Get a list of all available source keys.
    
    Returns:
        list: List of available source key strings
    """
    # Extract unique source keys from the command map
    sources = set()
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
