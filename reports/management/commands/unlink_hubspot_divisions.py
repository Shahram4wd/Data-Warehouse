from django.core.management.base import BaseCommand
from django.db import connection
from django.utils import timezone
from reports.models import ReportCategory, Report
import json
import csv
import os

class Command(BaseCommand):
    help = 'Generate report of HubSpot contacts linked to multiple divisions'

    def add_arguments(self, parser):
        parser.add_argument(
            '--output-format',
            choices=['csv', 'json'],
            default='json',
            help='Output format for the report (default: json)'
        )
        parser.add_argument(
            '--output-file',
            type=str,
            help='Output file path (optional)'
        )

    def handle(self, *args, **options):
        output_format = options['output_format']
        output_file = options['output_file']
        
        self.stdout.write("Generating HubSpot contacts with multiple divisions report...")
        
        # SQL query to find contacts with multiple divisions
        query = """
        SELECT 
            hc.id as contact_id,
            hc.hubspot_id as hubspot_contact_id,
            hc.first_name,
            hc.last_name,
            hc.email,
            COUNT(DISTINCT hd.id) as division_count,
            STRING_AGG(DISTINCT hd.name, ', ') as division_names,
            STRING_AGG(DISTINCT CAST(hd.id AS TEXT), ', ') as division_ids
        FROM ingestion_hubspotcontact hc
        INNER JOIN ingestion_hubspotcontactdivisionassociation hcda ON hc.id = hcda.contact_id
        INNER JOIN ingestion_hubspotdivision hd ON hcda.division_id = hd.id
        GROUP BY hc.id, hc.hubspot_id, hc.first_name, hc.last_name, hc.email
        HAVING COUNT(DISTINCT hd.id) > 1
        ORDER BY division_count DESC, hc.last_name, hc.first_name;
        """
        
        with connection.cursor() as cursor:
            cursor.execute(query)
            columns = [col[0] for col in cursor.description]
            results = [dict(zip(columns, row)) for row in cursor.fetchall()]
        
        total_contacts = len(results)
        self.stdout.write(f"Found {total_contacts} contacts linked to multiple divisions")
        
        if total_contacts == 0:
            self.stdout.write("No contacts found with multiple divisions.")
            return
        
        # Generate report data
        report_data = {
            'report_title': 'HubSpot Contacts with Multiple Divisions',
            'generated_at': timezone.now().isoformat(),
            'total_contacts': total_contacts,
            'contacts': results
        }
        
        # Output results
        if output_format == 'json':
            if output_file:
                with open(output_file, 'w') as f:
                    json.dump(report_data, f, indent=2, default=str)
                self.stdout.write(f"Report saved to {output_file}")
            else:
                self.stdout.write(json.dumps(report_data, indent=2, default=str))
        
        elif output_format == 'csv':
            fieldnames = ['contact_id', 'hubspot_contact_id', 'first_name', 'last_name', 
                         'email', 'division_count', 'division_names', 'division_ids']
            
            if output_file:
                with open(output_file, 'w', newline='') as csvfile:
                    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                    writer.writeheader()
                    for contact in results:
                        writer.writerow(contact)
                self.stdout.write(f"CSV report saved to {output_file}")
            else:
                # Print CSV to stdout
                import io
                output = io.StringIO()
                writer = csv.DictWriter(output, fieldnames=fieldnames)
                writer.writeheader()
                for contact in results:
                    writer.writerow(contact)
                self.stdout.write(output.getvalue())
        
        # Summary statistics
        division_count_stats = {}
        for contact in results:
            count = contact['division_count']
            division_count_stats[count] = division_count_stats.get(count, 0) + 1
        
        self.stdout.write("\nSummary:")
        for count, num_contacts in sorted(division_count_stats.items()):
            self.stdout.write(f"  {num_contacts} contacts linked to {count} divisions")
        
        self.stdout.write(self.style.SUCCESS('Report generation completed'))
