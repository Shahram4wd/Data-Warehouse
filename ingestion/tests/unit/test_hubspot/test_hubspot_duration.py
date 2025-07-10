#!/usr/bin/env python3
"""
Unit tests for HubSpot appointment duration parsing (no database required)
"""
import unittest
from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor

class HubSpotDurationParsingTestCase(unittest.TestCase):
    """Test case for HubSpot duration parsing functionality"""
    
    def test_parse_duration(self):
        """Test parse_duration method"""
        print("Testing parse_duration method...")
        
        # Create processor instance
        processor = HubSpotAppointmentProcessor()
        
        # Test cases
        test_cases = [
            # HH:MM:SS format
            ("01:30:00", 90),  # 1 hour 30 minutes
            ("02:00:00", 120),  # 2 hours
            ("00:30:00", 30),   # 30 minutes
            ("00:15:00", 15),   # 15 minutes
            ("03:45:00", 225),  # 3 hours 45 minutes
            ("24:00:00", 1440), # 24 hours
            ("1:30:00", 90),    # Without leading zero
            
            # MM:SS format
            ("30:00", 30),      # 30 minutes
            ("15:30", 15),      # 15 minutes 30 seconds
            
            # Numeric strings (seconds) - these were causing the warnings
            ("7200", 120),      # 7200 seconds = 120 minutes  
            ("120", 2),         # 120 seconds = 2 minutes
            ("3600", 60),       # 3600 seconds = 60 minutes
            
            # Numeric strings (milliseconds) - these were causing the warnings
            ("7200000", 120),   # 7200000 ms = 120 minutes
            ("120000", 2),      # 120000 ms = 2 minutes
            
            # Edge cases
            ("", 0),            # Empty string
            (None, 0),          # None value
            ("invalid", 0),     # Invalid format
        ]
        
        for input_duration, expected_minutes in test_cases:
            with self.subTest(input_duration=input_duration):
                result = processor.parse_duration(input_duration)
                print(f"Input: '{input_duration}' -> Expected: {expected_minutes}, Got: {result}")
                self.assertEqual(result, expected_minutes, 
                    f"Failed for input '{input_duration}': expected {expected_minutes}, got {result}")
        
        print("✓ All parse_duration tests passed!")

    def test_appointment_transformation(self):
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
        
        # Just test the duration parsing, not the full transformation
        # since that might require database access
        duration_result = processor.parse_duration(test_record['duration'])
        hs_duration_result = processor.parse_duration(test_record['hs_duration'])
        
        # Check that duration fields are converted to minutes
        self.assertEqual(duration_result, 90, f"Expected duration 90, got {duration_result}")
        self.assertEqual(hs_duration_result, 120, f"Expected hs_duration 120, got {hs_duration_result}")
        
        print("✓ Appointment transformation test passed!")

    def test_base_processor_parse_duration(self):
        """Test that parse_duration is available in base processor"""
        print("\nTesting base processor parse_duration...")
        
        # Use concrete processor instead of abstract base
        processor = HubSpotAppointmentProcessor()
        
        # Test that the method exists and works
        result = processor.parse_duration("01:30:00")
        self.assertEqual(result, 90, f"Expected 90, got {result}")
        
        print("✓ Base processor parse_duration test passed!")

    def test_numeric_duration_formats(self):
        """Test the specific numeric formats that were causing warnings"""
        processor = HubSpotAppointmentProcessor()
        
        # Test the exact values from the warning messages
        result_7200000 = processor.parse_duration('7200000')  # milliseconds
        result_120 = processor.parse_duration('120')  # seconds
        
        self.assertEqual(result_7200000, 120, "7200000 milliseconds should equal 120 minutes")
        self.assertEqual(result_120, 2, "120 seconds should equal 2 minutes")
        
        print("✓ Numeric duration format tests passed!")

if __name__ == '__main__':
    unittest.main(verbosity=2)
