"""
Unit tests for HubSpot sync engines
"""
import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone
from django.test import TestCase
from django.utils import timezone as django_timezone

from ingestion.sync.hubspot.engines import (
    HubSpotContactSyncEngine,
    HubSpotAppointmentSyncEngine,
    HubSpotDivisionSyncEngine,
    HubSpotDealSyncEngine,
    HubSpotAssociationSyncEngine
)
from ingestion.base.exceptions import SyncException, ValidationException


class TestHubSpotContactSyncEngine(TestCase):
    """Test HubSpot contact sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = HubSpotContactSyncEngine()
        
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.crm_source, 'hubspot')
        self.assertEqual(self.engine.sync_type, 'contacts')
        self.assertEqual(self.engine.get_default_batch_size(), 100)
        
    @patch('ingestion.sync.hubspot.engines.HubSpotClient')
    async def test_initialize_client(self, mock_client_class):
        """Test client initialization"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        await self.engine.initialize_client()
        
        self.assertIsNotNone(self.engine.client)
        self.assertIsNotNone(self.engine.processor)
        mock_client.authenticate.assert_called_once()
        
    @patch('ingestion.sync.hubspot.engines.HubSpotClient')
    async def test_fetch_data_success(self, mock_client_class):
        """Test successful data fetching"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock the async generator
        async def mock_fetch_contacts(*args, **kwargs):
            yield [{'id': '1', 'properties': {'firstname': 'John'}}]
            yield [{'id': '2', 'properties': {'firstname': 'Jane'}}]
        
        mock_client.fetch_contacts = mock_fetch_contacts
        
        await self.engine.initialize_client()
        
        batches = []
        async for batch in self.engine.fetch_data():
            batches.append(batch)
        
        self.assertEqual(len(batches), 2)
        self.assertEqual(batches[0][0]['id'], '1')
        self.assertEqual(batches[1][0]['id'], '2')
        
    async def test_fetch_data_without_client(self):
        """Test fetch data without initialized client"""
        with self.assertRaises(SyncException):
            async for batch in self.engine.fetch_data():
                pass
                
    @patch('ingestion.sync.hubspot.engines.HubSpotClient')
    async def test_transform_data(self, mock_client_class):
        """Test data transformation"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        await self.engine.initialize_client()
        
        raw_data = [
            {'id': '1', 'properties': {'firstname': 'John', 'lastname': 'Doe'}},
            {'id': '2', 'properties': {'firstname': 'Jane', 'lastname': 'Smith'}}
        ]
        
        transformed = await self.engine.transform_data(raw_data)
        
        self.assertEqual(len(transformed), 2)
        self.assertEqual(transformed[0]['id'], '1')
        self.assertEqual(transformed[0]['firstname'], 'John')
        
    async def test_transform_data_without_processor(self):
        """Test transform data without initialized processor"""
        raw_data = [{'id': '1', 'properties': {'firstname': 'John'}}]
        
        with self.assertRaises(SyncException):
            await self.engine.transform_data(raw_data)
            
    @patch('ingestion.sync.hubspot.engines.HubSpotClient')
    async def test_validate_data(self, mock_client_class):
        """Test data validation"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        await self.engine.initialize_client()
        
        data = [
            {'id': '1', 'firstname': 'John', 'email': 'john@example.com'},
            {'id': '2', 'firstname': 'Jane', 'email': 'jane@example.com'}
        ]
        
        validated = await self.engine.validate_data(data)
        
        self.assertEqual(len(validated), 2)
        self.assertEqual(validated[0]['id'], '1')
        
    async def test_validate_data_without_processor(self):
        """Test validate data without initialized processor"""
        data = [{'id': '1', 'firstname': 'John'}]
        
        with self.assertRaises(SyncException):
            await self.engine.validate_data(data)
            
    @patch('ingestion.models.hubspot.Hubspot_Contact.objects.update_or_create')
    async def test_save_data(self, mock_update_or_create):
        """Test data saving"""
        # Mock the sync_to_async wrapper
        async def mock_sync_to_async(func, thread_sensitive=True):
            return func
        
        mock_contact = MagicMock()
        mock_update_or_create.return_value = (mock_contact, True)
        
        data = [
            {'id': '1', 'firstname': 'John', 'email': 'john@example.com'},
            {'id': '2', 'firstname': 'Jane', 'email': 'jane@example.com'}
        ]
        
        with patch('ingestion.sync.hubspot.engines.sync_to_async', side_effect=mock_sync_to_async):
            results = await self.engine.save_data(data)
        
        self.assertEqual(results['created'], 2)
        self.assertEqual(results['updated'], 0)
        self.assertEqual(results['failed'], 0)
        
    async def test_cleanup(self):
        """Test cleanup method"""
        mock_client = AsyncMock()
        self.engine.client = mock_client
        
        await self.engine.cleanup()
        
        mock_client.close.assert_called_once()


class TestHubSpotAppointmentSyncEngine(TestCase):
    """Test HubSpot appointment sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = HubSpotAppointmentSyncEngine()
        
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.crm_source, 'hubspot')
        self.assertEqual(self.engine.sync_type, 'appointments')
        self.assertEqual(self.engine.get_default_batch_size(), 100)


