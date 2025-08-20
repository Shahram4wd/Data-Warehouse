"""
Move Django tables to django schema
"""
from django.core.management.base import BaseCommand
from django.db import connection
from django.apps import apps
from django.conf import settings


class Command(BaseCommand):
    help = 'Move Django framework tables to django schema and configure schema separation'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be moved without actually moving tables'
        )
        parser.add_argument(
            '--setup-only',
            action='store_true', 
            help='Only set up schemas without moving tables'
        )

    def handle(self, *args, **options):
        dry_run = options['dry_run']
        setup_only = options['setup_only']
        
        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - No changes will be made"))
        
        # Step 1: Create schemas
        self.create_schemas(dry_run)
        
        if setup_only:
            self.stdout.write(self.style.SUCCESS("Schema setup completed"))
            return
        
        # Step 2: Move Django framework tables
        self.move_django_tables(dry_run)
        
        # Step 3: Update search path
        self.configure_search_path(dry_run)
        
        self.stdout.write(self.style.SUCCESS("Schema migration completed!"))
        self.stdout.write("Next steps:")
        self.stdout.write("1. Restart your Django application")
        self.stdout.write("2. Run migrations: python manage.py migrate")
        self.stdout.write("3. Django tables will now be in 'django' schema")
        self.stdout.write("4. Application tables will be in 'warehouse' schema")

    def create_schemas(self, dry_run):
        """Create django and warehouse schemas"""
        with connection.cursor() as cursor:
            if not dry_run:
                cursor.execute("CREATE SCHEMA IF NOT EXISTS django;")
                cursor.execute("CREATE SCHEMA IF NOT EXISTS warehouse;")
                self.stdout.write(self.style.SUCCESS("✓ Created django and warehouse schemas"))
            else:
                self.stdout.write("Would create django and warehouse schemas")

    def move_django_tables(self, dry_run):
        """Move Django framework tables to django schema"""
        # Django framework apps that should be moved to django schema
        django_apps = {
            'admin': ['admin_logentry'],
            'auth': ['auth_group', 'auth_group_permissions', 'auth_permission', 
                    'auth_user', 'auth_user_groups', 'auth_user_user_permissions'],
            'contenttypes': ['django_content_type'],
            'sessions': ['django_session'],
            'django_celery_beat': [
                'django_celery_beat_clockedschedule', 'django_celery_beat_crontabschedule',
                'django_celery_beat_intervalschedule', 'django_celery_beat_periodictask',
                'django_celery_beat_periodictasks', 'django_celery_beat_solarschedule'
            ],
            'explorer': [
                'explorer_query', 'explorer_querylog', 'explorer_queryfavorite',
                'explorer_promptlog', 'explorer_explorervalue', 'explorer_databaseconnection',
                'explorer_tabledescription'
            ]
        }
        
        # Also move Django's migration table
        django_system_tables = [
            'django_migrations',
        ]
        
        all_tables_to_move = []
        
        # Add system tables
        all_tables_to_move.extend(django_system_tables)
        
        # Add app tables
        for app_name, tables in django_apps.items():
            all_tables_to_move.extend(tables)
        
        # Move tables to django schema
        moved_count = 0
        with connection.cursor() as cursor:
            for table_name in all_tables_to_move:
                try:
                    # Check if table exists in warehouse schema
                    cursor.execute("""
                        SELECT EXISTS (
                            SELECT FROM information_schema.tables 
                            WHERE table_schema = 'warehouse' 
                            AND table_name = %s
                        );
                    """, [table_name])
                    
                    table_exists = cursor.fetchone()[0]
                    
                    if table_exists:
                        if not dry_run:
                            # Move table to django schema
                            cursor.execute(f'ALTER TABLE warehouse."{table_name}" SET SCHEMA django;')
                            self.stdout.write(f"✓ Moved {table_name} -> django.{table_name}")
                        else:
                            self.stdout.write(f"Would move {table_name} -> django.{table_name}")
                        moved_count += 1
                    else:
                        # Check if already in django schema
                        cursor.execute("""
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_schema = 'django' 
                                AND table_name = %s
                            );
                        """, [table_name])
                        
                        if cursor.fetchone()[0]:
                            self.stdout.write(f"- Already in django schema: {table_name}")
                        else:
                            self.stdout.write(f"- Table not found: {table_name}")
                        
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f"✗ Error moving {table_name}: {e}")
                    )
        
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(f"✓ Moved {moved_count} tables to django schema")
            )
        else:
            self.stdout.write(f"Would move {moved_count} tables to django schema")

    def configure_search_path(self, dry_run):
        """Configure the search path for the current session"""
        if not dry_run:
            with connection.cursor() as cursor:
                # Set session-level search path (doesn't require database owner privileges)
                cursor.execute("SET search_path TO django, warehouse;")
                self.stdout.write(self.style.SUCCESS("✓ Configured session search path: django, warehouse"))
                self.stdout.write(self.style.WARNING("Note: Search path is set for current session only."))
        else:
            self.stdout.write("Would configure session search path: django, warehouse")
