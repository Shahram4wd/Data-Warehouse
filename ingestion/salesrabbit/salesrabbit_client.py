import requests
import logging
from django.conf import settings

logger = logging.getLogger(__name__)

class SalesRabbitClient:
    """Simple client for SalesRabbit API"""
    def __init__(self, api_token=None, base_url=None):
        self.api_token = api_token or settings.SALESRABBIT_API_TOKEN
        self.base_url = base_url or settings.SALESRABBIT_API_URL.rstrip('/')
        self.headers = {
            'Authorization': f"Bearer {self.api_token}",
            'Accept': 'application/json'
        }
    
    def get_leads(self, page_size=1000, max_pages=None):
        """Fetch all leads from SalesRabbit with pagination support"""
        from ingestion.models.salesrabbit import SalesRabbit_Lead
        from django.utils.dateparse import parse_datetime
        from datetime import datetime

        url = f"{self.base_url}/leads"
        all_leads = []
        page = 1
        while True:
            params = {'page': page, 'limit': page_size}
            print(f"[DEBUG] Requesting {url} with params {params}")
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=10)
                print(f"[DEBUG] Response status: {response.status_code}")
                response.raise_for_status()
                data = response.json()
                # Handle different possible response formats
                if isinstance(data, list):
                    leads = data
                elif isinstance(data, dict) and 'data' in data:
                    leads = data['data']
                elif isinstance(data, dict) and 'leads' in data:
                    leads = data.get('leads')
                else:
                    leads = []
                print(f"[DEBUG] Got {len(leads)} leads on page {page}")
                if not leads:
                    break

                # Save leads to the database in batches
                batch_size = 100
                total_leads = len(leads)
                for i in range(0, total_leads, batch_size):
                    batch = leads[i:i + batch_size]
                    print(f"[DEBUG] Saving batch {i // batch_size + 1} of size {len(batch)}")
                    try:
                        # Prepare objects for bulk operations
                        lead_objects = []
                        for lead_data in batch:
                            defaults = {
                                'business_name': lead_data.get('businessName'),
                                'first_name': lead_data.get('firstName'),
                                'last_name': lead_data.get('lastName'),
                                'email': lead_data.get('email'),
                                'phone_primary': lead_data.get('phonePrimary'),
                                'phone_alternate': lead_data.get('phoneAlternate'),
                                'street1': lead_data.get('street1'),
                                'street2': lead_data.get('street2'),
                                'city': lead_data.get('city'),
                                'state': lead_data.get('state'),
                                'zip': lead_data.get('zip'),
                                'country': lead_data.get('country'),
                                'latitude': lead_data.get('latitude'),
                                'longitude': lead_data.get('longitude'),
                                'status': lead_data.get('status'),
                                'campaign_id': lead_data.get('campaignId'),
                                'user_id': lead_data.get('userId'),
                                'user_name': lead_data.get('userName'),
                                'notes': lead_data.get('notes'),
                                'custom_fields': lead_data.get('customFields'),
                                'date_created': parse_datetime(lead_data.get('dateCreated')) if lead_data.get('dateCreated') else None,
                                'date_modified': parse_datetime(lead_data.get('dateModified')) if lead_data.get('dateModified') else None,
                                'deleted_at': parse_datetime(lead_data.get('deletedAt')) if lead_data.get('deletedAt') else None,
                                'status_modified': parse_datetime(lead_data.get('statusModified')) if lead_data.get('statusModified') else None,
                                'owner_modified': parse_datetime(lead_data.get('ownerModified')) if lead_data.get('ownerModified') else None,
                                'date_of_birth': parse_datetime(lead_data.get('dateOfBirth')) if lead_data.get('dateOfBirth') else None,
                                'synced_at': datetime.now(),
                                'data': lead_data,
                            }
                            lead_objects.append(SalesRabbit_Lead(id=lead_data['id'], **defaults))

                        # Perform bulk create or update
                        SalesRabbit_Lead.objects.bulk_create(lead_objects, ignore_conflicts=True)
                        SalesRabbit_Lead.objects.bulk_update(lead_objects, fields=defaults.keys())
                    except Exception as e:
                        logger.error(f"Failed to save batch {i // batch_size + 1}: {str(e)}")
                        print(f"[ERROR] Exception saving batch {i // batch_size + 1}: {e}")

                    # Update progress bar
                    current = i + len(batch)
                    percent = (current / total_leads) * 100
                    print(f"\rProgress: [{'#' * int(percent // 2)}{'-' * (50 - int(percent // 2))}] {percent:.2f}% ({current}/{total_leads})", end='')
                print()  # New line after progress bar

                all_leads.extend(leads)
                if len(leads) < page_size:
                    break  # Last page
                page += 1
                if max_pages and page > max_pages:
                    break
            except Exception as e:
                logger.error(f"Failed to fetch leads on page {page}: {e}")
                print(f"[ERROR] Exception fetching leads on page {page}: {e}")
                break
        print(f"[DEBUG] Returning {len(all_leads)} total leads")
        return {'data': all_leads}

    def test_connection(self):
        """Test connection to SalesRabbit API"""
        # Try fetching a small sample of leads
        test_url = f"{self.base_url}/leads?limit=1"
        try:
            response = requests.get(test_url, headers=self.headers, timeout=10)
            response.raise_for_status()
            return True, response.json()
        except Exception as e:
            logger.error(f"SalesRabbit connection test failed: {e}")
            return False, str(e)
