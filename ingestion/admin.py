from django.contrib import admin
from django.utils.html import format_html
from django.urls import path
from django.shortcuts import redirect
from django.contrib import messages
from django.core.management import call_command

from .models import (
    Genius_DivisionGroup,  # Updated import
    Genius_Division,  # Updated import
    Genius_UserData,  # Updated import
    Genius_Prospect,  # Updated import
    Genius_Appointment,  # Updated import
    Genius_Quote,  # Updated import
    Genius_MarketingSource,  # Updated import
)
from ingestion.models.hubspot import Hubspot_Contact, Hubspot_Deal, Hubspot_SyncHistory

# Register models with the admin site
admin.site.register(Genius_DivisionGroup)
admin.site.register(Genius_Division)
admin.site.register(Genius_UserData)
admin.site.register(Genius_Prospect)
admin.site.register(Genius_Appointment)
admin.site.register(Genius_Quote)
admin.site.register(Genius_MarketingSource)

@admin.register(Hubspot_SyncHistory)
class HubspotSyncHistoryAdmin(admin.ModelAdmin):
    list_display = ('endpoint', 'last_synced_at', 'sync_actions')
    search_fields = ('endpoint',)
    readonly_fields = ('last_synced_at',)
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:pk>/sync/', self.admin_site.admin_view(self.trigger_sync), name='hubspot-trigger-sync'),
            path('<int:pk>/full-sync/', self.admin_site.admin_view(self.trigger_full_sync), name='hubspot-trigger-full-sync'),
        ]
        return custom_urls + urls
    
    def sync_actions(self, obj):
        """Generate sync action buttons for each history record."""
        return format_html(
            '<a class="button" href="{}">Delta Sync</a>&nbsp;'
            '<a class="button" href="{}">Full Sync</a>',
            f'../../../admin/ingestion/hubspot_synchistory/{obj.pk}/sync/',
            f'../../../admin/ingestion/hubspot_synchistory/{obj.pk}/full-sync/',
        )
    sync_actions.short_description = 'Sync Actions'
    
    def trigger_sync(self, request, pk):
        """Trigger a delta sync for the selected endpoint."""
        history = self.get_object(request, pk)
        if history.endpoint == 'contacts':
            call_command('sync_hubspot_contacts')
            messages.success(request, f"Delta sync for {history.endpoint} has been initiated.")
        elif history.endpoint == 'deals':
            call_command('sync_hubspot_deals')
            messages.success(request, f"Delta sync for {history.endpoint} has been initiated.")
        else:
            messages.error(request, f"Unknown endpoint: {history.endpoint}")
        return redirect('../../')
    
    def trigger_full_sync(self, request, pk):
        """Trigger a full sync for the selected endpoint."""
        history = self.get_object(request, pk)
        if history.endpoint == 'contacts':
            call_command('sync_hubspot_contacts', '--full')
            messages.success(request, f"Full sync for {history.endpoint} has been initiated.")
        elif history.endpoint == 'deals':
            call_command('sync_hubspot_deals', '--full')
            messages.success(request, f"Full sync for {history.endpoint} has been initiated.")
        else:
            messages.error(request, f"Unknown endpoint: {history.endpoint}")
        return redirect('../../')

@admin.register(Hubspot_Contact)
class HubspotContactAdmin(admin.ModelAdmin):
    list_display = ('id', 'firstname', 'lastname', 'email', 'division', 'createdate', 'lastmodifieddate')
    search_fields = ('firstname', 'lastname', 'email', 'division')
    list_filter = ('division', 'createdate', 'lastmodifieddate')
    readonly_fields = ('id', 'hs_object_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'hs_object_id', 'firstname', 'lastname', 'email', 'phone')
        }),
        ('Address Information', {
            'fields': ('address', 'city', 'state', 'zip')
        }),
        ('Source Information', {
            'fields': ('division', 'campaign_name', 'original_lead_source', 'marketsharp_id')
        }),
        ('Tracking Data', {
            'fields': ('createdate', 'lastmodifieddate', 'created_at', 'updated_at')
        }),
        ('Advanced', {
            'classes': ('collapse',),
            'fields': ('adgroupid', 'ap_leadid', 'campaign_content', 'clickcheck', 
                      'clicktype', 'comments', 'hs_google_click_id', 'lead_salesrabbit_lead_id',
                      'msm_source', 'original_lead_source_created', 'price', 'reference_code',
                      'search_terms', 'tier', 'trustedform_cert_url', 'vendorleadid', 'vertical')
        }),
    )
    actions = ['trigger_sync']
    
    def trigger_sync(self, request, queryset):
        """Trigger a sync for HubSpot contacts."""
        call_command('sync_hubspot_contacts')
        self.message_user(request, "Delta sync for contacts has been initiated.")
    trigger_sync.short_description = "Trigger sync for contacts"

@admin.register(Hubspot_Deal)
class HubspotDealAdmin(admin.ModelAdmin):
    list_display = ('id', 'deal_name', 'amount', 'dealstage', 'division', 'createdate', 'closedate')
    search_fields = ('deal_name', 'description', 'division')
    list_filter = ('dealstage', 'division', 'createdate', 'closedate')
    readonly_fields = ('id', 'hs_object_id', 'created_at', 'updated_at')
    fieldsets = (
        ('Basic Information', {
            'fields': ('id', 'hs_object_id', 'deal_name', 'amount', 'description')
        }),
        ('Deal Status', {
            'fields': ('dealstage', 'dealtype', 'pipeline', 'priority')
        }),
        ('Organization', {
            'fields': ('division', 'hubspot_owner_id')
        }),
        ('Dates', {
            'fields': ('createdate', 'closedate', 'created_at', 'updated_at')
        }),
    )
    actions = ['trigger_sync']
    
    def trigger_sync(self, request, queryset):
        """Trigger a sync for HubSpot deals."""
        call_command('sync_hubspot_deals')
        self.message_user(request, "Delta sync for deals has been initiated.")
    trigger_sync.short_description = "Trigger sync for deals"
