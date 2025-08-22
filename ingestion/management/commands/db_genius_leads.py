import os
from django.core.management.base import BaseCommand
from django.db import connections
from ingestion.utils import get_mysql_connection
from tqdm import tqdm
from psycopg2.extras import execute_values  # type: ignore  # for fast bulk upsert
from django.db import transaction  # type: ignore

BATCH_SIZE = int(os.getenv("BATCH_SIZE", 2000))
MYSQL_FETCH_SIZE = int(os.getenv("MYSQL_FETCH_SIZE", 5000))

class Command(BaseCommand):
    help = "Download leads directly from the database and upsert into local Genius_Lead."

    def add_arguments(self, parser):
        parser.add_argument("--table", type=str, default="lead")
        parser.add_argument("--limit", type=int, default=None)
        parser.add_argument("--added_on_after", type=str, default=None, help="Filter records with added_on after the given date (YYYY-MM-DD)")

    def handle(self, *args, **options):
        table_name = options["table"]
        limit = options["limit"]
        added_on_after = options["added_on_after"]

        conn = get_mysql_connection()
        src_cursor = conn.cursor()
        try:
            # Build the base query
            base_query = f"SELECT COUNT(*) FROM `{table_name}`"
            if added_on_after:
                base_query += f" WHERE added_on > '{added_on_after}'"

            # Get total
            src_cursor.execute(base_query)
            total = src_cursor.fetchone()[0]
            if limit:
                total = min(total, limit)

            self.stdout.write(f"Processing {total:,} rows from `{table_name}`…")
            processed = 0
            with tqdm(total=total, unit="rows") as pbar:
                while processed < total:
                    chunk = min(MYSQL_FETCH_SIZE, total - processed)
                    query = f"""
                        SELECT 
                          lead_id, contact, division,
                          first_name, last_name, address1, address2, city, state, zip,
                          cdyne_county, is_valid_address, email, phone1, type1, phone2, type2,
                          phone3, type3, phone4, type4, source, source_notes, sourced_on,
                          job_type, rating, year_built, is_year_built_verified, is_zillow, 
                          is_express_consent, express_consent_set_by, express_consent_set_on,
                          express_consent_source, express_consent_upload_file_id,
                          is_express_consent_being_reviewed, express_consent_being_reviewed_by,
                          notes, status, substatus, substatus_reason, alternate_id, added_by,
                          added_on, viewed_on, is_estimate_set, estimate_set_by, estimate_set_on,
                          dead_on, dead_by, dead_note, is_credit_request, credit_request_by,
                          credit_request_on, credit_request_reason, credit_request_status,
                          credit_request_update_on, credit_request_update_by, credit_request_note,
                          lead_cost, import_source, call_screen_viewed_on, call_screen_viewed_by,
                          copied_to_id, copied_to_on, copied_from_id, copied_from_on,
                          cwp_client, cwp_referral, rc_paid_to, rc_paid_on, with_dm,
                          voicemail_file, agent_id, agent_name, invalid_address,
                          is_valid_email, is_high_potential, is_mobile_lead, is_dnc, is_dummy,
                          lead_central_estimate_date, do_not_call_before, is_estimate_confirmed,
                          estimate_confirmed_by, estimate_confirmed_on,
                          added_by_latitude, added_by_longitude, is_carpentry_followup,
                          carpentry_followup_notes, marketing_source, prospect_id,
                          added_by_supervisor, salesrabbit_lead_id, third_party_source_id
                        FROM `{table_name}`
                    """
                    if added_on_after:
                        query += f" WHERE added_on > '{added_on_after}'"
                    query += f" ORDER BY lead_id LIMIT {chunk} OFFSET {processed}"

                    src_cursor.execute(query)
                    rows = src_cursor.fetchall()
                    if not rows:
                        break

                    self._upsert_chunk(rows)
                    processed += len(rows)
                    pbar.update(len(rows))

            self.stdout.write(self.style.SUCCESS("Done!"))
        finally:
            src_cursor.close()
            conn.close()

    def _upsert_chunk(self, rows):
        # These must match the SELECT above **in order**:
        cols = [
          "lead_id","contact","division","first_name","last_name","address1","address2","city","state","zip",
          "cdyne_county","is_valid_address","email","phone1","type1","phone2","type2","phone3","type3","phone4","type4",
          "source","source_notes","sourced_on","job_type","rating","year_built","is_year_built_verified","is_zillow",
          "is_express_consent","express_consent_set_by","express_consent_set_on","express_consent_source",
          "express_consent_upload_file_id","is_express_consent_being_reviewed","express_consent_being_reviewed_by",
          "notes","status","substatus","substatus_reason","alternate_id","added_by","added_on","viewed_on",
          "is_estimate_set","estimate_set_by","estimate_set_on","dead_on","dead_by","dead_note","is_credit_request",
          "credit_request_by","credit_request_on","credit_request_reason","credit_request_status",
          "credit_request_update_on","credit_request_update_by","credit_request_note","lead_cost","import_source",
          "call_screen_viewed_on","call_screen_viewed_by","copied_to_id","copied_to_on","copied_from_id","copied_from_on",
          "cwp_client","cwp_referral","rc_paid_to","rc_paid_on","with_dm","voicemail_file","agent_id","agent_name",
          "invalid_address","is_valid_email","is_high_potential","is_mobile_lead","is_dnc","is_dummy",
          "lead_central_estimate_date","do_not_call_before","is_estimate_confirmed","estimate_confirmed_by",
          "estimate_confirmed_on","added_by_latitude","added_by_longitude","is_carpentry_followup","carpentry_followup_notes",
          "marketing_source","prospect_id","added_by_supervisor","salesrabbit_lead_id","third_party_source_id",
          "updated_at","sync_created_at","sync_updated_at"  # Add required timestamp fields
        ]
        
        # Add current timestamp to each row for the new fields
        from django.utils import timezone
        current_time = timezone.now()
        rows_with_timestamps = []
        for row in rows:
            # Convert row tuple to list and add timestamp fields
            row_list = list(row)
            row_list.extend([current_time, current_time, current_time])  # updated_at, sync_created_at, sync_updated_at
            rows_with_timestamps.append(tuple(row_list))
        
        placeholders = ",".join(["%s"] * len(cols))
        # Use Postgres ON CONFLICT syntax for upsert
        update_clause = ",".join(f"{c}=EXCLUDED.{c}" for c in cols if c!="lead_id")

        # Use execute_values for faster bulk upsert
        sql = f"""
            INSERT INTO genius_lead ({','.join(cols)})
            VALUES %s
            ON CONFLICT (lead_id) DO UPDATE SET {update_clause}
        """
        values_template = f"({','.join(['%s'] * len(cols))})"
        # Perform upsert inside a transaction for speed
        with transaction.atomic(), connections['default'].cursor() as dest:
            # Use actual chunk size for page_size
            execute_values(dest, sql, rows_with_timestamps, template=values_template, page_size=len(rows_with_timestamps))
