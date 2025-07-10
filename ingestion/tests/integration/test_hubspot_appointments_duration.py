#!/usr/bin/env python
"""
Integration tests for HubSpot appointments duration parsing
"""
import unittest
import os
import sys
import django
from django.test import TestCase

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'data_warehouse.settings')
django.setup()

from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor


class TestHubSpotAppointmentDurationParsing(TestCase):
    """Tests for HubSpot appointment duration parsing"""
    
    def setUp(self):
        """Set up test processor"""
        self.processor = HubSpotAppointmentProcessor()
    
    def test_parse_duration_hh_mm_ss_format(self):
        """Test parsing duration in HH:MM:SS format"""
        test_cases = [
            ('2:00:00', 120),  # 2 hours = 120 minutes
            ('1:30:00', 90),   # 1 hour 30 minutes = 90 minutes
            ('0:45:00', 45),   # 45 minutes
            ('0:30:30', 30),   # 30 minutes 30 seconds = 30 minutes (seconds truncated)
            ('3:15:45', 195),  # 3 hours 15 minutes 45 seconds = 195 minutes
        ]
        
        for input_value, expected in test_cases:
            with self.subTest(input_value=input_value):
                result = self.processor.parse_duration(input_value)
                self.assertEqual(result, expected)
    
    def test_parse_duration_numeric_input(self):
        """Test parsing duration with numeric input"""
        test_cases = [
            (120, 120),    # Integer input
            (90.5, 90),    # Float input (should be truncated)
            (0, 0),        # Zero
        ]
        
        for input_value, expected in test_cases:
            with self.subTest(input_value=input_value):
                result = self.processor.parse_duration(input_value)
                self.assertEqual(result, expected)
    
    def test_parse_duration_invalid_input(self):
        """Test parsing duration with invalid input"""
        test_cases = [
            None,          # None input
            '',            # Empty string
            'invalid',     # Invalid format
            '25:00',       # Missing seconds
            '1:2:3:4',     # Too many components
        ]
        
        for input_value in test_cases:
            with self.subTest(input_value=input_value):
                result = self.processor.parse_duration(input_value)
                self.assertEqual(result, 0)  # Should return 0 for invalid input
    
    def test_transform_record_with_duration(self):
        """Test complete record transformation with duration fields"""
        test_record = {
            'id': 'test-123',
            'properties': {
                'hs_duration': '2:00:00',
                'duration': '1:30:00',
                'hs_appointment_name': 'Test Appointment',
                'first_name': 'John',
                'last_name': 'Doe',
            }
        }
        
        result = self.processor.transform_record(test_record)
        
        # Check that duration fields are properly parsed
        self.assertEqual(result['hs_duration'], 120)  # 2 hours
        self.assertEqual(result['duration'], 90)      # 1.5 hours
        self.assertEqual(result['id'], 'test-123')
        self.assertEqual(result['first_name'], 'John')
        self.assertEqual(result['last_name'], 'Doe')


if __name__ == '__main__':
    unittest.main()