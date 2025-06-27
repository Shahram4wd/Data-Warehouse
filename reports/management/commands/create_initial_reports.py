from django.core.management.base import BaseCommand
from reports.models import ReportCategory, Report

class Command(BaseCommand):
    help = 'Create initial report data'

    def handle(self, *args, **options):
        # Remove old "Data Cleanup" category if it exists and has no reports
        try:
            old_category = ReportCategory.objects.get(name="Data Cleanup")
            if old_category.reports.count() == 0:
                old_category.delete()
                self.stdout.write(f"Removed empty category: Data Cleanup")
            else:
                # Move reports to Data Quality category first
                self.stdout.write(f"Found {old_category.reports.count()} reports in Data Cleanup category, will migrate them")
        except ReportCategory.DoesNotExist:
            pass
        
        # Create Data Quality category
        category, created = ReportCategory.objects.get_or_create(
            name="Data Quality"
        )
        
        if created:
            self.stdout.write(f"Created category: {category.name}")
        else:
            self.stdout.write(f"Category already exists: {category.name}")
        
        # Create Duplicated Genius Prospects report
        genius_report, created = Report.objects.get_or_create(
            title="Duplicated Genius Prospects",
            defaults={
                'category': category,
                'description': 'Find and display duplicate prospects in Genius data using fuzzy matching'
            }
        )
        
        # Update category if report exists but has different category
        if not created and genius_report.category.name != "Data Quality":
            genius_report.category = category
            genius_report.save()
            self.stdout.write(f"Updated category for report: {genius_report.title}")
        
        if created:
            self.stdout.write(f"Created report: {genius_report.title}")
        else:
            self.stdout.write(f"Report already exists: {genius_report.title}")
        
        # Create Duplicated HubSpot Appointments report
        hubspot_report, created = Report.objects.get_or_create(
            title="Duplicated HubSpot Appointments",
            defaults={
                'category': category,
                'description': 'Find and display duplicate HubSpot appointments using exact matching'
            }
        )
        
        # Update category if report exists but has different category
        if not created and hubspot_report.category.name != "Data Quality":
            hubspot_report.category = category
            hubspot_report.save()
            self.stdout.write(f"Updated category for report: {hubspot_report.title}")
        
        if created:
            self.stdout.write(f"Created report: {hubspot_report.title}")
        else:
            self.stdout.write(f"Report already exists: {hubspot_report.title}")
        
        # Clean up old "Data Cleanup" category if it still exists and is now empty
        try:
            old_category = ReportCategory.objects.get(name="Data Cleanup")
            if old_category.reports.count() == 0:
                old_category.delete()
                self.stdout.write(f"Removed empty category: Data Cleanup")
        except ReportCategory.DoesNotExist:
            pass
            
        self.stdout.write(self.style.SUCCESS('Successfully created initial report data'))
