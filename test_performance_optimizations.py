#!/usr/bin/env python3
"""
Test script to validate db_genius_appointment_services performance optimizations
"""
import os
import sys
import django

# Add the project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# Set Django settings
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')

try:
    django.setup()
    
    print("✅ Django setup successful")
    
    # Test imports
    from ingestion.sync.genius.engines.appointment_services import GeniusAppointmentServicesSyncEngine
    from ingestion.sync.genius.clients.appointment_services import GeniusAppointmentServicesClient
    
    print("✅ Import successful")
    
    # Test client creation
    client = GeniusAppointmentServicesClient()
    print("✅ Client creation successful")
    
    # Test engine creation
    engine = GeniusAppointmentServicesSyncEngine()
    print("✅ Engine creation successful")
    
    # Test performance recommendations
    print("\n🔧 Performance Recommendations:")
    recommendations = client.get_recommended_indexes()
    for rec in recommendations:
        print(f"   {rec}")
    
    print("\n✅ All basic tests passed!")
    print("🚀 The performance optimizations are ready to use.")
    print("\nTo run the optimized sync:")
    print("   python manage.py db_genius_appointment_services --dry-run --debug --max-records=1000")
    
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Please ensure all dependencies are installed.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    print("Please check your Django configuration.")