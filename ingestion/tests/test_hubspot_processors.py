"""
Unit tests for HubSpot data processors
"""
from datetime import datetime, timezone
from decimal import Decimal
from django.test import TestCase
from ingestion.sync.hubspot.processors import (
    HubSpotContactProcessor,
    HubSpotAppointmentProcessor,
    HubSpotDivisionProcessor,
    HubSpotDealProcessor
)
from ingestion.base.exceptions import ValidationException


class TestHubSpotContactProcessor(TestCase):
    """Test HubSpot contact processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = HubSpotContactProcessor()
        
    def test_get_field_mappings(self):
        """Test field mappings"""
        mappings = self.processor.get_field_mappings()
        
        self.assertIn('id', mappings)
        self.assertIn('properties.firstname', mappings)
        self.assertIn('properties.email', mappings)
        self.assertEqual(mappings['id'], 'id')
        self.assertEqual(mappings['properties.firstname'], 'firstname')
        
    def test_transform_record_success(self):
        """Test successful record transformation"""
        record = {
            'id': '12345',
            'properties': {
                'firstname': 'John',
                'lastname': 'Doe',
                'email': 'john.doe@example.com',
                'phone': '555-1234',
                'createdate': '1640995200000',  # Timestamp in milliseconds
                'price': '1000.50'
            }
        }
        
        transformed = self.processor.transform_record(record)
        
        self.assertEqual(transformed['id'], '12345')
        self.assertEqual(transformed['firstname'], 'John')
        self.assertEqual(transformed['lastname'], 'Doe')
        self.assertEqual(transformed['email'], 'john.doe@example.com')
        self.assertEqual(transformed['phone'], '555-1234')
        self.assertIsInstance(transformed['createdate'], datetime)
        self.assertEqual(transformed['price'], 1000.50)
        
    def test_transform_record_with_empty_properties(self):
        """Test transformation with empty properties"""
        record = {
            'id': '12345',
            'properties': {}
        }
        
        transformed = self.processor.transform_record(record)
        
        self.assertEqual(transformed['id'], '12345')
        self.assertIsNone(transformed['firstname'])
        self.assertIsNone(transformed['lastname'])
        self.assertIsNone(transformed['email'])
        
    def test_validate_record_success(self):
        """Test successful record validation"""
        record = {
            'id': '12345',
            'firstname': 'John',
            'lastname': 'Doe',
            'email': 'JOHN.DOE@EXAMPLE.COM',
            'phone': '(555) 123-4567'
        }
        
        validated = self.processor.validate_record(record)
        
        self.assertEqual(validated['id'], '12345')
        self.assertEqual(validated['email'], 'john.doe@example.com')  # Should be lowercased
        self.assertEqual(validated['phone'], '5551234567')  # Should be cleaned
        
    def test_validate_record_missing_id(self):
        """Test validation with missing ID"""
        record = {
            'firstname': 'John',
            'lastname': 'Doe'
        }
        
        with self.assertRaises(ValidationException):
            self.processor.validate_record(record)
            
    def test_parse_datetime_timestamp(self):
        """Test parsing datetime from timestamp"""
        # Test with millisecond timestamp
        result = self.processor._parse_datetime('1640995200000')
        self.assertIsInstance(result, datetime)
        self.assertEqual(result.year, 2022)
        
    def test_parse_datetime_none(self):
        """Test parsing None datetime"""
        result = self.processor._parse_datetime(None)
        self.assertIsNone(result)
        
    def test_parse_datetime_empty_string(self):
        """Test parsing empty string datetime"""
        result = self.processor._parse_datetime('')
        self.assertIsNone(result)
        
    def test_parse_decimal_success(self):
        """Test parsing decimal value"""
        result = self.processor._parse_decimal('1000.50')
        self.assertEqual(result, 1000.50)
        
    def test_parse_decimal_invalid(self):
        """Test parsing invalid decimal value"""
        result = self.processor._parse_decimal('not_a_number')
        self.assertIsNone(result)
        
    def test_clean_phone_success(self):
        """Test phone number cleaning"""
        result = self.processor._clean_phone('(555) 123-4567')
        self.assertEqual(result, '5551234567')
        
    def test_clean_phone_with_country_code(self):
        """Test phone number cleaning with country code"""
        result = self.processor._clean_phone('+1 (555) 123-4567')
        self.assertEqual(result, '+15551234567')
        
    def test_clean_phone_empty(self):
        """Test cleaning empty phone number"""
        result = self.processor._clean_phone('')
        self.assertEqual(result, '')
        
    def test_clean_email_success(self):
        """Test email cleaning"""
        result = self.processor._clean_email('  JOHN.DOE@EXAMPLE.COM  ')
        self.assertEqual(result, 'john.doe@example.com')
        
    def test_clean_email_empty(self):
        """Test cleaning empty email"""
        result = self.processor._clean_email('')
        self.assertEqual(result, '')


class TestHubSpotAppointmentProcessor(TestCase):
    """Test HubSpot appointment processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = HubSpotAppointmentProcessor()
        
    def test_get_field_mappings(self):
        """Test field mappings"""
        mappings = self.processor.get_field_mappings()
        
        self.assertIn('id', mappings)
        self.assertIn('properties.appointment_id', mappings)
        self.assertIn('properties.hs_appointment_start', mappings)
        self.assertEqual(mappings['id'], 'id')
        self.assertEqual(mappings['properties.appointment_id'], 'appointment_id')
        
    def test_transform_record_success(self):
        """Test successful appointment record transformation"""
        record = {
            'id': '54321',
            'properties': {
                'appointment_id': 'APT-12345',
                'hs_appointment_name': 'Sales Meeting',
                'hs_appointment_start': '1640995200000',
                'hs_appointment_end': '1640998800000',
                'first_name': 'John',
                'last_name': 'Doe',
                'email': 'john.doe@example.com'
            }
        }
        
        transformed = self.processor.transform_record(record)
        
        self.assertEqual(transformed['id'], '54321')
        self.assertEqual(transformed['appointment_id'], 'APT-12345')
        self.assertEqual(transformed['hs_appointment_name'], 'Sales Meeting')
        self.assertEqual(transformed['first_name'], 'John')
        self.assertEqual(transformed['last_name'], 'Doe')
        self.assertEqual(transformed['email'], 'john.doe@example.com')
        self.assertIsInstance(transformed['hs_appointment_start'], datetime)
        self.assertIsInstance(transformed['hs_appointment_end'], datetime)


