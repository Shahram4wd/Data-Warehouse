#!/usr/bin/env python3
"""
Simple test for HubSpot appointment duration parsing
"""
import sys
import os
# Add the project root to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..'))

from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor
from ingestion.sync.hubspot.processors.base import HubSpotBaseProcessor

def test_parse_duration():
    """Test parse_duration method"""
    print("Testing parse_duration method...")
    
    # Create processor instance
    processor = HubSpotAppointmentProcessor()
    
    # Test cases
    test_cases = [
        ("01:30:00", 90),  # 1 hour 30 minutes
        ("02:00:00", 120),  # 2 hours
        ("00:30:00", 30),   # 30 minutes
        ("00:15:00", 15),   # 15 minutes
        ("03:45:00", 225),  # 3 hours 45 minutes
        ("24:00:00", 1440), # 24 hours
        ("", 0),            # Empty string
        (None, 0),          # None value
        ("invalid", 0),     # Invalid format
        ("1:30:00", 90),    # Without leading zero
    ]
    
    for input_duration, expected_minutes in test_cases:
        result = processor.parse_duration(input_duration)
        print(f"Input: '{input_duration}' -> Expected: {expected_minutes}, Got: {result}")
        assert result == expected_minutes, f"Failed for input '{input_duration}': expected {expected_minutes}, got {result}"
    
    print("✓ All parse_duration tests passed!")

def test_appointment_transformation():
    """Test appointment transformation with duration fields"""
    print("\nTesting appointment transformation...")
    
    processor = HubSpotAppointmentProcessor()
    
    # Test record with duration fields
    test_record = {
        'id': '123',
        'title': 'Test Appointment',
        'duration': '01:30:00',
        'hs_duration': '02:00:00',
        'start_time': '2023-01-01T10:00:00Z',
        'end_time': '2023-01-01T11:30:00Z'
    }
    
    # Transform the record
    transformed = processor.transform_record(test_record)
    
    # Check that duration fields are converted to minutes
    assert transformed['duration'] == 90, f"Expected duration 90, got {transformed['duration']}"
    assert transformed['hs_duration'] == 120, f"Expected hs_duration 120, got {transformed['hs_duration']}"
    
    print("✓ Appointment transformation test passed!")

def test_base_processor_parse_duration():
    """Test that parse_duration is available in base processor"""
    print("\nTesting base processor parse_duration...")
    
    base_processor = HubSpotBaseProcessor()
    
    # Test that the method exists and works
    result = base_processor.parse_duration("01:30:00")
    assert result == 90, f"Expected 90, got {result}"
    
    print("✓ Base processor parse_duration test passed!")

if __name__ == "__main__":
    try:
        test_parse_duration()
        test_appointment_transformation()
        test_base_processor_parse_duration()
        print("\n🎉 All HubSpot duration parsing tests passed!")
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
