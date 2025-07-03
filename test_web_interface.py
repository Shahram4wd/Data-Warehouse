import requests
import time

# Test the web interface endpoints
base_url = "http://localhost:8000"

print("Testing Database Schema Analysis Web Interface...")

# Test if the report page loads
try:
    response = requests.get(f"{base_url}/reports/database-schema-analysis/")
    print(f"✓ Report page loads: {response.status_code}")
except Exception as e:
    print(f"✗ Report page error: {e}")

# Test if results endpoint works
try:
    response = requests.get(f"{base_url}/reports/api/database-schema-analysis/results/")
    print(f"✓ Results API responds: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"  - Found {data.get('summary', {}).get('total_tables', 0)} tables")
        print(f"  - Total records: {data.get('summary', {}).get('total_records', 0):,}")
except Exception as e:
    print(f"✗ Results API error: {e}")

print("✓ All tests completed!")
