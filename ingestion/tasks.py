from celery import shared_task
from ingestion.genius.division_sync import sync_divisions

@shared_task
def sync_divisions_task():
    sync_divisions()