"""
CRM Dashboard API Views

REST API endpoints for the CRM dashboard providing JSON responses
for dynamic content loading, sync operations, and data access.
"""
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from django.core.exceptions import ValidationError
from ingestion.services.crm_discovery import CRMDiscoveryService
from ingestion.services.sync_management import SyncManagementService
from ingestion.services.data_access import DataAccessService
from ingestion.models.common import SyncHistory
import json
import logging

logger = logging.getLogger(__name__)


class BaseAPIView(View):
    """Base API view with common functionality"""
    
    def dispatch(self, request, *args, **kwargs):
        try:
            return super().dispatch(request, *args, **kwargs)
        except Exception as e:
            logger.error(f"API Error in {self.__class__.__name__}: {e}")
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=500)
    
    def json_response(self, data, status=200):
        """Helper method for JSON responses"""
        return JsonResponse(data, status=status)
    
    def error_response(self, message, status=400):
        """Helper method for error responses"""
        return JsonResponse({
            'success': False,
            'error': message
        }, status=status)


class CRMListAPIView(BaseAPIView):
    """API endpoint for getting all CRM sources"""
    
    def get(self, request):
        try:
            crm_discovery = CRMDiscoveryService()
            crm_sources = crm_discovery.get_all_crm_sources()
            
            return self.json_response({
                'success': True,
                'data': crm_sources,
                'total': len(crm_sources)
            })
            
        except Exception as e:
            logger.error(f"Error getting CRM list: {e}")
            return self.error_response(str(e), 500)


class CRMModelsAPIView(BaseAPIView):
    """API endpoint for getting models for a specific CRM"""
    
    def get(self, request, crm_source):
        try:
            crm_discovery = CRMDiscoveryService()
            models = crm_discovery.get_crm_models(crm_source)
            
            return self.json_response({
                'success': True,
                'crm_source': crm_source,
                'data': models,
                'total': len(models)
            })
            
        except Exception as e:
            logger.error(f"Error getting models for {crm_source}: {e}")
            return self.error_response(str(e), 500)


class ModelDetailAPIView(BaseAPIView):
    """API endpoint for getting detailed model information"""
    
    def get(self, request, crm_source, model_name):
        try:
            data_access = DataAccessService()
            crm_discovery = CRMDiscoveryService()
            
            # Get model class
            model_class = data_access.get_model_class(crm_source, model_name)
            if not model_class:
                return self.error_response(f"Model {model_name} not found in {crm_source}", 404)
            
            # Get model metadata
            metadata = data_access.get_model_metadata(model_class)
            
            # Get model statistics
            statistics = data_access.get_model_statistics(model_class)
            
            # Get sync information
            models = crm_discovery.get_crm_models(crm_source)
            model_info = next((m for m in models if m['name'].lower() == model_name.lower()), None)
            
            return self.json_response({
                'success': True,
                'crm_source': crm_source,
                'model_name': model_name,
                'metadata': metadata,
                'statistics': statistics,
                'sync_info': model_info.get('sync_info') if model_info else None
            })
            
        except Exception as e:
            logger.error(f"Error getting model detail for {crm_source}.{model_name}: {e}")
            return self.error_response(str(e), 500)


class ModelDataAPIView(BaseAPIView):
    """API endpoint for getting paginated model data"""
    
    def get(self, request, crm_source, model_name):
        try:
            data_access = DataAccessService()
            
            # Get model class
            model_class = data_access.get_model_class(crm_source, model_name)
            if not model_class:
                return self.error_response(f"Model {model_name} not found in {crm_source}", 404)
            
            # Parse query parameters
            page = int(request.GET.get('page', 1))
            per_page = min(int(request.GET.get('per_page', 25)), 100)  # Max 100 per page
            search = request.GET.get('search', '').strip()
            order_by = request.GET.get('order_by', '')
            
            # Parse filters from query parameters
            filters = {}
            for key, value in request.GET.items():
                if key.startswith('filter_') and value:
                    filter_field = key[7:]  # Remove 'filter_' prefix
                    filters[filter_field] = value
            
            # Get paginated data
            result = data_access.get_model_data(
                model_class=model_class,
                page=page,
                per_page=per_page,
                search=search,
                order_by=order_by,
                filters=filters
            )
            
            return self.json_response(result)
            
        except Exception as e:
            logger.error(f"Error getting model data for {crm_source}.{model_name}: {e}")
            return self.error_response(str(e), 500)


