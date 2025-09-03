# Ingestion Scheduling – Requirements & Implementation Plan

> Scope: Add a **“Set up schedule”** capability on each source detail page (e.g., `/ingestion/crm-dashboard/arrivy/`) that writes to **Celery Beat** and supports **multiple schedules per item** (e.g., delta every 5 minutes + full weekly). Includes backend models, Celery integration, UI, and safety (overlap prevention, visibility of last/next runs).

---

## 1) Answers to the original questions (decisions made)

- **Placement**: A **Set up schedule** button on each source detail view (e.g., Arrivy). Clicking opens **Schedules for {Source}** page with list + create/edit form.
- **Fields per schedule**:
  - **Name** (label for display)
  - **Mode**: `delta` or `full`
  - **Recurrence**: `Interval` (every N minutes/hours/days) **or** `Crontab` (specific times; e.g., 02:00 daily, weekends)
  - **Start at / End at** (optional window)
  - **Enabled** toggle
  - **Extra options** (stored as JSON): `batch_size`, `max_records`, `since`, `force_overwrite`, etc.
- **Edit/delete**: Yes. Users can create, update, delete, and enable/disable schedules.
- **Permissions**: Staff-only by default via Django permissions. Granular permission `ingestion.manage_schedules` is defined.
- **Activation timing**: Changes take effect immediately upon save (sync to `django_celery_beat` in the same transaction).
- **Storage**: **Database-backed** via `django-celery-beat` (not the local `celerybeat-schedule` file).
- **Status surface**: Show **next run**, **last run time**, **last status**, and **last error**; include a **Run now** action.
- **Frontend**: Server-rendered Django templates (same stack as existing dashboard). Minimal JS for toggles; no SPA required.
- **Multiple schedules**: Supported per item (e.g., delta every 5 min and full weekly). Overlap prevention ensures only one run per `(source, mode)` executes concurrently.

---

## 2) Functional Requirements

### 2.1 Schedules UX
- On each source detail page, show a **Set up schedule** button.
- **Schedules for {Source}** page:
  - **List** existing schedules: Name, Mode, Recurrence (human-readable), Enabled, Next run, Last run, Last status, actions (Edit, Delete, Toggle, **Run now**).
  - **Create/Edit form** with validation:
    - **Mode**: `delta | full` (required)
    - **Recurrence type**: `Interval | Crontab` (required)
      - Interval fields: `every` (int), `period` (minutes|hours|days)
      - Crontab fields: minute, hour, day_of_week, day_of_month, month_of_year
    - **Timezone**: implicitly the project `TIME_ZONE` (displayed for clarity)
    - **Start at / End at** (optional; ISO datetime)
    - **Enabled** (bool)
    - **Extra options** JSON editor (key-value pairs with helpers for common fields)
  - **Validations**:
    - At least one valid recurrence is required.
    - If `End at` < `Start at` → error.
    - Warn but allow if schedules could logically collide; actual runtime overlap is prevented.

### 2.2 Execution behavior
- Persist schedules in DB via `django-celery-beat` `PeriodicTask` linked 1:1 to our `IngestionSchedule`.
- Each run enqueues `ingestion.tasks.run_ingestion(source_key, mode, **options)`.
- **Overlap prevention**: per `(source_key, mode)` lock using cache key; if locked → skip (record as `skipped_overlap`).
- **Run Now**: Enqueues the same task immediately; respects lock.
- **Visibility**: Maintain an `IngestionRun` history with `started_at`, `finished_at`, `status` (success|failed|skipped_overlap), `duration_ms`, and `error`.

### 2.3 Multiple schedules per item
- Allow any number of schedules per `(source_key)` and mode.
- UI shows **Mode chips** (DELTA, FULL) to segment entries.

---

## 3) Non-Functional Requirements
- **Permissions**:
  - `is_staff` or `ingestion.manage_schedules` required for CRUD/Run-now/Toggle.
  - Read-only for other authenticated users (if they can view the source page).
- **Reliability**:
  - DB transactions ensure we only create/update `PeriodicTask` if `IngestionSchedule` saves successfully.
  - Service layer retries on race conditions for Beat sync.
