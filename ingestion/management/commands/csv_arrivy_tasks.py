import csv
import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
from ingestion.models.arrivy import ArrivyTask

class Command(BaseCommand):
    help = 'Import Arrivy tasks from a CSV file into the database.'

    def add_arguments(self, parser):
        parser.add_argument('csv_file', type=str, help='Path to the CSV file to import.')

    def handle(self, *args, **kwargs):
        csv_file = kwargs['csv_file']

        def parse_date(date_str):
            try:
                return datetime.datetime.strptime(date_str, '%m/%d/%Y').date()
            except (ValueError, TypeError):
                return None

        def parse_time(time_str):
            try:
                return datetime.datetime.strptime(time_str, '%I:%M:%S %p').time()
            except (ValueError, TypeError):
                return None

        def parse_datetime(datetime_str):
            try:
                naive_datetime = datetime.datetime.strptime(datetime_str, '%m/%d/%Y %I:%M:%S %p')
                return timezone.make_aware(naive_datetime)
            except (ValueError, TypeError):
                return None

        try:
            total_rows = sum(1 for _ in open(csv_file, mode='r', encoding='utf-8')) - 1  # Exclude header row
            processed_rows = 0
            batch_size = 10000  # Process rows in batches of 500
            batch = []

            with open(csv_file, mode='r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row_number, row in enumerate(reader, start=1):
                    try:
                        task_title = row['Task Title'].replace('Booking - ', '')
                        first_name, last_name = task_title.split(' ', 1) if ' ' in task_title else (task_title, '')

                        batch.append(ArrivyTask(
                            task_id=row['Task ID'],
                            task_title=row['Task Title'],
                            template=row.get('Template', ''),
                            group=row.get('Group', ''),
                            status=row.get('Status', ''),
                            timezone=row.get('Timezone', ''),
                            instructions=row.get('Instructions (task-details)', ''),
                            forms=row.get('Forms', ''),
                            external_id=row.get('External ID', ''),
                            created_by=row.get('Created by (company or team member)', ''),
                            created_on=parse_datetime(row.get('Created on', None)),
                            scheduled_by=row.get('Scheduled by', ''),
                            rescheduled_count=int(row.get('Rescheduled (count)', 0)),
                            crew_assigned_by=row.get('Crew Assigned by', ''),
                            booking_id=row.get('Booking ID', ''),
                            booking_name=row.get('Booking Name', ''),
                            route_name=row.get('Route Name', ''),
                            assignees=row.get('Assignees', ''),
                            resources=row.get('Resources', ''),
                            resource_template=row.get('Resource Template', ''),
                            employee_ids=row.get('Employee IDs', ''),
                            customer_id=row.get('Customer ID', ''),
                            first_name=row.get('First Name', ''),
                            last_name=row.get('Last Name', ''),
                            company=row.get('Company', ''),
                            email=row.get('Email', ''),
                            mobile_number=row.get('Mobile Number', ''),
                            address=row.get('Address', ''),
                            city=row.get('City', ''),
                            state=row.get('State', ''),
                            zipcode=row.get('Zipcode', ''),
                            country=row.get('Country', ''),
                            latitude=float(row['Latitude']) if row.get('Latitude') else None,
                            longitude=float(row['Longitude']) if row.get('Longitude') else None,
                            start_date=parse_date(row.get('Start Date', None)),
                            start_time=parse_time(row.get('Start Time', None)),
                            end_date=parse_date(row.get('End Date', None)),
                            end_time=parse_time(row.get('End Time', None)),
                            start_timezone=row.get('Start Timezone', ''),
                            end_timezone=row.get('End Timezone', ''),
                            duration=row.get('Duration', ''),
                            unscheduled=row.get('Unscheduled', '').lower() == 'true',
                            expected_start_date=parse_date(row.get('Expected Start Date', None)),
                            expected_end_date=parse_date(row.get('Expected End Date', None)),
                            actual_start_time=parse_datetime(row.get('Actual Start Time', None)),
                            actual_end_time=parse_datetime(row.get('Actual End Time', None)),
                            travel_time=row.get('Travel Time', ''),
                            wait_time=row.get('Wait Time', ''),
                            task_time=row.get('Task Time', ''),
                            total_time=row.get('Total Time', ''),
                            mileage=float(row['Mileage (in miles)']) if row.get('Mileage (in miles)') else None,
                            rating=float(row['Rating']) if row.get('Rating') else None,
                            rating_text=row.get('Rating Text', ''),
                            outbound_sms_count=int(row.get('Outbound SMS (count)', 0)),
                            inbound_sms_count=int(row.get('Inbound SMS (count)', 0)),
                            outbound_email_count=int(row.get('Outbound Email (count)', 0)),
                            inbound_email_count=int(row.get('Inbound Email (count)', 0)),
                            template_extra_field_product_interest_primary=row.get('Template Extra Field Product Interest Primary', ''),
                            template_extra_field_product_interest_secondary=row.get('Template Extra Field Product Interest Secondary', ''),
                            template_extra_field_primary_source=row.get('Template Extra Field Primary Source', ''),
                            template_extra_field_secondary_source=row.get('Template Extra Field Secondary Source', ''),
                            complete=row.get('Complete', '').lower() == 'true',
                            cancel=row.get('Cancel', '').lower() == 'true',
                            custom_cancel_test=row.get('Custom Cancel Test', '').lower() == 'true',
                            appointment_confirmed=row.get('Appointment Confirmed', '').lower() == 'true',
                            demo_sold=row.get('Demo Sold', '').lower() == 'true',
                            on_our_way=row.get('On our way', '').lower() == 'true',
                            start=row.get('Start', '').lower() == 'true',
                            exception=row.get('Exception', '').lower() == 'true',
                            customer_extra_fields=row.get('Customer Extra Fields', ''),
                            task_extra_fields=row.get('Task Extra Fields', ''),
                            resource_template_extra_field=row.get('Resource Template Extra Field', ''),
                            resource_extra_field=row.get('Resource Extra Field', ''),
                        ))

                        if len(batch) >= batch_size:
                            ArrivyTask.objects.bulk_create(batch, ignore_conflicts=True)
                            processed_rows += len(batch)
                            batch.clear()
                            self.stdout.write(f"Processed {processed_rows}/{total_rows} rows...")

                    except Exception as row_error:
                        self.stderr.write(self.style.ERROR(f"Error processing row {row_number}: {row_error}"))
                        self.stderr.write(self.style.ERROR(f"Row data: {row}"))

                # Process remaining rows in the batch
                if batch:
                    try:
                        ArrivyTask.objects.bulk_create(batch, ignore_conflicts=True)
                        processed_rows += len(batch)
                        self.stdout.write(f"Processed {processed_rows}/{total_rows} rows...")
                    except Exception as batch_error:
                        self.stderr.write(self.style.ERROR(f"Error processing final batch: {batch_error}"))
                        self.stderr.write(self.style.ERROR(f"Batch data: {batch}"))

            self.stdout.write(self.style.SUCCESS(f"Successfully imported {processed_rows} tasks from CSV."))

        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f'File not found: {csv_file}'))
        except Exception as e:
            self.stderr.write(self.style.ERROR(f'An error occurred: {e}'))
