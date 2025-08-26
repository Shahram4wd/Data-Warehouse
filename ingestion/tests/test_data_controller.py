"""
Test Data Controller for CRM Testing Framework

Controls data usage levels and safety boundaries for CRM tests.
"""

from enum import Enum
from typing import Optional, Dict, Any


class DataUsageLevel(Enum):
    MOCKED = "MOCKED"           # No real API calls
    MINIMAL = "MINIMAL"         # 1-10 records max
    SAMPLE = "SAMPLE"           # 50-100 records max  
    RECENT = "RECENT"           # Last 7 days only
    FULL_SYNC = "FULL_SYNC"     # ALL records (dangerous!)


class TestDataController:
    """
    Controls and validates data usage for CRM tests
    """
    
    def __init__(self):
        self.current_level = DataUsageLevel.MOCKED
        self.safety_limits = {
            DataUsageLevel.MOCKED: {
                'max_records': 0,
                'max_api_calls': 0,
                'time_limit_days': None,
                'safety_score': 'safe'
            },
            DataUsageLevel.MINIMAL: {
                'max_records': 10,
                'max_api_calls': 5,
                'time_limit_days': 1,
                'safety_score': 'safe'
            },
            DataUsageLevel.SAMPLE: {
                'max_records': 100,
                'max_api_calls': 20,
                'time_limit_days': 7,
                'safety_score': 'moderate'
            },
            DataUsageLevel.RECENT: {
                'max_records': 1000,
                'max_api_calls': 50,
                'time_limit_days': 7,
                'safety_score': 'moderate'
            },
            DataUsageLevel.FULL_SYNC: {
                'max_records': None,  # Unlimited
                'max_api_calls': None,  # Unlimited
                'time_limit_days': None,  # No time limit
                'safety_score': 'dangerous'
            }
        }
    
    def set_data_usage_level(self, level: str) -> None:
        """Set the data usage level with validation"""
        try:
            self.current_level = DataUsageLevel(level)
        except ValueError:
            valid_levels = [level.value for level in DataUsageLevel]
            raise ValueError(f"Invalid data usage level '{level}'. Must be one of: {valid_levels}")
    
    def get_current_limits(self) -> Dict[str, Any]:
        """Get current safety limits"""
        return self.safety_limits[self.current_level]
    
    def is_safe_level(self) -> bool:
        """Check if current level is considered safe"""
        limits = self.get_current_limits()
        return limits['safety_score'] == 'safe'
    
    def validate_test_parameters(self, **kwargs) -> Dict[str, Any]:
        """Validate test parameters against current limits"""
        limits = self.get_current_limits()
        
        validation_result = {
            'valid': True,
            'warnings': [],
            'adjusted_params': kwargs.copy()
        }
        
        # Check batch size against max records
        if 'batch_size' in kwargs and limits['max_records'] is not None:
            requested_batch = kwargs['batch_size']
            if requested_batch > limits['max_records']:
                validation_result['warnings'].append(
                    f"Batch size {requested_batch} exceeds limit {limits['max_records']}, adjusting"
                )
                validation_result['adjusted_params']['batch_size'] = limits['max_records']
        
        # Add safety parameters
        if self.current_level != DataUsageLevel.MOCKED:
            # Always add dry-run for non-mocked tests unless explicitly disabled
            if 'dry_run' not in validation_result['adjusted_params']:
                validation_result['adjusted_params']['dry_run'] = True
                validation_result['warnings'].append("Added --dry-run flag for safety")
        
        # Add time limits for applicable levels
        if limits['time_limit_days'] is not None:
            from datetime import datetime, timedelta
            if 'start_date' not in validation_result['adjusted_params']:
                start_date = datetime.now() - timedelta(days=limits['time_limit_days'])
                validation_result['adjusted_params']['start_date'] = start_date.strftime('%Y-%m-%d')
                validation_result['warnings'].append(
                    f"Added time limit: last {limits['time_limit_days']} days"
                )
        
        return validation_result
    
    def get_safety_summary(self) -> str:
        """Get a human-readable safety summary"""
        limits = self.get_current_limits()
        level_name = self.current_level.value
        
        summary = f"Data Usage Level: {level_name}\n"
        summary += f"Safety Level: {limits['safety_score'].upper()}\n"
        
        if limits['max_records'] is not None:
            summary += f"Max Records: {limits['max_records']}\n"
        else:
            summary += "Max Records: Unlimited ⚠️\n"
        
        if limits['max_api_calls'] is not None:
            summary += f"Max API Calls: {limits['max_api_calls']}\n"
        else:
            summary += "Max API Calls: Unlimited ⚠️\n"
        
        if limits['time_limit_days'] is not None:
            summary += f"Time Limit: Last {limits['time_limit_days']} days\n"
        else:
            summary += "Time Limit: None ⚠️\n"
        
        return summary
    
    @classmethod
    def get_all_levels_info(cls) -> Dict[str, Dict]:
        """Get information about all available data usage levels"""
        controller = cls()
        return {level.value: controller.safety_limits[level] for level in DataUsageLevel}
