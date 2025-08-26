"""
Test Data Usage Controller

This module provides explicit control over what data is used in tests,
with clear safety boundaries and usage reporting.
"""

from enum import Enum
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

class TestDataMode(Enum):
    """Define test data usage modes with clear boundaries"""
    
    # Safe modes (no risk of massive data imports)
    MOCKED = "mocked"           # No real API calls
    MINIMAL = "minimal"         # Real API, 1-5 records max
    SAMPLE = "sample"           # Real API, 10-50 records max
    
    # Controlled modes (limited real data)
    RECENT = "recent"           # Last 3-7 days only
    WEEKLY = "weekly"           # Last 1 week only
    MONTHLY = "monthly"         # Last 1 month only
    
    # Dangerous modes (use with extreme caution)
    FULL_RECENT = "full_recent" # Full sync of recent data (3 months)
    FULL_SYNC = "full_sync"     # ⚠️ DANGER: Full historical sync

@dataclass
class TestDataConfig:
    """Configuration for test data usage"""
    mode: TestDataMode
    max_records: Optional[int] = None
    batch_size: int = 10
    date_range_days: Optional[int] = None
    force_dry_run: bool = True
    description: str = ""
    estimated_records: str = ""
    safety_level: str = ""

class TestDataController:
    """Control and monitor test data usage"""
    
    # Predefined safe configurations
    SAFE_CONFIGS = {
        TestDataMode.MOCKED: TestDataConfig(
            mode=TestDataMode.MOCKED,
            max_records=0,
            batch_size=0,
            force_dry_run=True,
            description="No real API calls, purely mocked responses",
            estimated_records="0",
            safety_level="🟢 SAFE"
        ),
        
        TestDataMode.MINIMAL: TestDataConfig(
            mode=TestDataMode.MINIMAL,
            max_records=5,
            batch_size=5,
            date_range_days=1,
            force_dry_run=True,
            description="Real API, maximum 5 records, dry-run only",
            estimated_records="1-5",
            safety_level="🟢 SAFE"
        ),
        
        TestDataMode.SAMPLE: TestDataConfig(
            mode=TestDataMode.SAMPLE,
            max_records=50,
            batch_size=10,
            date_range_days=7,
            force_dry_run=True,
            description="Real API, maximum 50 records, last 7 days, dry-run only",
            estimated_records="10-50",
            safety_level="🟡 CONTROLLED"
        ),
        
        TestDataMode.RECENT: TestDataConfig(
            mode=TestDataMode.RECENT,
            max_records=None,
            batch_size=25,
            date_range_days=7,
            force_dry_run=False,
            description="Real API, last 7 days, actual sync with small batches",
            estimated_records="50-500",
            safety_level="🟠 MODERATE"
        ),
        
        TestDataMode.FULL_SYNC: TestDataConfig(
            mode=TestDataMode.FULL_SYNC,
            max_records=None,
            batch_size=100,
            date_range_days=None,
            force_dry_run=False,
            description="⚠️ FULL HISTORICAL SYNC - MILLIONS OF RECORDS!",
            estimated_records="MILLIONS",
            safety_level="🔴 DANGEROUS"
        ),
    }
    
    @classmethod
    def get_config(cls, mode: TestDataMode) -> TestDataConfig:
        """Get configuration for specified test data mode"""
        return cls.SAFE_CONFIGS[mode]
    
    @classmethod
    def build_command_args(cls, mode: TestDataMode, command_name: str = "") -> List[str]:
        """Build command arguments based on data mode"""
        config = cls.get_config(mode)
        args = []
        
        # Always add dry-run for safe modes
        if config.force_dry_run:
            args.append('--dry-run')
        
        # Add batch size
        if config.batch_size > 0:
            args.extend(['--batch-size', str(config.batch_size)])
        
        # Add date range if specified
        if config.date_range_days:
            end_date = datetime.now()
            start_date = end_date - timedelta(days=config.date_range_days)
            args.extend([
                '--start-date', start_date.strftime('%Y-%m-%d'),
                '--end-date', end_date.strftime('%Y-%m-%d')
            ])
        
        # Add debug for visibility
        args.append('--debug')
        
        return args
    
    @classmethod
    def validate_safe_usage(cls, mode: TestDataMode) -> Dict[str, Any]:
        """Validate if the test mode is safe to run"""
        config = cls.get_config(mode)
        
        if mode == TestDataMode.FULL_SYNC:
            return {
                'safe': False,
                'warning': 'FULL SYNC MODE - Will process millions of records!',
                'confirmation_required': True,
                'estimated_time': '30+ minutes',
                'data_usage': 'HIGH'
            }
        
        if mode in [TestDataMode.FULL_RECENT]:
            return {
                'safe': False,
                'warning': 'Large data sync - may process thousands of records',
                'confirmation_required': True,
                'estimated_time': '10-20 minutes',
                'data_usage': 'MODERATE'
            }
        
        return {
            'safe': True,
            'warning': None,
            'confirmation_required': False,
            'estimated_time': '< 5 minutes',
            'data_usage': 'LOW'
        }
    
    @classmethod
    def print_usage_report(cls, mode: TestDataMode, command_name: str = ""):
        """Print detailed report of what data will be used"""
        config = cls.get_config(mode)
        
        report = f"""
{'='*60}
TEST DATA USAGE REPORT
{'='*60}

Command: {command_name or 'Generic CRM Command'}
Data Mode: {mode.value.upper()}
Safety Level: {config.safety_level}

Configuration:
- Max Records: {config.max_records or 'No limit'}
- Batch Size: {config.batch_size}
- Date Range: {config.date_range_days or 'No limit'} days
- Dry Run: {'YES' if config.force_dry_run else 'NO'}

Estimated Impact:
- Records: {config.estimated_records}
- Duration: < 5 minutes
- API Calls: {'None' if mode == TestDataMode.MOCKED else 'Minimal'}

Description: {config.description}

Command Args: {' '.join(cls.build_command_args(mode, command_name))}
{'='*60}
"""
        print(report)

# Usage examples for different test scenarios
class TestScenarios:
    """Pre-defined test scenarios with appropriate data controls"""
    
    @staticmethod
    def unit_test_scenario():
        """For unit tests - no real data"""
        return TestDataController.get_config(TestDataMode.MOCKED)
    
    @staticmethod
    def integration_test_scenario():
        """For integration tests - minimal real data"""
        return TestDataController.get_config(TestDataMode.SAMPLE)
    
    @staticmethod  
    def validation_test_scenario():
        """For validating recent changes - controlled real data"""
        return TestDataController.get_config(TestDataMode.RECENT)
    
    @staticmethod
    def full_system_test_scenario():
        """For full system testing - use with extreme caution!"""
        return TestDataController.get_config(TestDataMode.FULL_SYNC)

if __name__ == "__main__":
    # Example usage
    print("Available test data modes:")
    for mode in TestDataMode:
        config = TestDataController.get_config(mode)
        print(f"  {config.safety_level} {mode.value}: {config.description}")
    
    print("\nExample: Integration test for Arrivy entities")
    TestDataController.print_usage_report(TestDataMode.SAMPLE, "sync_arrivy_entities")
