import pytest
from ingestion.sync.hubspot.validators import HubSpotDurationValidator
from ingestion.base.exceptions import ValidationException

class TestHubSpotDurationValidator:
    """Test suite for HubSpot duration validator"""
    
    @pytest.fixture
    def validator(self):
        return HubSpotDurationValidator()
    
    def test_convert_hms_format(self, validator):
        """Test HH:MM:SS format conversion"""
        result = validator.validate("2:00:00")
        assert result == 120  # 2 hours = 120 minutes
        
        result = validator.validate("1:30:30")
        assert result == 90  # 1.5 hours = 90 minutes (rounded down)
        
        result = validator.validate("0:45:00")
        assert result == 45  # 45 minutes
    
    def test_convert_hm_format(self, validator):
        """Test HH:MM format conversion"""
        result = validator.validate("2:30")
        assert result == 150  # 2.5 hours = 150 minutes
        
        result = validator.validate("0:45")
        assert result == 45  # 45 minutes
        
        result = validator.validate("1:00")
        assert result == 60  # 1 hour = 60 minutes
    
    def test_convert_integer_minutes(self, validator):
        """Test integer minutes conversion"""
        result = validator.validate(90)
        assert result == 90
        
        result = validator.validate("60")
        assert result == 60
        
        result = validator.validate(0)
        assert result == 0
    
    def test_convert_decimal_hours(self, validator):
        """Test decimal hours conversion"""
        result = validator.validate("2.5")
        assert result == 150  # 2.5 hours = 150 minutes
        
        result = validator.validate("0.5")
        assert result == 30  # 0.5 hours = 30 minutes
        
        result = validator.validate("1.75")
        assert result == 105  # 1.75 hours = 105 minutes
    
    def test_invalid_formats(self, validator):
        """Test invalid format handling"""
        with pytest.raises(ValidationException):
            validator.validate("invalid")
        
        with pytest.raises(ValidationException):
            validator.validate("25:99:99")
        
        with pytest.raises(ValidationException):
            validator.validate("abc:def")
        
        with pytest.raises(ValidationException):
            validator.validate(":")
    
    def test_empty_values(self, validator):
        """Test empty value handling"""
        result = validator.validate(None)
        assert result is None
        
        result = validator.validate("")
        assert result is None
        
        result = validator.validate("   ")
        assert result is None
    
    def test_negative_values(self, validator):
        """Test negative value handling"""
        result = validator.validate(-30)
        assert result == 0  # Should be converted to 0
        
        result = validator.validate("-1:30:00")
        # This would be treated as invalid format since regex doesn't match negative
        with pytest.raises(ValidationException):
            validator.validate("-1:30:00")
    
    def test_edge_cases(self, validator):
        """Test edge cases"""
        # Large values
        result = validator.validate("10:00:00")
        assert result == 600  # 10 hours = 600 minutes
        
        # Single digit hours/minutes
        result = validator.validate("1:05:30")
        assert result == 65  # 1 hour 5 minutes 30 seconds = 65 minutes
        
        # Zero values
        result = validator.validate("0:00:00")
        assert result == 0
        
        result = validator.validate("0:00")
        assert result == 0
    
    def test_required_validator(self):
        """Test required field validation"""
        required_validator = HubSpotDurationValidator(required=True)
        
        with pytest.raises(ValidationException):
            required_validator.validate(None)
        
        with pytest.raises(ValidationException):
            required_validator.validate("")
        
        # Valid value should pass
        result = required_validator.validate("2:00:00")
        assert result == 120
    
    def test_specific_error_case(self, validator):
        """Test the specific error case from the issue"""
        # This is the exact case from the error message
        result = validator.validate("2:00:00")
        assert result == 120
        assert isinstance(result, int)
