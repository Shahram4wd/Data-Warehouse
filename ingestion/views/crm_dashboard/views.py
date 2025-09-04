"""
CRM Dashboard Views

Main dashboard views for displaying CRM management interface,
including the overview page, model listings, and detail pages.
"""
from django.shortcuts import render, get_object_or_404
from django.views.generic import TemplateView
from django.contrib import messages
from django.http import JsonResponse
from ingestion.services.crm_discovery import CRMDiscoveryService
from ingestion.services.sync_management import SyncManagementService
from ingestion.services.data_access import DataAccessService
from ingestion.models.common import SyncHistory, SyncSchedule
from ingestion.forms import IngestionScheduleForm
import logging

logger = logging.getLogger(__name__)


class CRMDashboardView(TemplateView):
    """Main CRM dashboard overview page"""
    template_name = 'crm_dashboard/dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            crm_discovery = CRMDiscoveryService()
            sync_management = SyncManagementService()
            
            # Get all CRM sources
            crm_sources = crm_discovery.get_all_crm_sources()
            
            # Get running syncs
            running_syncs = sync_management.get_running_syncs()
            
            # Get recent sync activity (last 10 syncs)
            recent_syncs = SyncHistory.objects.order_by('-start_time')[:10]
            
            context.update({
                'crm_sources': crm_sources,
                'running_syncs': running_syncs,
                'recent_syncs': recent_syncs,
                'total_crms': len(crm_sources),
                'running_count': len(running_syncs),
                'page_title': 'CRM Management Dashboard'
            })
            
        except Exception as e:
            logger.error(f"Error loading CRM dashboard: {e}")
            messages.error(self.request, f"Error loading dashboard: {e}")
            context.update({
                'crm_sources': [],
                'running_syncs': [],
                'recent_syncs': [],
                'error': str(e)
            })
        
        return context


class CRMModelsView(TemplateView):
    """CRM models listing page"""
    template_name = 'crm_dashboard/crm_models.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        crm_source = kwargs.get('crm_source')
        
        try:
            crm_discovery = CRMDiscoveryService()
            sync_management = SyncManagementService()
            
            # Get models for this CRM
            models = crm_discovery.get_crm_models(crm_source)
            
            # Get available commands for this CRM
            available_commands = sync_management.get_available_commands(crm_source)
            
            # Get sync history for this CRM
            sync_history = crm_discovery.get_sync_history_for_crm(crm_source, limit=20)
            
            # Get running syncs for this CRM
            running_syncs = [
                sync for sync in sync_management.get_running_syncs()
                if sync['crm_source'] == crm_source
            ]
            
            context.update({
                'crm_source': crm_source,
                'crm_display_name': crm_source.title(),
                'models': models,
                'available_commands': available_commands,
                'sync_history': sync_history,
                'running_syncs': running_syncs,
                'total_models': len(models),
                'page_title': f'{crm_source.title()} CRM Models'
            })
            
        except Exception as e:
            logger.error(f"Error loading CRM models for {crm_source}: {e}")
            messages.error(self.request, f"Error loading models: {e}")
            context.update({
                'crm_source': crm_source,
                'models': [],
                'error': str(e)
            })
        
        return context


