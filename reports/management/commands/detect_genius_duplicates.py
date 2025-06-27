import json
import os
from datetime import datetime
from django.core.management.base import BaseCommand
from django.conf import settings
from ingestion.models.genius import Genius_Prospect
from fuzzywuzzy import fuzz
from collections import defaultdict
import re
import hashlib
from rapidfuzz import fuzz as rapidfuzz_fuzz
from multiprocessing import Pool, cpu_count
import django
import sys

# Module-level helpers for multiprocessing to avoid pickling self
def normalize_phone(phone):
    if not phone:
        return ''
    return re.sub(r'\D', '', phone)

def are_dupes(p1, p2, threshold):
    # Fuzzy logic for names
    from rapidfuzz import fuzz as rf_fuzz
    first_score = rf_fuzz.ratio(p1['first_name'].lower().strip(), p2['first_name'].lower().strip())
    last_score = rf_fuzz.ratio(p1['last_name'].lower().strip(), p2['last_name'].lower().strip())
    if first_score < threshold or last_score < threshold:
        return False
    # Exact match phone
    if p1.get('phone1') and p2.get('phone1'):
        if normalize_phone(p1['phone1']) != normalize_phone(p2['phone1']):
            return False
    # Exact match email
    if p1.get('email') and p2.get('email'):
        if p1['email'].lower().strip() != p2['email'].lower().strip():
            return False
    # Exact match zip
    if p1.get('zip') and p2.get('zip'):
        z1 = ''.join(filter(str.isdigit, p1['zip']))[:5]
        z2 = ''.join(filter(str.isdigit, p2['zip']))[:5]
        if z1 != z2:
            return False
    return True

def process_block_helper(args):
    key, block, threshold = args
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

