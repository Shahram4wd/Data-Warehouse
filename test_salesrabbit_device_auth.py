#!/usr/bin/env python3
"""
SalesRabbit API Device Authentication Test
Tests device-specific authentication patterns.
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

class SalesRabbitDeviceAuthTester:
    def __init__(self):
        self.base_url = "https://app.salesrabbit.com/api/v1"
        self.api_token = getattr(settings, 'SALESRABBIT_API_TOKEN', None)
        print(f"🔑 API Token: {self.api_token[:20]}...{self.api_token[-10:] if len(self.api_token) > 30 else self.api_token}")
        
    def test_device_auth_with_user_agent(self):
        """Test with specific User-Agent"""
        print("\n🔐 Testing with User-Agent device identifier")
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'User-Agent': 'SalesRabbit-DataWarehouse/1.0'
        }
        return self._test_request(headers, "Device User-Agent")
    
    def test_device_auth_with_device_id(self):
        """Test with device ID parameter"""
        print("\n🔐 Testing with device_id parameter")
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {'device_id': 'data-warehouse-001'}
        return self._test_request(headers, "Device ID Param", params=params)
    
    def test_device_auth_with_device_header(self):
        """Test with device header"""
        print("\n🔐 Testing with X-Device-ID header")
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'X-Device-ID': 'data-warehouse-001'
        }
        return self._test_request(headers, "Device Header")
    
    def test_auth_info_endpoint(self):
        """Test authentication info endpoint"""
        print("\n🔐 Testing authentication info endpoint")
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        try:
            # Try different auth-related endpoints
            auth_endpoints = ['/auth', '/authenticate', '/auth/check', '/me', '/profile', '/user']
            for endpoint in auth_endpoints:
                print(f"  🔍 Testing {endpoint}")
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=headers, timeout=10)
                print(f"     Status: {response.status_code}")
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"     ✅ SUCCESS: {endpoint}")
                        print(f"     Response: {json.dumps(data, indent=2)[:300]}...")
                        return True, data
                    except json.JSONDecodeError:
                        print(f"     📄 HTML/Text response: {response.text[:100]}...")
                else:
                    print(f"     Response: {response.text[:100]}...")
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
        return False, None
    
    def test_post_authentication(self):
        """Test POST authentication"""
        print("\n🔐 Testing POST authentication")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        # Try POST with token in body
        auth_data = {
            'api_token': self.api_token,
            'device_id': 'data-warehouse-001'
        }
        
        try:
            url = f"{self.base_url}/authenticate"
            response = requests.post(url, headers=headers, json=auth_data, timeout=10)
            print(f"  📡 POST Authentication")
            print(f"     Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"     ✅ SUCCESS: POST Auth")
                    print(f"     Response: {json.dumps(data, indent=2)[:300]}...")
                    return True, data
                except json.JSONDecodeError:
                    print(f"     📄 Non-JSON response: {response.text[:100]}...")
            else:
                print(f"     Response: {response.text[:100]}...")
                
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
        
        return False, None
    
    def test_basic_endpoints_without_auth(self):
        """Test basic endpoints to see what's available without auth"""
        print("\n🔐 Testing endpoints without authentication")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        
        endpoints = ['/', '/version', '/info', '/status', '/health']
        working_endpoints = []
        
        for endpoint in endpoints:
            try:
                url = f"{self.base_url}{endpoint}"
                response = requests.get(url, headers=headers, timeout=10)
                print(f"  📡 {endpoint}")
                print(f"     Status: {response.status_code}")
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        print(f"     ✅ SUCCESS: {endpoint}")
                        print(f"     Response: {json.dumps(data, indent=2)[:200]}...")
                        working_endpoints.append(endpoint)
                    except json.JSONDecodeError:
                        print(f"     📄 Text response: {response.text[:100]}...")
                        if 'html' not in response.text.lower():
                            working_endpoints.append(endpoint)
                else:
                    print(f"     Response: {response.text[:100]}...")
                    
            except Exception as e:
                print(f"     ❌ Error: {str(e)}")
        
        return working_endpoints
    
    def _test_request(self, headers, method_name, params=None):
        """Make test request and analyze response"""
        try:
            url = f"{self.base_url}/leads"
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            print(f"  📡 {method_name}")
            print(f"     Status: {response.status_code}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"     ✅ SUCCESS: {method_name}")
                    print(f"     Response: {json.dumps(data, indent=2)[:300]}...")
                    return True, data
                except json.JSONDecodeError:
                    print(f"     ❌ Invalid JSON response")
                    print(f"     Content: {response.text[:200]}...")
                    return False, None
            else:
                print(f"     ❌ Failed with status {response.status_code}")
                print(f"     Response: {response.text[:200]}...")
                return False, None
                
        except Exception as e:
            print(f"     ❌ Error: {str(e)}")
            return False, None
    
    def run_all_tests(self):
        """Run all device authentication tests"""
        print("🚀 SalesRabbit API Device Authentication Tests")
        print("=" * 60)
        
        if not self.api_token:
            print("❌ No API token found in settings!")
            return
        
        # Test device authentication methods
        print("\n📱 DEVICE AUTHENTICATION TESTS")
        print("-" * 40)
        
        device_methods = [
            self.test_device_auth_with_user_agent,
            self.test_device_auth_with_device_id,
            self.test_device_auth_with_device_header,
        ]
        
        successful_methods = []
        
        for method in device_methods:
            success, data = method()
            if success:
                successful_methods.append(method.__name__)
        
        # Test authentication endpoints
        print("\n🔍 AUTHENTICATION ENDPOINT TESTS")
        print("-" * 40)
        success, data = self.test_auth_info_endpoint()
        if success:
            successful_methods.append("auth_info_endpoint")
        
        # Test POST authentication
        print("\n📤 POST AUTHENTICATION TESTS")
        print("-" * 40)
        success, data = self.test_post_authentication()
        if success:
            successful_methods.append("post_authentication")
        
        # Test basic endpoints
        print("\n🌐 BASIC ENDPOINT TESTS")
        print("-" * 40)
        working_endpoints = self.test_basic_endpoints_without_auth()
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        if successful_methods:
            print(f"✅ Found {len(successful_methods)} working authentication method(s):")
            for method in successful_methods:
                print(f"  • {method}")
        else:
            print("❌ No working device authentication methods found!")
        
        if working_endpoints:
            print(f"\n🌐 Found {len(working_endpoints)} working basic endpoint(s):")
            for endpoint in working_endpoints:
                print(f"  • {endpoint}")

if __name__ == "__main__":
    tester = SalesRabbitDeviceAuthTester()
    tester.run_all_tests()
