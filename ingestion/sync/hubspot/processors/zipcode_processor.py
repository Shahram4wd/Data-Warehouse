"""
Processor for parsing and validating zip code CSV for HubSpot integration
Follows import_refactoring.md enterprise architecture standards
"""
import csv

class HubSpotZipCodeProcessor:
    def parse_csv(self, csv_content):
        reader = csv.DictReader(csv_content.splitlines())
        records = list(reader)
        return records

    def validate_record(self, record):
        # Basic validation: must have zipcode
        return bool(record.get('zipcode') or record.get('zip'))

    def filter_valid(self, records):
        return [r for r in records if self.validate_record(r)]
