from datetime import datetime
from django.db import transaction

def parse_datetime_obj(value):
    """Convert common date/datetime formats to datetime objects.
       Returns None if parsing fails or input is empty.
       Assumes parsed datetime is naive UTC.
    """
    if not value or not str(value).strip():
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%m/%d/%Y %H:%M:%S", "%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"):
        try:
            return datetime.strptime(value.strip(), fmt)
        except ValueError:
            continue
    return None

def process_batches(to_create, to_update, model_class, update_fields, batch_size):
    """Process batches for bulk_create and bulk_update."""
    if to_update:
        with transaction.atomic():
            model_class.objects.bulk_update(to_update, update_fields)
        to_update.clear()

    if to_create:
        with transaction.atomic():
            model_class.objects.bulk_create(to_create, ignore_conflicts=True)
        to_create.clear()

def prepare_data(row, field_mapping, required_fields):
    """Prepare data for model creation or update from a CSV row."""
    data = {}
    for csv_field, model_field in field_mapping.items():
        value = row.get(csv_field)
        if csv_field in required_fields and not value:
            return None  # Skip rows with missing required fields
        data[model_field] = value
    return data