class SyncExecuteAPIView(BaseAPIView):
    """API endpoint for executing sync commands"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            # Parse request body
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            crm_source = data.get('crm_source')
            sync_type = data.get('sync_type')
            parameters = data.get('parameters', {})
            
            if not crm_source or not sync_type:
                return self.error_response("crm_source and sync_type are required", 400)
            
            # Execute sync
            sync_management = SyncManagementService()
            result = sync_management.execute_sync_command(crm_source, sync_type, parameters)
            
            if result['success']:
                return self.json_response(result)
            else:
                return self.error_response(result.get('error', 'Sync execution failed'), 400)
            
        except json.JSONDecodeError:
            return self.error_response("Invalid JSON in request body", 400)
        except Exception as e:
            logger.error(f"Error executing sync: {e}")
            return self.error_response(str(e), 500)


class SyncStatusAPIView(BaseAPIView):
    """API endpoint for getting sync status"""
    
    def get(self, request, sync_id):
        try:
            sync_management = SyncManagementService()
            status = sync_management.get_sync_status(sync_id)
            
            if 'error' in status:
                return self.error_response(status['error'], 404)
            
            return self.json_response({
                'success': True,
                'data': status
            })
            
        except Exception as e:
            logger.error(f"Error getting sync status for {sync_id}: {e}")
            return self.error_response(str(e), 500)


class SyncStopAPIView(BaseAPIView):
    """API endpoint for stopping a running sync"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request, sync_id):
        try:
            sync_management = SyncManagementService()
            result = sync_management.stop_sync(sync_id)
            
            if result['success']:
                return self.json_response(result)
            else:
                return self.error_response(result.get('error', 'Failed to stop sync'), 400)
            
        except Exception as e:
            logger.error(f"Error stopping sync {sync_id}: {e}")
            return self.error_response(str(e), 500)


class RunningSyncsAPIView(BaseAPIView):
    """API endpoint for getting all running syncs"""
    
    def get(self, request):
        try:
            sync_management = SyncManagementService()
            running_syncs = sync_management.get_running_syncs()
            
            return self.json_response({
                'success': True,
                'data': running_syncs,
                'total': len(running_syncs)
            })
            
        except Exception as e:
            logger.error(f"Error getting running syncs: {e}")
            return self.error_response(str(e), 500)


class SyncHistoryAPIView(BaseAPIView):
    """API endpoint for getting sync history"""
    
    def get(self, request):
        try:
            # Parse query parameters
            crm_source = request.GET.get('crm_source')
            sync_type = request.GET.get('sync_type')
            status = request.GET.get('status')
            limit = min(int(request.GET.get('limit', 50)), 200)  # Max 200 records
            offset = int(request.GET.get('offset', 0))
            
            # Build query
            queryset = SyncHistory.objects.all()
            
            if crm_source:
                queryset = queryset.filter(crm_source=crm_source)
            
            if sync_type:
                queryset = queryset.filter(sync_type__icontains=sync_type)
            
            if status:
                queryset = queryset.filter(status=status)
            
            # Get total count
            total_count = queryset.count()
            
            # Apply pagination
            sync_history = queryset.order_by('-start_time')[offset:offset + limit]
            
            # Convert to dict format
            data = []
            for sync in sync_history:
                data.append({
                    'id': sync.id,
                    'crm_source': sync.crm_source,
                    'sync_type': sync.sync_type,
                    'status': sync.status,
                    'start_time': sync.start_time.isoformat() if sync.start_time else None,
                    'end_time': sync.end_time.isoformat() if sync.end_time else None,
                    'duration': sync.duration_seconds,
                    'records_processed': sync.records_processed,
                    'records_created': sync.records_created,
                    'records_updated': sync.records_updated,
                    'records_failed': sync.records_failed,
                    'error_message': sync.error_message,
                    'configuration': sync.configuration,
                    'performance_metrics': sync.performance_metrics
                })
            
            return self.json_response({
                'success': True,
                'data': data,
                'total': total_count,
                'limit': limit,
                'offset': offset,
                'has_more': (offset + limit) < total_count
            })
            
        except Exception as e:
            logger.error(f"Error getting sync history: {e}")
            return self.error_response(str(e), 500)


