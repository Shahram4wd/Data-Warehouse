"""
Test script for SalesRabbit sync implementation
"""
import os
import sys
import asyncio
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.sync.salesrabbit.engines.leads import SalesRabbitLeadSyncEngine
from ingestion.sync.salesrabbit.clients.leads import SalesRabbitLeadsClient

async def test_client():
    """Test the SalesRabbit client"""
    print("Testing SalesRabbit API client...")
    
    try:
        client = SalesRabbitLeadsClient()
        success = await client.test_connection()
        
        if success:
            print("✓ Client test passed")
            
            # Try to get a count
            count = await client.get_lead_count_since()
            print(f"✓ Lead count: {count}")
            
        else:
            print("✗ Client test failed")
            
    except Exception as e:
        print(f"✗ Client test error: {e}")

async def test_engine():
    """Test the sync engine"""
    print("\nTesting SalesRabbit sync engine...")
    
    try:
        engine = SalesRabbitLeadSyncEngine(dry_run=True)
        
        # Test connection
        success = await engine.test_connection()
        if success:
            print("✓ Engine connection test passed")
        else:
            print("✗ Engine connection test failed")
            return
        
        # Test sync (dry run)
        print("Running dry run sync...")
        results = await engine.run_sync(force_full=True)
        print(f"✓ Dry run completed: {results}")
        
    except Exception as e:
        print(f"✗ Engine test error: {e}")
        import traceback
        traceback.print_exc()

async def main():
    """Main test function"""
    print("SalesRabbit Framework Implementation Test")
    print("=" * 50)
    
    await test_client()
    await test_engine()
    
    print("\n" + "=" * 50)
    print("Test completed")

if __name__ == "__main__":
    asyncio.run(main())
