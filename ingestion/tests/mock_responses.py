"""
Mock API responses and test data for CRM command testing.
Provides realistic mock responses for different CRM systems.
"""

import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
from unittest.mock import Mock


class MockResponseGenerator:
    """Generates mock API responses for different CRM systems"""
    
    @staticmethod
    def hubspot_contacts_response(count: int = 50) -> Dict[str, Any]:
        """Generate mock HubSpot contacts API response"""
        contacts = []
        for i in range(count):
            contacts.append({
                "id": f"hubspot_contact_{i+1}",
                "properties": {
                    "firstname": f"John{i+1}",
                    "lastname": f"Doe{i+1}",
                    "email": f"john.doe{i+1}@example.com",
                    "phone": f"+1555000{i+1:04d}",
                    "createdate": "2024-01-15T10:30:00Z",
                    "lastmodifieddate": "2024-01-16T14:22:00Z",
                    "lifecyclestage": "lead",
                    "hs_lead_status": "NEW"
                },
                "createdAt": "2024-01-15T10:30:00Z",
                "updatedAt": "2024-01-16T14:22:00Z",
                "archived": False
            })
        
        return {
            "results": contacts,
            "paging": {
                "next": {
                    "after": f"contact_{count}",
                    "link": "https://api.hubapi.com/crm/v3/objects/contacts?limit=100&after=contact_50"
                } if count >= 50 else None
            }
        }
    
    @staticmethod
    def hubspot_companies_response(count: int = 30) -> Dict[str, Any]:
        """Generate mock HubSpot companies API response"""
        companies = []
        for i in range(count):
            companies.append({
                "id": f"company_{i+1}",
                "properties": {
                    "name": f"Company {i+1} Inc",
                    "domain": f"company{i+1}.com",
                    "industry": "Technology",
                    "city": "New York",
                    "state": "NY",
                    "country": "United States",
                    "numberofemployees": 50 + i * 10,
                    "annualrevenue": 1000000 + i * 100000,
                    "createdate": "2024-01-10T09:15:00Z",
                    "hs_lastmodifieddate": "2024-01-17T11:30:00Z"
                }
            })
        
        return {
            "results": companies,
            "paging": {
                "next": {
                    "after": f"company_{count}"
                } if count >= 30 else None
            }
        }
    
    @staticmethod
    def salesrabbit_leads_response(count: int = 100) -> Dict[str, Any]:
        """Generate mock SalesRabbit leads API response"""
        leads = []
        for i in range(count):
            leads.append({
                "id": f"sr_lead_{i+1}",
                "firstName": f"Jane{i+1}",
                "lastName": f"Smith{i+1}",
                "email": f"jane.smith{i+1}@example.com",
                "phone": f"+1555100{i+1:04d}",
                "address": {
                    "street": f"{100+i} Main Street",
                    "city": "Phoenix",
                    "state": "AZ",
                    "zip": f"85001{i%10}"
                },
                "status": ["NEW", "CONTACTED", "QUALIFIED", "CLOSED"][i % 4],
                "source": "Website",
                "createdAt": "2024-01-12T08:45:00Z",
                "updatedAt": "2024-01-18T16:20:00Z",
                "assignedTo": f"rep_{(i % 5) + 1}",
                "customFields": {
                    "interest_level": ["Low", "Medium", "High"][i % 3],
                    "product_interest": "Solar Panels"
                }
            })
        
        return {
            "data": leads,
            "pagination": {
                "total": count,
                "page": 1,
                "pages": max(1, count // 100),
                "hasNext": count > 100
            }
        }
    
    @staticmethod
    def callrail_calls_response(count: int = 75) -> Dict[str, Any]:
        """Generate mock CallRail calls API response"""
        calls = []
        for i in range(count):
            calls.append({
                "id": f"call_{i+1}",
                "caller_id": f"+1555200{i+1:04d}",
                "business_phone_number": "+15551234567",
                "tracking_phone_number": f"+1555300{i+1:04d}",
                "duration": 120 + i * 5,
                "start_time": "2024-01-15T14:30:00Z",
                "direction": "inbound",
                "answered": True,
                "first_call": i % 3 == 0,
                "value": "qualified" if i % 4 == 0 else "unqualified",
                "source": {
                    "name": ["Google Ads", "Facebook", "Website", "Direct"][i % 4],
                    "medium": "cpc" if i % 2 == 0 else "organic"
                },
                "lead_status": ["new", "contacted", "converted"][i % 3],
                "tags": [f"tag_{i%3+1}"],
                "recording_url": f"https://app.callrail.com/calls/{i+1}/recording"
            })
        
        return {
            "calls": calls,
            "total_records": count,
            "page": 1,
            "per_page": 100
        }
    
    @staticmethod
    def arrivy_orders_response(count: int = 40) -> Dict[str, Any]:
        """Generate mock Arrivy orders API response"""
        orders = []
        for i in range(count):
            orders.append({
                "id": f"order_{i+1}",
                "customer_name": f"Customer {i+1}",
                "customer_email": f"customer{i+1}@example.com",
                "customer_phone": f"+1555400{i+1:04d}",
                "service_type": ["Installation", "Maintenance", "Repair"][i % 3],
                "status": ["scheduled", "in_progress", "completed", "cancelled"][i % 4],
                "scheduled_date": "2024-01-20T10:00:00Z",
                "actual_start": "2024-01-20T10:15:00Z",
                "actual_end": "2024-01-20T12:30:00Z",
                "technician": f"tech_{(i % 8) + 1}",
                "location": {
                    "address": f"{200+i} Oak Street",
                    "city": "Austin",
                    "state": "TX",
                    "zip": f"73301{i%10}"
                },
                "notes": f"Order notes for order {i+1}",
                "created_at": "2024-01-18T09:00:00Z",
                "updated_at": "2024-01-20T12:45:00Z"
            })
        
        return {
            "orders": orders,
            "total": count,
            "page": 1,
            "limit": 100
        }


class MockDatabaseResponses:
    """Mock database query responses for database-based CRMs"""
    
    @staticmethod
    def genius_leads_query_response(count: int = 200) -> List[tuple]:
        """Generate mock Genius database query response"""
        leads = []
        for i in range(count):
            leads.append((
                i + 1,  # id
                f"Lead{i+1}",  # first_name
                f"Customer{i+1}",  # last_name
                f"lead{i+1}@example.com",  # email
                f"+1555500{i+1:04d}",  # phone
                "2024-01-15 10:30:00",  # created_date
                "2024-01-18 14:22:00",  # modified_date
                ["New", "Contacted", "Qualified", "Closed", "Lost"][i % 5],  # status
                f"source_{(i % 10) + 1}",  # source
                50000 + i * 1000  # estimated_value
            ))
        return leads
    
    @staticmethod
    def genius_appointments_query_response(count: int = 150) -> List[tuple]:
        """Generate mock Genius appointments query response"""
        appointments = []
        for i in range(count):
            appointments.append((
                i + 1,  # appointment_id
                (i % 200) + 1,  # lead_id (references leads)
                "2024-01-22 14:00:00",  # scheduled_datetime
                60 + i * 5,  # duration_minutes
                ["scheduled", "completed", "cancelled", "no_show"][i % 4],  # status
                f"rep_{(i % 12) + 1}",  # assigned_rep
                f"Appointment notes {i+1}",  # notes
                "2024-01-19 11:15:00"  # created_date
            ))
        return appointments
    
    @staticmethod
    def salespro_customers_query_response(count: int = 120) -> List[tuple]:
        """Generate mock SalesPro database query response"""
        customers = []
        for i in range(count):
            customers.append((
                i + 1,  # customer_id
                f"SalesPro{i+1}",  # first_name
                f"Client{i+1}",  # last_name
                f"client{i+1}@example.com",  # email_address
                f"+1555600{i+1:04d}",  # primary_phone
                f"{300+i} Pine Street",  # street_address
                "Denver",  # city
                "CO",  # state
                f"80201{i%10}",  # zip_code
                ["Active", "Inactive", "Prospect"][i % 3],  # customer_status
                "2024-01-14 16:45:00",  # date_created
                25000 + i * 500  # lifetime_value
            ))
        return customers


class MockHTTPResponses:
    """Mock HTTP response objects for testing"""
    
    @staticmethod
    def create_success_response(data: Dict[str, Any], status_code: int = 200) -> Mock:
        """Create a mock successful HTTP response"""
        response = Mock()
        response.status_code = status_code
        response.json.return_value = data
        response.text = json.dumps(data)
        response.headers = {
            'Content-Type': 'application/json',
            'X-RateLimit-Remaining': '95',
            'X-RateLimit-Reset': '1642678800'
        }
        response.raise_for_status.return_value = None
        return response
    
    @staticmethod
    def create_error_response(status_code: int, error_message: str = "API Error") -> Mock:
        """Create a mock error HTTP response"""
        response = Mock()
        response.status_code = status_code
        
        error_data = {
            "error": {
                "message": error_message,
                "code": status_code,
                "timestamp": datetime.utcnow().isoformat()
            }
        }
        
        response.json.return_value = error_data
        response.text = json.dumps(error_data)
        response.headers = {'Content-Type': 'application/json'}
        
        def raise_for_status():
            if status_code >= 400:
                raise Exception(f"HTTP {status_code}: {error_message}")
        
        response.raise_for_status.side_effect = raise_for_status
        return response
    
    @staticmethod
    def create_rate_limit_response() -> Mock:
        """Create a mock rate limit (429) response"""
        return MockHTTPResponses.create_error_response(
            429, "Rate limit exceeded. Please retry after 60 seconds."
        )
    
    @staticmethod
    def create_timeout_response() -> Mock:
        """Create a mock timeout response"""
        response = Mock()
        response.raise_for_status.side_effect = Exception("Request timeout")
        return response


class MockAuthResponses:
    """Mock authentication and credential responses"""
    
    @staticmethod
    def hubspot_auth_success():
        """Mock successful HubSpot authentication"""
        return {
            "access_token": "mock_hubspot_token_12345",
            "refresh_token": "mock_hubspot_refresh_67890",
            "expires_in": 3600,
            "token_type": "bearer",
            "scope": "contacts companies deals"
        }
    
    @staticmethod
    def salesrabbit_auth_success():
        """Mock successful SalesRabbit authentication"""
        return {
            "api_key": "mock_salesrabbit_key_abcdef",
            "user_id": "mock_user_123",
            "account_id": "mock_account_456",
            "permissions": ["leads:read", "leads:write", "reports:read"]
        }
    
    @staticmethod
    def callrail_auth_success():
        """Mock successful CallRail authentication"""
        return {
            "token": "mock_callrail_token_xyz789",
            "account": {
                "id": "mock_account_789",
                "name": "Test Company Account",
                "timezone": "America/New_York"
            }
        }


class TestDataFactory:
    """Factory for creating test data sets"""
    
    @staticmethod
    def create_mixed_status_responses(success_count: int = 80, error_count: int = 20):
        """Create a mix of successful and error responses"""
        responses = []
        
        # Add successful responses
        for i in range(success_count):
            data = MockResponseGenerator.hubspot_contacts_response(count=10)
            responses.append(MockHTTPResponses.create_success_response(data))
        
        # Add error responses
        error_codes = [400, 401, 403, 404, 429, 500, 502, 503]
        for i in range(error_count):
            status_code = error_codes[i % len(error_codes)]
            responses.append(MockHTTPResponses.create_error_response(status_code))
        
        return responses
    
    @staticmethod
    def create_pagination_scenario(total_records: int = 500, page_size: int = 100):
        """Create a multi-page response scenario"""
        pages = []
        for page in range(0, total_records, page_size):
            page_count = min(page_size, total_records - page)
            if page_count > 0:
                data = MockResponseGenerator.hubspot_contacts_response(count=page_count)
                # Adjust pagination info
                data["paging"]["next"] = {
                    "after": f"record_{page + page_count}",
                    "link": f"https://api.example.com/contacts?after=record_{page + page_count}"
                } if page + page_count < total_records else None
                
                pages.append(MockHTTPResponses.create_success_response(data))
        
        return pages
    
    @staticmethod
    def create_rate_limiting_scenario(initial_success: int = 50, rate_limited: int = 5, recovery: int = 20):
        """Create a rate limiting scenario with recovery"""
        responses = []
        
        # Initial successful calls
        for i in range(initial_success):
            data = MockResponseGenerator.hubspot_contacts_response(count=100)
            responses.append(MockHTTPResponses.create_success_response(data))
        
        # Rate limited responses
        for i in range(rate_limited):
            responses.append(MockHTTPResponses.create_rate_limit_response())
        
        # Recovery responses
        for i in range(recovery):
            data = MockResponseGenerator.hubspot_contacts_response(count=100)
            responses.append(MockHTTPResponses.create_success_response(data))
        
        return responses


# Pre-built test scenarios
COMMON_TEST_SCENARIOS = {
    'hubspot_full_success': {
        'contacts': MockResponseGenerator.hubspot_contacts_response(100),
        'companies': MockResponseGenerator.hubspot_companies_response(50),
        'response': MockHTTPResponses.create_success_response
    },
    'salesrabbit_mixed_results': {
        'leads': MockResponseGenerator.salesrabbit_leads_response(200),
        'responses': TestDataFactory.create_mixed_status_responses(150, 50)
    },
    'callrail_rate_limiting': {
        'calls': MockResponseGenerator.callrail_calls_response(300),
        'responses': TestDataFactory.create_rate_limiting_scenario()
    },
    'database_large_dataset': {
        'genius_leads': MockDatabaseResponses.genius_leads_query_response(1000),
        'genius_appointments': MockDatabaseResponses.genius_appointments_query_response(750)
    }
}
