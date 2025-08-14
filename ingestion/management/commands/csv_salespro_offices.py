"""
Import SalesPro Offices from a CSV file into the database.
Follows CRM sync guideline patterns similar to the users importer.
"""
import csv
import logging
from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from ingestion.models.salespro import SalesPro_Office

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Import SalesPro offices from a CSV file"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", type=str, help="Path to CSV file (e.g., ingestion/csv/salespro_offices.csv)")
        parser.add_argument("--dry-run", action="store_true", help="Parse only; don't write to DB")
        parser.add_argument("--batch-size", type=int, default=1000, help="Bulk create/update batch size")

    def handle(self, *args, **options):
        csv_path = options["csv_path"]
        dry_run = options["dry_run"]
        batch_size = options["batch_size"]

        self.stdout.write(f"Importing SalesPro offices from {csv_path}...")

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
        """Map CSV row to SalesPro_Office fields with safe parsing."""
        def parse_bool(val: str) -> bool:
            return str(val).strip().upper() in ("TRUE", "1", "YES", "Y")

        def parse_dt(val: str) -> Optional[datetime]:
            if not val:
                return None
            s = str(val).strip()
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

        office_id = (row.get("objectId") or "").strip()
        if not office_id:
            return None

        mapped = {
            "office_id": office_id[:50],
            "name": (row.get("name") or None),
            "company_id": (row.get("companyId") or None),
            "company_name": (row.get("company") or None),
            "can_search_all_estimates": parse_bool(row.get("canSearchAllEstimates")),
            "last_edit_user": (row.get("last_edit_user") or None),
            "created_at": parse_dt(row.get("createdAt")),
            "updated_at": parse_dt(row.get("updatedAt")),
            "last_edit_date": parse_dt(row.get("last_edit_date")),
        }

        for field, max_len in {
            "name": 255,
            "company_id": 50,
            "company_name": 255,
            "last_edit_user": 255,
        }.items():
            v = mapped.get(field)
            if v and len(str(v)) > max_len:
                mapped[field] = str(v)[:max_len]

        return mapped

    def _save_batch(self, records: list[dict], dry_run: bool) -> tuple[int, int]:
        if dry_run:
            logger.info(f"Dry run: would save {len(records)} records")
            return 0, 0

        pks = [r["office_id"] for r in records]
        existing = {o.office_id: o for o in SalesPro_Office.objects.filter(office_id__in=pks)}

        to_create = []
        to_update = []
        for r in records:
            pk = r["office_id"]
            obj = existing.get(pk)
            if obj:
                for k, v in r.items():
                    setattr(obj, k, v)
                to_update.append(obj)
            else:
                to_create.append(SalesPro_Office(**r))

        created = 0
        updated = 0
        if to_create:
            SalesPro_Office.objects.bulk_create(to_create, ignore_conflicts=True, batch_size=max(100, len(to_create)))
            created = len(to_create)
        if to_update:
            update_fields = [k for k in records[0].keys() if k != "office_id"]
            SalesPro_Office.objects.bulk_update(to_update, fields=update_fields, batch_size=max(100, len(to_update)))
            updated = len(to_update)

        return created, updated
