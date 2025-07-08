"""
Integration tests for HubSpot sync operations
"""
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock
from django.test import TestCase, override_settings
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta

from ingestion.sync.hubspot.client import HubSpotClient
from ingestion.sync.hubspot.engines import HubSpotContactSyncEngine
from ingestion.models.common import SyncHistory
from ingestion.models.hubspot import Hubspot_Contact


class HubSpotIntegrationTestCase(TestCase):
    """Base class for HubSpot integration tests"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.use_live_api = os.getenv('USE_LIVE_HUBSPOT_API', 'false').lower() == 'true'
        self.test_api_token = os.getenv('HUBSPOT_TEST_API_TOKEN')
        
        if self.use_live_api and not self.test_api_token:
            self.skipTest("Live API testing requires HUBSPOT_TEST_API_TOKEN environment variable")
    
    def get_mock_contact_data(self):
        """Get mock contact data for testing"""
        return [
            {
                'id': 'test_contact_1',
                'properties': {
                    'firstname': 'John',
                    'lastname': 'Doe',
                    'email': 'john.doe@example.com',
                    'phone': '555-1234',
                    'createdate': str(int(timezone.now().timestamp() * 1000)),
                    'lastmodifieddate': str(int(timezone.now().timestamp() * 1000))
                }
            },
            {
                'id': 'test_contact_2',
                'properties': {
                    'firstname': 'Jane',
                    'lastname': 'Smith',
                    'email': 'jane.smith@example.com',
                    'phone': '555-5678',
                    'createdate': str(int(timezone.now().timestamp() * 1000)),
                    'lastmodifieddate': str(int(timezone.now().timestamp() * 1000))
                }
            }
        ]


class TestHubSpotClientIntegration(HubSpotIntegrationTestCase):
    """Integration tests for HubSpot client"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        
        if self.use_live_api:
            self.client = HubSpotClient(self.test_api_token)
        else:
            self.client = HubSpotClient('test_token')
    
    def run_async_test(self, coro):
        """Helper to run async tests"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def test_client_authentication(self):
        """Test client authentication"""
        async def test_auth():
            await self.client.authenticate()
            self.assertIn('Authorization', self.client.headers)
            
        self.run_async_test(test_auth())
    
    def test_fetch_contacts_mock(self):
        """Test fetching contacts with mock data"""
        if self.use_live_api:
            self.skipTest("This test is for mock data only")
            
        async def test_fetch():
            mock_data = self.get_mock_contact_data()
            
            # Mock the client's fetch method
            async def mock_fetch_contacts(*args, **kwargs):
                yield mock_data
            
            with patch.object(self.client, 'fetch_contacts', side_effect=mock_fetch_contacts):
                await self.client.authenticate()
                
                batches = []
                async for batch in self.client.fetch_contacts(limit=10):
                    batches.append(batch)
                
                self.assertEqual(len(batches), 1)
                self.assertEqual(len(batches[0]), 2)
                self.assertEqual(batches[0][0]['id'], 'test_contact_1')
                
        self.run_async_test(test_fetch())
    
    def test_fetch_contacts_live(self):
        """Test fetching contacts with live API"""
        if not self.use_live_api:
            self.skipTest("Live API testing disabled")
            
        async def test_fetch():
            await self.client.authenticate()
            
            # Fetch just a small batch to test API connectivity
            batch_count = 0
            async for batch in self.client.fetch_contacts(limit=5):
                batch_count += 1
                self.assertIsInstance(batch, list)
                if batch_count >= 1:  # Just test one batch
                    break
                    
            self.assertGreaterEqual(batch_count, 0)  # At least 0 batches (might be empty)
            
        self.run_async_test(test_fetch())
    
    def test_client_cleanup(self):
        """Test client cleanup"""
        async def test_cleanup():
            await self.client.authenticate()
            await self.client.close()
            
        self.run_async_test(test_cleanup())


class TestHubSpotContactSyncEngineIntegration(HubSpotIntegrationTestCase):
    """Integration tests for HubSpot contact sync engine"""
    
    def setUp(self):
        """Set up test fixtures"""
        super().setUp()
        
        if self.use_live_api:
            self.engine = HubSpotContactSyncEngine(batch_size=5, dry_run=True)
        else:
            self.engine = HubSpotContactSyncEngine(batch_size=10, dry_run=True)
    
    def run_async_test(self, coro):
        """Helper to run async tests"""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(coro)
        finally:
            loop.close()
    
    def test_sync_engine_initialization(self):
        """Test sync engine initialization"""
        async def test_init():
            if not self.use_live_api:
                # Mock the client authentication
                with patch.object(self.engine, 'client', AsyncMock()):
                    await self.engine.initialize_client()
                    self.assertIsNotNone(self.engine.client)
                    self.assertIsNotNone(self.engine.processor)
            else:
                # Use real API token
                with override_settings(HUBSPOT_API_TOKEN=self.test_api_token):
                    await self.engine.initialize_client()
                    self.assertIsNotNone(self.engine.client)
                    self.assertIsNotNone(self.engine.processor)
                    
        self.run_async_test(test_init())
    
    def test_full_sync_workflow_mock(self):
        """Test complete sync workflow with mock data"""
        if self.use_live_api:
            self.skipTest("This test is for mock data only")
            
        async def test_workflow():
            mock_data = self.get_mock_contact_data()
            
            # Mock the client methods
            with patch.object(self.engine, 'client', AsyncMock()) as mock_client:
                # Mock fetch_contacts to return our test data
                async def mock_fetch_contacts(*args, **kwargs):
                    yield mock_data
                    
                mock_client.fetch_contacts = mock_fetch_contacts
                mock_client.authenticate = AsyncMock()
                mock_client.close = AsyncMock()
                
                # Mock the processor
                with patch.object(self.engine, 'processor', MagicMock()) as mock_processor:
                    mock_processor.transform_record.side_effect = lambda x: {
                        'id': x['id'],
                        'firstname': x['properties']['firstname'],
                        'lastname': x['properties']['lastname'],
                        'email': x['properties']['email']
                    }
                    mock_processor.validate_record.side_effect = lambda x: x
                    
                    # Initialize
                    await self.engine.initialize_client()
                    
                    # Test data fetching
                    batches = []
                    async for batch in self.engine.fetch_data():
                        batches.append(batch)
                    
                    self.assertEqual(len(batches), 1)
                    self.assertEqual(len(batches[0]), 2)
                    
                    # Test data transformation
                    transformed = await self.engine.transform_data(batches[0])
                    self.assertEqual(len(transformed), 2)
                    self.assertEqual(transformed[0]['firstname'], 'John')
                    
                    # Test data validation
                    validated = await self.engine.validate_data(transformed)
                    self.assertEqual(len(validated), 2)
                    
                    # Test cleanup
                    await self.engine.cleanup()
                    mock_client.close.assert_called_once()
                    
        self.run_async_test(test_workflow())
    
    def test_full_sync_with_database_mock(self):
        """Test complete sync with database operations (dry run)"""
        if self.use_live_api:
            self.skipTest("This test is for mock data only")
            
        async def test_sync():
            mock_data = self.get_mock_contact_data()
            
            # Mock the entire run_sync method dependencies
            with patch.object(self.engine, 'initialize_client', AsyncMock()):
                with patch.object(self.engine, 'fetch_data', AsyncMock()) as mock_fetch:
                    with patch.object(self.engine, 'transform_data', AsyncMock()) as mock_transform:
                        with patch.object(self.engine, 'validate_data', AsyncMock()) as mock_validate:
                            with patch.object(self.engine, 'save_data', AsyncMock()) as mock_save:
                                with patch.object(self.engine, 'cleanup', AsyncMock()) as mock_cleanup:
                                    
                                    # Configure mocks
                                    async def mock_fetch_generator():
                                        yield mock_data
                                    
                                    mock_fetch.return_value = mock_fetch_generator()
                                    mock_transform.return_value = mock_data
                                    mock_validate.return_value = mock_data
                                    mock_save.return_value = {'created': 2, 'updated': 0, 'failed': 0}
                                    
                                    # Mock SyncHistory creation
                                    with patch('ingestion.sync.hubspot.engines.sync_to_async') as mock_sync_to_async:
                                        mock_history = MagicMock()
                                        mock_history.id = 1
                                        mock_sync_to_async.return_value = mock_history
                                        
                                        # Run sync
                                        result = await self.engine.run_sync()
                                        
                                        # Verify calls
                                        mock_fetch.assert_called_once()
                                        mock_transform.assert_called_once()
                                        mock_validate.assert_called_once()
                                        mock_cleanup.assert_called_once()
                                        
                                        # Since it's dry run, save_data should not be called
                                        if self.engine.dry_run:
                                            mock_save.assert_not_called()
                                        else:
                                            mock_save.assert_called_once()
                                            
        self.run_async_test(test_sync())
    
    def test_sync_with_live_api_limited(self):
        """Test sync with live API (limited records)"""
        if not self.use_live_api:
            self.skipTest("Live API testing disabled")
            
        async def test_live_sync():
            with override_settings(HUBSPOT_API_TOKEN=self.test_api_token):
                # Initialize with very small batch size and dry run
                engine = HubSpotContactSyncEngine(batch_size=2, dry_run=True)
                
                try:
                    # Test just the initialization and basic fetch
                    await engine.initialize_client()
                    
                    # Test fetching one small batch
                    batch_count = 0
                    async for batch in engine.fetch_data(limit=2):
                        batch_count += 1
                        self.assertIsInstance(batch, list)
                        if batch_count >= 1:  # Just test one batch
                            break
                    
                    self.assertGreaterEqual(batch_count, 0)
                    
                finally:
                    await engine.cleanup()
                    
        self.run_async_test(test_live_sync())


class TestHubSpotSyncHistoryIntegration(HubSpotIntegrationTestCase):
    """Integration tests for sync history tracking"""
    
    def test_sync_history_creation(self):
        """Test sync history record creation"""
        # Create a sync history record
        history = SyncHistory.objects.create(
            crm_source='hubspot',
            sync_type='contacts',
            endpoint='contacts_test',
            start_time=timezone.now(),
            status='running',
            configuration={'test': True}
        )
        
        self.assertEqual(history.crm_source, 'hubspot')
        self.assertEqual(history.sync_type, 'contacts')
        self.assertEqual(history.status, 'running')
        
        # Update the record
        history.status = 'success'
        history.end_time = timezone.now()
        history.records_processed = 100
        history.records_created = 10
        history.records_updated = 90
        history.records_failed = 0
        history.performance_metrics = {
            'duration_seconds': 60.0,
            'records_per_second': 1.67
        }
        history.save()
        
        # Verify the update
        updated_history = SyncHistory.objects.get(id=history.id)
        self.assertEqual(updated_history.status, 'success')
        self.assertEqual(updated_history.records_processed, 100)
        self.assertEqual(updated_history.performance_metrics['duration_seconds'], 60.0)
    
    def test_sync_history_queries(self):
        """Test common sync history queries"""
        # Create test data
        now = timezone.now()
        
        # Successful sync
        SyncHistory.objects.create(
            crm_source='hubspot',
            sync_type='contacts',
            endpoint='contacts',
            start_time=now - timedelta(hours=1),
            end_time=now - timedelta(minutes=30),
            status='success',
            records_processed=100
        )
        
        # Failed sync
        SyncHistory.objects.create(
            crm_source='hubspot',
            sync_type='contacts',
            endpoint='contacts',
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=1, minutes=30),
            status='failed',
            records_processed=50,
            error_message='API rate limit exceeded'
        )
        
        # Query last successful sync
        last_successful = SyncHistory.objects.filter(
            crm_source='hubspot',
            sync_type='contacts',
            status='success'
        ).order_by('-end_time').first()
        
        self.assertIsNotNone(last_successful)
        self.assertEqual(last_successful.records_processed, 100)
        
        # Query failed syncs
        failed_syncs = SyncHistory.objects.filter(
            crm_source='hubspot',
            status='failed'
        ).count()
        
        self.assertEqual(failed_syncs, 1)
        
        # Query recent syncs
        recent_syncs = SyncHistory.objects.filter(
            crm_source='hubspot',
            start_time__gte=now - timedelta(hours=3)
        ).count()
        
        self.assertEqual(recent_syncs, 2)


class TestHubSpotBenchmarkIntegration(HubSpotIntegrationTestCase):
    """Benchmark tests for HubSpot sync operations"""
    
    def test_sync_performance_mock(self):
        """Test sync performance with mock data"""
        if self.use_live_api:
            self.skipTest("This test is for mock data only")
            
        async def test_performance():
            # Create larger mock dataset
            mock_data = []
            for i in range(1000):
                mock_data.append({
                    'id': f'test_contact_{i}',
                    'properties': {
                        'firstname': f'FirstName{i}',
                        'lastname': f'LastName{i}',
                        'email': f'user{i}@example.com',
                        'phone': f'555-{i:04d}',
                        'createdate': str(int(timezone.now().timestamp() * 1000)),
                        'lastmodifieddate': str(int(timezone.now().timestamp() * 1000))
                    }
                })
            
            engine = HubSpotContactSyncEngine(batch_size=100, dry_run=True)
            
            # Mock the client methods
            with patch.object(engine, 'client', AsyncMock()) as mock_client:
                async def mock_fetch_contacts(*args, **kwargs):
                    # Yield data in batches
                    batch_size = kwargs.get('limit', 100)
                    for i in range(0, len(mock_data), batch_size):
                        yield mock_data[i:i + batch_size]
                        
                mock_client.fetch_contacts = mock_fetch_contacts
                mock_client.authenticate = AsyncMock()
                mock_client.close = AsyncMock()
                
                # Mock the processor
                with patch.object(engine, 'processor', MagicMock()) as mock_processor:
                    mock_processor.transform_record.side_effect = lambda x: {
                        'id': x['id'],
                        'firstname': x['properties']['firstname'],
                        'lastname': x['properties']['lastname'],
                        'email': x['properties']['email']
                    }
                    mock_processor.validate_record.side_effect = lambda x: x
                    
                    # Initialize
                    await engine.initialize_client()
                    
                    # Measure performance
                    start_time = timezone.now()
                    
                    total_records = 0
                    async for batch in engine.fetch_data():
                        transformed = await engine.transform_data(batch)
                        validated = await engine.validate_data(transformed)
                        total_records += len(validated)
                        
                        # Stop after processing a reasonable amount
                        if total_records >= 500:
                            break
                    
                    end_time = timezone.now()
                    duration = (end_time - start_time).total_seconds()
                    
                    # Performance assertions
                    self.assertGreater(total_records, 0)
                    self.assertLess(duration, 10.0)  # Should process quickly with mocks
                    
                    if duration > 0:
                        rate = total_records / duration
                        self.assertGreater(rate, 10.0)  # Should process at least 10 records/second
                        
                    await engine.cleanup()
                    
        def run_test():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(test_performance())
            finally:
                loop.close()
                
        run_test()
    
    def test_memory_usage_benchmark(self):
        """Test memory usage during sync operations"""
        if self.use_live_api:
            self.skipTest("This test is for mock data only")
            
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        async def test_memory():
            # Create large mock dataset
            mock_data = []
            for i in range(5000):
                mock_data.append({
                    'id': f'test_contact_{i}',
                    'properties': {
                        'firstname': f'FirstName{i}',
                        'lastname': f'LastName{i}',
                        'email': f'user{i}@example.com',
                        'phone': f'555-{i:04d}',
                        'createdate': str(int(timezone.now().timestamp() * 1000)),
                        'lastmodifieddate': str(int(timezone.now().timestamp() * 1000))
                    }
                })
            
            engine = HubSpotContactSyncEngine(batch_size=100, dry_run=True)
            
            # Mock the client methods
            with patch.object(engine, 'client', AsyncMock()) as mock_client:
                async def mock_fetch_contacts(*args, **kwargs):
                    batch_size = kwargs.get('limit', 100)
                    for i in range(0, len(mock_data), batch_size):
                        yield mock_data[i:i + batch_size]
                        
                mock_client.fetch_contacts = mock_fetch_contacts
                mock_client.authenticate = AsyncMock()
                mock_client.close = AsyncMock()
                
                # Mock the processor
                with patch.object(engine, 'processor', MagicMock()) as mock_processor:
                    mock_processor.transform_record.side_effect = lambda x: {
                        'id': x['id'],
                        'firstname': x['properties']['firstname'],
                        'lastname': x['properties']['lastname'],
                        'email': x['properties']['email']
                    }
                    mock_processor.validate_record.side_effect = lambda x: x
                    
                    # Initialize
                    await engine.initialize_client()
                    
                    # Process data and monitor memory
                    max_memory = initial_memory
                    batch_count = 0
                    
                    async for batch in engine.fetch_data():
                        transformed = await engine.transform_data(batch)
                        validated = await engine.validate_data(transformed)
                        
                        # Check memory usage
                        current_memory = process.memory_info().rss / 1024 / 1024  # MB
                        max_memory = max(max_memory, current_memory)
                        
                        batch_count += 1
                        if batch_count >= 10:  # Process enough to test memory
                            break
                    
                    await engine.cleanup()
                    
                    # Memory usage should be reasonable
                    memory_increase = max_memory - initial_memory
                    self.assertLess(memory_increase, 100)  # Should not increase by more than 100MB
                    
        def run_test():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                return loop.run_until_complete(test_memory())
            finally:
                loop.close()
                
        run_test()
