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

# Normalize helpers at module level for multiprocessing
def normalize_phone(phone):
    """Normalize phone number by removing all non-digit characters"""
    return re.sub(r'\D', '', phone or '')

def normalize_text(value):
    """Normalize text by converting to lowercase and stripping whitespace"""
    return (value or '').lower().strip()

def normalize_zip(zip_code):
    """Normalize ZIP code by extracting first 5 digits"""
    return ''.join(filter(str.isdigit, zip_code or ''))[:5]

def preprocess_prospect(p):
    """Preprocess a prospect by adding normalized fields"""
    return {
        **p,
        'first_name_norm': normalize_text(p.get('first_name')),
        'last_name_norm': normalize_text(p.get('last_name')),
        'email_norm': normalize_text(p.get('email')),
        'phone_norm': normalize_phone(p.get('phone1')),
        'zip_norm': normalize_zip(p.get('zip')),
    }

def are_dupes(p1, p2, threshold):
    """Check if two prospects are duplicates using normalized similarity"""
    # Check first name similarity
    if Levenshtein.normalized_similarity(p1['first_name_norm'], p2['first_name_norm']) * 100 < threshold:
        return False
    
    # Check last name similarity
    if Levenshtein.normalized_similarity(p1['last_name_norm'], p2['last_name_norm']) * 100 < threshold:
        return False
    
    # If both have phone numbers, they must match exactly
    if p1['phone_norm'] and p2['phone_norm'] and p1['phone_norm'] != p2['phone_norm']:
        return False
    
    # If both have emails, they must match exactly
    if p1['email_norm'] and p2['email_norm'] and p1['email_norm'] != p2['email_norm']:
        return False
    
    # If both have ZIP codes, they must match exactly
    if p1['zip_norm'] and p2['zip_norm'] and p1['zip_norm'] != p2['zip_norm']:
        return False
    
    return True

def calculate_similarity_score(p1, p2):
    """Calculate overall similarity score between two prospects"""
    first_score = Levenshtein.normalized_similarity(p1['first_name_norm'], p2['first_name_norm']) * 100
    last_score = Levenshtein.normalized_similarity(p1['last_name_norm'], p2['last_name_norm']) * 100
    
    scores = [first_score, last_score]
    
    # Add phone score if both have phones
    if p1['phone_norm'] and p2['phone_norm']:
        phone_score = 100 if p1['phone_norm'] == p2['phone_norm'] else 0
        scores.append(phone_score)
    
    # Add email score if both have emails
    if p1['email_norm'] and p2['email_norm']:
        email_score = 100 if p1['email_norm'] == p2['email_norm'] else 0
        scores.append(email_score)
    
    return sum(scores) / len(scores)

def process_block(args):
    """Process a single block of prospects to find duplicates"""
    block, threshold = args
    groups = []
    seen = set()
    
    for i, prospect_a in enumerate(block):
        if prospect_a['id'] in seen:
            continue
        
        similar_prospects = [prospect_a]
        
        for prospect_b in block[i+1:]:
            if prospect_b['id'] in seen:
                continue
            
            if are_dupes(prospect_a, prospect_b, threshold):
                similar_prospects.append(prospect_b)
                seen.add(prospect_b['id'])
        
        if len(similar_prospects) > 1:
            # Calculate average similarity for the group
            total_score = 0
            comparisons = 0
            
            for k in range(len(similar_prospects)):
                for l in range(k+1, len(similar_prospects)):
                    score = calculate_similarity_score(similar_prospects[k], similar_prospects[l])
                    total_score += score
                    comparisons += 1
            
            avg_score = total_score / comparisons if comparisons > 0 else 0
            
            group = {
                'group_id': len(groups) + 1,
                'prospects': similar_prospects,
                'average_similarity_score': round(avg_score, 2)
            }
            groups.append(group)
            seen.add(prospect_a['id'])
    
    return groups


