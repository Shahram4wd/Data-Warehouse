from django.core.management.base import BaseCommand
from ingestion.leadconduit.leadconduit_client import LeadConduitClient
from ingestion.leadconduit.base_processor import BaseLeadConduitProcessor
from ingestion.models.leadconduit import LeadConduit_Event, LeadConduit_Lead, LeadConduit_SyncHistory
from django.db import transaction
from tqdm import tqdm
from datetime import datetime, timezone as tz, timedelta
import logging
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand, BaseLeadConduitProcessor):
    help = "Download and sync leads from LeadConduit API by extracting lead data from events"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        BaseLeadConduitProcessor.__init__(self, 'leads')

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=1000,
            help='Maximum number of events to process for lead extraction (default: 1000)'
        )
        parser.add_argument(
            '--days',
            type=int,
            default=7,
            help='Number of days back to fetch events for lead extraction (default: 7)'
        )
        parser.add_argument(
            '--start-date',
            type=str,
            help='Start date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--end-date',
            type=str,
            help='End date (YYYY-MM-DD format)'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be imported without saving to database'
        )
        parser.add_argument(
            '--force-refresh',
            action='store_true',
            help='Force refresh of existing leads'
        )
        parser.add_argument(
            '--search-query',
            type=str,
            help='Search for specific leads using LeadConduit search API'
        )
        parser.add_argument(
            '--export-json',
            type=str,
            help='Export leads to JSON file (provide filename)'
        )
        parser.add_argument(
            '--events-only',
            action='store_true',
            help='Fetch events first, then extract leads from stored events'
        )
        parser.add_argument(
            '--source-events',
            action='store_true',
            help='Fetch source events specifically (contain original lead data)'
        )
        parser.add_argument(
            '--use-search-api',
            action='store_true',
            help='Use the search API to find all leads instead of extracting from events'
        )

    def handle(self, *args, **options):
        self.dry_run = options['dry_run']
        self.force_refresh = options['force_refresh']
        
        if self.dry_run:
            self.stdout.write(self.style.WARNING('DRY RUN MODE - No data will be saved'))

        try:
            # Initialize client
            client = LeadConduitClient()
            
            # Test connection
            if not client.test_connection():
                raise Exception("Failed to connect to LeadConduit API")
            
            self.stdout.write(self.style.SUCCESS('✓ Connected to LeadConduit API'))
              # Handle search query mode
            if options.get('search_query'):
                self._handle_search_leads(client, options)
                return
            
            # Handle search API mode (find all leads using search)
            if options.get('use_search_api'):
                self._handle_search_all_leads(client, options)
                return
            
            # Handle events-only mode
            if options.get('events_only'):
                self._fetch_events_then_extract_leads(client, options)
            elif options.get('source_events'):
                # Fetch source events specifically
                self._fetch_source_events_and_extract_leads(client, options)
            else:
                # Standard mode: fetch events and extract leads simultaneously
                self._fetch_and_extract_leads(client, options)
                
            # Export to JSON if requested
            if options.get('export_json'):
                self._export_leads_to_json(options['export_json'], options)
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            logger.error(f"LeadConduit leads sync failed: {str(e)}")
            return

    def _fetch_and_extract_leads(self, client, options):
        """Fetch events and extract leads in one process"""
        self.stdout.write('Fetching events and extracting leads...')
        
        # Determine date range
        start_date, end_date = self._get_date_range(options)
        
        # Fetch events
        events = self._fetch_events(client, options, start_date, end_date)
        
        if not events:
            self.stdout.write(self.style.WARNING('No events found in the specified date range'))
            return
        
        # Extract and save leads
        leads_processed = self._extract_leads_from_events(events, options)
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Successfully processed {leads_processed} leads from {len(events)} events')
        )

    def _fetch_events_then_extract_leads(self, client, options):
        """First fetch and save events, then extract leads from stored events"""
        self.stdout.write('Mode: Fetch events first, then extract leads')
        
        # Determine date range
        start_date, end_date = self._get_date_range(options)
        
        # Fetch and save events
        events = self._fetch_events(client, options, start_date, end_date)
        
        if not events:
            self.stdout.write(self.style.WARNING('No events found'))
            return
        
        # Save events to database first
        events_saved = self._save_events_to_db(events)
        
        # Now extract leads from stored events
        stored_events = LeadConduit_Event.objects.filter(
            start_timestamp__gte=int(start_date.timestamp() * 1000) if start_date else None,
            start_timestamp__lte=int(end_date.timestamp() * 1000) if end_date else None
        ).order_by('-start_timestamp')[:options['limit']]
        
        leads_processed = self._extract_leads_from_stored_events(stored_events, options)
        
        self.stdout.write(
            self.style.SUCCESS(f'✓ Saved {events_saved} events and processed {leads_processed} leads')
        )

    def _handle_search_leads(self, client, options):
        """Handle lead search functionality"""
        query = options['search_query']
        self.stdout.write(f'Searching for leads: "{query}"')
        
        try:
            # Use the search API
            search_results = client.search_leads(query, limit=options.get('limit', 100))
            
            if not search_results.get('leads'):
                self.stdout.write(self.style.WARNING('No leads found matching the search query'))
                return
            
            leads = search_results['leads']
            self.stdout.write(f'Found {len(leads)} leads matching search query')
            
            # Process search results (they may be in a different format)
            leads_processed = self._process_search_results(leads, options)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Processed {leads_processed} leads from search results')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Search failed: {str(e)}'))

    def _handle_search_all_leads(self, client, options):
        """Use search API to find all leads with a wildcard search"""
        self.stdout.write('Using search API to find all leads...')
        
        try:
            # Use a wildcard-like search or common terms to find all leads
            # We'll try multiple common search terms to get a broader set
            search_queries = ['*', 'a', 'e', 'i', 'o', 'u']  # Common letters to catch most leads
            all_leads = []
            seen_lead_ids = set()
            
            for query in search_queries[:1]:  # Start with just '*' - if that doesn't work, try others
                self.stdout.write(f'Searching with query: "{query}"')
                
                # Use paginated search
                leads = client.search_leads_paginated(
                    query=query,
                    limit_per_page=100,
                    max_total=options.get('limit', 1000),
                    sort_by='submission_timestamp',
                    sort_dir='desc'
                )
                
                # Deduplicate based on lead_id
                for lead in leads:
                    lead_id = lead.get('lead_id')
                    if lead_id and lead_id not in seen_lead_ids:
                        all_leads.append(lead)
                        seen_lead_ids.add(lead_id)
                
                self.stdout.write(f'Found {len(leads)} leads with query "{query}"')
                
                # If we got good results with the first query, no need to try others
                if len(leads) > 50:
                    break
            
            if not all_leads:
                self.stdout.write(self.style.WARNING('No leads found using search API'))
                return
            
            # Process the search results
            leads_processed = self._process_search_api_results(all_leads, options)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Processed {leads_processed} leads from search API')
            )
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Search API failed: {str(e)}'))

    def _fetch_source_events_and_extract_leads(self, client, options):
        """Fetch source events specifically and extract leads"""
        self.stdout.write('Fetching source events and extracting leads...')
        
        # Determine date range
        start_date, end_date = self._get_date_range(options)
        
        # Fetch source events
        try:
            limit = options.get('limit', 1000)
            
            if limit > 1000:
                source_events = client.get_source_events_paginated(
                    limit_per_page=1000,
                    max_total=limit,
                    start=start_date,
                    end=end_date
                )
            else:
                source_events = client.get_source_events(
                    limit=limit,
                    start=start_date,
                    end=end_date,
                    sort='desc'
                )
            
            if not source_events:
                self.stdout.write(self.style.WARNING('No source events found'))
                return
            
            self.stdout.write(f'✓ Fetched {len(source_events)} source events')
            
            # Extract and save leads from source events
            leads_processed = self._extract_leads_from_events(source_events, options)
            
            self.stdout.write(
                self.style.SUCCESS(f'✓ Successfully processed {leads_processed} leads from {len(source_events)} source events')
            )
            
        except Exception as e:
            raise Exception(f"Failed to fetch source events: {str(e)}")

    def _get_date_range(self, options):
        """Determine the date range for fetching events"""
        if options.get('start_date'):
            start_date = datetime.strptime(options['start_date'], '%Y-%m-%d').replace(tzinfo=tz.utc)
        else:
            # Default to specified days back
            days_back = options.get('days', 7)
            start_date = datetime.now(tz.utc) - timedelta(days=days_back)
        
        if options.get('end_date'):
            end_date = datetime.strptime(options['end_date'], '%Y-%m-%d').replace(tzinfo=tz.utc)
        else:
            end_date = datetime.now(tz.utc)
        
        self.stdout.write(f'Date range: {start_date.strftime("%Y-%m-%d")} to {end_date.strftime("%Y-%m-%d")}')
        return start_date, end_date

    def _fetch_events(self, client, options, start_date, end_date):
        """Fetch events from LeadConduit API"""
        self.stdout.write('Fetching events from LeadConduit API...')
        
        limit = options.get('limit', 1000)
        
        try:
            # Use paginated fetch for larger datasets
            if limit > 1000:
                events = client.get_events_paginated(
                    limit_per_page=1000,
                    max_total=limit,
                    start=start_date,
                    end=end_date
                )
            else:
                events = client.get_events(
                    limit=limit,
                    start=start_date,
                    end=end_date,
                    sort='desc'
                )
            
            self.stdout.write(f'✓ Fetched {len(events)} events')
            return events
            
        except Exception as e:
            raise Exception(f"Failed to fetch events: {str(e)}")

    def _save_events_to_db(self, events):
        """Save events to database"""
        if self.dry_run:
            return len(events)
        
        saved_count = 0
        with tqdm(total=len(events), desc="Saving events") as pbar:
            for event in events:
                try:
                    with transaction.atomic():
                        event_obj, created = self._save_event(event)
                        if created:
                            saved_count += 1
                        pbar.update(1)
                except Exception as e:
                    logger.error(f"Failed to save event {event.get('id', 'unknown')}: {str(e)}")
                    pbar.update(1)
        
        return saved_count

    def _extract_leads_from_events(self, events, options):
        """Extract lead data from event objects and save as leads"""
        if not events:
            return 0
        
        leads_processed = 0
        
        with tqdm(total=len(events), desc="Extracting leads") as pbar:
            for event in events:
                try:
                    # Extract lead data from event
                    lead_data = self._extract_lead_from_event(event)
                    
                    if lead_data:
                        if not self.dry_run:
                            # Save or update lead
                            lead_obj, created = self._save_or_update_lead(lead_data, event)
                            if created or self.force_refresh:
                                leads_processed += 1
                        else:
                            # Dry run - just count
                            leads_processed += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Would save lead: {lead_data.get('email', 'No email')} - {lead_data.get('full_name', 'No name')}")
                            )
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Failed to extract lead from event {event.get('id', 'unknown')}: {str(e)}")
                    pbar.update(1)
        
        return leads_processed

    def _extract_leads_from_stored_events(self, stored_events, options):
        """Extract leads from stored LeadConduit_Event objects"""
        leads_processed = 0
        
        with tqdm(total=len(stored_events), desc="Extracting leads from stored events") as pbar:
            for event_obj in stored_events:
                try:
                    # Convert stored event back to dict format for processing
                    event_dict = {
                        'id': event_obj.id,
                        'outcome': event_obj.outcome,
                        'vars': event_obj.vars_data or {},
                        'appended': event_obj.appended_data or {},
                        'start': event_obj.start_timestamp,
                        'end': event_obj.end_timestamp,
                        'type': event_obj.event_type,
                    }
                    
                    # Extract lead data
                    lead_data = self._extract_lead_from_event(event_dict)
                    
                    if lead_data:
                        if not self.dry_run:
                            lead_obj, created = self._save_or_update_lead(lead_data, event_dict, event_obj)
                            if created or self.force_refresh:
                                leads_processed += 1
                        else:
                            leads_processed += 1
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Failed to extract lead from stored event {event_obj.id}: {str(e)}")
                    pbar.update(1)
        
        return leads_processed

    def _extract_lead_from_event(self, event):
        """Extract lead information from a single event"""
        vars_data = event.get('vars', {})
        appended_data = event.get('appended', {})
        
        # Also check the request body for original lead data
        request_data = {}
        if event.get('request') and event['request'].get('body'):
            try:
                import json
                body_str = event['request']['body']
                if isinstance(body_str, str):
                    request_data = json.loads(body_str)
                elif isinstance(body_str, dict):
                    request_data = body_str
            except (json.JSONDecodeError, ValueError):
                logger.debug(f"Could not parse request body as JSON for event {event.get('id')}")
        
        # Combine all data sources, with vars taking highest precedence, then appended, then request
        combined_data = {**request_data, **appended_data, **vars_data}
        
        # Check if this event contains lead data
        if not self._has_lead_data(combined_data):
            return None
        
        # Extract lead fields with more comprehensive field mapping
        lead_data = {
            'lead_id': self._extract_lead_id(event, combined_data),
            'flow_id': combined_data.get('flow_id'),
            'flow_name': combined_data.get('flow_name'),
            'source_id': combined_data.get('source_id'),
            'source_name': combined_data.get('source_name'),
            'first_name': (
                combined_data.get('first_name') or 
                combined_data.get('fname') or 
                combined_data.get('firstName') or
                combined_data.get('given_name')
            ),
            'last_name': (
                combined_data.get('last_name') or 
                combined_data.get('lname') or 
                combined_data.get('lastName') or
                combined_data.get('family_name') or
                combined_data.get('surname')
            ),
            'email': (
                combined_data.get('email') or
                combined_data.get('email_address') or
                combined_data.get('emailAddress')
            ),
            'phone_1': (
                combined_data.get('phone_1') or 
                combined_data.get('phone') or 
                combined_data.get('phone_number') or
                combined_data.get('phoneNumber') or
                combined_data.get('primary_phone') or
                combined_data.get('home_phone')
            ),
            'phone_2': (
                combined_data.get('phone_2') or
                combined_data.get('secondary_phone') or
                combined_data.get('work_phone') or
                combined_data.get('mobile_phone')
            ),
            'address_1': (
                combined_data.get('address_1') or 
                combined_data.get('address') or
                combined_data.get('street_address') or
                combined_data.get('street') or
                combined_data.get('addr1')
            ),
            'address_2': (
                combined_data.get('address_2') or
                combined_data.get('address_line_2') or
                combined_data.get('addr2')
            ),
            'city': combined_data.get('city'),
            'state': (
                combined_data.get('state') or
                combined_data.get('state_code') or
                combined_data.get('province')
            ),
            'postal_code': (
                combined_data.get('postal_code') or 
                combined_data.get('zip') or
                combined_data.get('zip_code') or
                combined_data.get('zipcode')
            ),
            'country': (
                combined_data.get('country') or
                combined_data.get('country_code')
            ),
            'reference': (
                combined_data.get('reference') or 
                combined_data.get('ref') or
                combined_data.get('external_id') or
                combined_data.get('id')
            ),
            'submission_timestamp': self._parse_submission_timestamp(event, combined_data),
            'full_data': combined_data,
            'latest_event_id': event.get('id'),
            'latest_outcome': event.get('outcome'),
        }
        
        return lead_data

    def _has_lead_data(self, data):
        """Check if the data contains actual lead information"""
        lead_indicators = ['email', 'phone', 'phone_1', 'phone_number', 'first_name', 'last_name', 'fname', 'lname']
        return any(data.get(field) for field in lead_indicators)

    def _extract_lead_id(self, event, data):
        """Extract or generate a lead ID"""
        # Try to find an existing lead ID in the data
        lead_id = (
            data.get('lead_id') or
            data.get('id') or
            data.get('leadId') or
            data.get('reference') or
            event.get('id')  # Fallback to event ID
        )
        return str(lead_id)

    def _parse_submission_timestamp(self, event, data):
        """Parse submission timestamp from various possible fields"""
        # Try different timestamp fields
        timestamp = (
            data.get('submission_timestamp') or
            data.get('created_at') or
            data.get('timestamp') or
            event.get('start')
        )
        
        if timestamp:
            try:
                if isinstance(timestamp, (int, float)):
                    # Assume milliseconds if > 1e10, otherwise seconds
                    if timestamp > 1e10:
                        return datetime.fromtimestamp(timestamp / 1000, tz=tz.utc)
                    else:
                        return datetime.fromtimestamp(timestamp, tz=tz.utc)
                elif isinstance(timestamp, str):
                    return datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        
        return None

    def _save_or_update_lead(self, lead_data, event, event_obj=None):
        """Save or update a lead in the database"""
        lead_id = lead_data['lead_id']
        
        try:
            with transaction.atomic():
                lead, created = LeadConduit_Lead.objects.update_or_create(
                    lead_id=lead_id,
                    defaults=lead_data
                )
                
                # Update sync history if we have an event object
                if event_obj:
                    self._update_sync_history('lead_extraction', 1, 0, {
                        'lead_id': lead_id,
                        'event_id': event.get('id'),
                        'outcome': event.get('outcome')
                    })
                
                return lead, created
                
        except Exception as e:
            logger.error(f"Failed to save lead {lead_id}: {str(e)}")
            raise

    def _process_search_api_results(self, leads, options):
        """Process leads from search API results"""
        if not leads:
            return 0
        
        leads_processed = 0
        
        with tqdm(total=len(leads), desc="Processing search results") as pbar:
            for lead_result in leads:
                try:
                    # Convert search result to our lead format
                    lead_data = self._convert_search_result_to_lead_data(lead_result)
                    
                    if lead_data:
                        if not self.dry_run:
                            lead_obj, created = self._save_or_update_lead(lead_data, {})
                            if created or self.force_refresh:
                                leads_processed += 1
                        else:
                            leads_processed += 1
                            self.stdout.write(
                                self.style.SUCCESS(f"Would save lead: {lead_data.get('email', 'No email')} - {lead_data.get('first_name', '')} {lead_data.get('last_name', '')}")
                            )
                    
                    pbar.update(1)
                    
                except Exception as e:
                    logger.error(f"Failed to process search result: {str(e)}")
                    pbar.update(1)
        
        return leads_processed

    def _convert_search_result_to_lead_data(self, search_result):
        """Convert search API result to our lead data format"""
        # Search results have a well-defined structure according to the API docs
        lead_data = {
            'lead_id': search_result.get('lead_id'),
            'flow_id': search_result.get('flow_id'),
            'flow_name': search_result.get('flow_name'),
            'source_id': search_result.get('source_id'),
            'source_name': search_result.get('source_name'),
            'first_name': search_result.get('first_name'),
            'last_name': search_result.get('last_name'),
            'email': search_result.get('email'),
            'phone_1': search_result.get('phone_1'),
            'phone_2': search_result.get('phone_2'),
            'address_1': search_result.get('address_1'),
            'address_2': None,  # Not in search results
            'city': search_result.get('city'),
            'state': search_result.get('state'),
            'postal_code': search_result.get('postal_code'),
            'country': None,  # Not in search results
            'reference': search_result.get('reference'),
            'submission_timestamp': self._parse_submission_timestamp_from_search(search_result),
            'full_data': search_result,  # Store the complete search result
            'latest_event_id': search_result.get('latest_event', {}).get('id'),
            'latest_outcome': search_result.get('latest_event', {}).get('outcome'),
        }
        
        return lead_data

    def _parse_submission_timestamp_from_search(self, search_result):
        """Parse submission timestamp from search result"""
        timestamp_str = search_result.get('submission_timestamp')
        if timestamp_str:
            try:
                return datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
            except (ValueError, TypeError):
                pass
        return None

    def _process_search_results(self, leads, options):
        """Process leads from search API results (legacy method)"""
        return self._process_search_api_results(leads, options)

    def _convert_search_result_to_lead(self, search_result):
        """Convert search API result to our lead data format (legacy method)"""
        return self._convert_search_result_to_lead_data(search_result)

    def _export_leads_to_json(self, filename, options):
        """Export leads to JSON file"""
        self.stdout.write(f'Exporting leads to {filename}...')
        
        # Get leads from database
        leads = LeadConduit_Lead.objects.all().order_by('-updated_at')
        
        if options.get('limit'):
            leads = leads[:options['limit']]
        
        # Convert to list of dictionaries
        leads_data = []
        for lead in leads:
            lead_dict = {
                'lead_id': lead.lead_id,
                'flow_name': lead.flow_name,
                'source_name': lead.source_name,
                'first_name': lead.first_name,
                'last_name': lead.last_name,
                'email': lead.email,
                'phone_1': lead.phone_1,
                'address_1': lead.address_1,
                'city': lead.city,
                'state': lead.state,
                'postal_code': lead.postal_code,
                'submission_timestamp': lead.submission_timestamp.isoformat() if lead.submission_timestamp else None,
                'latest_outcome': lead.latest_outcome,
                'created_at': lead.created_at.isoformat(),
                'updated_at': lead.updated_at.isoformat(),
                'full_data': lead.full_data,
            }
            leads_data.append(lead_dict)
        
        # Write to file
        with open(filename, 'w') as f:
            json.dump(leads_data, f, indent=2, default=str)
        
        self.stdout.write(self.style.SUCCESS(f'✓ Exported {len(leads_data)} leads to {filename}'))
