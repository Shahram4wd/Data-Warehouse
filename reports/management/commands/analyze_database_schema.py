import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import connection


class Command(BaseCommand):
    help = 'Analyze database schema for all tables starting with "ingestion_" showing record counts, last update dates, and column completeness ratios'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_file = None
        self.last_reported_progress = 0

    def setup_progress_tracking(self):
        """Initialize progress tracking file"""
        progress_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis')
        os.makedirs(progress_dir, exist_ok=True)
        self.progress_file = os.path.join(progress_dir, 'analysis_progress.json')

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
        """Check if the analysis has been cancelled"""
        if not self.progress_file or not os.path.exists(self.progress_file):
            return False
            
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                return progress_data.get('cancelled', False)
        except:
            return False

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-dir',
            type=str,
            help='Custom output directory for results (default: reports/data/database_schema_analysis)',
        )
        parser.add_argument(
            '--table-prefix',
            type=str,
            default='ingestion_',
            help='Table name prefix to analyze (default: ingestion_)',
        )

    def handle(self, *args, **options):
        """Main command handler"""
        
        # Setup progress tracking
        self.setup_progress_tracking()
        
        # Check if already running
        if self.check_cancellation():
            self.stdout.write(self.style.WARNING('Analysis was cancelled'))
            return
        
        try:
            self.update_progress(0, 'Starting database schema analysis...', 'Initializing analysis process')
            
            # Get table prefix from options
            table_prefix = options.get('table_prefix', 'ingestion_')
            
            self.stdout.write(f'Starting database schema analysis for tables with prefix: {table_prefix}')
            
            # Run the analysis
            results = self.analyze_database_schema(table_prefix)
            
            # Save results
            output_dir = options.get('output_dir')
            if not output_dir:
                output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'database_schema_analysis')
            
            self.save_results(results, output_dir)
            
            self.update_progress(100, 'Analysis completed successfully', f'Analyzed {results["summary"]["total_tables"]} tables with {results["summary"]["total_records"]} total records')
            
            self.stdout.write(
                self.style.SUCCESS(
                    f'✓ Database schema analysis completed successfully! '
                    f'Analyzed {results["summary"]["total_tables"]} tables with {results["summary"]["total_records"]} total records.'
                )
            )
            
        except Exception as e:
            self.update_progress(0, f'Analysis failed: {str(e)}', 'Error occurred during analysis')
            self.stdout.write(self.style.ERROR(f'Analysis failed: {str(e)}'))
            raise

    def analyze_database_schema(self, table_prefix):
        """Analyze database schema for tables with the given prefix"""
        
        self.update_progress(10, 'Fetching table list...', f'Looking for tables starting with "{table_prefix}"')
        
        with connection.cursor() as cursor:
            # Get all tables with the specified prefix using Django's introspection
            all_table_names = connection.introspection.table_names(cursor)
            tables = [(table_name, 'public') for table_name in all_table_names if table_name.startswith(table_prefix)]
            tables.sort(key=lambda x: x[0])  # Sort by table name
            
            total_tables = len(tables)
            
            if total_tables == 0:
                self.update_progress(100, f'No tables found with prefix "{table_prefix}"', 'Analysis completed')
                return {
                    'summary': {
                        'total_tables': 0,
                        'total_records': 0,
                        'analysis_date': datetime.now().isoformat()
                    },
                    'tables': [],
                    'generated_at': datetime.now().isoformat()
                }
            
            self.stdout.write(f'Found {total_tables} tables to analyze')
            
            results = {
                'summary': {
                    'total_tables': total_tables,
                    'total_records': 0,
                    'analysis_date': datetime.now().isoformat()
                },
                'tables': [],
                'generated_at': datetime.now().isoformat()
            }
            
            for idx, (table_name, schema_name) in enumerate(tables):
                # Check for cancellation
                if self.check_cancellation():
                    self.stdout.write(self.style.WARNING('Analysis cancelled by user'))
                    return results
                
                progress = 20 + (idx / total_tables) * 70
                self.update_progress(int(progress), f'Analyzing table {table_name}...', f'Table {idx + 1} of {total_tables}')
                self.stdout.write(f'Analyzing table {idx + 1}/{total_tables}: {table_name}')
                
                table_info = {
                    'table_name': table_name,
                    'display_name': table_name.replace(table_prefix, '').replace('_', ' ').title(),
                    'record_count': 0,
                    'last_updated': None,
                    'columns': []
                }
                
                try:
                    # Get record count
                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
                    count_result = cursor.fetchone()
                    table_info['record_count'] = count_result[0] if count_result else 0
                    results['summary']['total_records'] += table_info['record_count']
                    
                    # Get last updated (check common timestamp columns)
                    timestamp_columns = ['updated_at', 'last_modified', 'modified_date', 'hs_lastmodifieddate', 'lastmodifieddate']
                    for col in timestamp_columns:
                        try:
                            cursor.execute(f'SELECT MAX("{col}") FROM "{table_name}" WHERE "{col}" IS NOT NULL')
                            max_date = cursor.fetchone()
                            if max_date and max_date[0]:
                                table_info['last_updated'] = max_date[0].isoformat() if hasattr(max_date[0], 'isoformat') else str(max_date[0])
                                break
                        except:
                            continue
                    
                    # Get column information using Django's introspection
                    column_descriptions = connection.introspection.get_table_description(cursor, table_name)
                    
                    for column in column_descriptions:
                        col_name = column.name
                        data_type = column.type_code if hasattr(column, 'type_code') else 'unknown'
                        is_nullable = column.null_ok if hasattr(column, 'null_ok') else True
                        # Calculate completeness ratio
                        try:
                            if table_info['record_count'] > 0:
                                # For text/varchar fields, check for both NULL and empty string
                                # For numeric and other fields, only check for NULL
                                if str(data_type) in ['1043', '25']:  # varchar and text types in PostgreSQL
                                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NOT NULL AND "{col_name}" != \'\'')
                                else:
                                    # For numeric, boolean, date, and other non-text fields
                                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NOT NULL')
                                non_null_count = cursor.fetchone()[0]
                                completeness_ratio = round((non_null_count / table_info['record_count']) * 100, 1)
                            else:
                                completeness_ratio = 0.0
                        except Exception as e:
                            # If there's an error, fall back to just checking for NULL
                            try:
                                if table_info['record_count'] > 0:
                                    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}" WHERE "{col_name}" IS NOT NULL')
                                    non_null_count = cursor.fetchone()[0]
                                    completeness_ratio = round((non_null_count / table_info['record_count']) * 100, 1)
                                else:
                                    completeness_ratio = 0.0
                            except:
                                completeness_ratio = 0.0
                        
                        table_info['columns'].append({
                            'name': col_name,
                            'data_type': str(data_type),
                            'is_nullable': is_nullable,
                            'completeness_ratio': completeness_ratio
                        })
                        
                except Exception as e:
                    self.stdout.write(self.style.WARNING(f'Error analyzing table {table_name}: {str(e)}'))
                    continue
                
                results['tables'].append(table_info)
        
        self.update_progress(90, 'Finalizing results...', 'Preparing output data')
        return results

    def save_results(self, results, output_dir):
        """Save analysis results to JSON files"""
        
        self.update_progress(95, 'Saving results...', 'Writing analysis to file')
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Save timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_file = os.path.join(output_dir, f'database_schema_analysis_{timestamp}.json')
        latest_file = os.path.join(output_dir, 'latest.json')
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        with open(latest_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        self.stdout.write(f'Results saved to: {output_file}')
        self.stdout.write(f'Latest results available at: {latest_file}')
