"""
Views for ingestion schedule management.
"""
from django.contrib.auth.decorators import login_required, permission_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db import transaction

from ingestion.models import SyncSchedule
from ingestion.models.common import SyncHistory
from ingestion.forms import IngestionScheduleForm, RunNowForm
from ingestion.services.schedule_sync import sync_periodic_task, delete_periodic_task
from ingestion.tasks import run_ingestion

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def list_schedules(request, source_key):
    """
    List all schedules for a specific source.
    """
    schedules = SyncSchedule.objects.filter(source_key=source_key).select_related('periodic_task').order_by('mode', 'name')
    
    # Add recent runs to each schedule
    for schedule in schedules:
        schedule.recent_runs = schedule.get_recent_runs(limit=5)
        schedule.last_run = schedule.get_last_run()
        
        # Get next run time from periodic task
        schedule.next_run = None
        if schedule.periodic_task and schedule.enabled:
            # This would need to be calculated based on the schedule type
            # For now, we'll leave it as None and handle in the template
            pass
    
    context = {
        'source_key': source_key,
        'schedules': schedules,
        'source_display': source_key.title(),
    }
    
    return render(request, 'ingestion/schedules/list.html', context)

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def create_schedule(request, source_key):
    """
    Create a new schedule for a specific source.
    """
    if request.method == 'POST':
        form = IngestionScheduleForm(request.POST, source_key=source_key)
        if form.is_valid():
            with transaction.atomic():
                schedule = form.save(commit=False)
                schedule.source_key = source_key
                schedule.created_by = request.user
                schedule.updated_by = request.user
                schedule.save()
                
                # Sync with celery beat
                try:
                    sync_periodic_task(schedule)
                    messages.success(request, f'Schedule "{schedule.name}" created successfully.')
                except Exception as e:
                    messages.error(request, f'Schedule created but failed to sync with task scheduler: {e}')
                
            return redirect(reverse('ingestion:schedules', args=[source_key]))
    else:
        form = IngestionScheduleForm(source_key=source_key)
    
    context = {
        'form': form,
        'source_key': source_key,
        'source_display': source_key.title(),
        'action': 'Create',
    }
    
    return render(request, 'ingestion/schedules/form.html', context)

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def edit_schedule(request, source_key, pk):
    """
    Edit an existing schedule.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    
    if request.method == 'POST':
        form = IngestionScheduleForm(request.POST, instance=schedule, source_key=source_key)
        if form.is_valid():
            with transaction.atomic():
                schedule = form.save(commit=False)
                schedule.updated_by = request.user
                schedule.save()
                
                # Sync with celery beat
                try:
                    sync_periodic_task(schedule)
                    messages.success(request, f'Schedule "{schedule.name}" updated successfully.')
                except Exception as e:
                    messages.error(request, f'Schedule updated but failed to sync with task scheduler: {e}')
                
            return redirect(reverse('ingestion:schedules', args=[source_key]))
    else:
        # Pre-populate options as JSON string for editing
        initial_data = {}
        if schedule.options:
            import json
            initial_data['options'] = json.dumps(schedule.options, indent=2)
        
        form = IngestionScheduleForm(instance=schedule, source_key=source_key, initial=initial_data)
    
    context = {
        'form': form,
        'schedule': schedule,
        'source_key': source_key,
        'source_display': source_key.title(),
        'action': 'Edit',
    }
    
    return render(request, 'ingestion/schedules/form.html', context)

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def delete_schedule(request, source_key, pk):
    """
    Delete a schedule.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    schedule_name = schedule.name
    
    with transaction.atomic():
        # The model's delete() override will handle periodic task deletion
        # No need to call delete_periodic_task() here to avoid double deletion
        schedule.delete()
        messages.success(request, f'Schedule "{schedule_name}" deleted successfully.')
    
    return redirect(reverse('ingestion:schedules', args=[source_key]))

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def toggle_schedule(request, source_key, pk):
    """
    Toggle a schedule's enabled status.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    
    with transaction.atomic():
        schedule.enabled = not schedule.enabled
        schedule.updated_by = request.user
        schedule.save(update_fields=['enabled', 'updated_by'])
        
        # Sync with celery beat
        try:
            sync_periodic_task(schedule)
            status = "enabled" if schedule.enabled else "disabled"
            messages.success(request, f'Schedule "{schedule.name}" {status} successfully.')
        except Exception as e:
            messages.error(request, f'Failed to update task scheduler: {e}')
    
    return redirect(reverse('ingestion:schedules', args=[source_key]))

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def run_now(request, source_key, pk):
    """
    Trigger a schedule to run immediately.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    
    try:
        # Queue the task
        result = run_ingestion.delay(schedule.id)
        messages.success(request, f'Schedule "{schedule.name}" queued for immediate execution. Task ID: {result.id}')
    except Exception as e:
        messages.error(request, f'Failed to queue schedule for execution: {e}')
    
    return redirect(reverse('ingestion:schedules', args=[source_key]))

@login_required
def schedule_runs(request, source_key, pk):
    """
    View detailed run history for a specific schedule.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    
    runs = schedule.get_recent_runs(limit=1000)  # large cap for pagination
    paginator = Paginator(runs, 25)  # Show 25 runs per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'schedule': schedule,
        'source_key': source_key,
        'source_display': source_key.title(),
        'page_obj': page_obj,
        'runs': page_obj,
    }
    
    return render(request, 'ingestion/schedules/runs.html', context)

@login_required
def schedule_api_status(request, source_key, pk):
    """
    API endpoint to get current status of a schedule.
    """
    schedule = get_object_or_404(SyncSchedule, pk=pk, source_key=source_key)
    
    last_run = schedule.get_last_run()
    
    data = {
        'id': schedule.id,
        'name': schedule.name,
        'enabled': schedule.enabled,
        'last_run': ({
            'started_at': last_run.start_time.isoformat() if last_run and last_run.start_time else None,
            'status': last_run.status if last_run else None,
            'duration_ms': (last_run.performance_metrics or {}).get('duration_ms') if last_run else None,
            'error': last_run.error_message if last_run else None,
        } if last_run else None),
        'next_run': None,  # TODO: Calculate next run time
    }
    
    return JsonResponse(data)
