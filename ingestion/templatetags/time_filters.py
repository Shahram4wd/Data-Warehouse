"""
Custom template filters for time and duration formatting
"""
from django import template
from django.utils import timezone
from django.utils.timesince import timesince, timeuntil
from datetime import datetime, timedelta
import math

register = template.Library()


@register.filter
def format_duration(duration_seconds):
    """
    Format duration in seconds to human-readable format.
    Shows appropriate time units based on duration length.
    
    Args:
        duration_seconds: Duration in seconds (float or int)
        
    Returns:
        str: Formatted duration string
        
    Examples:
        30 -> "30s"
        90 -> "1m 30s"
        3661 -> "1h 1m"
        86461 -> "1d 1m"
    """
    if not duration_seconds or duration_seconds <= 0:
        return "0s"
    
    # Convert to int to avoid decimal places in display
    total_seconds = int(duration_seconds)
    
    # Calculate time components
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    
    # Build formatted string based on duration length
    parts = []
    
    if days > 0:
        parts.append(f"{days}d")
        if hours > 0:
            parts.append(f"{hours}h")
        if minutes > 0 and days == 0:  # Only show minutes if no days
            parts.append(f"{minutes}m")
    elif hours > 0:
        parts.append(f"{hours}h")
        if minutes > 0:
            parts.append(f"{minutes}m")
    elif minutes > 0:
        parts.append(f"{minutes}m")
        if seconds > 0:
            parts.append(f"{seconds}s")
    else:
        parts.append(f"{seconds}s")
    
    return " ".join(parts)


@register.filter
def time_ago(datetime_obj):
    """
    Format datetime to show time ago in appropriate units.
    
    Args:
        datetime_obj: DateTime object
        
    Returns:
        str: Time ago string
        
    Examples:
        "2 minutes ago"
        "1 hour ago"  
        "3 days ago"
        "Sep 5, 2025" (for older dates)
    """
    if not datetime_obj:
        return "Never"
    
    now = timezone.now()
    
    # Handle timezone-naive datetimes
    if timezone.is_naive(datetime_obj):
        datetime_obj = timezone.make_aware(datetime_obj)
    
    diff = now - datetime_obj
    
    # If it's in the future, use timeuntil
    if diff.total_seconds() < 0:
        return f"in {timeuntil(datetime_obj)}"
    
    total_seconds = diff.total_seconds()
    
    # Less than a minute
    if total_seconds < 60:
        return "Just now"
    
    # Less than an hour - show minutes
    elif total_seconds < 3600:
        minutes = int(total_seconds // 60)
        return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
    
    # Less than a day - show hours
    elif total_seconds < 86400:
        hours = int(total_seconds // 3600)
        return f"{hours} hour{'s' if hours != 1 else ''} ago"
    
    # Less than a week - show days
    elif total_seconds < 604800:
        days = int(total_seconds // 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"
    
    # Older than a week - show actual date
    else:
        return datetime_obj.strftime("%b %d, %Y")


@register.filter
def format_records_count(count):
    """
    Format record count with appropriate units (K, M, etc.)
    
    Args:
        count: Number of records
        
    Returns:
        str: Formatted count
        
    Examples:
        1234 -> "1.2K"
        1234567 -> "1.2M"
    """
    if not count or count == 0:
        return "0"
    
    count = int(count)
    
    if count < 1000:
        return str(count)
    elif count < 1000000:
        return f"{count/1000:.1f}K"
    elif count < 1000000000:
        return f"{count/1000000:.1f}M"
    else:
        return f"{count/1000000000:.1f}B"


@register.filter
def next_run_time(periodic_task):
    """
    Format next run time for a periodic task.
    
    Args:
        periodic_task: PeriodicTask object
        
    Returns:
        str: Next run time or status
    """
    if not periodic_task or not periodic_task.enabled:
        return "Disabled"
    
    if hasattr(periodic_task, 'clocked') and periodic_task.clocked:
        return time_ago(periodic_task.clocked.clocked_time)
    
    # For interval and crontab tasks, Django calculates next run time
    if hasattr(periodic_task, 'next_run_time') and periodic_task.next_run_time:
        return time_ago(periodic_task.next_run_time)
    
    return "Unknown"