class TestHubSpotDivisionProcessor(TestCase):
    """Test HubSpot division processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = HubSpotDivisionProcessor()
        
    def test_get_field_mappings(self):
        """Test field mappings"""
        mappings = self.processor.get_field_mappings()
        
        self.assertIn('id', mappings)
        self.assertIn('properties.name', mappings)
        self.assertEqual(mappings['id'], 'id')
        self.assertEqual(mappings['properties.name'], 'name')
        
    def test_transform_record_success(self):
        """Test successful division record transformation"""
        record = {
            'id': '67890',
            'properties': {
                'name': 'Sales Division',
                'description': 'Main sales division',
                'genius_division_id': 'DIV-123'
            }
        }
        
        transformed = self.processor.transform_record(record)
        
        self.assertEqual(transformed['id'], '67890')
        self.assertEqual(transformed['name'], 'Sales Division')
        self.assertEqual(transformed['description'], 'Main sales division')
        self.assertEqual(transformed['genius_division_id'], 'DIV-123')


class TestHubSpotDealProcessor(TestCase):
    """Test HubSpot deal processor"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.processor = HubSpotDealProcessor()
        
    def test_get_field_mappings(self):
        """Test field mappings"""
        mappings = self.processor.get_field_mappings()
        
        self.assertIn('id', mappings)
        self.assertIn('properties.dealname', mappings)
        self.assertIn('properties.amount', mappings)
        self.assertEqual(mappings['id'], 'id')
        self.assertEqual(mappings['properties.dealname'], 'dealname')
        
    def test_transform_record_success(self):
        """Test successful deal record transformation"""
        record = {
            'id': '99999',
            'properties': {
                'dealname': 'Big Sale',
                'amount': '50000.00',
                'dealstage': 'closedwon',
                'createdate': '1640995200000',
                'closedate': '1641081600000'
            }
        }
        
        transformed = self.processor.transform_record(record)
        
        self.assertEqual(transformed['id'], '99999')
        self.assertEqual(transformed['dealname'], 'Big Sale')
        self.assertEqual(transformed['amount'], 50000.00)
        self.assertEqual(transformed['dealstage'], 'closedwon')
        self.assertIsInstance(transformed['createdate'], datetime)
        self.assertIsInstance(transformed['closedate'], datetime)
        
    def test_validate_record_success(self):
        """Test successful deal record validation"""
        record = {
            'id': '99999',
            'dealname': 'Big Sale',
            'amount': 50000.00
        }
        
        validated = self.processor.validate_record(record)
        
        self.assertEqual(validated['id'], '99999')
        self.assertEqual(validated['dealname'], 'Big Sale')
        self.assertEqual(validated['amount'], 50000.00)
        
    def test_validate_record_missing_id(self):
        """Test deal validation with missing ID"""
        record = {
            'dealname': 'Big Sale',
            'amount': 50000.00
        }
        
        with self.assertRaises(ValidationException):
            self.processor.validate_record(record)
