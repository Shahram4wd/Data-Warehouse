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

    def handle(self, *args, **options):
        threshold = options['threshold']
        limit = options['limit']
        
        self.stdout.write(f'Starting duplicate detection with {threshold}% similarity threshold...')
        
        # Initialize progress tracking
        self.setup_progress_tracking()
        self.update_progress(0, 'Initializing...', 'Preparing to load prospects')
        
        # Get all prospects with required fields (first_name and last_name are required)
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

        # For very large datasets, suggest using a limit or provide warning
        if len(prospects_list) > 50000 and not limit:
            self.stdout.write(
                self.style.WARNING(
                    f'Warning: Processing {len(prospects_list)} prospects may take a very long time.\n'
                    f'Consider using --limit parameter for faster testing (e.g., --limit 10000)'
                )
            )

        duplicate_groups = []
        processed_ids = set()
        total_prospects = len(prospects_list)

        self.update_progress(22, 'Finding exact matches...', 'Quickly identifying obvious duplicates')
        
        # First, find exact matches (much faster)
        exact_groups, exact_processed_ids = self.find_exact_matches(prospects_list)
        processed_ids.update(exact_processed_ids)
        
        # Convert exact matches to proper duplicate groups
        for i, exact_group in enumerate(exact_groups):
            # Calculate average similarity for the group
            total_score = 0
            comparisons = 0
            
            for k in range(len(exact_group)):
                for l in range(k+1, len(exact_group)):
                    score = self.calculate_similarity(exact_group[k], exact_group[l])
                    total_score += score
                    comparisons += 1
            
            avg_score = total_score / comparisons if comparisons > 0 else 0
            
            duplicate_group = {
                'group_id': len(duplicate_groups) + 1,
                'group_display_name': self.generate_group_display_name(exact_group),
                'total_duplicates': len(exact_group),
                'prospects': exact_group,
                'detection_details': {
                    'threshold_used': threshold,
                    'detection_method': 'exact_match_optimization',
                    'average_similarity_score': round(avg_score, 2),
                    'fields_analyzed': ['phone1', 'first_name', 'last_name'],
                }
            }
            duplicate_groups.append(duplicate_group)
        
        self.update_progress(25, 'Creating search index...', f'Found {len(exact_groups)} exact match groups, continuing with fuzzy matching')
        
        # Filter out already processed prospects for fuzzy matching
        remaining_prospects = [p for p in prospects_list if p['id'] not in processed_ids]
        
        if not remaining_prospects:
            self.update_progress(85, 'Generating report...', 'All duplicates found via exact matching')
        else:
            # Group remaining prospects into blocks for efficient comparison
            prospect_blocks = self.group_prospects_by_blocks(remaining_prospects)
            
            # Calculate total comparisons for better progress tracking
            total_comparisons = sum(len(block) * (len(block) - 1) // 2 for block in prospect_blocks.values())
            self.stdout.write(f'Exact matching found {len(exact_groups)} groups, fuzzy matching {len(remaining_prospects):,} remaining prospects')
            self.stdout.write(f'Reduced fuzzy comparisons to {total_comparisons:,} using blocking')
        
        # Group prospects into blocks for efficient comparison
        prospect_blocks = self.group_prospects_by_blocks(prospects_list)
        
        # Calculate total comparisons for better progress tracking
        total_comparisons = sum(len(block) * (len(block) - 1) // 2 for block in prospect_blocks.values())
        self.stdout.write(f'Reduced comparisons from {total_prospects * (total_prospects - 1) // 2:,} to {total_comparisons:,} using blocking')
        
        self.update_progress(30, 'Detecting duplicates...', f'Processing {len(prospect_blocks)} blocks instead of {total_prospects:,} individual comparisons')

        # Process each block separately
        comparisons_done = 0
        import time
        start_time = time.time()
        
        for block_key, block_prospects in prospect_blocks.items():
            if len(block_prospects) < 2:
                continue  # Skip blocks with only one prospect
            
            # Only compare prospects within the same block
            for i, prospect1 in enumerate(block_prospects):
                if prospect1['id'] in processed_ids:
                    continue
                
                # Check for cancellation periodically
                if comparisons_done % 100 == 0 and self.check_cancellation():
                    self.update_progress(0, 'Cancelled', 'Detection was cancelled by user')
                    self.stdout.write(self.style.WARNING('Detection cancelled by user.'))
                    return "Detection cancelled"
                
                similar_prospects = [prospect1]
                
                for j in range(i + 1, len(block_prospects)):
                    prospect2 = block_prospects[j]
                    if prospect2['id'] in processed_ids:
                        continue
                    
                    # Check if prospects are duplicates
                    if self.are_prospects_duplicates(prospect1, prospect2, threshold):
                        similar_prospects.append(prospect2)
                        processed_ids.add(prospect2['id'])
                    
                    comparisons_done += 1
                
                # Update progress based on comparisons done
                if comparisons_done % 500 == 0 or block_key == list(prospect_blocks.keys())[-1]:
                    if total_comparisons > 0:
                        progress_pct = 30 + (comparisons_done / total_comparisons) * 50  # 30% to 80%
                        progress = min(80, progress_pct)
                        
                        # Calculate ETA
                        if comparisons_done > 0:
                            current_time = time.time()
                            elapsed = current_time - start_time
                            rate = comparisons_done / elapsed if elapsed > 0 else 0
                            remaining_comparisons = total_comparisons - comparisons_done
                            remaining_time = remaining_comparisons / rate if rate > 0 else 0
                            
                            if remaining_time > 60:
                                eta_text = f" (ETA: {int(remaining_time/60)}min {int(remaining_time%60)}s)"
                            else:
                                eta_text = f" (ETA: {int(remaining_time)}s)"
                        else:
                            eta_text = ""
                        
                        self.update_progress(progress, 'Detecting duplicates...', 
                                           f'Processed {comparisons_done:,} of {total_comparisons:,} comparisons{eta_text}')
                
                # If we found duplicates, add to results
                if len(similar_prospects) > 1:
                    # Calculate average similarity for the group
                    total_score = 0
                    comparisons = 0
                    
                    for k in range(len(similar_prospects)):
                        for l in range(k+1, len(similar_prospects)):
                            score = self.calculate_similarity(similar_prospects[k], similar_prospects[l])
                            total_score += score
                            comparisons += 1
                    
                    avg_score = total_score / comparisons if comparisons > 0 else 0
                    
                    duplicate_group = {
                        'group_id': len(duplicate_groups) + 1,
                        'group_display_name': self.generate_group_display_name(similar_prospects),
                        'total_duplicates': len(similar_prospects),
                        'prospects': similar_prospects,
                        'detection_details': {
                            'threshold_used': threshold,
                            'detection_method': 'optimized_blocking',
                            'average_similarity_score': round(avg_score, 2),
                            'fields_analyzed': ['first_name', 'last_name', 'phone1', 'email', 'zip'],
                            'block_key': block_key
                        }
                    }
                    duplicate_groups.append(duplicate_group)
                    processed_ids.add(prospect1['id'])

        # Sort duplicate groups by latest creation date (descending)
        for group in duplicate_groups:
            # Sort prospects within each group by add_date descending
            group['prospects'] = sorted(
                group['prospects'],
                key=lambda x: x['add_date'] if x['add_date'] else datetime.min,
                reverse=True
            )
            # Add latest_creation_date for sorting groups
            group['latest_creation_date'] = group['prospects'][0]['add_date'] if group['prospects'] and group['prospects'][0]['add_date'] else datetime.min

        # Sort groups by latest creation date (descending)
        duplicate_groups = sorted(
            duplicate_groups,
            key=lambda x: x['latest_creation_date'],
            reverse=True
        )

        # Re-assign group IDs after sorting
        for i, group in enumerate(duplicate_groups, 1):
            group['group_id'] = i
            # Remove the temporary sorting field
            if 'latest_creation_date' in group:
                del group['latest_creation_date']

        self.update_progress(85, 'Generating report...', 'Preparing results for output')

        # Prepare results
        results = {
            'report_type': 'duplicated_genius_prospects',
            'generated_at': datetime.now().isoformat(),
            'parameters': {
                'similarity_threshold': threshold,
                'total_prospects_analyzed': len(prospects_list),
                'fields_compared': ['first_name', 'last_name', 'phone1', 'email', 'zip'],
                'limit_used': limit
            },
            'summary': {
                'total_duplicate_groups': len(duplicate_groups),
                'total_duplicate_prospects': sum(group['total_duplicates'] for group in duplicate_groups),
                'percentage_duplicates': round(
                    (sum(group['total_duplicates'] for group in duplicate_groups) / len(prospects_list)) * 100, 2
                ) if prospects_list else 0
            },
            'duplicate_groups': duplicate_groups
        }

        self.update_progress(90, 'Saving results...', 'Writing report files to disk')

        # Save results to timestamped file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'duplicated_genius_prospects_{timestamp}.json'
        
        # Ensure directory exists
        output_dir = os.path.join(settings.BASE_DIR, 'reports', 'data', 'duplicated_genius_prospects')
        os.makedirs(output_dir, exist_ok=True)
        
        output_path = os.path.join(output_dir, filename)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        # Also save as "latest.json" for easy access
        latest_path = os.path.join(output_dir, 'latest.json')
        with open(latest_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)

        self.update_progress(100, 'Complete!', f'Found {len(duplicate_groups)} duplicate groups')

        self.stdout.write(
            self.style.SUCCESS(
                f'Duplicate detection completed!\n'
                f'Found {len(duplicate_groups)} duplicate groups with {sum(group["total_duplicates"] for group in duplicate_groups)} total duplicates.\n'
                f'Results saved to: {output_path}'
            )
        )

        # Clean up progress file
        self.cleanup_progress()

        return f"Detection completed: {len(duplicate_groups)} groups found"

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
        """Check if two prospects are duplicates using original logic"""
        # Always require first_name and last_name similarity
        first_name_score = fuzz.ratio(
            prospect1['first_name'].lower().strip(),
            prospect2['first_name'].lower().strip()
        )
        last_name_score = fuzz.ratio(
            prospect1['last_name'].lower().strip(),
            prospect2['last_name'].lower().strip()
        )
        
        # If either name score is too low, not a match
        if first_name_score < threshold or last_name_score < threshold:
            return False
        
        # Both prospects have phone1, compare phone numbers
        if prospect1.get('phone1') and prospect2.get('phone1'):
            phone_score = fuzz.ratio(
                self.normalize_phone(prospect1['phone1']),
                self.normalize_phone(prospect2['phone1'])
            )
            return phone_score >= threshold
        
        # If no phone, fall back to email comparison
        if prospect1.get('email') and prospect2.get('email'):
            email_score = fuzz.ratio(
                prospect1['email'].lower().strip(),
                prospect2['email'].lower().strip()
            )
            return email_score >= threshold
        
        # If no email either, fall back to zip comparison
        if prospect1.get('zip') and prospect2.get('zip'):
            # Extract numeric part of ZIP codes for comparison
            zip1 = ''.join(filter(str.isdigit, prospect1['zip']))[:5]
            zip2 = ''.join(filter(str.isdigit, prospect2['zip']))[:5]
            if zip1 and zip2:
                zip_score = fuzz.ratio(zip1, zip2)
                return zip_score >= threshold
        
        # If we can't compare additional fields, don't consider it a match
        return False

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
