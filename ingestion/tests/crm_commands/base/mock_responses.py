"""
Mock API responses for CRM command testing

Provides realistic mock data for all CRM systems to enable
comprehensive testing without hitting real APIs.
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
import json


class CRMMockResponses:
    """
    Centralized mock API responses for all CRM systems
    
    Provides realistic test data that matches actual API response formats
    from each CRM system.
    """
    
    @staticmethod
    def get_arrivy_responses() -> Dict[str, Any]:
        """Mock responses for Arrivy API"""
        base_time = datetime.now()
        
        return {
            'entities': {
                'entities': [
                    {
                        'id': 1001,
                        'name': 'John Smith',
                        'email': 'john.smith@example.com',
                        'phone': '+1-555-0101',
                        'status': 'active',
                        'created_at': (base_time - timedelta(days=30)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                        'external_id': 'ext_1001',
                        'timezone': 'America/New_York',
                    },
                    {
                        'id': 1002,
                        'name': 'Jane Doe', 
                        'email': 'jane.doe@example.com',
                        'phone': '+1-555-0102',
                        'status': 'active',
                        'created_at': (base_time - timedelta(days=15)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                        'external_id': 'ext_1002',
                        'timezone': 'America/Los_Angeles',
                    }
                ],
                'total': 2,
                'page': 1,
                'per_page': 100
            },
            'tasks': {
                'tasks': [
                    {
                        'id': 2001,
                        'title': 'Installation Appointment',
                        'description': 'Install solar panels at customer location',
                        'status': 'pending',
                        'entity_id': 1001,
                        'created_at': (base_time - timedelta(days=1)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=3)).isoformat() + 'Z',
                        'start_datetime': (base_time + timedelta(days=1)).isoformat() + 'Z',
                        'end_datetime': (base_time + timedelta(days=1, hours=2)).isoformat() + 'Z',
                    },
                    {
                        'id': 2002,
                        'title': 'Maintenance Check',
                        'description': 'Routine maintenance check',
                        'status': 'completed',
                        'entity_id': 1002,
                        'created_at': (base_time - timedelta(days=5)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(days=1)).isoformat() + 'Z',
                        'start_datetime': (base_time - timedelta(days=1)).isoformat() + 'Z',
                        'end_datetime': (base_time - timedelta(days=1, hours=-1)).isoformat() + 'Z',
                    }
                ],
                'total': 2,
                'page': 1,
                'per_page': 100
            },
            'groups': {
                'groups': [
                    {
                        'id': 3001,
                        'name': 'Installation Team Alpha',
                        'description': 'Primary installation team for residential',
                        'created_at': (base_time - timedelta(days=60)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(days=10)).isoformat() + 'Z',
                        'entity_count': 5,
                    }
                ],
                'total': 1,
                'page': 1,
                'per_page': 100
            }
        }
    
    @staticmethod
    def get_callrail_responses() -> Dict[str, Any]:
        """Mock responses for CallRail API"""
        base_time = datetime.now()
        
        return {
            'accounts': {
                'accounts': [
                    {
                        'id': 'AC1234567890abcdef',
                        'name': 'Test Company Account',
                        'plan': 'pro',
                        'created_at': (base_time - timedelta(days=365)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(days=1)).isoformat() + 'Z',
                        'status': 'active',
                        'timezone': 'America/New_York',
                    }
                ],
                'page': 1,
                'per_page': 100,
                'total_pages': 1,
                'total_records': 1
            },
            'companies': {
                'companies': [
                    {
                        'id': 'COM1234567890abcdef',
                        'name': 'Test Company',
                        'status': 'active', 
                        'created_at': (base_time - timedelta(days=200)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=6)).isoformat() + 'Z',
                        'account_id': 'AC1234567890abcdef',
                        'timezone': 'America/New_York',
                        'callscore_enabled': True,
                    }
                ],
                'page': 1,
                'per_page': 100,
                'total_pages': 1,
                'total_records': 1
            },
            'calls': {
                'calls': [
                    {
                        'id': 'CAL1234567890abcdef',
                        'company_id': 'COM1234567890abcdef',
                        'duration': 185,
                        'direction': 'inbound',
                        'answered': True,
                        'created_at': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                        'start_time': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                        'caller_number': '+15551234567',
                        'dialed_number': '+15559876543',
                        'source': 'search',
                        'value': 'high',
                    },
                    {
                        'id': 'CAL0987654321fedcba',
                        'company_id': 'COM1234567890abcdef',
                        'duration': 45,
                        'direction': 'outbound',
                        'answered': True,
                        'created_at': (base_time - timedelta(hours=4)).isoformat() + 'Z',
                        'start_time': (base_time - timedelta(hours=4)).isoformat() + 'Z',
                        'caller_number': '+15559876543',
                        'dialed_number': '+15551111111',
                        'source': 'direct',
                        'value': 'medium',
                    }
                ],
                'page': 1,
                'per_page': 100,
                'total_pages': 1,
                'total_records': 2
            }
        }
    
    @staticmethod
    def get_hubspot_responses() -> Dict[str, Any]:
        """Mock responses for HubSpot API"""
        base_time = datetime.now()
        
        return {
            'contacts': {
                'results': [
                    {
                        'id': '101',
                        'properties': {
                            'firstname': 'Alice',
                            'lastname': 'Johnson',
                            'email': 'alice.johnson@example.com',
                            'phone': '+1-555-0201',
                            'company': 'Example Corp',
                            'hs_createdate': (base_time - timedelta(days=45)).isoformat() + 'Z',
                            'hs_lastmodifieddate': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                            'lifecyclestage': 'lead',
                        },
                        'createdAt': (base_time - timedelta(days=45)).isoformat() + 'Z',
                        'updatedAt': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                    },
                    {
                        'id': '102',
                        'properties': {
                            'firstname': 'Bob',
                            'lastname': 'Wilson',
                            'email': 'bob.wilson@example.com',
                            'phone': '+1-555-0202',
                            'company': 'Wilson Industries',
                            'hs_createdate': (base_time - timedelta(days=20)).isoformat() + 'Z',
                            'hs_lastmodifieddate': (base_time - timedelta(hours=3)).isoformat() + 'Z',
                            'lifecyclestage': 'customer',
                        },
                        'createdAt': (base_time - timedelta(days=20)).isoformat() + 'Z',
                        'updatedAt': (base_time - timedelta(hours=3)).isoformat() + 'Z',
                    }
                ],
                'paging': {
                    'next': {'after': '102'}
                }
            },
            'deals': {
                'results': [
                    {
                        'id': '201',
                        'properties': {
                            'dealname': 'Solar Installation - Johnson',
                            'amount': '15000.00',
                            'dealstage': 'proposalsentdealstage',
                            'pipeline': 'default',
                            'hs_createdate': (base_time - timedelta(days=10)).isoformat() + 'Z',
                            'hs_lastmodifieddate': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                            'closedate': (base_time + timedelta(days=30)).isoformat() + 'Z',
                        },
                        'createdAt': (base_time - timedelta(days=10)).isoformat() + 'Z',
                        'updatedAt': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                    }
                ],
                'paging': {}
            }
        }
    
    @staticmethod
    def get_five9_responses() -> Dict[str, Any]:
        """Mock responses for Five9 API"""
        base_time = datetime.now()
        
        return {
            'contacts': [
                {
                    'id': 'F9_001',
                    'first_name': 'Charlie',
                    'last_name': 'Brown',
                    'phone': '+1-555-0301',
                    'email': 'charlie.brown@example.com',
                    'created_date': (base_time - timedelta(days=30)).isoformat(),
                    'modified_date': (base_time - timedelta(hours=5)).isoformat(),
                    'status': 'active',
                },
                {
                    'id': 'F9_002',
                    'first_name': 'Diana',
                    'last_name': 'Prince',
                    'phone': '+1-555-0302',
                    'email': 'diana.prince@example.com',
                    'created_date': (base_time - timedelta(days=15)).isoformat(),
                    'modified_date': (base_time - timedelta(hours=8)).isoformat(),
                    'status': 'active',
                }
            ]
        }
    
    @staticmethod
    def get_gsheet_responses() -> Dict[str, Any]:
        """Mock responses for Google Sheets API"""
        return {
            'marketing_leads': {
                'values': [
                    ['Name', 'Email', 'Phone', 'Source', 'Date'],
                    ['Eve Adams', 'eve.adams@example.com', '+1-555-0401', 'Google Ads', '2025-01-15'],
                    ['Frank Castle', 'frank.castle@example.com', '+1-555-0402', 'Facebook', '2025-01-16'],
                ]
            },
            'marketing_spends': {
                'values': [
                    ['Date', 'Source', 'Amount', 'Clicks', 'Impressions'],
                    ['2025-01-15', 'Google Ads', '250.00', '45', '1200'],
                    ['2025-01-16', 'Facebook', '180.00', '32', '980'],
                ]
            }
        }
    
    @staticmethod
    def get_leadconduit_responses() -> Dict[str, Any]:
        """Mock responses for LeadConduit API"""
        base_time = datetime.now()
        
        return {
            'leads': [
                {
                    'id': 'LC_10001',
                    'first_name': 'Grace',
                    'last_name': 'Hopper',
                    'email': 'grace.hopper@example.com',
                    'phone': '+1-555-0501',
                    'source': 'web_form',
                    'created_at': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                    'updated_at': (base_time - timedelta(minutes=30)).isoformat() + 'Z',
                    'status': 'new',
                },
                {
                    'id': 'LC_10002',
                    'first_name': 'Alan',
                    'last_name': 'Turing',
                    'email': 'alan.turing@example.com',
                    'phone': '+1-555-0502',
                    'source': 'phone_call',
                    'created_at': (base_time - timedelta(hours=3)).isoformat() + 'Z',
                    'updated_at': (base_time - timedelta(hours=1)).isoformat() + 'Z',
                    'status': 'qualified',
                }
            ]
        }
    
    @staticmethod
    def get_salesrabbit_responses() -> Dict[str, Any]:
        """Mock responses for SalesRabbit API"""
        base_time = datetime.now()
        
        return {
            'leads': {
                'data': [
                    {
                        'id': 'SR_20001',
                        'first_name': 'Isaac',
                        'last_name': 'Newton',
                        'email': 'isaac.newton@example.com',
                        'phone': '+1-555-0601',
                        'address': '123 Apple St, Science City, SC 12345',
                        'status': 'new',
                        'created_at': (base_time - timedelta(days=2)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=6)).isoformat() + 'Z',
                        'rep_id': 'REP_001',
                    },
                    {
                        'id': 'SR_20002',
                        'first_name': 'Marie',
                        'last_name': 'Curie',
                        'email': 'marie.curie@example.com',
                        'phone': '+1-555-0602',
                        'address': '456 Radium Ave, Discovery Town, DT 67890',
                        'status': 'contacted',
                        'created_at': (base_time - timedelta(days=5)).isoformat() + 'Z',
                        'updated_at': (base_time - timedelta(hours=2)).isoformat() + 'Z',
                        'rep_id': 'REP_002',
                    }
                ],
                'meta': {
                    'current_page': 1,
                    'per_page': 100,
                    'total': 2
                }
            }
        }
    
    @staticmethod
    def get_all_mock_responses() -> Dict[str, Dict[str, Any]]:
        """Get all mock responses organized by CRM"""
        return {
            'arrivy': CRMMockResponses.get_arrivy_responses(),
            'callrail': CRMMockResponses.get_callrail_responses(),
            'hubspot': CRMMockResponses.get_hubspot_responses(),
            'five9': CRMMockResponses.get_five9_responses(),
            'gsheet': CRMMockResponses.get_gsheet_responses(),
            'leadconduit': CRMMockResponses.get_leadconduit_responses(),
            'salesrabbit': CRMMockResponses.get_salesrabbit_responses(),
        }


class APIErrorSimulator:
    """
    Simulates common API errors for testing error handling
    """
    
    @staticmethod
    def authentication_error(crm_name: str):
        """Simulate authentication/authorization errors"""
        messages = {
            'arrivy': 'Invalid API token provided',
            'callrail': 'Authentication failed: Invalid API key',
            'hubspot': 'Invalid access token',
            'five9': 'SOAP authentication failed',
            'leadconduit': 'Unauthorized: Invalid API key',
            'salesrabbit': 'Authentication failed',
        }
        return Exception(messages.get(crm_name, 'Authentication failed'))
    
    @staticmethod
    def rate_limit_error(crm_name: str):
        """Simulate rate limiting errors"""
        messages = {
            'arrivy': 'Rate limit exceeded: 100 requests per minute',
            'callrail': 'Rate limit exceeded: 120 requests per minute',
            'hubspot': 'Rate limit exceeded: 100 requests per 10 seconds',
            'five9': 'Request limit exceeded',
            'leadconduit': 'Rate limit exceeded',
            'salesrabbit': 'Too many requests',
        }
        return Exception(messages.get(crm_name, 'Rate limit exceeded'))
    
    @staticmethod
    def timeout_error():
        """Simulate network timeout errors"""
        return Exception('Request timeout after 30 seconds')
    
    @staticmethod
    def server_error():
        """Simulate server errors"""
        return Exception('Internal server error: 500')
    
    @staticmethod
    def network_error():
        """Simulate network connectivity errors"""
        return Exception('Network error: Connection refused')


# Database mock responses for DB-based CRMs (Genius, SalesPro)
class DatabaseMockResponses:
    """
    Mock database query results for CRMs that sync from databases
    """
    
    @staticmethod
    def get_genius_responses() -> Dict[str, Any]:
        """Mock responses for Genius database queries"""
        base_time = datetime.now()
        
        return {
            'appointments': [
                {
                    'id': 1001,
                    'customer_name': 'Test Customer 1',
                    'appointment_date': base_time.date(),
                    'status': 'scheduled',
                    'created_at': base_time - timedelta(days=1),
                    'updated_at': base_time - timedelta(hours=2),
                },
                {
                    'id': 1002,
                    'customer_name': 'Test Customer 2',
                    'appointment_date': (base_time + timedelta(days=1)).date(),
                    'status': 'confirmed',
                    'created_at': base_time - timedelta(days=2),
                    'updated_at': base_time - timedelta(hours=1),
                }
            ],
            'users': [
                {
                    'id': 2001,
                    'username': 'testuser1',
                    'email': 'testuser1@example.com',
                    'role': 'sales_rep',
                    'created_at': base_time - timedelta(days=30),
                    'updated_at': base_time - timedelta(days=1),
                }
            ]
        }
    
    @staticmethod
    def get_salespro_responses() -> Dict[str, Any]:
        """Mock responses for SalesPro database queries"""
        base_time = datetime.now()
        
        return {
            'customers': [
                {
                    'id': 3001,
                    'name': 'SalesPro Customer 1',
                    'email': 'customer1@salespro.com',
                    'phone': '+1-555-0701',
                    'created_date': base_time - timedelta(days=10),
                    'modified_date': base_time - timedelta(hours=4),
                },
                {
                    'id': 3002,
                    'name': 'SalesPro Customer 2',
                    'email': 'customer2@salespro.com',
                    'phone': '+1-555-0702',
                    'created_date': base_time - timedelta(days=5),
                    'modified_date': base_time - timedelta(hours=1),
                }
            ]
        }
    
    @staticmethod
    def get_all_database_mock_responses() -> Dict[str, Dict[str, Any]]:
        """Get all database mock responses"""
        return {
            'genius': DatabaseMockResponses.get_genius_responses(),
            'salespro': DatabaseMockResponses.get_salespro_responses(),
        }
