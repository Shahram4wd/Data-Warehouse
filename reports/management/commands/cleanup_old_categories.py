from django.core.management.base import BaseCommand
from reports.models import ReportCategory, Report

class Command(BaseCommand):
    help = 'Clean up old report categories and migrate reports to new categories'

    def handle(self, *args, **options):
        # Find and remove the old "Data Cleanup" category
        try:
            old_category = ReportCategory.objects.get(name="Data Cleanup")
            
            # Get the Data Quality category (should exist from create_initial_reports)
            data_quality_category, created = ReportCategory.objects.get_or_create(
                name="Data Quality"
            )
            
            if created:
                self.stdout.write(f"Created Data Quality category")
            
            # Move any reports from Data Cleanup to Data Quality
            reports_moved = 0
            for report in old_category.reports.all():
                report.category = data_quality_category
                report.save()
                reports_moved += 1
                self.stdout.write(f"Moved report '{report.title}' to Data Quality category")
            
            # Delete the old category
            old_category.delete()
            self.stdout.write(f"Deleted old 'Data Cleanup' category")
            self.stdout.write(f"Total reports moved: {reports_moved}")
            
        except ReportCategory.DoesNotExist:
            self.stdout.write("No 'Data Cleanup' category found to remove")
        
        self.stdout.write(self.style.SUCCESS('Category cleanup completed successfully'))
