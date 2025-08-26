"""
Docker-optimized pytest configuration for CRM command testing

Leverages existing Docker infrastructure with PostgreSQL database
and provides fixtures for command testing with proper isolation.
"""
import os
import pytest
import logging
from io import StringIO
from unittest.mock import patch, MagicMock
from typing import Dict, Any, Generator
from contextlib import contextmanager

import django
from django.test import TestCase, override_settings, TransactionTestCase
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.db import transaction, connections
from django.conf import settings
from django.utils import timezone

# Configure Django for tests running in Docker
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.models.common import SyncHistory


@pytest.fixture(scope='session', autouse=True)
def setup_test_environment():
    """
    Session-wide setup for Docker-based testing
    Configures logging and database for test environment
    """
    # Configure test logging
    logging.getLogger().setLevel(logging.WARNING)
    logging.getLogger('django.db.backends').setLevel(logging.ERROR)
    
    # Enable debug logging for our CRM modules
    for crm in ['arrivy', 'callrail', 'hubspot', 'five9', 'genius', 'gsheet', 
                'leadconduit', 'salespro', 'salesrabbit']:
        logging.getLogger(crm).setLevel(logging.DEBUG)
    
    yield
    
    # Session cleanup
    logging.getLogger().setLevel(logging.WARNING)


@pytest.fixture(scope='function')
def db_transaction():
    """
    Database transaction fixture for Docker environment
    Provides isolated database state for each test
    """
    # Use transaction rollback for test isolation
    with transaction.atomic():
        # Create savepoint
        sid = transaction.savepoint()
        yield
        # Always rollback
        transaction.savepoint_rollback(sid)


@pytest.fixture
def clean_sync_history(db_transaction):
    """
    Ensure clean SyncHistory table for each test
    Critical for testing SyncHistory compliance
    """
    # Clean up any existing sync history
    SyncHistory.objects.all().delete()
    yield
    # Cleanup handled by db_transaction rollback


@pytest.fixture
def command_output():
    """
    Capture command stdout/stderr for testing
    """
    stdout = StringIO()
    stderr = StringIO()
    yield stdout, stderr
    stdout.close()
    stderr.close()


@pytest.fixture
def test_logger():
    """
    Test-specific logger with captured output
    """
    log_stream = StringIO()
    handler = logging.StreamHandler(log_stream)
    handler.setLevel(logging.DEBUG)
    
    logger = logging.getLogger('crm_command_test')
    logger.addHandler(handler)
    logger.setLevel(logging.DEBUG)
    
    yield logger, log_stream
    
    logger.removeHandler(handler)


@pytest.fixture
def docker_db_settings():
    """
    Database settings optimized for Docker environment
    Uses the existing database configuration from docker-compose
    """
    # In Docker, database should already be configured
    # This fixture validates the configuration is correct for testing
    db_config = settings.DATABASES['default']
    
    # Ensure we're using the correct database for tests
    assert db_config['ENGINE'] == 'django.db.backends.postgresql'
    assert db_config['NAME'], "Database name not configured"
    
    yield db_config


@pytest.fixture
def crm_api_settings():
    """
    Test settings for CRM API credentials
    Uses test values that won't hit real APIs
    """
    test_settings = {
        'ARRIVY_API_TOKEN': 'test_arrivy_token_12345',
        'ARRIVY_BASE_URL': 'https://test-api.arrivy.com',
        'CALLRAIL_API_KEY': 'test_callrail_key_12345',
        'CALLRAIL_BASE_URL': 'https://test-api.callrail.com',
        'HUBSPOT_API_TOKEN': 'test_hubspot_token_12345',
        'HUBSPOT_BASE_URL': 'https://test-api.hubspot.com',
        'FIVE9_USERNAME': 'test_five9_user',
        'FIVE9_PASSWORD': 'test_five9_password',
        'GSHEET_CREDENTIALS_FILE': '/tmp/test_gsheet_creds.json',
        'LEADCONDUIT_API_KEY': 'test_leadconduit_key_12345',
        'SALESRABBIT_API_KEY': 'test_salesrabbit_key_12345',
        'SALESPRO_DATABASE_URL': 'postgresql://test:test@localhost/test_salespro',
        'GENIUS_DATABASE_URL': 'postgresql://test:test@localhost/test_genius',
    }
    
    with override_settings(**test_settings):
        yield test_settings