- **Observability**:
  - Expose last 20 runs inline.
  - Log structured context (`source_key`, `mode`, `schedule_id`, run id).
- **Time zone**: Display and compute in `settings.TIME_ZONE`.

---

## 4) Data Model

```python
# ingestion/models.py
from django.conf import settings
from django.db import models, transaction
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.utils import timezone
from django.contrib.postgres.fields import JSONField  # or models.JSONField on Django 3.1+

class IngestionSchedule(models.Model):
    MODE_CHOICES = [("delta", "Delta"), ("full", "Full")]
    RECURRENCE_CHOICES = [("interval", "Interval"), ("crontab", "Crontab")]

    source_key = models.CharField(max_length=64, db_index=True)  # e.g., "arrivy"
    name = models.CharField(max_length=128)
    mode = models.CharField(max_length=16, choices=MODE_CHOICES)

    recurrence_type = models.CharField(max_length=16, choices=RECURRENCE_CHOICES)
    # Interval
    every = models.PositiveIntegerField(null=True, blank=True)
    period = models.CharField(max_length=16, null=True, blank=True, choices=[
        ("minutes", "Minutes"), ("hours", "Hours"), ("days", "Days")
    ])
    # Crontab
    minute = models.CharField(max_length=64, null=True, blank=True, default="0")
    hour = models.CharField(max_length=64, null=True, blank=True, default="*")
    day_of_week = models.CharField(max_length=64, null=True, blank=True, default="*")
    day_of_month = models.CharField(max_length=64, null=True, blank=True, default="*")
    month_of_year = models.CharField(max_length=64, null=True, blank=True, default="*")

    start_at = models.DateTimeField(null=True, blank=True)
    end_at = models.DateTimeField(null=True, blank=True)

    enabled = models.BooleanField(default=True)
    options = models.JSONField(default=dict, blank=True)

    periodic_task = models.OneToOneField(PeriodicTask, null=True, blank=True, on_delete=models.SET_NULL)

    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_schedules")
    updated_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="updated_schedules")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [models.Index(fields=["source_key", "mode"])]
        permissions = [("manage_schedules", "Can manage ingestion schedules")]

    def __str__(self):
        return f"{self.source_key}:{self.mode}:{self.name}"

class IngestionRun(models.Model):
    STATUS = [("success", "Success"), ("failed", "Failed"), ("skipped_overlap", "Skipped (Overlap)")]
    schedule = models.ForeignKey(IngestionSchedule, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=32, choices=STATUS)
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True, default="")

    def mark(self, status: str, err: str = "", started_at=None):
        self.status = status
        self.finished_at = timezone.now()
        if started_at:
            self.duration_ms = int((self.finished_at - started_at).total_seconds() * 1000)
        if err:
            self.error = err
        self.save(update_fields=["status", "finished_at", "duration_ms", "error"])
```

---

## 5) Celery Task & Overlap Lock

```python
# ingestion/tasks.py
from celery import shared_task
from django.core.cache import cache
from django.utils import timezone
from .models import IngestionSchedule, IngestionRun
from .services import run_source_ingestion

LOCK_TTL = 60 * 60  # 1 hour safety

def _lock_key(source_key: str, mode: str) -> str:
    return f"ingestion-lock:{source_key}:{mode}"

@shared_task(bind=True, name="ingestion.run_ingestion")
def run_ingestion(self, schedule_id: int):
    schedule = IngestionSchedule.objects.select_related().get(pk=schedule_id)
    key = _lock_key(schedule.source_key, schedule.mode)

    if not cache.add(key, "1", LOCK_TTL):
        IngestionRun.objects.create(schedule=schedule, status="skipped_overlap")
        return

    run = IngestionRun.objects.create(schedule=schedule, status="success")
    started = timezone.now()
    try:
        run_source_ingestion(
            source_key=schedule.source_key,
            mode=schedule.mode,
            **(schedule.options or {}),
        )
        run.mark("success", started_at=started)
    except Exception as e:
        run.mark("failed", err=str(e), started_at=started)
        raise
    finally:
        cache.delete(key)
```

> `run_source_ingestion` is a thin adapter that calls the appropriate management command(s) or service functions you already have (e.g., delta vs full importers) and passes optional arguments.

