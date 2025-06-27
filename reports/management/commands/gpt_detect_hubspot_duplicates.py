import json
import os
import re
import sys
import django
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.models.genius import Genius_Prospect
from collections import defaultdict
from rapidfuzz.distance import Levenshtein
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import cpu_count

# Normalize helpers
def normalize_phone(phone):
    return re.sub(r'\D', '', phone or '')

def normalize_text(value):
    return (value or '').lower().strip()

def normalize_zip(zip_code):
    return ''.join(filter(str.isdigit, zip_code or ''))[:5]

def preprocess_prospect(p):
    return {
        **p,
        'first_name_norm': normalize_text(p.get('first_name')),
        'last_name_norm': normalize_text(p.get('last_name')),
        'email_norm': normalize_text(p.get('email')),
        'phone_norm': normalize_phone(p.get('phone1')),
        'zip_norm': normalize_zip(p.get('zip')),
    }

def are_dupes(p1, p2, threshold):
    if Levenshtein.normalized_similarity(p1['first_name_norm'], p2['first_name_norm']) * 100 < threshold:
        return False
    if Levenshtein.normalized_similarity(p1['last_name_norm'], p2['last_name_norm']) * 100 < threshold:
        return False
    if p1['phone_norm'] and p2['phone_norm'] and p1['phone_norm'] != p2['phone_norm']:
        return False
    if p1['email_norm'] and p2['email_norm'] and p1['email_norm'] != p2['email_norm']:
        return False
    if p1['zip_norm'] and p2['zip_norm'] and p1['zip_norm'] != p2['zip_norm']:
        return False
    return True

def process_block(block, threshold):
    groups = []
    seen = set()
    for i, a in enumerate(block):
        if a['id'] in seen:
            continue
        sim = [a]
        for b in block[i+1:]:
            if b['id'] in seen:
                continue
            if are_dupes(a, b, threshold):
                sim.append(b)
                seen.add(b['id'])
        if len(sim) > 1:
            groups.append({'group_id': len(groups)+1, 'prospects': sim})
    return groups

def get_block_key(p):
    fn = p['first_name_norm'][:2]
    ln = p['last_name_norm'][:2]
    if p['phone_norm']:
        return f"{fn}_{ln}_{p['phone_norm'][:3]}"
    elif p['email_norm']:
        return f"{fn}_{ln}_{p['email_norm'].split('@')[0][:2]}"
    elif p['zip_norm']:
        return f"{fn}_{ln}_{p['zip_norm'][:3]}"
    else:
        return f"{fn}_{ln}"

class Command(BaseCommand):
    help = 'Optimized duplicate detection for Genius Prospects'

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=int, default=80)
        parser.add_argument('--limit', type=int, default=None)

    def handle(self, *args, **options):
        threshold = options['threshold']
        limit = options['limit']
        self.stdout.write(f'Starting duplicate detection (threshold: {threshold})')

        qs = Genius_Prospect.objects.filter(first_name__isnull=False, last_name__isnull=False)
        if limit:
            qs = qs[:limit]

        raw_list = list(qs.values('id', 'first_name', 'last_name', 'phone1', 'email', 'zip'))
        prospects = [preprocess_prospect(p) for p in raw_list if p['first_name'] and p['last_name']]

        blocks = defaultdict(list)
        for p in prospects:
            # Create multiple blocking keys for better recall
            fn2 = p['first_name_norm'][:2]
            ln2 = p['last_name_norm'][:2]
            
            keys = set()
            
            # Primary key: name + phone area code
            if p['phone_norm'] and len(p['phone_norm']) >= 3:
                keys.add(f"{fn2}_{ln2}_{p['phone_norm'][:3]}")
            
            # Secondary key: name + email domain
            if p['email_norm'] and '@' in p['email_norm']:
                domain = p['email_norm'].split('@')[1][:3]
                keys.add(f"{fn2}_{ln2}_{domain}")
            
            # Tertiary key: name + zip prefix
            if p['zip_norm']:
                keys.add(f"{fn2}_{ln2}_{p['zip_norm'][:3]}")
            
            # Always add name-only key as fallback
            keys.add(f"{fn2}_{ln2}")
            
            # Add prospect to all relevant blocks
            for key in keys:
                blocks[key].append(p)

        block_items = list(blocks.items())
        self.stdout.write(f'Processing {len(block_items)} blocks...')

        results = []
        with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
            futures = [executor.submit(process_block, block, threshold) for _, block in block_items]
            for idx, future in enumerate(futures, start=1):
                results.extend(future.result())
                sys.stdout.write(f"\rProcessed {idx}/{len(futures)} blocks")
                sys.stdout.flush()

        self.stdout.write(f"\nFound {len(results)} duplicate groups.")
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects')
        os.makedirs(output_dir, exist_ok=True)
        output_path = os.path.join(output_dir, f'duplicates_{timestamp}.json')

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump({'groups': results}, f, indent=2, default=str)

        self.stdout.write(self.style.SUCCESS(f'Results saved to {output_path}'))
