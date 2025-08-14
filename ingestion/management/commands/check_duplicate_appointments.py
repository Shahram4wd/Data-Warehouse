"""
Management command to check for duplicate appointments in the database
"""
from django.core.management.base import BaseCommand
from django.db.models import Count
from ingestion.models.hubspot import Hubspot_Appointment


class Command(BaseCommand):
    help = "Check for duplicate appointments in the database and optionally clean them up"

    def add_arguments(self, parser):
        parser.add_argument(
            "--delete-duplicates",
            action="store_true",
            help="Delete duplicate appointments, keeping the most recent"
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be deleted without actually deleting"
        )

    def handle(self, *args, **options):
        self.stdout.write("Checking for duplicate appointments...")
        
        # Find appointments with duplicate IDs
        duplicates = (
            Hubspot_Appointment.objects
            .values('id')
            .annotate(count=Count('id'))
            .filter(count__gt=1)
        )
        
        total_duplicates = duplicates.count()
        
        if total_duplicates == 0:
            self.stdout.write(self.style.SUCCESS("No duplicate appointments found!"))
            return
        
        self.stdout.write(
            self.style.WARNING(f"Found {total_duplicates} appointment IDs with duplicates")
        )
        
        total_extra_records = 0
        for duplicate in duplicates:
            appointment_id = duplicate['id']
            count = duplicate['count']
            total_extra_records += count - 1
            
            self.stdout.write(f"  Appointment ID {appointment_id}: {count} records")
            
            if options['delete_duplicates']:
                # Keep the most recent record (by created_at or hs_lastmodifieddate)
                appointments = Hubspot_Appointment.objects.filter(id=appointment_id).order_by(
                    '-hs_lastmodifieddate', '-hs_createdate'
                )
                
                to_delete = appointments[1:]  # Keep the first (most recent), delete the rest
                
                if options['dry_run']:
                    self.stdout.write(f"    Would delete {len(to_delete)} duplicate records")
                else:
                    deleted_count = len(to_delete)
                    for appointment in to_delete:
                        appointment.delete()
                    self.stdout.write(f"    Deleted {deleted_count} duplicate records")
        
        if options['delete_duplicates'] and not options['dry_run']:
            self.stdout.write(
                self.style.SUCCESS(f"Cleanup completed. Removed {total_extra_records} duplicate records.")
            )
        elif options['dry_run']:
            self.stdout.write(
                self.style.WARNING(f"Dry run completed. Would remove {total_extra_records} duplicate records.")
            )
        else:
            self.stdout.write(
                f"Total extra records to remove: {total_extra_records}"
            )
            self.stdout.write("Use --delete-duplicates to remove duplicates")
            self.stdout.write("Use --dry-run to see what would be deleted")