---

## 6) Beat Sync Service (create/update `PeriodicTask`)

```python
# ingestion/services/schedule_sync.py
from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
from django.conf import settings
from django.db import transaction
from django.utils import timezone
import json

def _ensure_interval(every: int, period: str) -> IntervalSchedule:
    return IntervalSchedule.objects.get_or_create(every=every, period=period)[0]

def _ensure_crontab(minute, hour, dow, dom, moy) -> CrontabSchedule:
    return CrontabSchedule.objects.get_or_create(
        minute=minute, hour=hour, day_of_week=dow, day_of_month=dom, month_of_year=moy, timezone=settings.TIME_ZONE
    )[0]

@transaction.atomic
def sync_periodic_task(schedule):
    kwargs = {"schedule_id": schedule.id}
    task_name = "ingestion.run_ingestion"

    if schedule.recurrence_type == "interval":
        interval = _ensure_interval(schedule.every, schedule.period)
        pt_kwargs = dict(task=task_name, interval=interval, args=json.dumps([schedule.id]))
    else:
        crontab = _ensure_crontab(schedule.minute or "*", schedule.hour or "*", schedule.day_of_week or "*", schedule.day_of_month or "*", schedule.month_of_year or "*")
        pt_kwargs = dict(task=task_name, crontab=crontab, args=json.dumps([schedule.id]))

    if schedule.periodic_task_id:
        pt = schedule.periodic_task
        for k, v in pt_kwargs.items():
            setattr(pt, k, v)
        pt.name = f"{schedule.source_key}:{schedule.mode}:{schedule.name}"
        pt.enabled = schedule.enabled
        pt.start_time = schedule.start_at
        pt.expires = schedule.end_at
        pt.save()
    else:
        pt = PeriodicTask.objects.create(
            name=f"{schedule.source_key}:{schedule.mode}:{schedule.name}",
            enabled=schedule.enabled,
            start_time=schedule.start_at,
            expires=schedule.end_at,
            **pt_kwargs,
        )
        schedule.periodic_task = pt
        schedule.save(update_fields=["periodic_task"])

    return schedule
```

Hook this in `IngestionSchedule.save()` or in the `ModelForm` view logic.

---

## 7) Forms, Views, URLs, Templates

```python
# ingestion/forms.py
from django import forms
from .models import IngestionSchedule

class IngestionScheduleForm(forms.ModelForm):
    class Meta:
        model = IngestionSchedule
        fields = [
            "name", "mode", "recurrence_type",
            "every", "period",
            "minute", "hour", "day_of_week", "day_of_month", "month_of_year",
            "start_at", "end_at", "enabled", "options",
        ]

    def clean(self):
        cleaned = super().clean()
        rt = cleaned.get("recurrence_type")
        if rt == "interval" and not cleaned.get("every"):
            self.add_error("every", "Required for interval schedules.")
        if rt == "crontab" and not any([cleaned.get("minute"), cleaned.get("hour"), cleaned.get("day_of_week"), cleaned.get("day_of_month"), cleaned.get("month_of_year")]):
            self.add_error("minute", "Provide at least one crontab field or use defaults.")
        sa, ea = cleaned.get("start_at"), cleaned.get("end_at")
        if sa and ea and ea < sa:
            self.add_error("end_at", "End must be after start.")
        return cleaned
```

