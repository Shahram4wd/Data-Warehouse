#!/usr/bin/env python3
"""
SalesRabbit API Authentication Test
Tests different authentication methods to determine the correct way to authenticate.
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

class SalesRabbitAuthTester:
    def __init__(self):
        self.base_url = "https://app.salesrabbit.com/api/v1"
        self.api_token = getattr(settings, 'SALESRABBIT_API_TOKEN', None)
        print(f"🔑 API Token: {self.api_token[:20]}...{self.api_token[-10:] if len(self.api_token) > 30 else self.api_token}")
        
    def test_auth_method_1_bearer_token(self):
        """Test using Bearer token in Authorization header"""
        print("\n🔐 Testing Method 1: Bearer Token in Authorization header")
        headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return self._test_request(headers, "Bearer Auth")
    
    def test_auth_method_2_api_key_header(self):
        """Test using API key in custom header"""
        print("\n🔐 Testing Method 2: API Key in custom header")
        headers = {
            'X-API-Key': self.api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return self._test_request(headers, "API Key Header")
    
    def test_auth_method_3_api_token_header(self):
        """Test using API token in custom header"""
        print("\n🔐 Testing Method 3: API Token in custom header")
        headers = {
            'X-API-Token': self.api_token,
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return self._test_request(headers, "API Token Header")
    
    def test_auth_method_4_query_param(self):
        """Test using API token as query parameter"""
        print("\n🔐 Testing Method 4: API Token as query parameter")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {'api_token': self.api_token}
        return self._test_request(headers, "Query Param", params=params)
    
    def test_auth_method_5_api_key_param(self):
        """Test using API key as query parameter"""
        print("\n🔐 Testing Method 5: API Key as query parameter")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {'api_key': self.api_token}
        return self._test_request(headers, "API Key Param", params=params)
    
    def test_auth_method_6_token_param(self):
        """Test using token as query parameter"""
        print("\n🔐 Testing Method 6: Token as query parameter")
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        params = {'token': self.api_token}
        return self._test_request(headers, "Token Param", params=params)
    
    def test_auth_method_7_authorization_header(self):
        """Test using Authorization header with token"""
        print("\n🔐 Testing Method 7: Authorization header with token")
        headers = {
            'Authorization': f'Token {self.api_token}',
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        }
        return self._test_request(headers, "Authorization Token")
    
    def _test_request(self, headers, method_name, params=None):
        """Make test request and analyze response"""
        try:
            url = f"{self.base_url}/leads"
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            print(f"  📡 {method_name}")
            print(f"     Status: {response.status_code}")
            print(f"     Headers: {dict(response.headers)}")
            
            if response.status_code == 200:
                try:
                    data = response.json()
                    print(f"     ✅ SUCCESS: {method_name}")
                    print(f"     Response: {json.dumps(data, indent=2)[:500]}...")
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
        """Run all authentication tests"""
        print("🚀 SalesRabbit API Authentication Tests")
        print("=" * 60)
        
        if not self.api_token:
            print("❌ No API token found in settings!")
            return
        
        methods = [
            self.test_auth_method_1_bearer_token,
            self.test_auth_method_2_api_key_header,
            self.test_auth_method_3_api_token_header,
            self.test_auth_method_4_query_param,
            self.test_auth_method_5_api_key_param,
            self.test_auth_method_6_token_param,
            self.test_auth_method_7_authorization_header,
        ]
        
        successful_methods = []
        
        for method in methods:
            success, data = method()
            if success:
                successful_methods.append(method.__name__)
        
        print("\n" + "=" * 60)
        print("📊 SUMMARY")
        print("=" * 60)
        
        if successful_methods:
            print(f"✅ Found {len(successful_methods)} working authentication method(s):")
            for method in successful_methods:
                print(f"  • {method}")
        else:
            print("❌ No working authentication methods found!")
            print("\nℹ️  Possible issues:")
            print("  • API token might be invalid or expired")
            print("  • API endpoint might be different")
            print("  • Additional authentication parameters might be required")
            print("  • Account might not have API access enabled")

if __name__ == "__main__":
    tester = SalesRabbitAuthTester()
    tester.run_all_tests()