class Command(BaseCommand):
    help = 'Optimized duplicate detection for Genius Prospects using blocking and parallel processing'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.progress_file = None
        self.last_reported_progress = 0

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
            return False
            
        try:
            with open(self.progress_file, 'r', encoding='utf-8') as f:
                progress_data = json.load(f)
                return progress_data.get('cancelled', False)
        except Exception:
            return False

    def cleanup_progress(self):
        """Remove progress file when detection is complete"""
        if self.progress_file and os.path.exists(self.progress_file):
            try:
                os.remove(self.progress_file)
            except Exception:
                pass

    def add_arguments(self, parser):
        parser.add_argument('--threshold', type=int, default=80, help='Similarity threshold (default: 80)')
        parser.add_argument('--limit', type=int, default=None, help='Limit prospects for testing')

    def generate_group_display_name(self, prospects):
        """Generate a descriptive group name based on the prospects"""
        if not prospects:
            return "Unknown Group"
        
        first_prospect = prospects[0]
        first_name = first_prospect.get('first_name', '').strip()
        last_name = first_prospect.get('last_name', '').strip()
        
        display_name = f"{first_name} {last_name}".strip()
        if not display_name:
            display_name = "Unknown Name"
        
        return f"{display_name} ({len(prospects)} duplicates)"

    def get_block_key(self, prospect):
        """Generate blocking key for a prospect"""
        fn = prospect['first_name_norm'][:2] if prospect['first_name_norm'] else ''
        ln = prospect['last_name_norm'][:2] if prospect['last_name_norm'] else ''
        
        # Use phone area code if available
        if prospect['phone_norm'] and len(prospect['phone_norm']) >= 3:
            return f"{fn}_{ln}_{prospect['phone_norm'][:3]}"
        
        # Use email domain if available
        elif prospect['email_norm'] and '@' in prospect['email_norm']:
            domain = prospect['email_norm'].split('@')[1][:3]
            return f"{fn}_{ln}_{domain}"
        
        # Use ZIP prefix if available
        elif prospect['zip_norm']:
            return f"{fn}_{ln}_{prospect['zip_norm'][:3]}"
        
        # Default to name only
        else:
            return f"{fn}_{ln}"

    def save_results(self, results):
        """Save detection results to files"""
        # Save to timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'duplicated_genius_prospects_{timestamp}.json'
        
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Also save as "latest.json"
        latest_path = os.path.join(output_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        return output_path

    def handle(self, *args, **options):
        threshold = options['threshold']
        limit = options['limit']
        
        self.stdout.write(f'Starting optimized duplicate detection (threshold: {threshold}%)')
        
        # Initialize progress tracking
        self.setup_progress_tracking()
        self.update_progress(0, 'Initializing...', 'Preparing to load prospects')

        # Load prospects
        qs = Genius_Prospect.objects.filter(
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
            qs = qs[:limit]

        self.update_progress(10, 'Loading prospects...', 'Fetching data from database')
        raw_list = list(qs)
        
        # Preprocess prospects
        prospects = [preprocess_prospect(p) for p in raw_list if p['first_name'] and p['last_name']]
        
        self.update_progress(20, 'Creating blocks...', f'Loaded {len(prospects)} prospects')
        self.stdout.write(f'Processing {len(prospects)} prospects...')

        # Group prospects into blocks for efficient processing
        blocks = defaultdict(list)
        for p in prospects:
            # Create multiple blocking keys for better recall
            fn2 = p['first_name_norm'][:2] if p['first_name_norm'] else ''
            ln2 = p['last_name_norm'][:2] if p['last_name_norm'] else ''
            
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

        # Filter out single-prospect blocks
        block_items = [(key, block) for key, block in blocks.items() if len(block) > 1]
        
        self.update_progress(30, 'Processing blocks...', f'Created {len(block_items)} blocks for comparison')
        self.stdout.write(f'Processing {len(block_items)} blocks with multiprocessing...')

        # Process blocks in parallel
        results = []
        try:
            with ProcessPoolExecutor(max_workers=cpu_count()) as executor:
                # Prepare arguments for parallel processing
                block_args = [(block, threshold) for _, block in block_items]
                
                futures = [executor.submit(process_block, args) for args in block_args]
                
                for idx, future in enumerate(futures, start=1):
                    if self.check_cancellation():
                        self.update_progress(0, 'Cancelled', 'Detection was cancelled by user')
                        self.stdout.write(self.style.WARNING('Detection cancelled by user.'))
                        return "Detection cancelled"
                    
                    try:
                        block_results = future.result()
                        results.extend(block_results)
                        
                        # Update progress
                        progress_pct = 30 + (idx / len(futures)) * 50  # 30% to 80%
                        self.update_progress(progress_pct, 'Processing blocks...', 
                                           f'Processed {idx}/{len(futures)} blocks')
                        
                        if idx % 10 == 0:
                            sys.stdout.write(f"\rProcessed {idx}/{len(futures)} blocks")
                            sys.stdout.flush()
                            
                    except Exception as e:
                        self.stdout.write(f"Error processing block {idx}: {e}")
                        continue

        except Exception as e:
            self.stdout.write(f"Error in parallel processing: {e}")
            self.update_progress(0, 'Error', f'Processing failed: {str(e)}')
            return f"Detection failed: {str(e)}"

        self.update_progress(80, 'Finalizing results...', f'Found {len(results)} duplicate groups')
        
        # Remove duplicates and assign final group IDs
        seen_prospect_ids = set()
        final_groups = []
        
        for group in results:
            # Remove prospects that are already in other groups
            unique_prospects = []
            for prospect in group['prospects']:
                if prospect['id'] not in seen_prospect_ids:
                    unique_prospects.append(prospect)
                    seen_prospect_ids.add(prospect['id'])
            
            if len(unique_prospects) > 1:
                # Sort prospects by add_date (newest first)
                unique_prospects.sort(
                    key=lambda x: x['add_date'] if x['add_date'] else datetime.min,
                    reverse=True
                )
                
                final_group = {
                    'group_id': len(final_groups) + 1,
                    'group_display_name': self.generate_group_display_name(unique_prospects),
                    'total_duplicates': len(unique_prospects),
                    'prospects': unique_prospects,
                    'detection_details': {
                        'threshold_used': threshold,
                        'detection_method': 'optimized_blocking_parallel',
                        'average_similarity_score': group.get('average_similarity_score', 0),
                        'fields_analyzed': ['first_name', 'last_name', 'phone1', 'email', 'zip'],
                    }
                }
                final_groups.append(final_group)

        # Sort groups by latest creation date
        final_groups.sort(
            key=lambda g: max(p['add_date'] for p in g['prospects'] if p['add_date']) if any(p['add_date'] for p in g['prospects']) else datetime.min,
            reverse=True
        )

        # Re-assign group IDs after sorting
        for i, group in enumerate(final_groups, 1):
            group['group_id'] = i

        self.update_progress(90, 'Saving results...', 'Writing report files')

        # Prepare final results
        final_results = {
            'report_type': 'duplicated_genius_prospects',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'similarity_threshold': threshold,
                'total_prospects_analyzed': len(prospects),
                'fields_compared': ['first_name', 'last_name', 'phone1', 'email', 'zip'],
                'limit_used': limit
            },
            'summary': {
                'total_duplicate_groups': len(final_groups),
                'total_duplicate_prospects': sum(group['total_duplicates'] for group in final_groups),
                'percentage_duplicates': round(
                    (sum(group['total_duplicates'] for group in final_groups) / len(prospects)) * 100, 2
                ) if prospects else 0
            },
            'duplicate_groups': final_groups
        }

        # Save results
        output_path = self.save_results(final_results)
        
        self.update_progress(100, 'Complete!', f'Found {len(final_groups)} duplicate groups')

        self.stdout.write(
            self.style.SUCCESS(
                f'\nOptimized duplicate detection completed!\n'
                f'Found {len(final_groups)} duplicate groups with {sum(group["total_duplicates"] for group in final_groups)} total duplicates.\n'
                f'Results saved to: {output_path}'
            )
        )

        # Clean up progress file
        self.cleanup_progress()

        return f"Detection completed: {len(final_groups)} groups found"
