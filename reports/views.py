from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.management import call_command
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from django.core.paginator import Paginator
from .models import Report, ReportCategory
import json
import os
from datetime import datetime
import subprocess

@login_required
def report_list(request):
    categories = ReportCategory.objects.prefetch_related('reports').all()
    return render(request, 'reports/simple_report_list.html', {'categories': categories})

@login_required
def report_detail(request, report_id):
    report = get_object_or_404(Report, id=report_id)
    
    # Special handling for duplicated genius prospects report
    if report.title == 'Duplicated Genius Prospects':
        return duplicated_genius_prospects_detail(request, report)
    
    # Special handling for duplicated hubspot appointments report
    if report.title == 'Duplicated HubSpot Appointments':
        return duplicated_hubspot_appointments_detail(request, report)
    
    # Special handling for sales rep division mismatch report
    if report.title == 'Sales Rep Does Not Exist In Appointment Division':
        return sales_rep_division_mismatch_detail(request, report)
    
    # Special handling for unlink hubspot division report
    if report.title == 'Unlink HubSpot Division':
        return unlink_hubspot_division_detail(request, report)
    
    # Special handling for database schema analysis report
    if report.title == 'Database Schema Analysis':
        return database_schema_analysis_detail(request, report)
    
    return render(request, 'reports/report_detail.html', {'report': report})

@login_required
def duplicated_genius_prospects_detail(request, report):
    """Special view for the duplicated genius prospects report"""
    
    # Load latest results if they exist
    latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', 'latest.json')
    results = None
    paginated_groups = None
    
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            # Paginate the duplicate groups
            if results and 'duplicate_groups' in results:
                page_number = request.GET.get('page', 1)
                paginator = Paginator(results['duplicate_groups'], 50)  # 50 groups per page
                paginated_groups = paginator.get_page(page_number)
                
        except Exception as e:
            messages.error(request, f'Error loading results: {str(e)}')
    
    # Get all available result files
    results_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects')
    available_files = []
    
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and filename != 'latest.json':
                file_path = os.path.join(results_dir, filename)
                try:
                    # Extract timestamp from filename
                    timestamp_str = filename.replace('duplicated_genius_prospects_', '').replace('.json', '')
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    available_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'display_name': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except:
                    pass
    
    # Sort by timestamp descending (newest first)
    available_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'report': report,
        'results': results,
        'paginated_groups': paginated_groups,
        'available_files': available_files[:10],  # Show last 10 files
    }
    
    return render(request, 'reports/duplicated_genius_prospects.html', context)

@login_required
def duplicated_hubspot_appointments_detail(request, report):
    """Special view for the duplicated hubspot appointments report"""
    
    # Load latest results if they exist
    latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'latest.json')
    results = None
    paginated_groups = None
    
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            # Paginate the duplicate groups
            if results and 'duplicate_groups' in results:
                page_number = request.GET.get('page', 1)
                paginator = Paginator(results['duplicate_groups'], 50)  # 50 groups per page
                paginated_groups = paginator.get_page(page_number)
                
        except Exception as e:
            messages.error(request, f'Error loading results: {str(e)}')
    
    # Get all available result files
    results_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments')
    available_files = []
    
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and filename != 'latest.json':
                file_path = os.path.join(results_dir, filename)
                try:
                    # Extract timestamp from filename
                    timestamp_str = filename.replace('duplicated_hubspot_appointments_', '').replace('.json', '')
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    available_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'display_name': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except:
                    pass
    
    # Sort by timestamp descending (newest first)
    available_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'report': report,
        'results': results,
        'paginated_groups': paginated_groups,
        'available_files': available_files[:10],  # Show last 10 files
    }
    
    return render(request, 'reports/duplicated_hubspot_appointments.html', context)

