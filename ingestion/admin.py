from django.contrib import admin
from ingestion.models import SyncSchedule
from ingestion.models.common import SyncHistory

@admin.register(SyncSchedule)
class SyncScheduleAdmin(admin.ModelAdmin):
	list_display = ("source_key", "name", "mode", "recurrence_type", "enabled")
	list_filter = ("source_key", "mode", "recurrence_type", "enabled")
	search_fields = ("name", "source_key")

@admin.register(SyncHistory)
class SyncHistoryAdmin(admin.ModelAdmin):
	list_display = ("crm_source", "sync_type", "status", "start_time", "end_time")
	list_filter = ("crm_source", "sync_type", "status")
	search_fields = ("crm_source", "sync_type", "error_message")