@pytest.fixture
def mock_crm_responses():
    """
    Mock API responses for different CRM systems
    Provides realistic test data for each CRM
    """
    return {
        'arrivy': {
            'entities': {
                'entities': [
                    {
                        'id': 1,
                        'name': 'Test Entity 1',
                        'email': 'test1@example.com',
                        'phone': '+1234567890',
                        'created_at': '2025-01-01T00:00:00Z',
                        'updated_at': '2025-01-01T12:00:00Z',
                    },
                    {
                        'id': 2,
                        'name': 'Test Entity 2', 
                        'email': 'test2@example.com',
                        'phone': '+0987654321',
                        'created_at': '2025-01-01T06:00:00Z',
                        'updated_at': '2025-01-01T18:00:00Z',
                    }
                ]
            },
            'tasks': {
                'tasks': [
                    {
                        'id': 101,
                        'title': 'Test Task 1',
                        'status': 'pending',
                        'created_at': '2025-01-01T00:00:00Z',
                        'updated_at': '2025-01-01T12:00:00Z',
                    }
                ]
            },
            'groups': {
                'groups': [
                    {
                        'id': 201,
                        'name': 'Test Group 1',
                        'description': 'Test group description',
                        'created_at': '2025-01-01T00:00:00Z',
                    }
                ]
            }
        },
        'callrail': {
            'accounts': {
                'accounts': [
                    {
                        'id': 'acc_123456789',
                        'name': 'Test Account',
                        'plan': 'pro',
                        'created_at': '2025-01-01T00:00:00Z',
                    }
                ]
            },
            'companies': {
                'companies': [
                    {
                        'id': 'com_123456789',
                        'name': 'Test Company',
                        'status': 'active',
                        'created_at': '2025-01-01T00:00:00Z',
                    }
                ]
            },
            'calls': {
                'calls': [
                    {
                        'id': 'call_123456789',
                        'duration': 120,
                        'direction': 'inbound',
                        'answered': True,
                        'created_at': '2025-01-01T00:00:00Z',
                    }
                ]
            }
        },
        'hubspot': {
            'contacts': {
                'results': [
                    {
                        'id': '12345',
                        'properties': {
                            'firstname': 'John',
                            'lastname': 'Doe',
                            'email': 'john.doe@example.com',
                            'phone': '+1234567890',
                            'hs_lastmodifieddate': '2025-01-01T00:00:00Z',
                        }
                    }
                ]
            },
            'deals': {
                'results': [
                    {
                        'id': '67890',
                        'properties': {
                            'dealname': 'Test Deal',
                            'amount': '1000.00',
                            'dealstage': 'closedwon',
                            'hs_lastmodifieddate': '2025-01-01T00:00:00Z',
                        }
                    }
                ]
            }
        }
    }


# Docker-specific test utilities

@pytest.fixture
def docker_exec_command():
    """
    Helper to execute commands in Docker test container
    Simulates running commands as they would be run in production Docker environment
    """
    def _exec_command(command_name, *args, **kwargs):
        """Execute a Django management command in Docker context"""
        stdout = StringIO()
        stderr = StringIO()
        
        try:
            call_command(
                command_name,
                *args,
                stdout=stdout,
                stderr=stderr,
                **kwargs
            )
            return {
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue(), 
                'success': True,
                'exception': None
            }
        except Exception as e:
            return {
                'stdout': stdout.getvalue(),
                'stderr': stderr.getvalue(),
                'success': False,
                'exception': e
            }
        finally:
            stdout.close()
            stderr.close()
    
    return _exec_command


@pytest.fixture
def mock_api_client():
    """
    Mock API client that can be configured for different CRM responses
    """
    class MockAPIClient:
        def __init__(self, responses_dict=None):
            self.responses = responses_dict or {}
            self.call_history = []
        
        def configure_response(self, method, endpoint, response):
            if method not in self.responses:
                self.responses[method] = {}
            self.responses[method][endpoint] = response
        
        def get(self, endpoint, **kwargs):
            self.call_history.append(('GET', endpoint, kwargs))
            return self.responses.get('GET', {}).get(endpoint, {'error': 'Not mocked'})
        
        def post(self, endpoint, **kwargs):
            self.call_history.append(('POST', endpoint, kwargs))
            return self.responses.get('POST', {}).get(endpoint, {'error': 'Not mocked'})
    
    return MockAPIClient


@contextmanager
def isolated_db_state():
    """
    Context manager for completely isolated database state
    Useful for tests that need guaranteed clean state
    """
    # Force close all database connections
    connections.close_all()
    
    with transaction.atomic():
        sid = transaction.savepoint()
        try:
            yield
        finally:
            transaction.savepoint_rollback(sid)


# Performance monitoring for Docker tests

@pytest.fixture
def performance_monitor():
    """
    Monitor test performance in Docker environment
    Helps identify slow tests and optimize Docker testing
    """
    import time
    import psutil
    
    class PerformanceMonitor:
        def __init__(self):
            self.start_time = None
            self.start_memory = None
        
        def start(self):
            self.start_time = time.time()
            self.start_memory = psutil.virtual_memory().used
        
        def stop(self):
            if self.start_time is None:
                return None
            
            duration = time.time() - self.start_time
            memory_used = psutil.virtual_memory().used - self.start_memory
            
            return {
                'duration_seconds': duration,
                'memory_used_mb': memory_used / 1024 / 1024
            }
    
    return PerformanceMonitor()


# Test database management for Docker

@pytest.fixture(autouse=True, scope='session')
def setup_test_database():
    """
    Ensure test database is properly set up in Docker environment
    Runs migrations and basic setup automatically
    """
    try:
        # Ensure migrations are up to date
        call_command('migrate', verbosity=0, interactive=False)
        
        # Clear any existing test data
        if SyncHistory._meta.db_table:
            SyncHistory.objects.all().delete()
        
        yield
        
    except Exception as e:
        pytest.fail(f"Failed to set up test database: {e}")


# Error simulation fixtures for robust testing

@pytest.fixture
def api_error_simulator():
    """
    Simulate various API error conditions for testing error handling
    """
    class APIErrorSimulator:
        @staticmethod
        def authentication_error():
            return Exception("Authentication failed: Invalid API token")
        
        @staticmethod  
        def timeout_error():
            return Exception("Request timeout after 30 seconds")
        
        @staticmethod
        def rate_limit_error():
            return Exception("Rate limit exceeded: 100 requests per minute")
        
        @staticmethod
        def server_error():
            return Exception("Internal server error: 500")
        
        @staticmethod
        def network_error():
            return Exception("Network error: Connection refused")
    
    return APIErrorSimulator()


# Fixtures for testing specific command patterns

@pytest.fixture(params=[
    '--dry-run',
    '--full',
    '--debug', 
    '--quiet',
    '--batch-size', '50',
    '--force',
    '--start-date', '2025-01-01'
])
def standard_command_flag(request):
    """
    Parametrized fixture for testing standard command flags
    Ensures all commands support required flags
    """
    return request.param