@login_required
def sales_rep_division_mismatch_detail(request, report):
    """Special view for the sales rep division mismatch report"""
    from django.db import connection
    from django.core.paginator import Paginator
    import csv
    from io import StringIO
    
    # Execute the SQL query to get mismatched appointments
    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT 
                CONCAT(p.first_name, ' ' , p.last_name) as prospect_name,
                p.email as hubspot_identifier,
                a.id as genius_app_id,
                da.label as appointment_division,
                CONCAT(u.first_name, ' ' , u.last_name) as sales_rep,
                du.label as sales_rep_division
            FROM ingestion_genius_appointment as a
            LEFT JOIN ingestion_genius_prospect as p ON a.prospect_id = p.id
            LEFT JOIN ingestion_genius_division as da ON p.division_id = da.id
            LEFT JOIN ingestion_genius_userdata as u ON u.id = a.user_id
            LEFT JOIN ingestion_genius_division as du ON u.division_id = du.id
            WHERE p.division_id != u.division_id 
                AND a.add_date > '2025-06-08'
            ORDER BY da.label, prospect_name
        """)
        
        columns = [col[0] for col in cursor.description]
        results = [dict(zip(columns, row)) for row in cursor.fetchall()]
    
    # Handle CSV export
    if request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="sales_rep_division_mismatch_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        headers = ['Prospect Name', 'HubSpot Identifier', 'Genius App ID', 'Appointment Division', 'Sales Rep', 'Sales Rep Division']
        writer.writerow(headers)
        
        # Write data
        for row in results:
            writer.writerow([
                row['prospect_name'],
                row['hubspot_identifier'],
                row['genius_app_id'],
                row['appointment_division'],
                row['sales_rep'],
                row['sales_rep_division']
            ])
        
        return response
    
    # Paginate results for display
    page_number = request.GET.get('page', 1)
    paginator = Paginator(results, 50)  # 50 results per page
    paginated_results = paginator.get_page(page_number)
    
    # Calculate summary statistics
    total_mismatches = len(results)
    divisions_affected = len(set(row['appointment_division'] for row in results if row['appointment_division']))
    sales_reps_affected = len(set(row['sales_rep'] for row in results if row['sales_rep']))
    
    context = {
        'report': report,
        'results': paginated_results,
        'total_mismatches': total_mismatches,
        'divisions_affected': divisions_affected,
        'sales_reps_affected': sales_reps_affected,
        'generated_at': datetime.now(),
    }
    
    return render(request, 'reports/sales_rep_division_mismatch.html', context)

@login_required
def unlink_hubspot_division_detail(request, report):
    """Special view for the unlink hubspot division report"""
    import csv
    
    # Load latest results if they exist
    latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', 'latest.json')
    results = None
    paginated_groups = None
    
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            # Paginate the contact groups
            if results and 'contact_groups' in results:
                page_number = request.GET.get('page', 1)
                paginator = Paginator(results['contact_groups'], 50)  # 50 groups per page
                paginated_groups = paginator.get_page(page_number)
                
        except Exception as e:
            messages.error(request, f'Error loading results: {str(e)}')
    
    # Get all available result files
    results_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions')
    available_files = []
    
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and filename != 'latest.json':
                file_path = os.path.join(results_dir, filename)
                try:
                    # Extract timestamp from filename
                    timestamp_str = filename.replace('unlink_hubspot_divisions_', '').replace('.json', '')
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    available_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'display_name': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except:
                    pass
    
    # Sort by timestamp descending (newest first)
    available_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'report': report,
        'results': results,
        'paginated_groups': paginated_groups,
        'available_files': available_files[:10],  # Show last 10 files
    }
    
    return render(request, 'reports/unlink_hubspot_division.html', context)

@login_required
def database_schema_analysis_detail(request, report):
    """Special view for the database schema analysis report"""
    
    # Load latest results if they exist
    latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis', 'latest.json')
    results = None
    paginated_tables = None
    
    if os.path.exists(latest_file):
        try:
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
                
            # Paginate the tables
            if results and 'tables' in results:
                page_number = request.GET.get('page', 1)
                paginator = Paginator(results['tables'], 20)  # 20 tables per page
                paginated_tables = paginator.get_page(page_number)
                
        except Exception as e:
            messages.error(request, f'Error loading results: {str(e)}')
    
    # Get all available result files
    results_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis')
    available_files = []
    
    if os.path.exists(results_dir):
        for filename in os.listdir(results_dir):
            if filename.endswith('.json') and filename != 'latest.json':
                file_path = os.path.join(results_dir, filename)
                try:
                    # Extract timestamp from filename
                    timestamp_str = filename.replace('database_schema_analysis_', '').replace('.json', '')
                    timestamp = datetime.strptime(timestamp_str, '%Y%m%d_%H%M%S')
                    available_files.append({
                        'filename': filename,
                        'timestamp': timestamp,
                        'display_name': timestamp.strftime('%Y-%m-%d %H:%M:%S')
                    })
                except:
                    pass
    
    # Sort by timestamp descending (newest first)
    available_files.sort(key=lambda x: x['timestamp'], reverse=True)
    
    context = {
        'report': report,
        'results': results,
        'paginated_tables': paginated_tables,
        'available_files': available_files[:10],  # Show last 10 files
    }
    
    return render(request, 'reports/database_schema_analysis.html', context)

@csrf_exempt
@login_required
def run_duplicate_detection(request):
    """Start the duplicate detection process"""
    if request.method == 'POST':
        try:
            limit = request.POST.get('limit')
            threshold = request.POST.get('threshold', 80)
            
            # Build command arguments
            cmd_args = ['dedup_genius_prospects', f'--threshold={threshold}', f'--limit={limit}' if limit else '--limit=None']
            
            # Run the command in background
            call_command('dedup_genius_prospects', f'--threshold={threshold}', f'--limit={limit}' if limit else '--limit=None')
            
            return JsonResponse({'status': 'success', 'message': 'Detection started successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def load_report_file(request, filename):
    """AJAX endpoint to load a specific report file"""
    if request.method == 'GET':
        try:
            file_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', filename)
            latest_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', 'latest.json')
            
            if not os.path.exists(file_path) or not filename.endswith('.json'):
                return JsonResponse({'status': 'error', 'message': 'File not found'})
            
            # Copy the selected file to latest.json
            import shutil
            shutil.copy2(file_path, latest_path)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully loaded report: {filename}'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error loading file: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def check_detection_progress(request):
    """AJAX endpoint to check the progress of duplicate detection"""
    if request.method == 'GET':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', 'detection_progress.json')
            
            if not os.path.exists(progress_file):
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No detection process is currently running'
                })
            
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            return JsonResponse({
                'status': 'running',
                'progress': progress_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error checking progress: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def cancel_detection(request):
    """AJAX endpoint to cancel running duplicate detection"""
    if request.method == 'POST':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', 'detection_progress.json')
            
            if os.path.exists(progress_file):
                # Mark the detection as cancelled
                cancelled_progress = {
                    'percent': 0,
                    'status': 'Cancelled',
                    'details': 'Detection was cancelled by user',
                    'timestamp': datetime.now().isoformat(),
                    'completed': True,
                    'cancelled': True
                }
                
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(cancelled_progress, f, indent=2)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Detection cancellation requested. The process will stop shortly.'
                })
            else:
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No detection process is currently running.'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error cancelling detection: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def export_duplicates_csv(request):
    """Export duplicate detection results to CSV"""
    if request.method == 'GET':
        try:
            # Load latest results
            latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects', 'latest.json')
            
            if not os.path.exists(latest_file):
                return JsonResponse({'status': 'error', 'message': 'No results found. Please run detection first.'})
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Create CSV content
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Group ID',
                'Group Name', 
                'Total Duplicates',
                'Prospect ID',
                'First Name',
                'Last Name',
                'Phone',
                'Email',
                'ZIP Code',
                'Division',
                'Creation Date',
                'Similarity Score',
                'Detection Method',
                'Is Primary'  # Mark the first one in each group as primary
            ])
            
            # Write data
            for group in results.get('duplicate_groups', []):
                group_id = group.get('group_id', '')
                group_name = group.get('group_display_name', '')
                total_duplicates = group.get('total_duplicates', 0)
                avg_similarity = group.get('detection_details', {}).get('average_similarity_score', 0)
                detection_method = group.get('detection_details', {}).get('detection_method', 'unknown')
                
                for i, prospect in enumerate(group.get('prospects', [])):
                    is_primary = 'Yes' if i == 0 else 'No'  # First prospect is considered primary
                    
                    writer.writerow([
                        group_id,
                        group_name,
                        total_duplicates,
                        prospect.get('id', ''),
                        prospect.get('first_name', ''),
                        prospect.get('last_name', ''),
                        prospect.get('phone1', ''),
                        prospect.get('email', ''),
                        prospect.get('zip', ''),
                        prospect.get('division__label', ''),
                        prospect.get('add_date', ''),
                        avg_similarity,
                        detection_method,
                        is_primary
                    ])
            
            # Create HTTP response with CSV
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'duplicated_genius_prospects_{timestamp}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error generating CSV: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def run_hubspot_duplicate_detection(request):
    """AJAX endpoint to run the HubSpot appointment duplicate detection script"""
    if request.method == 'POST':
        try:
            # Check if detection is already running
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'detection_progress.json')
            if os.path.exists(progress_file):
                return JsonResponse({
                    'status': 'already_running',
                    'message': 'HubSpot appointment duplicate detection is already running. Please wait for it to complete.'
                })
            
            # Run the management command in the background using subprocess
            import threading
            import sys
            
            def run_detection():
                try:
                    # Use subprocess to run the management command with a reasonable limit for demo
                    result = subprocess.run([
                        sys.executable, 'manage.py', 'dedup_hubspot_appointments', '--limit', '5000'
                    ], capture_output=True, text=True, cwd=settings.BASE_DIR)
                    
                except Exception as e:
                    # If there's an error, create an error progress file
                    error_progress = {
                        'percent': 0,
                        'status': 'Error',
                        'details': f'Failed to run HubSpot detection: {str(e)}',
                        'timestamp': datetime.now().isoformat(),
                        'completed': True,
                        'error': True
                    }
                    try:
                        os.makedirs(os.path.dirname(progress_file), exist_ok=True)
                        with open(progress_file, 'w', encoding='utf-8') as f:
                            json.dump(error_progress, f, indent=2)
                    except:
                        pass
            
            # Start the detection in a separate thread
            detection_thread = threading.Thread(target=run_detection)
            detection_thread.daemon = True
            detection_thread.start()
            
            return JsonResponse({
                'status': 'started',
                'message': 'HubSpot appointment duplicate detection started! Check progress for updates.'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error starting HubSpot duplicate detection: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def check_hubspot_detection_progress(request):
    """AJAX endpoint to check HubSpot detection progress"""
    if request.method == 'GET':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'detection_progress.json')
            
            if not os.path.exists(progress_file):
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No detection currently running'
                })
            
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            return JsonResponse({
                'status': 'running',
                'progress': progress_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error checking progress: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def cancel_hubspot_detection(request):
    """AJAX endpoint to cancel HubSpot detection"""
    if request.method == 'POST':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'detection_progress.json')
            
            if not os.path.exists(progress_file):
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No detection currently running'
                })
            
            # Mark detection as cancelled
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            progress_data['cancelled'] = True
            progress_data['status'] = 'Cancelled'
            progress_data['details'] = 'Detection cancelled by user'
            progress_data['timestamp'] = datetime.now().isoformat()
            
            with open(progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
            
            return JsonResponse({
                'status': 'cancelled',
                'message': 'HubSpot detection cancellation requested'
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error cancelling detection: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def load_hubspot_report_file(request, filename):
    """AJAX endpoint to load a specific HubSpot report file"""
    if request.method == 'GET':
        try:
            file_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', filename)
            latest_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'latest.json')
            
            if not os.path.exists(file_path) or not filename.endswith('.json'):
                return JsonResponse({'status': 'error', 'message': 'File not found'})
            
            # Copy the selected file to latest.json
            import shutil
            shutil.copy2(file_path, latest_path)
            
            # Load and return the data
            with open(file_path, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Loaded results from {filename}',
                'results': results
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error loading file: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def export_hubspot_duplicates_csv(request):
    """Export HubSpot appointment duplicates to CSV"""
    if request.method == 'GET':
        try:
            # Get the latest results
            latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_hubspot_appointments', 'latest.json')
            
            if not os.path.exists(latest_file):
                return JsonResponse({'status': 'error', 'message': 'No results found. Please run detection first.'})
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Create CSV content
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Group ID',
                'Group Name', 
                'Total Duplicates',
                'Appointment ID',
                'Appointment Date',
                'Appointment Time',
                'Contact First Name',
                'Contact Last Name',
                'Contact Email',
                'Contact Phone',
                'Appointment Email',
                'Appointment Phone',
                'Appointment Status',
                'Creation Date',
                'Similarity Score',
                'Detection Method',
                'Is Primary'  # Mark the first one in each group as primary
            ])
            
            # Write data
            for group in results.get('duplicate_groups', []):
                group_id = group.get('group_id', '')
                group_name = group.get('group_display_name', '')
                total_duplicates = group.get('total_duplicates', 0)
                avg_similarity = group.get('detection_details', {}).get('average_similarity_score', 0)
                detection_method = group.get('detection_details', {}).get('detection_method', 'unknown')
                
                for i, appointment in enumerate(group.get('appointments', [])):
                    is_primary = 'Yes' if i == 0 else 'No'  # First appointment is considered primary
                    
                    writer.writerow([
                        group_id,
                        group_name,
                        total_duplicates,
                        appointment.get('id', ''),
                        appointment.get('hs_appointment_start', ''),
                        appointment.get('time', ''),
                        appointment.get('contact_firstname', ''),
                        appointment.get('contact_lastname', ''),
                        appointment.get('contact_email', ''),
                        appointment.get('contact_phone', ''),
                        appointment.get('appointment_email', ''),
                        appointment.get('appointment_phone', ''),
                        appointment.get('appointment_status', ''),
                        appointment.get('hs_createdate', ''),
                        avg_similarity,
                        detection_method,
                        is_primary
                    ])
            
            # Create HTTP response with CSV
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'duplicated_hubspot_appointments_{timestamp}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error generating CSV: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def run_unlink_division_analysis(request):
    """AJAX endpoint to run the unlink HubSpot division analysis"""
    if request.method == 'POST':
        try:
            limit = request.POST.get('limit')
            min_divisions = request.POST.get('min_divisions', 2)
            
            # Build command arguments
            cmd_args = ['unlink_hubspot_divisions']
            if limit:
                cmd_args.extend([f'--limit={limit}'])
            if min_divisions:
                cmd_args.extend([f'--min-divisions={min_divisions}'])
            
            # Run the command in background
            call_command(*cmd_args)
            
            return JsonResponse({'status': 'success', 'message': 'Analysis started successfully'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def check_unlink_division_progress(request):
    """AJAX endpoint to check the progress of unlink division analysis"""
    if request.method == 'GET':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', 'detection_progress.json')
            
            if not os.path.exists(progress_file):
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No analysis process is currently running'
                })
            
            with open(progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
            
            return JsonResponse({
                'status': 'running',
                'progress': progress_data
            })
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error checking progress: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt
def cancel_unlink_division_analysis(request):
    """AJAX endpoint to cancel unlink division analysis"""
    if request.method == 'POST':
        try:
            progress_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', 'detection_progress.json')
            
            if os.path.exists(progress_file):
                # Mark the analysis as cancelled
                cancelled_progress = {
                    'percent': 0,
                    'status': 'Cancelled',
                    'details': 'Analysis was cancelled by user',
                    'timestamp': datetime.now().isoformat(),
                    'completed': True,
                    'cancelled': True
                }
                
                with open(progress_file, 'w', encoding='utf-8') as f:
                    json.dump(cancelled_progress, f, indent=2)
                
                return JsonResponse({
                    'status': 'success',
                    'message': 'Analysis cancellation requested. The process will stop shortly.'
                })
            else:
                return JsonResponse({
                    'status': 'not_running',
                    'message': 'No analysis process is currently running.'
                })
                
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error cancelling analysis: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def load_unlink_division_report_file(request, filename):
    """AJAX endpoint to load a specific unlink division report file"""
    if request.method == 'GET':
        try:
            file_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', filename)
            latest_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', 'latest.json')
            
            if not os.path.exists(file_path) or not filename.endswith('.json'):
                return JsonResponse({'status': 'error', 'message': 'File not found'})
            
            # Copy the selected file to latest.json
            import shutil
            shutil.copy2(file_path, latest_path)
            
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully loaded report: {filename}'
            })
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error loading file: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
@csrf_exempt 
def export_unlink_division_csv(request):
    """Export unlink division analysis to CSV"""
    if request.method == 'GET':
        try:
            # Load latest results
            latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'unlink_hubspot_divisions', 'latest.json')
            
            if not os.path.exists(latest_file):
                return JsonResponse({'status': 'error', 'message': 'No results found. Please run analysis first.'})
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Create CSV content
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Group ID',
                'Contact ID',
                'HubSpot Contact ID',
                'First Name',
                'Last Name',
                'Email',
                'Phone',
                'Division Count',
                'Division Names',
                'Division IDs',
                'Contact Created Date'
            ])
            
            # Write data
            for group in results.get('contact_groups', []):
                writer.writerow([
                    group.get('group_id', ''),
                    group.get('contact_id', ''),
                    group.get('hubspot_contact_id', ''),
                    group.get('firstname', ''),
                    group.get('lastname', ''),
                    group.get('email', ''),
                    group.get('phone', ''),
                    group.get('division_count', 0),
                    group.get('division_names', ''),
                    ', '.join([str(div.get('division_id', '')) for div in group.get('divisions', [])]),
                    group.get('contact_created_date', '')
                ])
            
            # Create HTTP response with CSV
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'unlink_hubspot_divisions_{timestamp}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error exporting CSV: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def run_database_schema_analysis(request):
    """Start the database schema analysis process"""
    if request.method == 'POST':
        try:
            # Use the management command like other reports
            from django.core.management import call_command
            import threading
            
            def run_analysis():
                try:
                    call_command('analyze_database_schema')
                except Exception as e:
                    # Error handling is done within the command itself
                    pass
            
            # Start analysis in background thread
            thread = threading.Thread(target=run_analysis)
            thread.daemon = True
            thread.start()
            
            return JsonResponse({'status': 'success', 'message': 'Schema analysis started successfully'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def check_schema_analysis_progress(request):
    """Check the progress of the schema analysis"""
    from django.core.cache import cache
    
    status = cache.get('schema_analysis_status', 'idle')
    progress = cache.get('schema_analysis_progress', {
        'percent': 0,
        'status': 'No analysis running',
        'details': '',
        'completed': False
    })
    
    return JsonResponse({
        'status': status,
        'progress': progress
    })

@csrf_exempt
@login_required
def cancel_schema_analysis(request):
    """Cancel the running schema analysis"""
    if request.method == 'POST':
        from django.core.cache import cache
        
        cache.set('schema_analysis_status', 'cancelled', timeout=3600)
        cache.set('schema_analysis_progress', {
            'percent': 0,
            'status': 'Analysis cancelled by user',
            'details': '',
            'completed': True
        }, timeout=3600)
        
        return JsonResponse({'status': 'success', 'message': 'Analysis cancelled successfully'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def export_schema_analysis_csv(request):
    """Export schema analysis results as CSV"""
    if request.method == 'GET':
        try:
            # Load latest results
            latest_file = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis', 'latest.json')
            
            if not os.path.exists(latest_file):
                return JsonResponse({'status': 'error', 'message': 'No results found. Please run analysis first.'})
            
            with open(latest_file, 'r', encoding='utf-8') as f:
                results = json.load(f)
            
            # Create CSV content
            import csv
            from io import StringIO
            
            output = StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'Table Name',
                'Display Name',
                'Record Count',
                'Last Updated',
                'Column Name',
                'Data Type',
                'Is Nullable',
                'Completeness Ratio (%)'
            ])
            
            # Write data
            for table in results.get('tables', []):
                for column in table.get('columns', []):
                    writer.writerow([
                        table.get('table_name', ''),
                        table.get('display_name', ''),
                        table.get('record_count', 0),
                        table.get('last_updated', ''),
                        column.get('name', ''),
                        column.get('data_type', ''),
                        'Yes' if column.get('is_nullable', False) else 'No',
                        column.get('completeness_ratio', 0)
                    ])
            
            # Create HTTP response with CSV
            response = HttpResponse(output.getvalue(), content_type='text/csv')
            
            # Generate filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f'database_schema_analysis_{timestamp}.csv'
            response['Content-Disposition'] = f'attachment; filename="{filename}"'
            
            return response
            
        except Exception as e:
            return JsonResponse({
                'status': 'error',
                'message': f'Error exporting CSV: {str(e)}'
            })
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@csrf_exempt
@login_required
def load_schema_analysis_report_file(request, filename):
    """AJAX endpoint to load a specific schema analysis report file"""
    if request.method == 'GET':
        try:
            file_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis', filename)
            latest_path = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis', 'latest.json')
            
            if not os.path.exists(file_path) or not filename.endswith('.json'):
                return JsonResponse({'status': 'error', 'message': 'File not found'})
            
            # Copy the selected file to latest.json
            import shutil
            shutil.copy2(file_path, latest_path)
            
            return JsonResponse({'status': 'success', 'message': f'Report "{filename}" loaded successfully'})
            
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
