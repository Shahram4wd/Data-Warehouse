"""
Engine for batch syncing zip codes into HubSpot_ZipCode model
Follows import_refactoring.md enterprise architecture standards
"""

from django.db import transaction
from ingestion.models.hubspot import Hubspot_ZipCode

try:
    from tqdm import tqdm
    TQDM_AVAILABLE = True
except ImportError:
    TQDM_AVAILABLE = False

class HubSpotZipCodeSyncEngine:
    def __init__(self, batch_size=500):
        self.batch_size = batch_size

    def sync_zipcodes(self, records, dry_run=False, show_progress=False, stdout=None):
        from django.db.models import Q
        created, updated = 0, 0
        total = len(records)
        use_progress = show_progress and TQDM_AVAILABLE and not dry_run
        bar = tqdm(total=total, desc="Syncing zip codes", unit="zip") if use_progress else None
        processed = 0
        for i in range(0, total, self.batch_size):
            batch = records[i:i+self.batch_size]
            zipcodes = [row.get('zipcode') or row.get('zip') for row in batch if row.get('zipcode') or row.get('zip')]
            if not zipcodes:
                if bar:
                    bar.update(len(batch))
                continue
            if not dry_run:
                with transaction.atomic():
                    # Fetch existing zipcodes in batch
                    existing_objs = Hubspot_ZipCode.objects.filter(zipcode__in=zipcodes)
                    existing_map = {obj.zipcode: obj for obj in existing_objs}
                    to_create = []
                    to_update = []
                    for row in batch:
                        zipcode = row.get('zipcode') or row.get('zip')
                        if not zipcode:
                            if bar:
                                bar.update(1)
                            continue
                        data = {
                            'division': row.get('division'),
                            'city': row.get('city'),
                            'county': row.get('county'),
                            'state': row.get('state'),
                            'archived': False
                        }
                        if zipcode in existing_map:
                            obj = existing_map[zipcode]
                            for k, v in data.items():
                                setattr(obj, k, v)
                            to_update.append(obj)
                            updated += 1
                        else:
                            obj = Hubspot_ZipCode(zipcode=zipcode, **data)
                            to_create.append(obj)
                            created += 1
                        if bar:
                            bar.update(1)
                        processed += 1
                    if to_create:
                        Hubspot_ZipCode.objects.bulk_create(to_create, batch_size=self.batch_size)
                    if to_update:
                        Hubspot_ZipCode.objects.bulk_update(
                            to_update,
                            fields=['division', 'city', 'county', 'state', 'archived'],
                            batch_size=self.batch_size
                        )
            else:
                # Just count what would be done
                for row in batch:
                    zipcode = row.get('zipcode') or row.get('zip')
                    if zipcode:
                        created += 1  # Assume all would be new in dry run
                    if bar:
                        bar.update(1)
                    processed += 1
            if not bar and show_progress and not dry_run and stdout:
                stdout.write(f"Processed {min(i+self.batch_size, total)}/{total} zip codes...")
        if bar:
            bar.close()
        return created, updated