```python
# ingestion/views/schedules.py
from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST
from .models import IngestionSchedule
from .forms import IngestionScheduleForm
from .services.schedule_sync import sync_periodic_task
from .tasks import run_ingestion

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def list_schedules(request, source_key):
    qs = IngestionSchedule.objects.filter(source_key=source_key).order_by("mode", "name")
    return render(request, "ingestion/schedules_list.html", {"source_key": source_key, "schedules": qs})

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def create_schedule(request, source_key):
    if request.method == "POST":
        form = IngestionScheduleForm(request.POST)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.source_key = source_key
            obj.created_by = request.user
            obj.updated_by = request.user
            obj.save()
            sync_periodic_task(obj)
            return redirect(reverse("ingestion:schedules", args=[source_key]))
    else:
        form = IngestionScheduleForm()
    return render(request, "ingestion/schedule_form.html", {"form": form, "source_key": source_key})

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
def edit_schedule(request, source_key, pk):
    obj = get_object_or_404(IngestionSchedule, pk=pk, source_key=source_key)
    if request.method == "POST":
        form = IngestionScheduleForm(request.POST, instance=obj)
        if form.is_valid():
            obj = form.save(commit=False)
            obj.updated_by = request.user
            obj.save()
            sync_periodic_task(obj)
            return redirect(reverse("ingestion:schedules", args=[source_key]))
    else:
        form = IngestionScheduleForm(instance=obj)
    return render(request, "ingestion/schedule_form.html", {"form": form, "source_key": source_key})

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def delete_schedule(request, source_key, pk):
    obj = get_object_or_404(IngestionSchedule, pk=pk, source_key=source_key)
    if obj.periodic_task:
        obj.periodic_task.delete()
    obj.delete()
    return redirect(reverse("ingestion:schedules", args=[source_key]))

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def toggle_schedule(request, source_key, pk):
    obj = get_object_or_404(IngestionSchedule, pk=pk, source_key=source_key)
    obj.enabled = not obj.enabled
    obj.save(update_fields=["enabled"])
    sync_periodic_task(obj)
    return redirect(reverse("ingestion:schedules", args=[source_key]))

@login_required
@permission_required("ingestion.manage_schedules", raise_exception=True)
@require_POST
def run_now(request, source_key, pk):
    obj = get_object_or_404(IngestionSchedule, pk=pk, source_key=source_key)
    run_ingestion.delay(obj.id)
    return redirect(reverse("ingestion:schedules", args=[source_key]))
```

```python
# ingestion/urls.py (excerpt)
from django.urls import path
from .views import schedules as v

app_name = "ingestion"
urlpatterns = [
    path("schedules/<str:source_key>/", v.list_schedules, name="schedules"),
    path("schedules/<str:source_key>/new/", v.create_schedule, name="schedule_new"),
    path("schedules/<str:source_key>/<int:pk>/edit/", v.edit_schedule, name="schedule_edit"),
    path("schedules/<str:source_key>/<int:pk>/delete/", v.delete_schedule, name="schedule_delete"),
    path("schedules/<str:source_key>/<int:pk>/toggle/", v.toggle_schedule, name="schedule_toggle"),
    path("schedules/<str:source_key>/<int:pk>/run/", v.run_now, name="schedule_run"),
]
```

```html
<!-- templates/ingestion/schedules_list.html (excerpt) -->
<h1>Schedules for {{ source_key|title }}</h1>
<a class="btn btn-primary" href="{% url 'ingestion:schedule_new' source_key %}">New schedule</a>
<table class="table">
  <thead>
    <tr><th>Name</th><th>Mode</th><th>Recurrence</th><th>Enabled</th><th>Next run</th><th>Last run</th><th>Status</th><th>Actions</th></tr>
  </thead>
  <tbody>
  {% for s in schedules %}
    <tr>
      <td>{{ s.name }}</td>
      <td><span class="badge {% if s.mode == 'full' %}bg-danger{% else %}bg-info{% endif %}">{{ s.mode|upper }}</span></td>
      <td>{% if s.recurrence_type == 'interval' %}Every {{ s.every }} {{ s.period }}{% else %}cron: {{ s.minute }} {{ s.hour }} {{ s.day_of_month }} {{ s.month_of_year }} {{ s.day_of_week }}{% endif %}</td>
      <td>{{ s.enabled }}</td>
      <td>{{ s.periodic_task.clocked or s.periodic_task.next_run_time }}</td>
      <td>{{ s.runs.last.started_at }}</td>
      <td>{{ s.runs.last.status|default:'—' }}</td>
      <td>
        <a href="{% url 'ingestion:schedule_edit' source_key s.id %}">Edit</a> |
        <form method="post" action="{% url 'ingestion:schedule_toggle' source_key s.id %}" style="display:inline;">{% csrf_token %}<button>Toggle</button></form> |
        <form method="post" action="{% url 'ingestion:schedule_run' source_key s.id %}" style="display:inline;">{% csrf_token %}<button>Run now</button></form> |
        <form method="post" action="{% url 'ingestion:schedule_delete' source_key s.id %}" style="display:inline;" onsubmit="return confirm('Delete schedule?');">{% csrf_token %}<button>Delete</button></form>
      </td>
    </tr>
  {% empty %}
    <tr><td colspan="8">No schedules yet.</td></tr>
  {% endfor %}
  </tbody>
</table>
```

