import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Generate report of HubSpot contacts linked to multiple divisions with interactive web interface'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_file = None
        self.last_reported_progress = 0

    def setup_progress_tracking(self):
        """Initialize progress tracking file"""
        progress_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions')
        os.makedirs(progress_dir, exist_ok=True)
        self.progress_file = os.path.join(progress_dir, 'detection_progress.json')

    def update_progress(self, percent, status, details):
        """Update progress file with current status"""
        if not self.progress_file:
            return
        
        # Ensure progress never goes backwards
        percent = max(self.last_reported_progress, percent)
        self.last_reported_progress = percent
            
        progress_data = {
            'percent': percent,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'completed': percent >= 100
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.stdout.write(f'Warning: Could not update progress file: {e}')

    def check_cancellation(self):
        """Check if the detection has been cancelled"""
        if not self.progress_file or not os.path.exists(self.progress_file):
            return False
            
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                return progress_data.get('cancelled', False)
        except Exception:
            return False

    def cleanup_progress(self):
        """Remove progress file when detection is complete"""
        if self.progress_file and os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception:
                pass

    def add_arguments(self, parser):
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of contacts to process (for testing)'
        )
        parser.add_argument(
            '--output-limit',
            type=int,
            default=None,
            help='Limit the number of contact groups in the output (for performance)'
        )
        parser.add_argument(
            '--min-divisions',
            type=int,
            default=2,
            help='Minimum number of divisions a contact must have to be included (default: 2)'
        )

    def handle(self, *args, **options):
        limit = options['limit']
        output_limit = options['output_limit']
        min_divisions = options['min_divisions']
        
        self.stdout.write(f'Starting HubSpot contact multi-division analysis...')
        
        # Initialize progress tracking
        self.setup_progress_tracking()
        self.update_progress(0, 'Initializing...', 'Preparing to analyze contacts')
        
        self.update_progress(10, 'Analyzing contacts...', 'Finding contacts with multiple divisions')
        
        # SQL query to find contacts with multiple divisions
        query = """
        SELECT 
            c.id as contact_id,
            c.id as hubspot_contact_id,
            c.firstname,
            c.lastname,
            c.email,
            c.phone,
            COUNT(DISTINCT d.id) as division_count,
            STRING_AGG(DISTINCT d.division_label, ', ') as division_names,
            STRING_AGG(DISTINCT CAST(d.id AS TEXT), ', ') as division_ids,
            c.createdate as contact_created_date
        FROM ingestion_hubspot_contact c
        INNER JOIN ingestion_hubspot_contact_division_assoc cd ON cd.contact_id = c.id
        INNER JOIN ingestion_hubspot_division d ON d.id = cd.division_id
        GROUP BY c.id, c.firstname, c.lastname, c.email, c.phone, c.createdate
        HAVING COUNT(DISTINCT d.id) >= %s
        ORDER BY COUNT(DISTINCT d.id) DESC, c.lastname, c.firstname
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        try:
            with connection.cursor() as cursor:
                # Set timeout for this query
                cursor.execute("SET statement_timeout = '60s'")
                cursor.execute(query, [min_divisions])
                contacts_raw = cursor.fetchall()
                # Reset timeout
                cursor.execute("SET statement_timeout = 0")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error executing contact analysis query: {e}'))
            self.update_progress(0, 'Error', f'Database query failed: {str(e)}')
            return "Analysis failed due to database error"
        
        self.stdout.write(f'Found {len(contacts_raw)} contacts with multiple divisions...')
        self.update_progress(30, 'Processing results...', f'Found {len(contacts_raw)} contacts with multiple divisions')

        # Check for cancellation
        if self.check_cancellation():
            self.update_progress(0, 'Cancelled', 'Analysis was cancelled by user')
            self.stdout.write(self.style.WARNING('Analysis cancelled by user.'))
            return "Analysis cancelled"

        if len(contacts_raw) == 0:
            self.update_progress(100, 'Complete!', 'No contacts with multiple divisions found')
            self.stdout.write(self.style.SUCCESS('No contacts with multiple divisions found.'))
            return self.save_empty_results()

        # Process contact groups
        self.update_progress(40, 'Building contact groups...', f'Processing {len(contacts_raw)} contact groups')
        
        contact_groups = []
        total_contacts_with_multiple_divisions = len(contacts_raw)
        
        for i, (contact_id, hubspot_contact_id, firstname, lastname, email, phone, 
                division_count, division_names, division_ids, contact_created_date) in enumerate(contacts_raw):
            
            if self.check_cancellation():
                self.update_progress(0, 'Cancelled', 'Analysis was cancelled by user')
                self.stdout.write(self.style.WARNING('Analysis cancelled by user.'))
                return "Analysis cancelled"
            
            # Generate group display name
            display_name = self.generate_contact_display_name(firstname, lastname, email, division_count)
            
            # Get individual divisions for this contact
            divisions = []
            if division_names and division_ids:
                names_list = [name.strip() for name in division_names.split(',')]
                ids_list = [id_str.strip() for id_str in division_ids.split(',')]
                
                for name, div_id in zip(names_list, ids_list):
                    divisions.append({
                        'division_id': div_id,
                        'division_name': name  # This will contain division_label from SQL
                    })
            
            contact_group = {
                'group_id': i + 1,
                'group_display_name': display_name,
                'contact_id': contact_id,
                'hubspot_contact_id': hubspot_contact_id,
                'firstname': firstname or '',
                'lastname': lastname or '',
                'email': email or '',
                'phone': phone or '',
                'division_count': division_count,
                'division_names': division_names or '',
                'divisions': divisions,
                'contact_created_date': contact_created_date.isoformat() if contact_created_date else None,
                'analysis_details': {
                    'total_divisions': division_count,
                    'analysis_method': 'exact_sql_matching'
                }
            }
            
            contact_groups.append(contact_group)
            
            # Update progress periodically
            if i % 100 == 0:
                progress = 40 + (i / len(contacts_raw)) * 40
                self.update_progress(int(progress), 'Processing contacts...', f'Processed {i+1}/{len(contacts_raw)} contacts')

        # Apply output limit if specified
        if output_limit and len(contact_groups) > output_limit:
            contact_groups = contact_groups[:output_limit]
            self.update_progress(85, 'Applying output limit...', f'Limited output to {output_limit} contact groups')

        self.update_progress(90, 'Generating report...', 'Preparing results for output')

        # Prepare results
        results = {
            'report_type': 'unlink_hubspot_divisions',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'min_divisions_threshold': min_divisions,
                'total_contacts_analyzed': total_contacts_with_multiple_divisions,
                'limit_used': limit,
                'output_limit_used': output_limit
            },
            'summary': {
                'total_contacts_with_multiple_divisions': len(contacts_raw),
                'total_contacts_displayed': len(contact_groups),
                'output_limited': output_limit is not None and len(contacts_raw) > output_limit,
                'total_divisions_involved': len(set(div['division_name'] for group in contact_groups for div in group['divisions'] if div['division_name']))
            },
            'contact_groups': contact_groups
        }

        self.update_progress(95, 'Saving results...', 'Writing report files to disk')

        # Save results to timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'unlink_hubspot_divisions_{timestamp}.json'
        
        # Ensure directory exists
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        # Also save as "latest.json" for easy access
        latest_path = os.path.join(output_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        self.update_progress(100, 'Complete!', f'Found {len(contact_groups)} contacts with multiple divisions')

        completion_message = (
            f'HubSpot contact multi-division analysis completed!\n'
            f'Found {len(contact_groups)} contacts with multiple divisions.\n'
        )
        
        if output_limit and len(contacts_raw) > output_limit:
            completion_message += f'Output limited to {output_limit} contacts for performance.\n'
        
        completion_message += f'Results saved to: {output_path}'

        self.stdout.write(self.style.SUCCESS(completion_message))

        # Clean up progress file
        self.cleanup_progress()

        return f"Analysis completed: {len(contact_groups)} contacts found"

    def generate_contact_display_name(self, firstname, lastname, email, division_count):
        """Generate a descriptive group name based on the contact"""
        # Clean up the name
        display_name = f"{firstname or ''} {lastname or ''}".strip()
        if not display_name:
            display_name = email or "Unknown Contact"
        
        # Add division count
        return f"{display_name} ({division_count} divisions)"

    def save_empty_results(self):
        """Save empty results when no contacts with multiple divisions are found"""
        results = {
            'report_type': 'unlink_hubspot_divisions',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'min_divisions_threshold': 2,
                'total_contacts_analyzed': 0
            },
            'summary': {
                'total_contacts_with_multiple_divisions': 0,
                'total_contacts_displayed': 0,
                'output_limited': False,
                'total_divisions_involved': 0
            },
            'contact_groups': []
        }

        # Save results
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'unlink_hubspot_divisions_{timestamp}.json'
        
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        latest_path = os.path.join(output_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, default=str)

        return "No contacts with multiple divisions found"
