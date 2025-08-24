"""
Smart HubSpot Contacts Sync Management Command

This command automatically chooses the best sync strategy:
- Incremental sync for small date ranges (likely < 10,000 records)
- Full sync for large date ranges or when incremental hits the 10,000 limit

Usage:
    python manage.py smart_sync_hubspot_contacts --since 2024-08-20
    python manage.py smart_sync_hubspot_contacts --days-back 30
    python manage.py smart_sync_hubspot_contacts --auto
"""

import asyncio
from datetime import datetime, timedelta
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from ingestion.models.hubspot import HubSpotContact
from ingestion.management.commands.sync_hubspot_contacts import Command as BaseContactsCommand


class Command(BaseCommand):
    help = 'Smart HubSpot contacts sync that automatically chooses optimal strategy'

    def add_arguments(self, parser):
        # Date-based options
        parser.add_argument(
            '--since',
            type=str,
            help='Sync contacts modified since this date (YYYY-MM-DD)'
        )
        parser.add_argument(
            '--days-back',
            type=int,
            help='Sync contacts modified in the last N days'
        )
        parser.add_argument(
            '--auto',
            action='store_true',
            help='Automatically determine sync period based on last successful sync'
        )
        
        # Strategy options
        parser.add_argument(
            '--force-full',
            action='store_true',
            help='Force full sync regardless of date range'
        )
        parser.add_argument(
            '--max-incremental-days',
            type=int,
            default=7,
            help='Maximum days back to use incremental sync (default: 7)'
        )
        
        # Standard options from base command
        parser.add_argument('--full', action='store_true', help='Perform full sync')
        parser.add_argument('--limit', type=int, help='Limit number of records to sync')

    def handle(self, *args, **options):
        # Determine sync strategy
        sync_strategy = self._determine_sync_strategy(**options)
        
        self.stdout.write(
            self.style.SUCCESS(f"Using {sync_strategy['strategy']} sync strategy")
        )
        
        if sync_strategy['reason']:
            self.stdout.write(f"Reason: {sync_strategy['reason']}")

        # Prepare arguments for the base command
        base_options = {
            'full': sync_strategy['strategy'] == 'full',
            'since': sync_strategy.get('since'),
            'limit': options.get('limit'),
        }
        
        # Remove None values
        base_options = {k: v for k, v in base_options.items() if v is not None}
        
        # Create and run base command
        base_command = BaseContactsCommand()
        base_command.stdout = self.stdout
        base_command.stderr = self.stderr
        base_command.style = self.style
        
        return base_command.handle(*args, **base_options)

    def _determine_sync_strategy(self, **options):
        """Determine the optimal sync strategy based on options and data analysis."""
        
        # Force full sync if requested
        if options.get('force_full') or options.get('full'):
            return {
                'strategy': 'full',
                'reason': 'Full sync requested explicitly'
            }
        
        # Determine date range
        since_date = self._get_since_date(**options)
        
        if not since_date:
            return {
                'strategy': 'full',
                'reason': 'No date range specified, defaulting to full sync'
            }
        
        # Calculate days back
        days_back = (timezone.now().date() - since_date).days
        max_incremental_days = options.get('max_incremental_days', 7)
        
        # Strategy decision logic
        if days_back > max_incremental_days:
            return {
                'strategy': 'full',
                'reason': f'Date range too large ({days_back} days > {max_incremental_days} days limit). '
                         f'Using full sync to avoid HubSpot 10,000 search API limit.'
            }
        
        # Estimate record count for incremental sync
        estimated_records = self._estimate_incremental_records(since_date)
        
        if estimated_records > 8000:  # Conservative threshold
            return {
                'strategy': 'full',
                'reason': f'Estimated {estimated_records} records for incremental sync. '
                         f'Using full sync to avoid HubSpot 10,000 search API limit.'
            }
        
        return {
            'strategy': 'incremental',
            'since': since_date.strftime('%Y-%m-%d'),
            'reason': f'Small date range ({days_back} days, ~{estimated_records} estimated records). '
                     f'Safe to use incremental sync.'
        }
    
    def _get_since_date(self, **options):
        """Get the since date from various options."""
        
        # Explicit since date
        if options.get('since'):
            try:
                return datetime.strptime(options['since'], '%Y-%m-%d').date()
            except ValueError:
                raise CommandError(f"Invalid date format: {options['since']}. Use YYYY-MM-DD")
        
        # Days back
        if options.get('days_back'):
            return timezone.now().date() - timedelta(days=options['days_back'])
        
        # Auto mode - use last successful sync or default
        if options.get('auto'):
            return self._get_auto_since_date()
        
        return None
    
    def _get_auto_since_date(self):
        """Automatically determine since date based on last successful sync."""
        try:
            # Get the most recent contact's last modified date
            latest_contact = HubSpotContact.objects.filter(
                lastmodifieddate__isnull=False
            ).order_by('-lastmodifieddate').first()
            
            if latest_contact and latest_contact.lastmodifieddate:
                # Start from 1 day before the latest contact to ensure overlap
                since_date = latest_contact.lastmodifieddate.date() - timedelta(days=1)
                
                # Don't go back more than 30 days in auto mode
                max_auto_date = timezone.now().date() - timedelta(days=30)
                if since_date < max_auto_date:
                    since_date = max_auto_date
                
                return since_date
                
        except Exception as e:
            self.stdout.write(
                self.style.WARNING(f"Could not determine auto since date: {e}")
            )
        
        # Default to 7 days back
        return timezone.now().date() - timedelta(days=7)
    
    def _estimate_incremental_records(self, since_date):
        """Estimate how many records an incremental sync would return."""
        try:
            # Get count of contacts modified since the date in our database
            # This gives us a rough estimate, though HubSpot may have more recent data
            local_count = HubSpotContact.objects.filter(
                lastmodifieddate__gte=since_date
            ).count()
            
            # Add some buffer for new records not in our DB yet
            # Multiply by 1.5 and add 500 as buffer
            estimated = int(local_count * 1.5 + 500)
            
            # If we have no local data, estimate based on days
            if estimated < 100:
                days_back = (timezone.now().date() - since_date).days
                # Rough estimate: 100-200 contacts per day modified
                estimated = days_back * 150
            
            return min(estimated, 15000)  # Cap at 15k for safety
            
        except Exception:
            # If estimation fails, return conservative estimate
            days_back = (timezone.now().date() - since_date).days
            return min(days_back * 200, 10000)
