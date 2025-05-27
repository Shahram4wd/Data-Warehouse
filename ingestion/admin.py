
from django.contrib import admin
from .models import (
    DivisionGroup, Division, UserData, Prospect, ProspectSource,
    AppointmentType, AppointmentOutcome, Appointment, AppointmentService,
    Service, Quote, MarketingSourceType, MarketingSource
)

@admin.register(DivisionGroup)
class DivisionGroupAdmin(admin.ModelAdmin):
    list_display = ('id', 'group_label', 'region', 'is_active')


@admin.register(Division)
class DivisionAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'abbreviation', 'is_utility', 'is_corp', 'is_omniscient')


@admin.register(UserData)
class UserDataAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'division')


@admin.register(Prospect)
class ProspectAdmin(admin.ModelAdmin):
    list_display = ('id', 'first_name', 'last_name', 'email', 'division')


@admin.register(ProspectSource)
class ProspectSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'prospect', 'marketing_source', 'source_date')


@admin.register(AppointmentType)
class AppointmentTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'is_active')


@admin.register(AppointmentOutcome)
class AppointmentOutcomeAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'type_id', 'is_active')


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = ('id', 'prospect', 'date', 'time', 'type', 'is_complete')


@admin.register(AppointmentService)
class AppointmentServiceAdmin(admin.ModelAdmin):
    list_display = ('appointment', 'service')


@admin.register(Service)
class ServiceAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'is_active', 'order_number')


@admin.register(Quote)
class QuoteAdmin(admin.ModelAdmin):
    list_display = ('id', 'prospect', 'appointment', 'amount', 'status_id')


@admin.register(MarketingSourceType)
class MarketingSourceTypeAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'is_active', 'division')


@admin.register(MarketingSource)
class MarketingSourceAdmin(admin.ModelAdmin):
    list_display = ('id', 'label', 'type', 'is_active', 'division')
