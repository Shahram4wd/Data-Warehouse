"""
Processor for HubSpot Genius Users sync
Follows import_refactoring.md enterprise architecture standards
"""
from .base import HubSpotBaseProcessor

class HubSpotGeniusUsersProcessor(HubSpotBaseProcessor):
    def __init__(self):
        from ingestion.models.hubspot import Hubspot_GeniusUser
        super().__init__(Hubspot_GeniusUser)

    def get_field_mappings(self):
        # Map API fields to model fields (only those that exist in the model)
        return {
            "id": "id",
            "hs_object_id": "hs_object_id",
            "hs_createdate": "hs_createdate",
            "hs_lastmodifieddate": "hs_lastmodifieddate",
            "createdAt": "createdAt",
            "updatedAt": "updatedAt",
            "archived": "archived",
            "arrivy_user_id": "arrivy_user_id",
            "division": "division",
            "division_id": "division_id",
            "email": "email",
            "job_title": "job_title",
            "name": "name",
            "title_id": "title_id",
            "user_account_type": "user_account_type",
            "user_id": "user_id",
            "user_status_inactive": "user_status_inactive",
        }

    def transform_record(self, user_data):
        # Only include fields that exist in the model
        from django.utils.dateparse import parse_datetime
        from django.utils.timezone import make_aware, utc
        import datetime
        props = user_data.get("properties", {})

        def parse_utc(dt_str):
            if not dt_str:
                return None
            dt = parse_datetime(dt_str)
            if dt is None:
                # Try parsing as milliseconds since epoch (HubSpot sometimes sends this)
                try:
                    ms = int(dt_str)
                    dt = datetime.datetime.utcfromtimestamp(ms / 1000.0)
                    dt = dt.replace(tzinfo=datetime.timezone.utc)
                except Exception:
                    return None
            if dt.tzinfo is None:
                dt = make_aware(dt, timezone=utc)
            return dt.astimezone(datetime.timezone.utc)

        record = {
            "id": user_data.get("id"),
            "hs_object_id": props.get("hs_object_id"),
            "hs_createdate": parse_utc(props.get("hs_createdate")),
            "hs_lastmodifieddate": parse_utc(props.get("hs_lastmodifieddate")),
            "createdAt": parse_utc(props.get("createdAt")),
            "updatedAt": parse_utc(props.get("updatedAt")),
            "archived": user_data.get("archived", False),
            "arrivy_user_id": props.get("arrivy_user_id"),
            "division": props.get("division"),
            "division_id": props.get("division_id"),
            "email": props.get("email"),
            "job_title": props.get("job_title"),
            "name": props.get("name"),
            "title_id": props.get("title_id"),
            "user_account_type": props.get("user_account_type"),
            "user_id": props.get("user_id"),
            "user_status_inactive": props.get("user_status_inactive"),
        }
        # Remove any keys with value None (optional, but keeps upserts clean)
        return {k: v for k, v in record.items() if v is not None}

    def validate_record(self, record):
        # Add validation logic as needed, or just return the record
        return record

    def process(self, user_data):
        # For compatibility with previous usage
        return self.validate_record(self.transform_record(user_data))