class Command(BaseCommand):
    help = 'Detect duplicate Genius prospects using fuzzy logic matching (80%+ similarity)'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_file = None
        self.last_reported_progress = 0  # Track progress to ensure monotonic increase

    def setup_progress_tracking(self):
        """Initialize progress tracking file"""
        progress_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects')
        os.makedirs(progress_dir, exist_ok=True)
        self.progress_file = os.path.join(progress_dir, 'detection_progress.json')

    def update_progress(self, percent, status, details):
        """Update progress file with current status"""
        if not self.progress_file:
            return
        
        # Ensure progress never goes backwards
        percent = max(self.last_reported_progress, percent)
        self.last_reported_progress = percent
            
        progress_data = {
            'percent': percent,
            'status': status,
            'details': details,
            'timestamp': datetime.now().isoformat(),
            'completed': percent >= 100
        }
        
        try:
            with open(self.progress_file, 'w', encoding='utf-8') as f:
                json.dump(progress_data, f, indent=2)
        except Exception as e:
            self.stdout.write(f'Warning: Could not update progress file: {e}')

    def check_cancellation(self):
        """Check if the detection has been cancelled"""
        if not self.progress_file or not os.path.exists(self.progress_file):
            self.stdout.write("Debug: Progress file does not exist.")
            return False

        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                cancelled = progress_data.get('cancelled', False)
                return cancelled
        except Exception as e:
            self.stdout.write(f"Debug: Error reading progress file: {e}")
            return False

    def cleanup_progress(self):
        """Remove progress file when detection is complete"""
        if self.progress_file and os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception:
                pass  # Ignore cleanup errors

    def add_arguments(self, parser):
        parser.add_argument(
            '--threshold',
            type=int,
            default=80,
            help='Similarity threshold for duplicate detection (default: 80)'
        )
        parser.add_argument(
            '--limit',
            type=int,
            default=None,
            help='Limit the number of prospects to process (for testing)'
        )
        parser.add_argument(
            '--fast',
            action='store_true',
            help='Use only exact matching for maximum speed (may miss some fuzzy duplicates)'
        )
        parser.add_argument(
            '--sample',
            type=int,
            default=None,
            help='Process a random sample of N prospects for quick testing'
        )

    # Optimize the handle method to use parallel processing for blocks
    def handle(self, *args, **options):
        threshold = options['threshold']
        limit = options['limit']

        self.stdout.write(f'Starting duplicate detection with {threshold}% similarity threshold...')

        # Initialize progress tracking
        self.setup_progress_tracking()
        self.update_progress(0, 'Initializing...', 'Preparing to load prospects')

        # Get all prospects with required fields
        prospects_query = Genius_Prospect.objects.filter(
            first_name__isnull=False,
            last_name__isnull=False
        ).exclude(
            first_name='',
            last_name=''
        ).select_related('division').values(
            'id', 'first_name', 'last_name', 'phone1', 'email', 
            'zip', 'add_date', 'division_id', 'division__label'
        )

        if limit:
            prospects_query = prospects_query[:limit]

        self.update_progress(10, 'Loading prospects...', 'Fetching prospect data from database')
        prospects_list = list(prospects_query)
        self.stdout.write(f'Processing {len(prospects_list)} prospects...')
        self.update_progress(20, 'Processing prospects...', f'Loaded {len(prospects_list)} prospects')

        # Determine matching strategy
        fast = options.get('fast', False)
        if fast:
            self.stdout.write('Fast mode: using only in-Python exact matching (skipping SQL)')
            self.update_progress(22, 'Exact matching', 'Using in-Python exact matching')
            exact_groups, processed_ids = self.find_exact_matches(prospects_list)
        else:
            # Use SQL-based exact matching for large datasets
            if len(prospects_list) > 50000:
                self.stdout.write('Using SQL-based exact matching for large dataset optimization...')
                self.update_progress(22, 'SQL matching', 'Starting SQL exact matching')
                # Allow cancellation before heavy SQL work
                if self.check_cancellation():
                    self.stdout.write('Detection cancelled before SQL matching.')
                    self.update_progress(self.last_reported_progress, 'Cancelled', 'Cancelled before SQL matching')
                    self.cleanup_progress()
                    return
                exact_groups, processed_ids = self.find_sql_exact_matches(prospects_list)
            else:
                self.stdout.write('Using in-Python exact matching...')
                exact_groups, processed_ids = self.find_exact_matches(prospects_list)

        self.update_progress(25, 'Creating search index...', f'Found {len(exact_groups)} exact match groups')

        # Filter out already processed prospects for fuzzy matching
        remaining_prospects = [p for p in prospects_list if p['id'] not in processed_ids]

        if not remaining_prospects:
            self.update_progress(85, 'Generating report...', 'All duplicates found via exact matching')
            return

        # Group remaining prospects into blocks
        prospect_blocks = self.group_prospects_by_blocks(remaining_prospects)
        total_comparisons = sum(len(block) * (len(block) - 1) // 2 for block in prospect_blocks.values())
        self.stdout.write(f'Reduced comparisons to {total_comparisons:,} using blocking')

        self.update_progress(30, 'Detecting duplicates...', f'Processing {len(prospect_blocks)} blocks')

        # Use multiprocessing to process blocks in parallel
        with Pool(cpu_count()) as pool:
            block_args = [(block_key, block_prospects, threshold) for block_key, block_prospects in prospect_blocks.items()]
            results = []
            total_blocks = len(block_args)
            # Process blocks concurrently and update progress
            for idx, result in enumerate(pool.imap_unordered(process_block_helper, block_args), start=1):
                results.append(result)
                # Calculate progress
                progress = 30 + int(50 * idx / total_blocks)
                # Update file and console
                self.update_progress(progress, 'Detecting duplicates...', f'Processed {idx}/{total_blocks} blocks')
                sys.stdout.write(f"\rDetecting duplicates: {idx}/{total_blocks} blocks ({progress}%)")
                sys.stdout.flush()
                # Check for cancellation
                if self.check_cancellation():
                    sys.stdout.write('\nDetection cancelled by user.\n')
                    sys.stdout.flush()
                    self.update_progress(self.last_reported_progress, 'Cancelled', 'Detection cancelled by user')
                    self.cleanup_progress()
                    return

        # Combine results from all blocks
        duplicate_groups = [group for result in results for group in result]

        self.update_progress(85, 'Generating report...', 'Preparing results for output')

        # Save results
        self.save_results(duplicate_groups, len(prospects_list), threshold, limit)

        self.update_progress(100, 'Complete!', f'Found {len(duplicate_groups)} duplicate groups')
        self.stdout.write(self.style.SUCCESS(f'Duplicate detection completed! Found {len(duplicate_groups)} groups.'))

    def process_block(self, args):
        """Process a single block of prospects"""
        block_key, block_prospects, threshold = args
        duplicate_groups = []
        processed_ids = set()

        for i, prospect1 in enumerate(block_prospects):
            if prospect1['id'] in processed_ids:
                continue

            similar_prospects = [prospect1]

            for j in range(i + 1, len(block_prospects)):
                prospect2 = block_prospects[j]
                if prospect2['id'] in processed_ids:
                    continue

                if self.are_prospects_duplicates(prospect1, prospect2, threshold):
                    similar_prospects.append(prospect2)
                    processed_ids.add(prospect2['id'])

            if len(similar_prospects) > 1:
                duplicate_groups.append({
                    'group_id': len(duplicate_groups) + 1,
                    'prospects': similar_prospects
                })

        return duplicate_groups

    def normalize_phone(self, phone):
        """Normalize phone number by removing all non-digit characters"""
        if not phone:
            return ""
        return re.sub(r'\D', '', phone)

    def generate_group_display_name(self, prospects):
        """Generate a descriptive group name based on the prospects"""
        if not prospects:
            return "Unknown Group"
        
        # Use the first prospect's name as the base
        first_prospect = prospects[0]
        first_name = first_prospect.get('first_name', '').strip()
        last_name = first_prospect.get('last_name', '').strip()
        
        # Clean up the name
        display_name = f"{first_name} {last_name}".strip()
        if not display_name:
            display_name = "Unknown Name"
        
        # Add duplicate count
        return f"{display_name} ({len(prospects)} duplicates)"

    def are_prospects_duplicates(self, prospect1, prospect2, threshold):
        """Check if two prospects are duplicates using exact matching for contact details and fuzzy logic for names"""
        # Fuzzy logic for names
        first_name_score = rapidfuzz_fuzz.ratio(
            prospect1['first_name'].lower().strip(),
            prospect2['first_name'].lower().strip()
        )
        last_name_score = rapidfuzz_fuzz.ratio(
            prospect1['last_name'].lower().strip(),
            prospect2['last_name'].lower().strip()
        )

        if first_name_score < threshold or last_name_score < threshold:
            return False

        # Exact matching for phone numbers
        if prospect1.get('phone1') and prospect2.get('phone1'):
            if self.normalize_phone(prospect1['phone1']) != self.normalize_phone(prospect2['phone1']):
                return False

        # Exact matching for emails
        if prospect1.get('email') and prospect2.get('email'):
            if prospect1['email'].lower().strip() != prospect2['email'].lower().strip():
                return False

        # Exact matching for zip codes
        if prospect1.get('zip') and prospect2.get('zip'):
            zip1 = ''.join(filter(str.isdigit, prospect1['zip']))[:5]
            zip2 = ''.join(filter(str.isdigit, prospect2['zip']))[:5]
            if zip1 != zip2:
                return False

        return True

    def calculate_similarity(self, prospect1, prospect2):
        """Calculate similarity score between two prospects for display purposes"""
        first_name_score = fuzz.ratio(
            prospect1['first_name'].lower().strip(),
            prospect2['first_name'].lower().strip()
        )
        last_name_score = fuzz.ratio(
            prospect1['last_name'].lower().strip(),
            prospect2['last_name'].lower().strip()
        )
        
        # Use phone if both have it
        if prospect1.get('phone1') and prospect2.get('phone1'):
            phone_score = fuzz.ratio(
                self.normalize_phone(prospect1['phone1']),
                self.normalize_phone(prospect2['phone1'])
            )
            return (first_name_score + last_name_score + phone_score) / 3
        
        # Fall back to email if both have it
        if prospect1.get('email') and prospect2.get('email'):
            email_score = fuzz.ratio(
                prospect1['email'].lower().strip(),
                prospect2['email'].lower().strip()
            )
            return (first_name_score + last_name_score + email_score) / 3
        
        # Fall back to zip if both have it
        if prospect1.get('zip') and prospect2.get('zip'):
            zip1 = ''.join(filter(str.isdigit, prospect1['zip']))[:5]
            zip2 = ''.join(filter(str.isdigit, prospect2['zip']))[:5]
            if zip1 and zip2:
                zip_score = fuzz.ratio(zip1, zip2)
                return (first_name_score + last_name_score + zip_score) / 3
        
        # If we can only compare names, use just the name scores
        return (first_name_score + last_name_score) / 2

    def create_blocking_key(self, prospect):
        """Create a blocking key to group similar prospects together"""
        # Use first 2 chars of first name + first 2 chars of last name + phone area code
        first_name = (prospect.get('first_name') or '').lower().strip()[:2]
        last_name = (prospect.get('last_name') or '').lower().strip()[:2]
        
        # Get area code from phone if available
        phone = self.normalize_phone(prospect.get('phone1') or '')
        area_code = phone[:3] if len(phone) >= 10 else ''
        
        # If no phone, use email domain or zip prefix
        if not area_code:
            email = prospect.get('email') or ''
            if '@' in email:
                domain = email.split('@')[1].lower()[:3]
                return f"{first_name}_{last_name}_{domain}"
            
            zip_code = prospect.get('zip') or ''
            zip_prefix = ''.join(filter(str.isdigit, zip_code))[:3]
            return f"{first_name}_{last_name}_{zip_prefix}"
        
        return f"{first_name}_{last_name}_{area_code}"

    def create_soundex_key(self, name):
        """Create a simple soundex-like key for phonetic matching"""
        if not name:
            return ""
        
        name = name.lower().strip()
        if not name:
            return ""
        
        # Simple phonetic replacements
        replacements = {
            'ph': 'f', 'gh': 'f', 'ck': 'k', 'th': 't',
            'sh': 's', 'ch': 's', 'wh': 'w'
        }
        
        for old, new in replacements.items():
            name = name.replace(old, new)
        
        # Remove vowels except first character and duplicates
        result = name[0] if name else ""
        for i in range(1, len(name)):
            if name[i] not in 'aeiou' and name[i] != result[-1]:
                result += name[i]
        
        return result[:4].ljust(4, '0')

    def group_prospects_by_blocks(self, prospects_list):
        """Group prospects into blocks for more efficient comparison"""
        blocks = defaultdict(list)
        
        for prospect in prospects_list:
            # Create multiple blocking keys for better recall
            keys = []
            
            # Primary blocking key
            keys.append(self.create_blocking_key(prospect))
            
            # Soundex-based key for phonetic matching
            first_soundex = self.create_soundex_key(prospect.get('first_name', ''))
            last_soundex = self.create_soundex_key(prospect.get('last_name', ''))
            keys.append(f"soundex_{first_soundex}_{last_soundex}")
            
            # Add prospect to all relevant blocks
            for key in keys:
                if key:
                    blocks[key].append(prospect)
        
        return blocks

    def find_exact_matches(self, prospects_list):
        """Quickly find exact matches before fuzzy matching"""
        exact_match_groups = []
        phone_map = defaultdict(list)
        email_map = defaultdict(list)
        name_phone_map = defaultdict(list)
        
        # Group by exact phone matches
        for prospect in prospects_list:
            phone = self.normalize_phone(prospect.get('phone1') or '')
            if phone and len(phone) >= 10:
                phone_map[phone].append(prospect)
            
            email = (prospect.get('email') or '').lower().strip()
            if email and '@' in email:
                email_map[email].append(prospect)
            
            # Name + phone combination
            first_name = (prospect.get('first_name') or '').lower().strip()
            last_name = (prospect.get('last_name') or '').lower().strip()
            name_key = f"{first_name}_{last_name}_{phone}"
            if first_name and last_name and phone:  # Ensure we have both names and phone
                name_phone_map[name_key].append(prospect)
        
        processed_ids = set()
        
        # Process exact phone matches
        for phone, prospects in phone_map.items():
            if len(prospects) > 1:
                # Verify names are similar for phone matches
                similar_prospects = []
                for prospect in prospects:
                    if prospect['id'] not in processed_ids:
                        similar_prospects.append(prospect)
                        processed_ids.add(prospect['id'])
                
                if len(similar_prospects) > 1:
                    # Quick name similarity check
                    base_prospect = similar_prospects[0]
                    filtered_prospects = [base_prospect]
                    
                    for other_prospect in similar_prospects[1:]:
                        first_score = fuzz.ratio(
                            (base_prospect.get('first_name') or '').lower().strip(),
                            (other_prospect.get('first_name') or '').lower().strip()
                        )
                        last_score = fuzz.ratio(
                            (base_prospect.get('last_name') or '').lower().strip(), 
                            (other_prospect.get('last_name') or '').lower().strip()
                        )
                        
                        if first_score >= 70 and last_score >= 70:  # Lower threshold for exact phone matches
                            filtered_prospects.append(other_prospect)
                    
                    if len(filtered_prospects) > 1:
                        exact_match_groups.append(filtered_prospects)
        
        return exact_match_groups, processed_ids

    def find_sql_exact_matches(self, prospects_list):
        """Find exact matches using SQL for optimization"""
        if not prospects_list:
            return [], set()

        # Use a temporary table to store prospects for exact matching
        # Dynamically import Django DB connection to avoid static lint issues
        connection = __import__('django.db', fromlist=['connection']).connection
        total = len(prospects_list)
        with connection.cursor() as cursor:
            # Create temporary table
            cursor.execute('''
                CREATE TEMPORARY TABLE temp_prospects (
                    id SERIAL PRIMARY KEY,
                    first_name VARCHAR(255),
                    last_name VARCHAR(255),
                    phone1 VARCHAR(255),
                    email VARCHAR(255),
                    zip VARCHAR(255),
                    add_date TIMESTAMP,
                    division_id INTEGER
                )
            ''')

            # Insert prospect data into temporary table with progress updates
            insert_query = '''
                INSERT INTO temp_prospects (first_name, last_name, phone1, email, zip, add_date, division_id)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            '''
            for idx, prospect in enumerate(prospects_list, start=1):
                cursor.execute(insert_query, (
                    prospect['first_name'],
                    prospect['last_name'],
                    self.normalize_phone(prospect.get('phone1')),
                    (prospect.get('email') or '').lower(),
                    ''.join(filter(str.isdigit, (prospect.get('zip') or ''))),
                    prospect['add_date'],
                    prospect['division_id']
                ))
                # Update progress during SQL insert every 20k rows
                if idx % 20000 == 0 or idx == total:
                    pct = 23 + int(2 * idx / total)
                    # Update file and console
                    self.update_progress(pct, 'SQL matching', f'Inserted {idx}/{total} rows into temp table')
                    sys.stdout.write(f"\rSQL insert: {idx}/{total} rows ({pct}%)")
                    sys.stdout.flush()
                # Check for cancellation
                if self.check_cancellation():
                    return [], set()

            # Create indexes on temporary table for faster querying
            cursor.execute('CREATE INDEX idx_phone ON temp_prospects (phone1)')
            cursor.execute('CREATE INDEX idx_email ON temp_prospects (email)')
            cursor.execute('CREATE INDEX idx_zip ON temp_prospects (zip)')
            cursor.execute('CREATE INDEX idx_name ON temp_prospects (first_name, last_name)')
            # Progress after indexing
            self.update_progress(25, 'SQL matching', 'Indexes created')

            # Find exact matches using SQL
            cursor.execute('''
                SELECT a.*, b.*
                FROM temp_prospects a
                JOIN temp_prospects b ON a.id < b.id
                WHERE
                    (a.phone1 = b.phone1 OR a.email = b.email OR a.zip = b.zip)
                    AND a.first_name = b.first_name
                    AND a.last_name = b.last_name
            ''')

            # Fetch and group results
            rows = cursor.fetchall()
            # Progress after fetching rows
            self.update_progress(27, 'SQL matching', f'Fetched {len(rows)} matching rows')
            exact_match_groups = defaultdict(list)
            processed_ids = set()
            
            for row in rows:
                prospect_id = row[0]
                if prospect_id not in processed_ids:
                    group = [dict(zip([col[0] for col in cursor.description], row))]
                    exact_match_groups[prospect_id] = group
                    processed_ids.add(prospect_id)
            
            # Convert groups to list of lists
            exact_match_groups = [group for group in exact_match_groups.values()]

        return exact_match_groups, processed_ids
    
    def save_results(self, duplicate_groups, total_prospects, threshold, limit):
        """Save duplicate groups to a JSON file with metadata"""
        # Prepare output directory
        output_dir = os.path.dirname(self.progress_file) if self.progress_file else os.getcwd()
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'genius_duplicates_thresh{threshold}'
        if limit:
            filename += f'_limit{limit}'
        filename += f'_{timestamp}.json'
        output_path = os.path.join(output_dir, filename)
        data = {
            'total_prospects': total_prospects,
            'threshold': threshold,
            'limit': limit,
            'groups_found': len(duplicate_groups),
            'groups': duplicate_groups,
        }
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            self.stdout.write(self.style.SUCCESS(f'Results saved to {output_path}'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error saving results: {e}'))
