#!/usr/bin/env python3
"""
SalesRabbit API Test Script
Tests connection and analyzes lead response structure
"""

import os
import sys
import django
import json
import requests
from datetime import datetime

# Setup Django environment
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from django.conf import settings

class SalesRabbitAPITester:
    """Test class for SalesRabbit API analysis"""
    
    def __init__(self):
        self.api_token = getattr(settings, 'SALESRABBIT_API_TOKEN', None)
        self.base_url = "https://app.salesrabbit.com/api/v1"
        
        if not self.api_token:
            raise ValueError("SALESRABBIT_API_TOKEN not found in settings")
        
        self.headers = {
            "Authorization": f"Token {self.api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "DataWarehouse/1.0"
        }
        
        print(f"🔧 SalesRabbit API Tester initialized")
        print(f"📍 Base URL: {self.base_url}")
        print(f"🔑 API Token: {self.api_token[:12]}...{self.api_token[-4:]}")
        print("-" * 60)

    def test_connection(self):
        """Test basic API connectivity"""
        print("🔍 Testing API connection...")
        
        # Try the most basic endpoint first
        test_endpoints = [
            "/leads",
            "/leads?limit=1",
            "/user",
            "/teams",
            "/areas"
        ]
        
        for endpoint in test_endpoints:
            url = f"{self.base_url}{endpoint}"
            print(f"  📡 Testing: {endpoint}")
            
            try:
                response = requests.get(url, headers=self.headers, timeout=30)
                print(f"     Status: {response.status_code}")
                print(f"     Headers: {dict(response.headers)}")
                
                if response.status_code == 200:
                    print(f"     ✅ SUCCESS: {endpoint}")
                    content_type = response.headers.get('content-type', '')
                    print(f"     Content-Type: {content_type}")
                    
                    if 'application/json' in content_type:
                        try:
                            data = response.json()
                            print(f"     📊 JSON Response: {len(str(data))} characters")
                            return True, endpoint, data
                        except json.JSONDecodeError:
                            print(f"     ⚠️  Invalid JSON response")
                    else:
                        print(f"     📄 Raw response (first 200 chars): {response.text[:200]}")
                        
                elif response.status_code == 401:
                    print(f"     🔒 UNAUTHORIZED: Check API token")
                elif response.status_code == 403:
                    print(f"     🚫 FORBIDDEN: Insufficient permissions")
                elif response.status_code == 404:
                    print(f"     ❌ NOT FOUND: Endpoint doesn't exist")
                elif response.status_code == 429:
                    print(f"     ⏰ RATE LIMITED: Too many requests")
                else:
                    print(f"     ❌ ERROR: {response.status_code}")
                    print(f"     Response: {response.text[:200]}")
                    
            except requests.exceptions.Timeout:
                print(f"     ⏰ TIMEOUT: Request took too long")
            except requests.exceptions.ConnectionError:
                print(f"     🔌 CONNECTION ERROR: Cannot reach server")
            except Exception as e:
                print(f"     💥 EXCEPTION: {str(e)}")
            
            print()
        
        return False, None, None

    def analyze_leads_endpoint(self, sample_data=None):
        """Analyze the leads endpoint response structure"""
        print("🔬 Analyzing leads endpoint...")
        
        if not sample_data:
            # Fetch sample data
            url = f"{self.base_url}/leads"
            params = {"limit": 10}  # Get a small sample
            
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=30)
                if response.status_code != 200:
                    print(f"❌ Failed to fetch leads: {response.status_code}")
                    print(f"Response: {response.text}")
                    return
                
                sample_data = response.json()
            except Exception as e:
                print(f"💥 Error fetching leads: {str(e)}")
                return
        
        # Analyze response structure
        print(f"📊 Response Analysis:")
        print(f"  Type: {type(sample_data)}")
        
        if isinstance(sample_data, dict):
            print(f"  Keys: {list(sample_data.keys())}")
            
            # Look for common pagination patterns
            for key in ['data', 'results', 'leads', 'items']:
                if key in sample_data:
                    leads = sample_data[key]
                    print(f"  📋 Found leads array in '{key}': {len(leads) if isinstance(leads, list) else 'not a list'}")
                    
                    if isinstance(leads, list) and leads:
                        self._analyze_lead_structure(leads[0])
                    break
            
            # Look for pagination info
            pagination_keys = ['pagination', 'meta', 'page_info', 'total', 'count', 'next', 'previous']
            for key in pagination_keys:
                if key in sample_data:
                    print(f"  📄 Pagination info in '{key}': {sample_data[key]}")
                    
        elif isinstance(sample_data, list):
            print(f"  📋 Direct array response: {len(sample_data)} items")
            if sample_data:
                self._analyze_lead_structure(sample_data[0])
        
        # Save full response for analysis
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"salesrabbit_leads_response_{timestamp}.json"
        
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(sample_data, f, indent=2, default=str)
            print(f"💾 Full response saved to: {filename}")
        except Exception as e:
            print(f"⚠️  Could not save response: {str(e)}")

    def _analyze_lead_structure(self, lead_sample):
        """Analyze the structure of a single lead object"""
        print(f"\n🧬 Lead Object Structure Analysis:")
        print(f"  Type: {type(lead_sample)}")
        
        if isinstance(lead_sample, dict):
            print(f"  Fields count: {len(lead_sample)}")
            print(f"  Fields:")
            
            # Group fields by type for better analysis
            field_types = {}
            important_fields = []
            
            for key, value in lead_sample.items():
                field_type = type(value).__name__
                if field_type not in field_types:
                    field_types[field_type] = []
                field_types[field_type].append(key)
                
                # Mark potentially important fields
                important_keywords = ['id', 'name', 'email', 'phone', 'address', 'created', 'updated', 'status', 'source']
                if any(keyword in key.lower() for keyword in important_keywords):
                    important_fields.append((key, value))
                
                # Show first few characters of values for analysis
                if isinstance(value, (str, int, float)):
                    display_value = str(value)[:50] + ("..." if len(str(value)) > 50 else "")
                    print(f"    {key}: {display_value} ({field_type})")
                elif isinstance(value, (list, dict)):
                    print(f"    {key}: {field_type} with {len(value) if hasattr(value, '__len__') else '?'} items")
                else:
                    print(f"    {key}: {field_type}")
            
            print(f"\n📊 Field Types Summary:")
            for field_type, fields in field_types.items():
                print(f"  {field_type}: {len(fields)} fields ({', '.join(fields[:3])}{'...' if len(fields) > 3 else ''})")
            
            if important_fields:
                print(f"\n⭐ Important Fields Detected:")
                for key, value in important_fields:
                    display_value = str(value)[:100] + ("..." if len(str(value)) > 100 else "")
                    print(f"  {key}: {display_value}")

    def test_different_methods(self):
        """Test different HTTP methods and parameters"""
        print("🔧 Testing different request methods and parameters...")
        
        base_endpoint = "/leads"
        
        # Test different parameters
        test_params = [
            {},
            {"limit": 1},
            {"limit": 5},
            {"page": 1},
            {"per_page": 5},
            {"offset": 0},
            {"fields": "id,name,email"},
        ]
        
        for i, params in enumerate(test_params, 1):
            print(f"  Test {i}: {params}")
            url = f"{self.base_url}{base_endpoint}"
            
            try:
                response = requests.get(url, headers=self.headers, params=params, timeout=15)
                print(f"    Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if isinstance(data, list):
                            print(f"    ✅ Array response: {len(data)} items")
                        elif isinstance(data, dict):
                            print(f"    ✅ Object response: {list(data.keys())}")
                    except json.JSONDecodeError:
                        print(f"    ⚠️  Non-JSON response: {response.text[:100]}")
                else:
                    print(f"    ❌ Error: {response.text[:100]}")
                    
            except Exception as e:
                print(f"    💥 Exception: {str(e)}")
            
            print()

    def discover_endpoints(self):
        """Try to discover available API endpoints"""
        print("🕵️ Discovering available endpoints...")
        
        # Common API endpoint patterns
        potential_endpoints = [
            "/",
            "/leads",
            "/users", 
            "/user",
            "/teams",
            "/areas",
            "/territories", 
            "/activities",
            "/appointments",
            "/customers",
            "/contacts",
            "/sales",
            "/reports",
            "/stats",
            "/settings",
            "/account",
            "/profile"
        ]
        
        working_endpoints = []
        
        for endpoint in potential_endpoints:
            url = f"{self.base_url}{endpoint}"
            
            try:
                response = requests.get(url, headers=self.headers, timeout=10)
                status = response.status_code
                
                if status == 200:
                    print(f"  ✅ {endpoint} - WORKING")
                    working_endpoints.append(endpoint)
                elif status == 401:
                    print(f"  🔒 {endpoint} - UNAUTHORIZED (endpoint exists)")
                    working_endpoints.append(f"{endpoint} (auth required)")
                elif status == 403:
                    print(f"  🚫 {endpoint} - FORBIDDEN (endpoint exists)")
                    working_endpoints.append(f"{endpoint} (forbidden)")
                elif status == 404:
                    print(f"  ❌ {endpoint} - NOT FOUND")
                elif status == 405:
                    print(f"  📝 {endpoint} - METHOD NOT ALLOWED (try POST?)")
                    working_endpoints.append(f"{endpoint} (different method)")
                else:
                    print(f"  ⚠️  {endpoint} - {status}")
                    
            except Exception as e:
                print(f"  💥 {endpoint} - ERROR: {str(e)}")
        
        print(f"\n📋 Summary: Found {len(working_endpoints)} potentially working endpoints:")
        for endpoint in working_endpoints:
            print(f"  • {endpoint}")

def main():
    """Main test function"""
    print("🚀 SalesRabbit API Test & Analysis")
    print("=" * 60)
    
    try:
        tester = SalesRabbitAPITester()
        
        # Test 1: Basic connection
        success, working_endpoint, sample_data = tester.test_connection()
        
        if success:
            print(f"🎉 SUCCESS: Found working endpoint: {working_endpoint}")
            
            # Test 2: Analyze the working endpoint (likely leads)
            if 'leads' in working_endpoint:
                tester.analyze_leads_endpoint(sample_data)
            
            # Test 3: Try different parameters
            tester.test_different_methods()
        else:
            print("❌ No working endpoints found with basic tests")
        
        # Test 4: Endpoint discovery
        tester.discover_endpoints()
        
    except Exception as e:
        print(f"💥 Fatal error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
