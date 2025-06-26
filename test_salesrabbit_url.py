#!/usr/bin/env python3
"""
SalesRabbit API URL Test
Tests the correct API URL from settings.
"""
import os
import sys
import json
import requests
from datetime import datetime

# Add the Django project path
sys.path.append('/app')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')

import django
django.setup()

from django.conf import settings

class SalesRabbitURLTester:
    def __init__(self):
        self.api_token = getattr(settings, 'SALESRABBIT_API_TOKEN', None)
        self.api_url = getattr(settings, 'SALESRABBIT_API_URL', None)
        
        print(f"🔑 API Token: {self.api_token[:20]}...{self.api_token[-10:] if len(self.api_token) > 30 else self.api_token}")
        print(f"🌐 API URL from settings: {self.api_url}")
        
        # Test different URL variations
        self.test_urls = [
            self.api_url,
            f"{self.api_url}/v1",
            f"{self.api_url}/api",
            f"{self.api_url}/api/v1",
            "https://api.salesrabbit.com",
            "https://api.salesrabbit.com/v1",
            "https://app.salesrabbit.com/api",
            "https://app.salesrabbit.com/api/v1",
        ]
        
    def test_url_with_bearer_auth(self, base_url):
        """Test a URL with Bearer authentication"""
        print(f"\n🔍 Testing URL: {base_url}")
        
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Test different endpoints
        endpoints = ['/leads', '/users', '/profile', '/me', '/', '']
        
        for endpoint in endpoints:
            try:
                test_url = f"{base_url.rstrip('/')}{endpoint}"
                print(f"  📡 {test_url}")
                
                response = requests.get(test_url, headers=headers, timeout=10)
                print(f"     Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"     ✅ SUCCESS")
                        print(f"     Response: {json.dumps(data, indent=2)[:200]}...")
                        
                        # If we get a successful response, save it
                        if data.get('success') == True or 'error' not in data:
                            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                            filename = f"salesrabbit_success_response_{timestamp}.json"
                            with open(filename, 'w') as f:
                                json.dump(data, f, indent=2)
                            print(f"     💾 Saved successful response to: {filename}")
                            return True, test_url, data
                        elif 'Device authentication failed' in str(data):
                            print(f"     ⚠️  Device auth issue - but URL works!")
                            return True, test_url, data
                        else:
                            print(f"     ❌ Error in response: {data}")
                            
                    except json.JSONDecodeError:
                        print(f"     📄 Non-JSON response: {response.text[:100]}...")
                        
                elif response.status_code == 404:
                    print(f"     404 - Endpoint not found")
                elif response.status_code == 401:
                    print(f"     401 - Unauthorized")
                elif response.status_code == 403:
                    print(f"     403 - Forbidden")
                else:
                    print(f"     {response.status_code} - {response.text[:100]}...")
                    
            except requests.exceptions.ConnectionError:
                print(f"     ❌ Connection failed")
                break
            except Exception as e:
                print(f"     ❌ Error: {str(e)}")
                break
                
        return False, None, None
        
    def run_all_tests(self):
        """Test all URL variations"""
        print("🚀 SalesRabbit API URL Tests")
        print("=" * 60)
        
        if not self.api_token:
            print("❌ No API token found in settings!")
            return
            
        if not self.api_url:
            print("❌ No API URL found in settings!")
            return
        
        working_urls = []
        
        for test_url in self.test_urls:
            success, final_url, data = self.test_url_with_bearer_auth(test_url)
            if success:
                working_urls.append((final_url, data))
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        if working_urls:
            print(f"✅ Found {len(working_urls)} working URL(s):")
            for url, data in working_urls:
                print(f"  • {url}")
                if data.get('success') == True:
                    print(f"    ✅ Fully authenticated")
                elif 'Device authentication failed' in str(data):
                    print(f"    ⚠️  Needs device authentication")
                else:
                    print(f"    ❓ Response: {str(data)[:50]}...")
        else:
            print("❌ No working URLs found!")
            print("\nℹ️  Next steps:")
            print("  • Check if API token is valid")
            print("  • Verify SalesRabbit API documentation")
            print("  • Contact SalesRabbit support for API access")

if __name__ == "__main__":
    tester = SalesRabbitURLTester()
    tester.run_all_tests()
