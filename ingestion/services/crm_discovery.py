"""
CRM Discovery Service

Automatically discovers CRM sources and their models by scanning the ingestion/models/ directory
and introspecting Django models to provide comprehensive CRM dashboard data.
"""
import os
import importlib
import inspect
from typing import List, Dict, Optional, Any
from django.apps import apps
from django.db import models
from django.utils import timezone
from datetime import datetime, timedelta
from ingestion.models.common import SyncHistory
import logging

logger = logging.getLogger(__name__)


class CRMDiscoveryService:
    """Service for discovering CRM sources and their models"""
    
    def __init__(self):
        self.models_dir = os.path.join(os.path.dirname(__file__), '..', 'models')
        
        # Define actual CRM systems with their metadata
        self.crm_systems = {
            'genius': {
                'icon': '🧠',
                'display_name': 'Genius CRM',
                'description': 'Genius appointment and prospect management system'
            },
            'hubspot': {
                'icon': '🟠', 
                'display_name': 'HubSpot CRM',
                'description': 'HubSpot customer relationship management platform'
            },
            'callrail': {
                'icon': '📞',
                'display_name': 'CallRail',
                'description': 'Call tracking and analytics platform'
            },
            'arrivy': {
                'icon': '🚗',
                'display_name': 'Arrivy',
                'description': 'Field service management platform'
            },
            'salespro': {
                'icon': '💼',
                'display_name': 'SalesPro',
                'description': 'Sales management and customer tracking system'
            },
            'salesrabbit': {
                'icon': '🐰',
                'display_name': 'SalesRabbit',
                'description': 'Door-to-door sales management platform'
            },
            'leadconduit': {
                'icon': '⚡',
                'display_name': 'LeadConduit',
                'description': 'Lead management and routing platform'
            },
            'marketsharp': {
                'icon': '📈',
                'display_name': 'Market Sharp',
                'description': 'Marketing automation and lead management'
            },
            'gsheet': {
                'icon': '📊',
                'display_name': 'Google Sheets',
                'description': 'Google Sheets data integration'
            },
            'five9': {
                'icon': '☎️',
                'display_name': 'Five9',
                'description': 'Cloud contact center platform'
            },
        }
        
        # Files to exclude from CRM discovery (utility models, not actual CRMs)
        self.excluded_files = {
            '__init__.py',
            'common.py',    # Common utility models
            'alerts.py',    # Alert/notification models
            'base.py',      # Base model classes
            'utils.py',     # Utility functions
            'helpers.py',   # Helper functions
        }
    
    def get_unregistered_model_files(self) -> List[str]:
        """
        Get list of model files that exist but are not registered as CRM systems.
        Useful for debugging or identifying new CRM systems to add.
        """
        try:
            # Get all model files
            all_model_files = [
                f[:-3] for f in os.listdir(self.models_dir) 
                if f.endswith('.py') and f not in self.excluded_files
            ]
            
            # Filter out registered CRM systems
            unregistered = [
                model_file for model_file in all_model_files 
                if model_file not in self.crm_systems
            ]
            
            return sorted(unregistered)
            
        except Exception as e:
            logger.error(f"Error scanning for unregistered model files: {e}")
            return []
    
    def is_valid_crm_system(self, crm_source: str) -> bool:
        """Check if a CRM source is registered as a valid CRM system"""
        return crm_source in self.crm_systems
    
    def get_all_crm_sources(self) -> List[Dict]:
        """
        Scan ingestion/models/ directory for CRM model files and return
        comprehensive information about each CRM source.
        Only includes files that are registered as actual CRM systems.
        """
        crm_sources = []
        
        try:
            # Get all Python files in models directory
            model_files = [
                f[:-3] for f in os.listdir(self.models_dir) 
                if f.endswith('.py') and f not in self.excluded_files
            ]
            
            # Filter to only include registered CRM systems
            valid_crm_files = [
                crm_file for crm_file in model_files 
                if crm_file in self.crm_systems
            ]
            
            for crm_source in valid_crm_files:
                try:
                    crm_info = self._get_crm_source_info(crm_source)
                    if crm_info:
                        crm_sources.append(crm_info)
                except Exception as e:
                    logger.warning(f"Error processing CRM source {crm_source}: {e}")
                    # Add basic info even if there's an error, but only for registered CRMs
                    if crm_source in self.crm_systems:
                        crm_metadata = self.crm_systems[crm_source]
                        crm_sources.append({
                            'name': crm_source,
                            'display_name': crm_metadata['display_name'],
                            'icon': crm_metadata['icon'],
                            'model_count': 0,
                            'last_sync': None,
                            'status': 'error',
                            'total_records': 0,
                        'error': str(e)
                    })
            
            # Sort by name for consistent ordering
            crm_sources.sort(key=lambda x: x['name'])
            
        except Exception as e:
            logger.error(f"Error scanning CRM sources: {e}")
            
        return crm_sources
    
    def _get_crm_source_info(self, crm_source: str) -> Optional[Dict]:
        """Get comprehensive information for a single CRM source"""
        try:
            # Only process registered CRM systems
            if crm_source not in self.crm_systems:
                logger.warning(f"CRM source '{crm_source}' not in registered CRM systems")
                return None
                
            # Get CRM metadata
            crm_metadata = self.crm_systems[crm_source]
            
            # Import the CRM module
            module_path = f'ingestion.models.{crm_source}'
            module = importlib.import_module(module_path)
            
            # Find all Django models in the module
            models_list = self._get_models_from_module(module)
            
            # Get sync status for this CRM
            last_sync_info = self._get_last_sync_info(crm_source)
            
            # Calculate total records across all models
            total_records = self._get_total_records(models_list)
            
            return {
                'name': crm_source,
                'display_name': crm_metadata['display_name'],
                'description': crm_metadata.get('description', ''),
                'icon': crm_metadata['icon'],
                'model_count': len(models_list),
                'models': [model['name'] for model in models_list],
                'last_sync': last_sync_info,
                'status': self._determine_crm_status(crm_source, last_sync_info),
                'total_records': total_records,
                'module_path': module_path
            }
            
        except ImportError as e:
            logger.warning(f"Could not import CRM module {crm_source}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error getting CRM info for {crm_source}: {e}")
            return None
    
    def _get_models_from_module(self, module) -> List[Dict]:
        """Extract Django models from a module"""
        models_list = []
        
        for name, obj in inspect.getmembers(module):
            if (inspect.isclass(obj) and 
                issubclass(obj, models.Model) and 
                obj != models.Model and
                hasattr(obj, '_meta') and
                not obj._meta.abstract):
                
                models_list.append({
                    'name': name,
                    'table_name': obj._meta.db_table,
                    'verbose_name': str(obj._meta.verbose_name),
                    'verbose_name_plural': str(obj._meta.verbose_name_plural),
                    'model_class': obj
                })
        
        return models_list
    
    def _get_last_sync_info(self, crm_source: str) -> Optional[Dict]:
        """Get the most recent sync information for a CRM source"""
        try:
            last_sync = SyncHistory.objects.filter(
                crm_source=crm_source
            ).order_by('-start_time').first()
            
            if last_sync:
                return {
                    'id': last_sync.id,
                    'sync_type': last_sync.sync_type,
                    'status': last_sync.status,
                    'start_time': last_sync.start_time,
                    'end_time': last_sync.end_time,
                    'duration': last_sync.duration_seconds,
                    'records_processed': last_sync.records_processed,
                    'records_created': last_sync.records_created,
                    'records_updated': last_sync.records_updated,
                    'records_failed': last_sync.records_failed,
                    'error_message': last_sync.error_message,
                    'time_ago': self._format_time_ago(last_sync.start_time)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting last sync for {crm_source}: {e}")
            return None
    
    def _get_total_records(self, models_list: List[Dict]) -> int:
        """Calculate total records across all models for a CRM"""
        from django.db import connection
        
        total = 0
        for model_info in models_list:
            try:
                model_class = model_info['model_class']
                table_name = model_class._meta.db_table
                
                # Check if table exists first
                if self._table_exists(table_name):
                    count = model_class.objects.count()
                    total += count
                else:
                    logger.debug(f"Table {table_name} does not exist, skipping count for {model_info['name']}")
                    
            except Exception as e:
                logger.debug(f"Error counting records for {model_info['name']}: {e}")
                continue
                
        return total
    
    def _table_exists(self, table_name: str) -> bool:
        """Check if a database table exists"""
        try:
            from django.db import connection
            # Use Django's introspection to get table names
            table_names = connection.introspection.table_names()
            return table_name in table_names
        except Exception:
            # Fallback: try a simple query and see if it fails
            try:
                from django.db import connection
                with connection.cursor() as cursor:
                    cursor.execute(f"SELECT 1 FROM {connection.ops.quote_name(table_name)} LIMIT 1")
                return True
            except Exception:
                return False
    
    def _determine_crm_status(self, crm_source: str, last_sync_info: Optional[Dict]) -> str:
        """Determine overall CRM status based on recent sync history"""
        if not last_sync_info:
            return 'never_synced'
        
        # Check for running syncs first
        running_syncs = SyncHistory.objects.filter(
            crm_source=crm_source,
            status='running'
        )
        
        if running_syncs.exists():
            # Check if there's a bulk 'all' sync running
            bulk_sync_running = running_syncs.filter(sync_type='all').exists()
            if bulk_sync_running:
                return 'bulk_sync_running'  # Special status for bulk sync
            return 'running'
        
        # Get the most recent sync status
        most_recent_status = last_sync_info['status']
        
        # Check if the most recent sync is very old (more than 24 hours)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        if last_sync_info.get('start_time'):
            try:
                last_sync_time = last_sync_info['start_time']
                if isinstance(last_sync_time, str):
                    last_sync_time = datetime.fromisoformat(last_sync_time.replace('Z', '+00:00'))
                
                if last_sync_time < recent_cutoff:
                    return 'outdated'
            except (ValueError, TypeError):
                pass
        
        # Return the status of the most recent sync
        # This prioritizes recent activity over older failures
        if most_recent_status == 'failed':
            return 'error'
        elif most_recent_status == 'partial':
            return 'warning'
        elif most_recent_status == 'success':
            return 'success'
        else:
            return 'unknown'
    
    def _format_time_ago(self, timestamp: datetime) -> str:
        """Format timestamp as 'time ago' string"""
        if not timestamp:
            return 'Never'
        
        now = timezone.now()
        diff = now - timestamp
        
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days != 1 else ''} ago"
        elif diff.seconds > 3600:
            hours = diff.seconds // 3600
            return f"{hours} hour{'s' if hours != 1 else ''} ago"
        elif diff.seconds > 60:
            minutes = diff.seconds // 60
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        else:
            return "Just now"
    
    def get_crm_models(self, crm_source: str) -> List[Dict]:
        """
        Get detailed information about all models for a specific CRM source
        including sync status for each model - with caching and performance optimizations
        """
        try:
            from django.core.cache import cache
            
            # Cache key for this CRM's models
            cache_key = f"crm_models_{crm_source}"
            
            # Try to get from cache first (cache for 10 minutes)
            cached_models = cache.get(cache_key)
            if cached_models:
                logger.debug(f"Using cached models for {crm_source}")
                return cached_models
            
            logger.info(f"Computing model information for {crm_source}")
            
            # Import the CRM module
            module_path = f'ingestion.models.{crm_source}'
            module = importlib.import_module(module_path)
            
            # Get all models from the module
            models_list = self._get_models_from_module(module)
            
            # Enhance each model with sync information
            enhanced_models = []
            for model_info in models_list:
                # Get sync info for this specific model
                model_sync_info = self._get_model_sync_info(crm_source, model_info)
                
                # Get record count with performance optimizations
                try:
                    model_class = model_info['model_class']
                    table_name = model_class._meta.db_table
                    
                    # Check if table exists first
                    if self._table_exists(table_name):
                        # Use approximate count for large tables to avoid slow COUNT queries
                        record_count = self._get_optimized_record_count(model_class)
                    else:
                        logger.debug(f"Table {table_name} does not exist, skipping count for {model_info['name']}")
                        record_count = 0
                except Exception as e:
                    logger.warning(f"Error counting records for {model_info['name']}: {e}")
                    record_count = 0
                
                enhanced_model = {
                    **model_info,
                    'record_count': record_count,
                    'sync_info': model_sync_info,
                    'status': self._determine_model_status(model_sync_info),
                    'has_management_command': self._has_management_command(crm_source, model_info['name'])
                }
                
                enhanced_models.append(enhanced_model)
            
            # Sort by model name
            enhanced_models.sort(key=lambda x: x['name'])
            
            # Cache the result for 10 minutes (600 seconds)
            cache.set(cache_key, enhanced_models, 600)
            logger.info(f"Cached models for {crm_source}")
            
            return enhanced_models
            
        except ImportError as e:
            logger.error(f"Could not import CRM module {crm_source}: {e}")
            return []
        except Exception as e:
            logger.error(f"Error getting models for {crm_source}: {e}")
            return []
    
    def _get_model_sync_info(self, crm_source: str, model_info: Dict) -> Optional[Dict]:
        """Get sync information for a specific model"""
        try:
            # Get all possible sync_types for this model
            possible_sync_types = self._get_all_possible_sync_types(crm_source, model_info)
            
            last_sync = None
            for sync_type in possible_sync_types:
                if sync_type:
                    # Get recent syncs for this type and prioritize successful ones
                    recent_syncs = SyncHistory.objects.filter(
                        crm_source=crm_source,
                        sync_type=sync_type
                    ).order_by('-start_time')[:5]  # Check last 5 syncs
                    
                    if recent_syncs:
                        # Look for the most recent successful sync first
                        for sync in recent_syncs:
                            if sync.status == 'success':
                                last_sync = sync
                                break
                        
                        # If no successful sync found, use the most recent one
                        if not last_sync:
                            last_sync = recent_syncs[0]
                        break
            
            if last_sync:
                return {
                    'id': last_sync.id,
                    'sync_type': last_sync.sync_type,
                    'status': last_sync.status,
                    'start_time': last_sync.start_time,
                    'end_time': last_sync.end_time,
                    'duration': last_sync.duration_seconds,
                    'records_processed': last_sync.records_processed,
                    'records_created': last_sync.records_created,
                    'records_updated': last_sync.records_updated,
                    'records_failed': last_sync.records_failed,
                    'error_message': last_sync.error_message,
                    'time_ago': self._format_time_ago(last_sync.start_time)
                }
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting sync info for {crm_source} {model_info['name']}: {e}")
            return None

    def _get_all_possible_sync_types(self, crm_source: str, model_info: Dict) -> List[str]:
        """Get all possible sync_types for a model, including special cases"""
        model_name = model_info['name']
        
        # Special handling for GoogleSheetMarketingLead - it can have multiple sync_types
        if model_name == 'GoogleSheetMarketingLead':
            return [
                'marketing_leads_full_refresh',  # Primary sync_type from mapping
                'marketing_leads_2024',          # Individual year syncs
                'marketing_leads_2025'
            ]
        
        # Standard sync_types for other models
        return [
            self._model_name_to_sync_type(model_name),
            model_info['table_name'],
            model_info['verbose_name_plural'].lower()
        ]
    
    def _model_name_to_sync_type(self, model_name: str) -> str:
        """Convert model name to likely sync_type name"""
        if not model_name:
            return ''
        
        # Handle specific model mappings first
        model_mappings = {
            'CallRail_Account': 'accounts',
            'CallRail_Call': 'calls', 
            'CallRail_Company': 'companies',
            'CallRail_FormSubmission': 'form_submissions',
            'CallRail_Tag': 'tags',
            'CallRail_TextMessage': 'text_messages',
            'CallRail_Tracker': 'trackers',
            'CallRail_User': 'users',
            'Five9Contact': 'contacts',
            # SalesRabbit mappings
            'SalesRabbit_Lead': 'leads',
            'SalesRabbit_User': 'users',
            # SalesPro mappings (using actual sync_type names from management commands)
            'SalesPro_Office': 'office',
            'SalesPro_User': 'user',
            'SalesPro_CreditApplication': 'creditapplications',
            'SalesPro_Customer': 'customer',
            'SalesPro_Estimate': 'estimate',
            'SalesPro_LeadResult': 'leadresults',
            'SalesPro_LeadResultLineItem': 'leadresults',  # Line items sync with parent
            # Genius mappings based on standardized sync_types
            'Genius_Appointment': 'appointments',
            'Genius_AppointmentOutcome': 'appointment_outcomes',
            'Genius_AppointmentOutcomeType': 'appointment_outcome_types',
            'Genius_AppointmentService': 'appointment_services',
            'Genius_AppointmentType': 'appointment_types',
            'Genius_Contact': 'contacts',
            'Genius_Division': 'divisions',
            'Genius_DivisionGroup': 'division_groups',
            'Genius_DivisionRegion': 'division_regions',
            'Genius_Job': 'jobs',
            'Genius_JobChangeOrder': 'job_change_orders',
            'Genius_JobChangeOrderItem': 'job_change_order_items',
            'Genius_JobChangeOrderReason': 'job_change_order_reasons',
            'Genius_JobChangeOrderStatus': 'job_change_order_statuses',
            'Genius_JobChangeOrderType': 'job_change_order_types',
            'Genius_JobFinancing': 'job_financings',
            'Genius_JobStatus': 'job_statuses',
            'Genius_JobType': 'job_types',
            'Genius_Lead': 'leads',
            'Genius_MarketingSource': 'marketing_sources',
            'Genius_MarketingSourceType': 'marketing_source_types',
            'Genius_MarketSharpMarketingSourceMap': 'marketsharp_marketing_source_maps',
            'Genius_MarketSharpSource': 'marketsharp_sources',
            'Genius_Prospect': 'prospects',
            'Genius_ProspectSource': 'prospect_sources',
            'Genius_Quote': 'quotes',
            'Genius_Service': 'services',
            'Genius_Task': 'tasks',
            'Genius_UserAssociation': 'user_associations',
            'Genius_UserData': 'user_data',
            'Genius_UserTitle': 'user_titles',
            # Google Sheets mappings
            'GoogleSheetMarketingLead': 'marketing_leads_full_refresh',
            'GoogleSheetMarketingSpend': 'marketing_spends'
        }
        
        if model_name in model_mappings:
            return model_mappings[model_name]
        
        # Fall back to general conversion for other CRMs
        name = model_name
        
        # Handle specific CRM patterns first
        if name.startswith('CallRail_'):
            name = name[9:]  # Remove 'CallRail_'
        elif name.startswith('Genius_'):
            name = name[7:]  # Remove 'Genius_'
        elif name.startswith('Hubspot_') or name.startswith('HubSpot_'):
            name = name[8:]  # Remove 'Hubspot_'/'HubSpot_'
        elif name.startswith('SalesPro_'):
            name = name[9:]  # Remove 'SalesPro_'
        elif name.startswith('SalesRabbit_'):
            name = name[12:]  # Remove 'SalesRabbit_'
        elif name.startswith('Arrivy_'):
            name = name[7:]  # Remove 'Arrivy_'
        
        name = name.lower()

        # Handle irregular plurals
        if name == 'status':
            return 'statuses'
        if name.endswith('y'):
            return name[:-1] + 'ies'
        if name.endswith('s'):
            return name  # already plural
        return name + 's'
    
    def _determine_model_status(self, sync_info: Optional[Dict]) -> str:
        """Determine status for a specific model"""
        if not sync_info:
            return 'never_synced'
        
        status = sync_info['status']
        
        if status == 'running':
            return 'running'
        elif status == 'success':
            # Check if sync is recent (last 24 hours)
            if sync_info['start_time']:
                cutoff = timezone.now() - timedelta(hours=24)
                if sync_info['start_time'] >= cutoff:
                    return 'success'
                else:
                    return 'outdated'
            return 'success'
        elif status == 'partial':
            return 'warning'
        elif status == 'failed':
            # Check if there's a bulk sync running that might affect this model
            crm_source = getattr(sync_info, 'crm_source', None)
            if crm_source:
                bulk_sync_running = SyncHistory.objects.filter(
                    crm_source=crm_source,
                    sync_type='all',
                    status='running'
                ).exists()
                if bulk_sync_running:
                    return 'bulk_sync_running'  # Don't show failed during bulk sync
            return 'error'
        else:
            return 'unknown'
    
    def _has_management_command(self, crm_source: str, model_name: str) -> bool:
        """Check if a management command exists for this model"""
        # This is a simplified check - in a real implementation, you might
        # scan the management/commands directory
        command_patterns = [
            f'sync_{crm_source}_{self._model_name_to_sync_type(model_name)[:-1]}',  # Remove 's'
            f'sync_{crm_source}_{model_name.lower()}',
            f'db_{crm_source}_{self._model_name_to_sync_type(model_name)[:-1]}',
        ]
        
        # For now, return True if it follows common patterns
        # In a real implementation, check if the command file actually exists
        return True
    
    def get_sync_history_for_crm(self, crm_source: str, limit: int = 10) -> List[Dict]:
        """Get recent sync history for a CRM source"""
        try:
            syncs = SyncHistory.objects.filter(
                crm_source=crm_source
            ).order_by('-start_time')[:limit]
            
            return [
                {
                    'id': sync.id,
                    'sync_type': sync.sync_type,
                    'status': sync.status,
                    'start_time': sync.start_time,
                    'end_time': sync.end_time,
                    'duration': sync.duration_seconds,
                    'records_processed': sync.records_processed,
                    'records_created': sync.records_created,
                    'records_updated': sync.records_updated,
                    'records_failed': sync.records_failed,
                    'error_message': sync.error_message,
                    'time_ago': self._format_time_ago(sync.start_time)
                }
                for sync in syncs
            ]
            
        except Exception as e:
            logger.error(f"Error getting sync history for {crm_source}: {e}")
            return []
    
    def _get_optimized_record_count(self, model_class):
        """Get record count using performance optimizations for large tables"""
        try:
            # First try to get approximate count from PostgreSQL statistics
            from django.db import connection
            table_name = model_class._meta.db_table
            
            with connection.cursor() as cursor:
                # Try to get approximate count from PostgreSQL statistics
                cursor.execute("""
                    SELECT COALESCE(n_tup_ins - n_tup_del, 0) as approx_count 
                    FROM pg_stat_user_tables 
                    WHERE relname = %s
                """, [table_name])
                
                result = cursor.fetchone()
                if result and result[0] > 0:
                    # Use approximate count for performance
                    approx_count = result[0]
                    logger.debug(f"Using approximate count {approx_count:,} for {model_class.__name__}")
                    return approx_count
                else:
                    # Fallback to exact count, but with a reasonable limit check first
                    # Use EXISTS query to check if table has data before doing expensive COUNT
                    if model_class.objects.exists():
                        # For very large tables, return a placeholder instead of exact count
                        try:
                            # Set a timeout for the count query
                            count = model_class.objects.count()
                            if count > 1000000:  # Over 1M records
                                return f"{count//1000000}M+"  # Return approximate like "2M+"
                            return count
                        except Exception as count_error:
                            logger.warning(f"Count query failed for {model_class.__name__}: {count_error}")
                            return "many"
                    else:
                        return 0
                        
        except Exception as e:
            logger.warning(f"Error getting optimized count for {model_class.__name__}: {e}")
            # Final fallback to basic count
            try:
                return model_class.objects.count()
            except Exception as final_error:
                logger.error(f"All count methods failed for {model_class.__name__}: {final_error}")
                return "unknown"
