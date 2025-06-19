#!/usr/bin/env python3

import requests
import json

# Test different authentication methods for Arrivy API

# Credentials from working script
auth_key = "Q6ImbkFdlr349S8zO1nVMJ"
api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoiYWNjZXNzIiwiZXhwIjoxNzY3Njk5NzE0LCJpYXQiOjE3MzYxNjM3MTQsImp0aSI6IjFlN2YwNWFlMTEzNjRkYjc5NmY4OWJkNmNjOTkxOGY4IiwidXNlcl9pZCI6OX0.fPaZ1vV2o_M7Zl6_KwH9eoJdRwMnOKYqwYzp5M74Q8M"
base_url = "https://app.arrivy.com/api/"

def test_auth_method_1():
    """Test with X-Auth-Key and X-Auth-Token headers"""
    print("Testing auth method 1: X-Auth-Key and X-Auth-Token headers")
    
    headers = {
        "Content-Type": "application/json",
        "X-Auth-Key": auth_key,
        "X-Auth-Token": api_key
    }
    
    params = {"page_size": 1, "page": 1}
    
    try:
        response = requests.get(f"{base_url}customers", headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_auth_method_2():
    """Test with Authorization header"""
    print("\nTesting auth method 2: Authorization header with Bearer token")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "X-Auth-Key": auth_key
    }
    
    params = {"page_size": 1, "page": 1}
    
    try:
        response = requests.get(f"{base_url}customers", headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_auth_method_3():
    """Test with query parameters"""
    print("\nTesting auth method 3: Query parameters")
    
    headers = {
        "Content-Type": "application/json"
    }
    
    params = {
        "page_size": 1, 
        "page": 1,
        "auth_key": auth_key,
        "api_key": api_key
    }
    
    try:
        response = requests.get(f"{base_url}customers", headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

def test_auth_method_4():
    """Test with different header names"""
    print("\nTesting auth method 4: Alternative header names")
    
    headers = {
        "Content-Type": "application/json",
        "auth_key": auth_key,
        "token": api_key
    }
    
    params = {"page_size": 1, "page": 1}
    
    try:
        response = requests.get(f"{base_url}customers", headers=headers, params=params, timeout=30)
        print(f"Status: {response.status_code}")
        print(f"Headers: {dict(response.headers)}")
        print(f"Body: {response.text[:500]}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing Arrivy API authentication methods...")
    print("=" * 60)
    
    methods = [
        test_auth_method_1,
        test_auth_method_2,
        test_auth_method_3,
        test_auth_method_4
    ]
    
    for method in methods:
        success = method()
        if success:
            print("✅ SUCCESS!")
            break
        else:
            print("❌ FAILED")
    
    print("\nTest complete.")
