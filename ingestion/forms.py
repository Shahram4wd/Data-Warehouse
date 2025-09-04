"""
Forms for ingestion schedule management.
"""
from django import forms
from django.core.exceptions import ValidationError
from ingestion.models import SyncSchedule
from ingestion.services.ingestion_adapter import validate_source_mode
import json

class IngestionScheduleForm(forms.ModelForm):
    """
    Form for creating and editing ingestion schedules.
    """
    
    class Meta:
        model = SyncSchedule
        fields = [
            'name', 'crm_source', 'model_name', 'mode', 'recurrence_type',
            'every', 'period',
            'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year',
            'start_at', 'end_at', 'enabled',
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Enter a descriptive name for this schedule'
            }),
            'crm_source': forms.HiddenInput(),
            'model_name': forms.HiddenInput(),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'recurrence_type': forms.Select(attrs={'class': 'form-control', 'id': 'id_recurrence_type'}),
            'every': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'minute': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '0 (or * for every minute)'
            }),
            'hour': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '* (or specific hour like 9)'
            }),
            'day_of_week': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '* (1=Monday, 7=Sunday)'
            }),
            'day_of_month': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '* (1-31)'
            }),
            'month_of_year': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': '* (1-12)'
            }),
            'start_at': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'end_at': forms.DateTimeInput(attrs={
                'class': 'form-control', 
                'type': 'datetime-local'
            }),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.crm_source = kwargs.pop('crm_source', None)
        self.model_name = kwargs.pop('model_name', None)
        super().__init__(*args, **kwargs)
        
        # Set source and model if provided
        if self.crm_source:
            self.fields['crm_source'].initial = self.crm_source
        if self.model_name:
            self.fields['model_name'].initial = self.model_name
        
    def clean(self):
        """Validate the form data."""
        cleaned_data = super().clean()
        
        # Validate recurrence configuration
        recurrence_type = cleaned_data.get('recurrence_type')
        
        if recurrence_type == 'interval':
            every = cleaned_data.get('every')
            period = cleaned_data.get('period')
            
            if not every:
                self.add_error('every', 'This field is required for interval schedules.')
            if not period:
                self.add_error('period', 'This field is required for interval schedules.')
        
        elif recurrence_type == 'crontab':
            # For crontab, validate that at least one field is properly set
            crontab_fields = ['minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year']
            # Allow defaults - they're all optional but should be valid cron expressions
            pass
        
        # Validate date range
        start_at = cleaned_data.get('start_at')
        end_at = cleaned_data.get('end_at')
        
        if start_at and end_at and start_at >= end_at:
            self.add_error('end_at', 'End time must be after start time.')
        
        return cleaned_data
        end_at = cleaned_data.get('end_at')
        
        if start_at and end_at and end_at <= start_at:
            self.add_error('end_at', 'End time must be after start time.')
        
        # Validate options JSON
        options = cleaned_data.get('options')
        if options:
            try:
                json.loads(options) if isinstance(options, str) else options
            except (json.JSONDecodeError, TypeError):
                self.add_error('options', 'Options must be valid JSON.')
        
        return cleaned_data
    
    def save(self, commit=True):
        """Save the schedule and handle options JSON."""
        instance = super().save(commit=False)
        
        # Parse options JSON if it's a string
        if isinstance(instance.options, str) and instance.options.strip():
            try:
                instance.options = json.loads(instance.options)
            except json.JSONDecodeError:
                instance.options = {}
        elif not instance.options:
            instance.options = {}
        
        if commit:
            instance.save()
            
        return instance

class RunNowForm(forms.Form):
    """
    Simple form for the "Run Now" action.
    """
    schedule_id = forms.IntegerField(widget=forms.HiddenInput())
    
    def __init__(self, schedule, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['schedule_id'].initial = schedule.id
        self.schedule = schedule
