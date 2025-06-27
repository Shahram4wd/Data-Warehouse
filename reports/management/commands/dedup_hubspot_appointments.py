import json
import os
from datetime import datetime, date, time
from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.models.hubspot import Hubspot_Appointment, Hubspot_Contact, Hubspot_AppointmentContactAssociation


class Command(BaseCommand):
    help = 'Detect duplicate HubSpot appointments using SQL-based exact matching (100% similarity)'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_file = None
        self.last_reported_progress = 0  # Track progress to ensure monotonic increase

    def setup_progress_tracking(self):
        """Initialize progress tracking file"""
        progress_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments')
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
                pass  # Ignore cleanup errors

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=100,
            help='Similarity threshold for duplicate detection (default: 100 for exact matching)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of appointments to process (for testing)'
        )
        parser.add_argument(
            '--output-limit',
            type=int,
            default=None,
            help='Limit the number of duplicate groups in the output (for performance)'
        )
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Use optimized SQL-only matching for maximum speed (default behavior)'
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=None,
            help='Process a random sample of N appointment groups for quick testing'
        )

    def handle(self, *args, **options):
        threshold = options['threshold']
        limit = options['limit']
        output_limit = options['output_limit']
        
        self.stdout.write(f'Starting HubSpot appointment duplicate detection with {threshold}% similarity threshold...')
        
        # Initialize progress tracking
        self.setup_progress_tracking()
        self.update_progress(0, 'Initializing...', 'Preparing to load appointments')
        
        # First, update appointments with missing time from hs_appointment_start
        self.update_progress(5, 'Updating time fields...', 'Filling missing time values from hs_appointment_start')
        self.fill_missing_time_fields()
        
        self.update_progress(100, 'Loading appointments...', 'Fetching appointment data with contact information')
        
        # For very large datasets, suggest using a limit or provide warning
        total_appointments_query = """
            SELECT COUNT(DISTINCT a.id)
            FROM ingestion_hubspot_appointment a
            INNER JOIN ingestion_hubspot_appointment_contact_assoc ac ON a.id = ac.appointment_id
            WHERE a.hs_appointment_start IS NOT NULL 
               AND a.time IS NOT NULL
               AND ac.contact_id IS NOT NULL
        """
        
        from django.db import connection
        with connection.cursor() as cursor:
            cursor.execute(total_appointments_query)
            total_appointments_count = cursor.fetchone()[0]
        
        if total_appointments_count > 50000 and not limit:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Processing {total_appointments_count} appointments may take a very long time.\n'
                    f'Consider using --limit parameter for faster testing (e.g., --limit 10000)'
                )
            )
        
        # Use SQL to find duplicate groups efficiently
        self.update_progress(10, 'Finding duplicates...', 'Using optimized SQL to identify exact duplicate appointments')
        
        duplicate_query = """
            SELECT 
                date(a.hs_appointment_start) as appointment_date,
                a.time,
                ac.contact_id,
                count(*) as duplicate_count,
                array_agg(a.id ORDER BY a.hs_createdate DESC) as appointment_ids
            FROM ingestion_hubspot_appointment a
            INNER JOIN ingestion_hubspot_appointment_contact_assoc ac ON a.id = ac.appointment_id
            WHERE a.hs_appointment_start IS NOT NULL 
               AND a.time IS NOT NULL
               AND ac.contact_id IS NOT NULL
            GROUP BY date(a.hs_appointment_start), a.time, ac.contact_id
            HAVING count(*) > 1
            ORDER BY count(*) DESC, date(a.hs_appointment_start) DESC
        """
        
        if limit:
            duplicate_query += f" LIMIT {limit}"
        
        # Execute raw SQL to get duplicate groups with timeout protection
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # Set a statement timeout to prevent hanging (30 seconds)
                cursor.execute("SET statement_timeout = '30s'")
                cursor.execute(duplicate_query)
                duplicate_groups_raw = cursor.fetchall()
                # Reset timeout
                cursor.execute("SET statement_timeout = 0")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error executing duplicate detection query: {e}'))
            self.update_progress(0, 'Error', f'Database query failed: {str(e)}')
            return "Detection failed due to database error"
        
        self.stdout.write(f'Found {len(duplicate_groups_raw)} duplicate groups...')
        self.update_progress(25, 'Processing duplicates...', f'Found {len(duplicate_groups_raw)} duplicate groups')

        # Check for cancellation before proceeding with heavy processing
        if self.check_cancellation():
            self.update_progress(0, 'Cancelled', 'Detection was cancelled by user')
            self.stdout.write(self.style.WARNING('Detection cancelled by user.'))
            return "Detection cancelled"

        if len(duplicate_groups_raw) == 0:
            self.update_progress(100, 'Complete!', 'No duplicate groups found')
            self.stdout.write(self.style.SUCCESS('No duplicate appointments found.'))
            
            # Still create an empty report file for consistency
            results = {
                'report_type': 'duplicated_hubspot_appointments',
                'generated_at': datetime.now().isoformat(),
                'parameters': {
                    'similarity_threshold': threshold,
                    'total_appointments_analyzed': 0,
                    'fields_compared': ['appointment_date', 'appointment_time', 'contact_id'],
                    'limit_used': limit,
                    'output_limit_used': output_limit
                },
                'summary': {
                    'total_duplicate_groups_found': 0,
                    'total_duplicate_groups_displayed': 0,
                    'output_limited': False,
                    'total_duplicate_appointments': 0,
                    'percentage_duplicates': 0
                },
                'duplicate_groups': []
            }
            
            # Save empty results
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'duplicated_hubspot_appointments_{timestamp}.json'
            output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments')
            os.makedirs(output_dir, exist_ok=True)
            
            output_path = os.path.join(output_dir, filename)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            # Also save as "latest.json"
            latest_path = os.path.join(output_dir, 'latest.json')
            with open(latest_path, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2, ensure_ascii=False, default=str)
            
            self.cleanup_progress()
            return "No duplicates found"

        # Collect all appointment IDs from duplicate groups for bulk fetching
        all_appointment_ids = []
        for _, _, _, _, appointment_ids in duplicate_groups_raw:
            all_appointment_ids.extend(appointment_ids)
        
        self.update_progress(30, 'Fetching appointment details...', f'Loading details for {len(all_appointment_ids)} appointments')
        
        # Check for cancellation before bulk fetch
        if self.check_cancellation():
            self.update_progress(0, 'Cancelled', 'Detection was cancelled by user')
            self.stdout.write(self.style.WARNING('Detection cancelled by user.'))
            return "Detection cancelled"
        
        # Fetch all appointment details in one query for better performance
        appointment_details_query = """
            SELECT 
                a.id,
                a.hs_appointment_start,
                a.time,
                a.hs_createdate,
                a.appointment_status,
                a.email as appointment_email,
                a.phone1 as appointment_phone,
                a.first_name as appointment_first_name,
                a.last_name as appointment_last_name,
                c.firstname as contact_firstname,
                c.lastname as contact_lastname,
                c.email as contact_email,
                c.phone as contact_phone
            FROM ingestion_hubspot_appointment a
            INNER JOIN ingestion_hubspot_appointment_contact_assoc ac ON a.id = ac.appointment_id
            LEFT JOIN ingestion_hubspot_contact c ON c.id = ac.contact_id
            WHERE a.id = ANY(%s)
            ORDER BY a.hs_createdate DESC
        """
        
        # Execute the bulk query with timeout protection
        try:
            with connection.cursor() as detail_cursor:
                # Set timeout for this query
                detail_cursor.execute("SET statement_timeout = '60s'")
                detail_cursor.execute(appointment_details_query, [all_appointment_ids])
                all_appointment_details = detail_cursor.fetchall()
                # Reset timeout
                detail_cursor.execute("SET statement_timeout = 0")
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error fetching appointment details: {e}'))
            self.update_progress(0, 'Error', f'Failed to fetch appointment details: {str(e)}')
            return "Detection failed during appointment detail fetch"
        
        # Create a lookup dictionary for appointment details
        appointment_lookup = {}
        for row in all_appointment_details:
            appointment_lookup[row[0]] = {
                'id': row[0],
                'hs_appointment_start': row[1],
                'time': row[2],
                'hs_createdate': row[3],
                'appointment_status': row[4] or 'Unknown',
                'appointment_email': row[5],
                'appointment_phone': row[6],
                'appointment_first_name': row[7],
                'appointment_last_name': row[8],
                'contact_firstname': row[9],
                'contact_lastname': row[10],
                'contact_email': row[11],
                'contact_phone': row[12],
            }
        
        self.update_progress(40, 'Building duplicate groups...', f'Processing {len(duplicate_groups_raw)} duplicate groups')
        
        duplicate_groups = []
        total_duplicate_appointments = 0
        
        for i, (appointment_date, appointment_time, contact_id, duplicate_count, appointment_ids) in enumerate(duplicate_groups_raw):
            # Check for cancellation periodically
            if i % 100 == 0 and self.check_cancellation():
                self.update_progress(0, 'Cancelled', 'Detection was cancelled by user')
                self.stdout.write(self.style.WARNING('Detection cancelled by user.'))
                return "Detection cancelled"
            
            # Update progress
            progress = 40 + (i / len(duplicate_groups_raw)) * 40  # 40% to 80%
            if i % 50 == 0:
                self.update_progress(progress, 'Building duplicate groups...', 
                                   f'Processing group {i+1} of {len(duplicate_groups_raw)}')
            
            # Build appointments list from the lookup dictionary
            appointments = []
            for appointment_id in appointment_ids:
                if appointment_id in appointment_lookup:
                    appointment_data = appointment_lookup[appointment_id].copy()
                    appointment_data.update({
                        'appointment_date': appointment_date,
                        'appointment_time': appointment_time,
                        'contact_id': contact_id
                    })
                    appointments.append(appointment_data)
            
            total_duplicate_appointments += len(appointments)
            
            duplicate_group = {
                'group_id': len(duplicate_groups) + 1,
                'group_display_name': self.generate_group_display_name(appointments, appointment_date, appointment_time),
                'total_duplicates': len(appointments),
                'appointments': appointments,
                'detection_details': {
                    'threshold_used': threshold,  # Use the actual threshold parameter
                    'detection_method': 'sql_exact_match',
                    'average_similarity_score': 100.0,  # Exact match = 100%
                    'appointment_date': str(appointment_date),
                    'appointment_time': str(appointment_time),
                    'contact_id': contact_id,
                    'fields_analyzed': ['appointment_date', 'appointment_time', 'contact_id'],
                }
            }
            duplicate_groups.append(duplicate_group)
        
        # Sort duplicate groups by latest creation date (descending)
        self.update_progress(80, 'Sorting results...', 'Organizing duplicate groups by creation date')
        
        for group in duplicate_groups:
            # Sort appointments within each group by hs_createdate descending
            group['appointments'] = sorted(
                group['appointments'],
                key=lambda x: x['hs_createdate'] if x['hs_createdate'] else datetime.min,
                reverse=True
            )
            # Add latest_creation_date for sorting groups
            group['latest_creation_date'] = group['appointments'][0]['hs_createdate'] if group['appointments'] and group['appointments'][0]['hs_createdate'] else datetime.min

        # Sort groups by latest creation date (descending)
        duplicate_groups = sorted(
            duplicate_groups,
            key=lambda x: x['latest_creation_date'],
            reverse=True
        )

        # Re-assign group IDs after sorting
        for i, group in enumerate(duplicate_groups, 1):
            group['group_id'] = i
            # Remove the temporary sorting field
            if 'latest_creation_date' in group:
                del group['latest_creation_date']

        # Apply output limit if specified
        if output_limit and len(duplicate_groups) > output_limit:
            original_count = len(duplicate_groups)
            duplicate_groups = duplicate_groups[:output_limit]
            self.stdout.write(f'Limited output to {output_limit} groups (found {original_count} total)')

        self.update_progress(90, 'Generating report...', 'Preparing results for output')

        # Prepare results
        results = {
            'report_type': 'duplicated_hubspot_appointments',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'similarity_threshold': threshold,  # Use the actual threshold parameter
                'total_appointments_analyzed': total_duplicate_appointments,
                'fields_compared': ['appointment_date', 'appointment_time', 'contact_id'],
                'limit_used': limit,
                'output_limit_used': output_limit
            },
            'summary': {
                'total_duplicate_groups_found': len(duplicate_groups_raw),
                'total_duplicate_groups_displayed': len(duplicate_groups),
                'output_limited': output_limit is not None and len(duplicate_groups_raw) > output_limit,
                'total_duplicate_appointments': total_duplicate_appointments,
                'percentage_duplicates': round(
                    (total_duplicate_appointments / max(total_duplicate_appointments, 1)) * 100, 2
                ) if total_duplicate_appointments > 0 else 0
            },
            'duplicate_groups': duplicate_groups
        }

        self.update_progress(90, 'Saving results...', 'Writing report files to disk')

        # Save results to timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'duplicated_hubspot_appointments_{timestamp}.json'
        
        # Ensure directory exists
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Also save as "latest.json" for easy access
        latest_path = os.path.join(output_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        self.update_progress(100, 'Complete!', f'Found {len(duplicate_groups)} duplicate groups')

        completion_message = (
            f'HubSpot appointment duplicate detection completed!\n'
            f'Found {len(duplicate_groups)} duplicate groups with {total_duplicate_appointments} total duplicates.\n'
        )
        
        if output_limit and len(duplicate_groups_raw) > output_limit:
            completion_message += f'Output limited to top {output_limit} groups (use --output-limit to adjust).\n'
        
        completion_message += f'Results saved to: {output_path}'

        self.stdout.write(self.style.SUCCESS(completion_message))

        # Clean up progress file
        self.cleanup_progress()

        return f"Detection completed: {len(duplicate_groups)} groups found"

    def generate_group_display_name(self, appointments, appointment_date, appointment_time):
        """Generate a descriptive group name based on the appointments"""
        if not appointments:
            return "Unknown Group"
        
        # Use the first appointment's contact name as the base
        first_appointment = appointments[0]
        contact_firstname = first_appointment.get('contact_firstname', '').strip()
        contact_lastname = first_appointment.get('contact_lastname', '').strip()
        
        # Clean up the name
        display_name = f"{contact_firstname} {contact_lastname}".strip()
        if not display_name:
            display_name = "Unknown Contact"
        
        # Add date/time info using the passed parameters
        date_str = appointment_date.strftime('%m/%d/%Y') if appointment_date else "Unknown Date"
        time_str = appointment_time.strftime('%I:%M %p') if appointment_time else "Unknown Time"
        
        # Add duplicate count
        return f"{display_name} - {date_str} {time_str} ({len(appointments)} duplicates)"



    def fill_missing_time_fields(self):
        """Fill missing time fields from hs_appointment_start before duplicate detection"""
        from django.db import connection
        
        try:
            with connection.cursor() as cursor:
                # First, check how many records need updating
                count_query = """
                    SELECT COUNT(*) 
                    FROM ingestion_hubspot_appointment 
                    WHERE time IS NULL 
                      AND hs_appointment_start IS NOT NULL
                """
                
                cursor.execute(count_query)
                records_to_update = cursor.fetchone()[0]
                
                if records_to_update == 0:
                    self.stdout.write('No appointments need time field updates')
                    return
                
                self.stdout.write(f'Found {records_to_update} appointments that need time field updates')
                self.update_progress(6, 'Updating time fields...', f'Processing {records_to_update} appointments')
                
                # Update appointments where time is NULL but hs_appointment_start is not NULL
                # Use a more efficient query with explicit transaction control
                update_query = """
                    UPDATE ingestion_hubspot_appointment 
                    SET time = hs_appointment_start::time
                    WHERE time IS NULL 
                      AND hs_appointment_start IS NOT NULL
                """
                
                cursor.execute(update_query)
                updated_count = cursor.rowcount
                
                self.stdout.write(f'Successfully updated {updated_count} appointments with time extracted from hs_appointment_start')
                
        except Exception as e:
            self.stdout.write(self.style.WARNING(f'Warning: Could not update time fields: {e}'))
            self.stdout.write(self.style.WARNING('Continuing with detection using existing time values...'))
            # Continue with detection even if update fails