class ModelDetailView(TemplateView):
    """Model detail page with data table"""
    template_name = 'crm_dashboard/model_detail.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        crm_source = kwargs.get('crm_source')
        model_name = kwargs.get('model_name')
        
        try:
            crm_discovery = CRMDiscoveryService()
            data_access = DataAccessService()
            
            # Get model class
            model_class = data_access.get_model_class(crm_source, model_name)
            if not model_class:
                raise ValueError(f"Model {model_name} not found in {crm_source}")
            
            # Get model metadata
            metadata = data_access.get_model_metadata(model_class)
            
            # Get model statistics
            statistics = data_access.get_model_statistics(model_class)
            
            # Get sync information for this specific model
            models = crm_discovery.get_crm_models(crm_source)
            model_info = next((m for m in models if m['name'].lower() == model_name.lower()), None)
            
            # Get recent sync history for this model
            model_sync_history = SyncHistory.objects.filter(
                crm_source=crm_source,
                sync_type__icontains=model_name.lower()
            ).order_by('-start_time')[:10]
            
            # Get existing schedules for this model
            existing_schedules = SyncSchedule.objects.filter(
                crm_source=crm_source,
                model_name=model_name
            ).order_by('-created_at')
            
            # Create schedule form for this specific model
            schedule_form = IngestionScheduleForm(
                crm_source=crm_source,
                model_name=model_name
            )
            
            context.update({
                'crm_source': crm_source,
                'model_name': model_name,
                'model_class': model_class,
                'metadata': metadata,
                'statistics': statistics,
                'model_info': model_info,
                'sync_history': model_sync_history,
                'existing_schedules': existing_schedules,
                'schedule_form': schedule_form,
                'page_title': f'{crm_source.title()} {model_name.title()} Details'
            })
            
        except Exception as e:
            logger.error(f"Error loading model detail for {crm_source}.{model_name}: {e}")
            messages.error(self.request, f"Error loading model detail: {e}")
            context.update({
                'crm_source': crm_source,
                'model_name': model_name,
                'error': str(e)
            })
        
        return context


class SyncHistoryView(TemplateView):
    """Sync history overview page"""
    template_name = 'crm_dashboard/sync_history.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get query parameters
            crm_source = self.request.GET.get('crm_source')
            status = self.request.GET.get('status')
            limit = int(self.request.GET.get('limit', 50))
            
            # Build query
            queryset = SyncHistory.objects.all()
            
            if crm_source:
                queryset = queryset.filter(crm_source=crm_source)
            
            if status:
                queryset = queryset.filter(status=status)
            
            # Get sync history
            sync_history = queryset.order_by('-start_time')[:limit]
            
            # Get filter options
            crm_discovery = CRMDiscoveryService()
            available_crms = [crm['name'] for crm in crm_discovery.get_all_crm_sources()]
            available_statuses = ['running', 'success', 'failed', 'partial']
            
            context.update({
                'sync_history': sync_history,
                'available_crms': available_crms,
                'available_statuses': available_statuses,
                'current_crm': crm_source,
                'current_status': status,
                'limit': limit,
                'total_syncs': queryset.count(),
                'page_title': 'Sync History'
            })
            
        except Exception as e:
            logger.error(f"Error loading sync history: {e}")
            messages.error(self.request, f"Error loading sync history: {e}")
            context.update({
                'sync_history': [],
                'error': str(e)
            })
        
        return context


class AllSchedulesView(TemplateView):
    """View for managing all schedules across all CRM sources"""
    template_name = 'crm_dashboard/all_schedules.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        try:
            # Get all schedules grouped by CRM source
            schedules = SyncSchedule.objects.all().order_by('crm_source', 'model_name', 'mode')
            
            # Group schedules by CRM source for better organization
            schedules_by_crm = {}
            for schedule in schedules:
                if schedule.crm_source not in schedules_by_crm:
                    schedules_by_crm[schedule.crm_source] = []
                schedules_by_crm[schedule.crm_source].append(schedule)
            
            # Get CRM sources for filtering
            crm_sources = list(schedules_by_crm.keys())
            
            # Get unique modes for filtering
            modes = SyncSchedule.objects.values_list('mode', flat=True).distinct()
            
            context.update({
                'schedules': schedules,
                'schedules_by_crm': schedules_by_crm,
                'crm_sources': crm_sources,
                'modes': modes,
                'total_schedules': schedules.count(),
                'active_schedules': schedules.filter(enabled=True).count(),
                'page_title': 'All Schedules Management'
            })
            
        except Exception as e:
            logger.error(f"Error loading all schedules: {e}")
            messages.error(self.request, f"Error loading schedules: {e}")
            context.update({
                'schedules': [],
                'schedules_by_crm': {},
                'crm_sources': [],
                'modes': [],
                'total_schedules': 0,
                'active_schedules': 0,
                'error': str(e)
            })
        
        return context
