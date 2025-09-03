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
            'name', 'source_key', 'mode', 'recurrence_type',
            'every', 'period',
            'minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year',
            'start_at', 'end_at', 'enabled', 'options',
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Schedule name'}),
            'source_key': forms.Select(attrs={'class': 'form-control'}),
            'mode': forms.Select(attrs={'class': 'form-control'}),
            'recurrence_type': forms.Select(attrs={'class': 'form-control'}),
            'every': forms.NumberInput(attrs={'class': 'form-control', 'min': '1'}),
            'period': forms.Select(attrs={'class': 'form-control'}),
            'minute': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '0'}),
            'hour': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '*'}),
            'day_of_week': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '*'}),
            'day_of_month': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '*'}),
            'month_of_year': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '*'}),
            'start_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'end_at': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'options': forms.Textarea(attrs={'class': 'form-control', 'rows': 4, 'placeholder': 'JSON options (e.g., {"batch_size": 1000})'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.source_key = kwargs.pop('source_key', None)
        super().__init__(*args, **kwargs)
        
        # Set source_key if provided and hide the field
        if self.source_key:
            self.fields['source_key'].initial = self.source_key
            self.fields['source_key'].widget = forms.HiddenInput()
        
        # Update choices dynamically
        self.fields['source_key'].choices = self.get_source_choices()
        
    def get_source_choices(self):
        """Get available source choices."""
        # This should match your available sources from ingestion_adapter
        sources = [
            ('arrivy', 'Arrivy'),
            ('hubspot', 'HubSpot'),
            ('marketsharp', 'MarketSharp'),
            ('genius', 'Genius'),
        ]
        return [('', 'Select Source')] + sources
    
    def clean(self):
        """Validate the form data."""
        cleaned_data = super().clean()
        
        # Validate source/mode combination
        source_key = cleaned_data.get('source_key')
        mode = cleaned_data.get('mode')
        
        if source_key and mode:
            if not validate_source_mode(source_key, mode):
                raise ValidationError(
                    f"The combination {source_key}/{mode} is not supported."
                )
        
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
            # For crontab, we allow defaults, but validate format if provided
            crontab_fields = ['minute', 'hour', 'day_of_week', 'day_of_month', 'month_of_year']
            has_any_crontab = any(cleaned_data.get(field) for field in crontab_fields)
            
            if not has_any_crontab:
                # Use defaults - this is okay
                pass
        
        # Validate date range
        start_at = cleaned_data.get('start_at')
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