class AvailableCommandsAPIView(BaseAPIView):
    """API endpoint for getting available sync commands for a CRM"""
    
    def get(self, request, crm_source):
        try:
            sync_management = SyncManagementService()
            commands = sync_management.get_available_commands(crm_source)
            
            return self.json_response({
                'success': True,
                'crm_source': crm_source,
                'data': commands,
                'total': len(commands)
            })
            
        except Exception as e:
            logger.error(f"Error getting available commands for {crm_source}: {e}")
            return self.error_response(str(e), 500)


class ValidateParametersAPIView(BaseAPIView):
    """API endpoint for validating sync parameters"""
    
    @method_decorator(csrf_exempt)
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def post(self, request):
        try:
            # Parse request body
            if request.content_type == 'application/json':
                data = json.loads(request.body)
            else:
                data = request.POST.dict()
            
            parameters = data.get('parameters', {})
            
            sync_management = SyncManagementService()
            validation_result = sync_management.validate_sync_parameters(parameters)
            
            return self.json_response({
                'success': True,
                'validation': validation_result
            })
            
        except json.JSONDecodeError:
            return self.error_response("Invalid JSON in request body", 400)
        except Exception as e:
            logger.error(f"Error validating parameters: {e}")
            return self.error_response(str(e), 500)


class SyncSchemasAPIView(BaseAPIView):
    """API endpoint for getting parameter schemas for sync commands"""
    
    def get(self, request):
        try:
            # Default parameter schemas for common sync commands
            schemas = [
                {
                    'command': 'sync_hubspot_all',
                    'description': 'Sync all HubSpot data',
                    'parameters': [
                        {
                            'name': 'force',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Force full sync ignoring last sync time'
                        },
                        {
                            'name': 'skip-associations',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Skip association syncing'
                        },
                        {
                            'name': 'batch-size',
                            'type': 'number',
                            'default': 100,
                            'min': 1,
                            'max': 1000,
                            'description': 'Batch size for processing'
                        }
                    ]
                },
                {
                    'command': 'sync_genius_all',
                    'description': 'Sync all Genius data',
                    'parameters': [
                        {
                            'name': 'force',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Force full sync'
                        },
                        {
                            'name': 'full',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Perform full sync'
                        },
                        {
                            'name': 'since',
                            'type': 'datetime',
                            'description': 'Sync records since this date (YYYY-MM-DD format)'
                        }
                    ]
                },
                {
                    'command': 'sync_gsheet_marketing_spends',
                    'description': 'Sync Google Sheets marketing spend data',
                    'parameters': [
                        {
                            'name': 'force',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Force update of existing records'
                        },
                        {
                            'name': 'sheet-id',
                            'type': 'string',
                            'description': 'Specific Google Sheet ID to sync'
                        }
                    ]
                },
                {
                    'command': 'sync_callrail_all',
                    'description': 'Sync all CallRail data',
                    'parameters': [
                        {
                            'name': 'force',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Force full sync'
                        },
                        {
                            'name': 'days',
                            'type': 'number',
                            'default': 30,
                            'min': 1,
                            'max': 365,
                            'description': 'Number of days to sync back'
                        }
                    ]
                },
                {
                    'command': 'sync_salesrabbit_all',
                    'description': 'Sync all SalesRabbit data',
                    'parameters': [
                        {
                            'name': 'force',
                            'type': 'boolean',
                            'default': False,
                            'description': 'Force full sync'
                        },
                        {
                            'name': 'batch-size',
                            'type': 'number',
                            'default': 100,
                            'min': 1,
                            'max': 500,
                            'description': 'Batch size for processing'
                        }
                    ]
                }
            ]
            
            return self.json_response({
                'success': True,
                'data': schemas
            })
            
        except Exception as e:
            logger.error(f"Error getting sync schemas: {e}")
            return self.error_response(str(e), 500)
