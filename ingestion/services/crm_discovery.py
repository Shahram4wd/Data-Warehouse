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
        self.crm_icon_mapping = {
            'genius': '🧠',
            'hubspot': '🟠', 
            'callrail': '📞',
            'arrivy': '🚗',
            'salespro': '💼',
            'salesrabbit': '🐰',
            'leadconduit': '⚡',
            'marketsharp': '📈',
            'gsheet': '📊',
        }
    
    def get_all_crm_sources(self) -> List[Dict]:
        """
        Scan ingestion/models/ directory for CRM model files and return
        comprehensive information about each CRM source
        """
        crm_sources = []
        
        try:
            # Get all Python files in models directory (excluding __init__ and common)
            model_files = [
                f[:-3] for f in os.listdir(self.models_dir) 
                if f.endswith('.py') and f not in ['__init__.py', 'common.py']
            ]
            
            for crm_source in model_files:
                try:
                    crm_info = self._get_crm_source_info(crm_source)
                    if crm_info:
                        crm_sources.append(crm_info)
                except Exception as e:
                    logger.warning(f"Error processing CRM source {crm_source}: {e}")
                    # Add basic info even if there's an error
                    crm_sources.append({
                        'name': crm_source,
                        'display_name': crm_source.title(),
                        'icon': self.crm_icon_mapping.get(crm_source, '📋'),
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
                'display_name': self._format_display_name(crm_source),
                'icon': self.crm_icon_mapping.get(crm_source, '📋'),
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
        total = 0
        for model_info in models_list:
            try:
                total += model_info['model_class'].objects.count()
            except Exception as e:
                logger.warning(f"Error counting records for {model_info['name']}: {e}")
        return total
    
    def _determine_crm_status(self, crm_source: str, last_sync_info: Optional[Dict]) -> str:
        """Determine overall CRM status based on recent sync history"""
        if not last_sync_info:
            return 'never_synced'
        
        status = last_sync_info['status']
        
        # Check for running syncs
        running_syncs = SyncHistory.objects.filter(
            crm_source=crm_source,
            status='running'
        ).exists()
        
        if running_syncs:
            return 'running'
        
        # Check recent sync status (last 24 hours)
        recent_cutoff = timezone.now() - timedelta(hours=24)
        recent_syncs = SyncHistory.objects.filter(
            crm_source=crm_source,
            start_time__gte=recent_cutoff
        )
        
        if not recent_syncs.exists():
            return 'outdated'
        
        # Check for any recent failures
        recent_failures = recent_syncs.filter(status='failed').exists()
        recent_partials = recent_syncs.filter(status='partial').exists()
        
        if recent_failures:
            return 'error'
        elif recent_partials:
            return 'warning'
        else:
            return 'success'
    
    def _format_display_name(self, crm_source: str) -> str:
        """Format CRM source name for display"""
        # Handle special cases
        display_names = {
            'hubspot': 'HubSpot',
            'callrail': 'CallRail',
            'salespro': 'SalesPro',
            'salesrabbit': 'SalesRabbit',
            'leadconduit': 'LeadConduit',
            'marketsharp': 'MarketSharp',
            'gsheet': 'Google Sheets'
        }
        
        return display_names.get(crm_source, crm_source.title())
    
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
        including sync status for each model
        """
        try:
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
                
                # Get record count
                try:
                    record_count = model_info['model_class'].objects.count()
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
            # Try to find sync history by matching model name patterns
            possible_sync_types = [
                self._model_name_to_sync_type(model_info['name']),
                model_info['table_name'],
                model_info['verbose_name_plural'].lower()
            ]
            
            last_sync = None
            for sync_type in possible_sync_types:
                if sync_type:
                    last_sync = SyncHistory.objects.filter(
                        crm_source=crm_source,
                        sync_type=sync_type
                    ).order_by('-start_time').first()
                    
                    if last_sync:
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
    
    def _model_name_to_sync_type(self, model_name: str) -> str:
        """Convert model name to likely sync_type name"""
        # Remove common prefixes (Genius, Hubspot, etc.)
        sync_type = model_name
        for prefix in ['Genius', 'Hubspot', 'Callrail', 'Salespro', 'Salesrabbit', 'Arrivy']:
            if sync_type.startswith(prefix):
                sync_type = sync_type[len(prefix):]
                break
        
        # Convert to lowercase and handle pluralization
        sync_type = sync_type.lower()
        
        # Common pluralization patterns
        if sync_type.endswith('y'):
            sync_type = sync_type[:-1] + 'ies'  # company -> companies
        elif sync_type.endswith('s'):
            pass  # already plural
        else:
            sync_type += 's'  # appointment -> appointments
        
        return sync_type
    
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
