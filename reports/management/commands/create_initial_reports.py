from django.core.management.base import BaseCommand
from reports.models import ReportCategory, Report

class Command(BaseCommand):
    help = 'Create initial report data'

    def handle(self, *args, **options):
        # Create Data Cleanup category
        category, created = ReportCategory.objects.get_or_create(
            name="Data Cleanup"
        )
        
        if created:
            self.stdout.write(f"Created category: {category.name}")
        else:
            self.stdout.write(f"Category already exists: {category.name}")
        
        # Create Duplicated Genius Prospects report
        report, created = Report.objects.get_or_create(
            title="Duplicated Genius Prospects",
            category=category,
            defaults={
                'description': 'Find and display duplicate prospects in Genius data using fuzzy matching'
            }
        )
        
        if created:
            self.stdout.write(f"Created report: {report.title}")
        else:
            self.stdout.write(f"Report already exists: {report.title}")
            
        self.stdout.write(self.style.SUCCESS('Successfully created initial report data'))
