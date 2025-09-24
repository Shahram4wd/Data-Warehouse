from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings

from ingestion.models.common import SyncHistory


class Command(BaseCommand):
    help = "Mark 'running' SyncHistory records older than the configured threshold as failed (stale cleanup)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--minutes",
            type=int,
            default=None,
            help="Override the staleness threshold in minutes (defaults to WORKER_POOL_STALE_MINUTES).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not write changes; only print what would be updated.",
        )

    def handle(self, *args, **options):
        minutes = options.get("minutes")
        dry_run = options.get("dry_run")

        threshold_minutes = (
            minutes if minutes is not None else getattr(settings, "WORKER_POOL_STALE_MINUTES", 30)
        )

        now = timezone.now()
        cutoff = now - timezone.timedelta(minutes=threshold_minutes)

        qs = SyncHistory.objects.filter(status="running", start_time__lt=cutoff)
        count = qs.count()

        if count == 0:
            self.stdout.write(self.style.SUCCESS("No stale running syncs found."))
            return

        self.stdout.write(
            f"Found {count} running sync(s) older than {threshold_minutes} minutes (before {cutoff.isoformat()})."
        )

        if dry_run:
            # Print a small sample for visibility
            sample = qs.order_by("-start_time").values("id", "crm_source", "sync_type", "start_time")[:20]
            for s in sample:
                self.stdout.write(
                    f"Would mark FAILED: id={s['id']} {s['crm_source']}.{s['sync_type']} started={s['start_time']}"
                )
            if count > 20:
                self.stdout.write(f"... and {count-20} more")
            self.stdout.write(self.style.WARNING("Dry run complete; no changes made."))
            return

        updated = 0
        for sh in qs.iterator(chunk_size=500):
            sh.status = "failed"
            sh.end_time = now
            msg = sh.error_message or ""
            suffix = " (auto-marked failed by cleanup_stale_syncs; no heartbeat for too long)"
            # Keep message concise
            sh.error_message = (msg + suffix) if suffix not in msg else msg
            sh.save(update_fields=["status", "end_time", "error_message"])
            updated += 1

        self.stdout.write(self.style.SUCCESS(f"Marked {updated} stale running sync(s) as failed."))
