"""
Import SalesPro Users from a CSV file into the database.
Follows CRM sync guideline patterns and BaseSalesProSyncCommand-style UX.
"""
import csv
import json
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.models.salespro import SalesPro_User

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import SalesPro users from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file (e.g., ingestion/csv/salespro_users.csv)")
        parser.add_argument("--dry-run", action="store_true", help="Parse only; don't write to DB")
        parser.add_argument("--batch-size", type=int, default=1000, help="Bulk create/update batch size")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        self.stdout.write(f"Importing SalesPro users from {csv_path}...")

        try:
            with open(csv_path, mode="r", encoding="utf-8-sig", newline="") as f:
                reader = csv.DictReader(f)
                records = []
                created = 0
                updated = 0
                total = 0

                for row in reader:
                    total += 1
                    rec = self._map_row(row)
                    if rec:
                        records.append(rec)

                    if len(records) >= batch_size:
                        c, u = self._save_batch(records, dry_run)
                        created += c
                        updated += u
                        records.clear()

                # remaining
                if records:
                    c, u = self._save_batch(records, dry_run)
                    created += c
                    updated += u

                self.stdout.write(self.style.SUCCESS(
                    f"Done. Parsed: {total}, Created: {created}, Updated: {updated}"
                ))
        except FileNotFoundError:
            raise CommandError(f"CSV not found: {csv_path}")
        except Exception as e:
            logger.exception("CSV import failed")
            raise CommandError(str(e))

    def _map_row(self, row: dict) -> Optional[dict]:
        """Map CSV row to SalesPro_User fields with safe parsing."""
        def parse_bool(val: str) -> bool:
            return str(val).strip().upper() in ("TRUE", "1", "YES", "Y")

        def parse_dt(val: str) -> Optional[datetime]:
            if not val:
                return None
            s = str(val).strip()
            # Support both ISO with Z and without
            fmts = [
                "%Y-%m-%dT%H:%M:%S.%fZ",
                "%Y-%m-%dT%H:%M:%S.%f",
                "%Y-%m-%dT%H:%M:%SZ",
                "%Y-%m-%dT%H:%M:%S",
            ]
            for fmt in fmts:
                try:
                    dt = datetime.strptime(s, fmt)
                    if dt.tzinfo is None:
                        return timezone.make_aware(dt)
                    return dt
                except ValueError:
                    continue
            return None

        def parse_json(val: str) -> Optional[str]:
            if not val:
                return None
            try:
                parsed = json.loads(val)
                return json.dumps(parsed)
            except Exception:
                # store raw text to avoid data loss
                return str(val)

        # Primary key
        user_object_id = (row.get("objectId") or "").strip()
        if not user_object_id:
            return None

        # Normalize username/email and apply fallback when email is missing
        username_val = (row.get("username") or "").strip()
        email_val = (row.get("email") or "").strip()
        if not email_val and username_val and "@" in username_val:
            email_val = username_val

        mapped = {
            "user_object_id": user_object_id[:50],
            "username": (username_val or None),
            "first_name": (row.get("nameFirst") or None),
            "last_name": (row.get("nameLast") or None),
            "email": (email_val or None),
            "phone_number": (row.get("phoneNumber") or None),

            "is_active": parse_bool(row.get("isActive")),
            "is_manager": parse_bool(row.get("isManager")),
            "is_available_to_call": parse_bool(row.get("isAvailableToCall")),

            "can_activate_users": parse_bool(row.get("canActivateUsers")),
            "can_change_settings": parse_bool(row.get("canChangeSettings")),
            "can_submit_credit_apps": parse_bool(row.get("canSubmitCreditApps")),
            "disable_change_company": parse_bool(row.get("disableChangeCompany")),

            "company_id": (row.get("company") or None),
            "selected_office": (row.get("selectedOffice") or None),
            "allowed_offices": parse_json(row.get("allowedOffices")),

            "identifier": (row.get("identifier") or None),
            "license_number": (row.get("licenseNumber") or None),

            "created_at": parse_dt(row.get("createdAt")),
            "updated_at": parse_dt(row.get("updatedAt")),
            "last_login_date": parse_dt(row.get("lastLoginDate")),
            "deactivated_date": parse_dt(row.get("deactivatedDate")),
        }

        # Trim oversize fields to model max_length
        for field, max_len in {
            "username": 255,
            "first_name": 100,
            "last_name": 100,
            "email": 254,
            "phone_number": 50,
            "company_id": 50,
            "selected_office": 50,
            "identifier": 255,
            "license_number": 100,
        }.items():
            v = mapped.get(field)
            if v and len(str(v)) > max_len:
                mapped[field] = str(v)[:max_len]

        return mapped

    def _save_batch(self, records: list[dict], dry_run: bool) -> tuple[int, int]:
        if dry_run:
            logger.info(f"Dry run: would save {len(records)} records")
            return 0, 0

        # Split into creates and updates
        pks = [r["user_object_id"] for r in records]
        existing = {u.user_object_id: u for u in SalesPro_User.objects.filter(user_object_id__in=pks)}

        to_create = []
        to_update = []
        for r in records:
            pk = r["user_object_id"]
            obj = existing.get(pk)
            if obj:
                # update fields
                for k, v in r.items():
                    setattr(obj, k, v)
                to_update.append(obj)
            else:
                to_create.append(SalesPro_User(**r))

        created = 0
        updated = 0
        if to_create:
            SalesPro_User.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=max(100, len(to_create)))
            created = len(to_create)
        if to_update:
            # Exclude PK from update fields
            update_fields = [k for k in records[0].keys() if k != "user_object_id"]
            SalesPro_User.objects.bulk_update(to_update, fields=update_fields, batch_size=max(100, len(to_update)))
            updated = len(to_update)

        return created, updated
