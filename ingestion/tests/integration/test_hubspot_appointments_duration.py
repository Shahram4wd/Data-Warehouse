import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from ingestion.sync.hubspot.processors.appointments import HubSpotAppointmentProcessor
from ingestion.sync.hubspot.validators import HubSpotDurationValidator
from ingestion.base.exceptions import ValidationException


class TestHubSpotAppointmentProcessorIntegration:
    """Integration tests for HubSpot appointment processor with duration handling"""
    
    @pytest.fixture
    def processor(self):
        return HubSpotAppointmentProcessor()
    
    @pytest.fixture
    def sample_hubspot_appointment(self):
        """Sample HubSpot appointment data with duration issues"""
        return {
            'id': '392484709473',
            'properties': {
                'appointment_id': '123456',
                'hs_appointment_name': 'Test Appointment',
                'hs_appointment_start': '2025-07-09T10:00:00Z',
                'hs_appointment_end': '2025-07-09T12:00:00Z',
                'hs_duration': '2:00:00',  # This is the problematic field
                'duration': '2:00:00',    # This too
                'email': 'test@example.com',
                'phone1': '555-123-4567',
                'first_name': 'John',
                'last_name': 'Doe',
                'appointment_status': 'scheduled',
                'is_complete': False,
            }
        }
    
    def test_duration_transformation_hms_format(self, processor):
        """Test duration transformation from HH:MM:SS format"""
        # Test the transform_duration method directly
        result = processor._transform_duration("2:00:00")
        assert result == 120  # 2 hours = 120 minutes
        
        result = processor._transform_duration("1:30:00")
        assert result == 90   # 1.5 hours = 90 minutes
        
        result = processor._transform_duration("0:45:00")
        assert result == 45   # 45 minutes
    
    def test_duration_transformation_various_formats(self, processor):
        """Test duration transformation with various formats"""
        # HH:MM format
        result = processor._transform_duration("2:30")
        assert result == 150
        
        # Integer minutes
        result = processor._transform_duration(90)
        assert result == 90
        
        # String integer
        result = processor._transform_duration("60")
        assert result == 60
        
        # Decimal hours
        result = processor._transform_duration("2.5")
        assert result == 150
    
    def test_duration_transformation_invalid_values(self, processor):
        """Test duration transformation with invalid values"""
        # Invalid format should return 0
        result = processor._transform_duration("invalid")
        assert result == 0
        
        # None should return 0
        result = processor._transform_duration(None)
        assert result == 0
        
        # Empty string should return 0
        result = processor._transform_duration("")
        assert result == 0
    
    def test_transform_record_with_duration_issue(self, processor, sample_hubspot_appointment):
        """Test transforming a record with the exact duration issue"""
        transformed = processor.transform_record(sample_hubspot_appointment)
        
        # Check that duration fields are converted to integers
        assert transformed['hs_duration'] == 120
        assert transformed['duration'] == 120
        assert isinstance(transformed['hs_duration'], int)
        assert isinstance(transformed['duration'], int)
        
        # Check other fields are preserved
        assert transformed['id'] == '392484709473'
        assert transformed['appointment_id'] == '123456'
        assert transformed['first_name'] == 'John'
        assert transformed['last_name'] == 'Doe'
    
    def test_validate_record_with_duration_issue(self, processor, sample_hubspot_appointment):
        """Test validating a record with duration issues"""
        # First transform the record
        transformed = processor.transform_record(sample_hubspot_appointment)
        
        # Then validate it
        validated = processor.validate_record(transformed)
        
        # Check that duration fields are properly validated
        assert validated['hs_duration'] == 120
        assert validated['duration'] == 120
        assert isinstance(validated['hs_duration'], int)
        assert isinstance(validated['duration'], int)
    
    def test_full_processing_pipeline(self, processor, sample_hubspot_appointment):
        """Test the complete processing pipeline for an appointment with duration issues"""
        # Transform the record
        transformed = processor.transform_record(sample_hubspot_appointment)
        
        # Validate the record
        validated = processor.validate_record(transformed)
        
        # Verify the final result
        assert validated['id'] == '392484709473'
        assert validated['hs_duration'] == 120
        assert validated['duration'] == 120
        assert validated['email'] == 'test@example.com'
        assert validated['appointment_status'] == 'scheduled'
        
        # Ensure duration fields are integers (not strings)
        assert isinstance(validated['hs_duration'], int)
        assert isinstance(validated['duration'], int)
    
    def test_batch_processing_with_duration_issues(self, processor):
        """Test batch processing with multiple appointments having duration issues"""
        appointments = [
            {
                'id': '1',
                'properties': {
                    'hs_duration': '2:00:00',
                    'duration': '1:30:00',
                    'hs_appointment_name': 'Appointment 1'
                }
            },
            {
                'id': '2',
                'properties': {
                    'hs_duration': '3:15:00',
                    'duration': '0:45:00',
                    'hs_appointment_name': 'Appointment 2'
                }
            },
            {
                'id': '3',
                'properties': {
                    'hs_duration': 90,  # Already an integer
                    'duration': '2.5',  # Decimal hours
                    'hs_appointment_name': 'Appointment 3'
                }
            }
        ]
        
        # Process all appointments
        processed = []
        for appointment in appointments:
            transformed = processor.transform_record(appointment)
            validated = processor.validate_record(transformed)
            processed.append(validated)
        
        # Verify results
        assert processed[0]['hs_duration'] == 120  # 2:00:00 -> 120 minutes
        assert processed[0]['duration'] == 90      # 1:30:00 -> 90 minutes
        
        assert processed[1]['hs_duration'] == 195  # 3:15:00 -> 195 minutes
        assert processed[1]['duration'] == 45      # 0:45:00 -> 45 minutes
        
        assert processed[2]['hs_duration'] == 90   # 90 -> 90 minutes
        assert processed[2]['duration'] == 150     # 2.5 hours -> 150 minutes
        
        # Ensure all are integers
        for appointment in processed:
            assert isinstance(appointment['hs_duration'], int)
            assert isinstance(appointment['duration'], int)
    
    def test_error_handling_with_invalid_duration(self, processor):
        """Test error handling when duration validation fails"""
        appointment = {
            'id': '123',
            'properties': {
                'hs_duration': 'completely_invalid',
                'duration': 'also_invalid',
                'hs_appointment_name': 'Test'
            }
        }
        
        # Transform and validate
        transformed = processor.transform_record(appointment)
        validated = processor.validate_record(transformed)
        
        # Should have fallback to 0 for invalid durations
        assert validated['hs_duration'] == 0
        assert validated['duration'] == 0
        assert isinstance(validated['hs_duration'], int)
        assert isinstance(validated['duration'], int)
    
    @patch('ingestion.sync.hubspot.processors.appointments.logger')
    def test_logging_for_duration_errors(self, mock_logger, processor):
        """Test that duration validation errors are properly logged"""
        appointment = {
            'id': '392484709473',
            'properties': {
                'hs_duration': 'invalid_format',
                'duration': 'also_invalid'
            }
        }
        
        # Transform (this should log errors)
        transformed = processor.transform_record(appointment)
        
        # Validate (this should also log errors)
        validated = processor.validate_record(transformed)
        
        # Verify logging was called
        assert mock_logger.error.called
        
        # Check that the appointment ID is in the log message
        log_calls = mock_logger.error.call_args_list
        assert any('392484709473' in str(call) for call in log_calls)