> On the source detail template (e.g., `/ingestion/crm-dashboard/arrivy/`), add:

```html
<a class="btn btn-outline-secondary" href="{% url 'ingestion:schedules' 'arrivy' %}">Set up schedule</a>
```

---

## 8) Wiring to existing ingestion commands

```python
# ingestion/services/__init__.py
from django.core.management import call_command

def run_source_ingestion(source_key: str, mode: str, **options):
    # Decide which command/module to call for each source & mode
    # Examples below; adjust to your project commands.
    command_map = {
        ("arrivy", "delta"): ("import_arrivy", {"since": options.get("since"), "batch_size": options.get("batch_size", 1000)}),
        ("arrivy", "full"): ("import_arrivy", {"full": True, "batch_size": options.get("batch_size", 1000)}),
        # add other sources here
    }
    cmd, base_kwargs = command_map[(source_key, mode)]
    # Merge and drop None
    for k, v in list(base_kwargs.items()):
        if v is None:
            base_kwargs.pop(k)
    # Allow overrides
    base_kwargs.update({k: v for k, v in options.items() if v is not None})
    call_command(cmd, **base_kwargs)
```

---

## 9) Admin & Permissions

```python
# ingestion/admin.py
from django.contrib import admin
from .models import IngestionSchedule, IngestionRun

@admin.register(IngestionSchedule)
class IngestionScheduleAdmin(admin.ModelAdmin):
    list_display = ("source_key", "name", "mode", "recurrence_type", "enabled")
    list_filter = ("source_key", "mode", "recurrence_type", "enabled")

@admin.register(IngestionRun)
class IngestionRunAdmin(admin.ModelAdmin):
    list_display = ("schedule", "status", "started_at", "finished_at", "duration_ms")
    list_filter = ("status", "schedule__source_key")
```

To grant access:
- Add permission `ingestion.manage_schedules` to desired groups.

---

## 10) Tests (outline)

- **Model**: validate `clean()` rules; create both Interval and Crontab; `sync_periodic_task` creates/updates `PeriodicTask` correctly.
- **Task**: lock prevents overlap; success and failure paths write `IngestionRun` as expected.
- **Views**: CRUD works behind permission; run-now enqueues task; toggle updates `PeriodicTask.enabled`.

---

## 11) Deployment & Ops

1. **Dependencies**: ensure `django-celery-beat` is installed and migrated; Celery worker and Beat running.
2. **Migrations**: create migrations for models above.
3. **Settings**: confirm `TIME_ZONE` and cache backend (for locks).
4. **Monitoring**: optional Sentry captures on task exceptions; include schedule and run IDs in scope.

---

## 12) Example Schedules

- **Arrivy – Delta**: Interval every **5 minutes**, enabled.
- **Arrivy – Full**: Crontab `0 3 * * 0` (Sundays 03:00), enabled.

---

## 13) Step-by-Step Implementation Checklist

1. Add models `IngestionSchedule`, `IngestionRun`; run migrations.
2. Implement `schedule_sync.sync_periodic_task` service; wire into create/edit/delete/toggle.
3. Implement Celery task `ingestion.run_ingestion` with overlap lock and `IngestionRun` logging.
4. Implement `run_source_ingestion` adapter mapping sources+modes to management commands.
5. Create forms, views, urls, and templates for List/Create/Edit/Toggle/Delete/Run now.
6. Add **Set up schedule** button to source detail templates (e.g., Arrivy).
7. Add admin registrations and permissions; restrict access to staff/`manage_schedules`.
8. Add tests (model/task/view) and basic monitoring.
9. Deploy migrations; verify Beat sync and worker execution; create first two schedules (delta 5 min, full Sunday 03:00).