class TestHubSpotDivisionSyncEngine(TestCase):
    """Test HubSpot division sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = HubSpotDivisionSyncEngine()
        
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.crm_source, 'hubspot')
        self.assertEqual(self.engine.sync_type, 'divisions')
        self.assertEqual(self.engine.get_default_batch_size(), 50)


class TestHubSpotDealSyncEngine(TestCase):
    """Test HubSpot deal sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = HubSpotDealSyncEngine()
        
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.crm_source, 'hubspot')
        self.assertEqual(self.engine.sync_type, 'deals')
        self.assertEqual(self.engine.get_default_batch_size(), 100)


class TestHubSpotAssociationSyncEngine(TestCase):
    """Test HubSpot association sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.engine = HubSpotAssociationSyncEngine()
        
    def test_initialization(self):
        """Test engine initialization"""
        self.assertEqual(self.engine.crm_source, 'hubspot')
        self.assertEqual(self.engine.sync_type, 'associations')
        self.assertEqual(self.engine.get_default_batch_size(), 100)
        
    @patch('ingestion.sync.hubspot.engines.HubSpotClient')
    async def test_fetch_data_success(self, mock_client_class):
        """Test successful association data fetching"""
        mock_client = AsyncMock()
        mock_client_class.return_value = mock_client
        
        # Mock the async generator
        async def mock_fetch_associations(*args, **kwargs):
            yield [
                {'from_object_type': 'contacts', 'from_object_id': '1', 
                 'to_object_type': 'deals', 'to_object_id': '101'}
            ]
        
        mock_client.fetch_associations = mock_fetch_associations
        
        await self.engine.initialize_client()
        
        batches = []
        async for batch in self.engine.fetch_data(from_object_type='contacts', to_object_type='deals'):
            batches.append(batch)
        
        self.assertEqual(len(batches), 1)
        self.assertEqual(batches[0][0]['from_object_type'], 'contacts')
        
    async def test_validate_data(self):
        """Test association data validation"""
        data = [
            {'from_object_id': '1', 'to_object_id': '101', 'from_object_type': 'contacts'},
            {'from_object_id': '', 'to_object_id': '102', 'from_object_type': 'contacts'},  # Invalid
            {'from_object_id': '2', 'to_object_id': '103', 'from_object_type': 'contacts'}
        ]
        
        validated = await self.engine.validate_data(data)
        
        self.assertEqual(len(validated), 2)  # One invalid record filtered out
        self.assertEqual(validated[0]['from_object_id'], '1')
        self.assertEqual(validated[1]['from_object_id'], '2')


# Helper to run async tests
def run_async_test(coro):
    """Helper to run async tests"""
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)


# Patch the test methods to run async
TestHubSpotContactSyncEngine.test_initialize_client = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_initialize_client(self)
)
TestHubSpotContactSyncEngine.test_fetch_data_success = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_fetch_data_success(self)
)
TestHubSpotContactSyncEngine.test_fetch_data_without_client = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_fetch_data_without_client(self)
)
TestHubSpotContactSyncEngine.test_transform_data = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_transform_data(self)
)
TestHubSpotContactSyncEngine.test_transform_data_without_processor = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_transform_data_without_processor(self)
)
TestHubSpotContactSyncEngine.test_validate_data = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_validate_data(self)
)
TestHubSpotContactSyncEngine.test_validate_data_without_processor = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_validate_data_without_processor(self)
)
TestHubSpotContactSyncEngine.test_save_data = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_save_data(self)
)
TestHubSpotContactSyncEngine.test_cleanup = lambda self: run_async_test(
    TestHubSpotContactSyncEngine.test_cleanup(self)
)

TestHubSpotAssociationSyncEngine.test_fetch_data_success = lambda self: run_async_test(
    TestHubSpotAssociationSyncEngine.test_fetch_data_success(self)
)
TestHubSpotAssociationSyncEngine.test_validate_data = lambda self: run_async_test(
    TestHubSpotAssociationSyncEngine.test_validate_data(self)
)
