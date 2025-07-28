#!/usr/bin/env python3
"""
Test script to verify enhanced PostgreSQL error logging functionality
"""

import asyncio
import logging
from unittest.mock import Mock, patch
import re

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
logger = logging.getLogger(__name__)

class MockSalesProSync:
    """Mock version of SalesProSync to test error logging methods"""
    
    def __init__(self):
        self.batch_size = 500
        self.table_name = "salespro_leadresult"
    
    def _log_record_field_lengths(self, record: dict, record_id: str) -> None:
        """Log field lengths for a record to help diagnose character length violations"""
        logger.error(f"Field lengths for record {record_id}:")
        for field, value in record.items():
            if value is not None:
                value_str = str(value)
                length = len(value_str)
                sample = value_str[:50] + '...' if length > 50 else value_str
                logger.error(f"  {field}: length={length}, sample='{sample}'")
    
    def _log_record_null_fields(self, record: dict, record_id: str) -> None:
        """Log null/empty fields for a record to help diagnose not-null violations"""
        null_fields = []
        empty_fields = []
        
        for field, value in record.items():
            if value is None:
                null_fields.append(field)
            elif value == '':
                empty_fields.append(field)
        
        if null_fields:
            logger.error(f"Record {record_id} has null fields: {null_fields}")
        if empty_fields:
            logger.error(f"Record {record_id} has empty string fields: {empty_fields}")
    
    async def _log_constraint_violation_details(self, records: list, error_msg: str, violation_type: str) -> None:
        """Log detailed information about PostgreSQL constraint violations"""
        
        logger.error(f"PostgreSQL UPSERT failed with {violation_type} violation: {error_msg}")
        
        # Extract field name from error message if possible
        field_pattern = r'column "([^"]+)"'
        field_match = re.search(field_pattern, error_msg)
        violating_field = field_match.group(1) if field_match else "unknown"
        
        # Extract character limit from "value too long" errors
        char_limit = None
        if violation_type == "character_length":
            limit_pattern = r'character varying\((\d+)\)'
            limit_match = re.search(limit_pattern, error_msg)
            char_limit = int(limit_match.group(1)) if limit_match else None
        
        # Log details for each record that might be causing the issue
        logger.error(f"Analyzing {len(records)} records for {violation_type} in field '{violating_field}':")
        
        problem_records = []
        for record in records:
            estimate_id = record.get('estimate_id', 'unknown')
            
            if violation_type == "character_length" and violating_field != "unknown" and char_limit:
                # Check field length violations
                field_value = record.get(violating_field)
                if field_value and len(str(field_value)) > char_limit:
                    problem_records.append({
                        'estimate_id': estimate_id,
                        'field': violating_field,
                        'value_length': len(str(field_value)),
                        'max_length': char_limit,
                        'sample_value': str(field_value)[:100] + '...' if len(str(field_value)) > 100 else str(field_value)
                    })
            
            elif violation_type == "not_null":
                # Check for null values in required fields
                if violating_field != "unknown":
                    field_value = record.get(violating_field)
                    if field_value is None or field_value == '':
                        problem_records.append({
                            'estimate_id': estimate_id,
                            'field': violating_field,
                            'issue': 'null_value'
                        })
            
            elif violation_type == "duplicate_key":
                # Log duplicate estimate_ids
                problem_records.append({
                    'estimate_id': estimate_id,
                    'field': 'estimate_id',
                    'issue': 'duplicate_key'
                })
        
        # Log specific problem records
        if problem_records:
            logger.error(f"Found {len(problem_records)} problematic records:")
            for i, problem in enumerate(problem_records[:10]):  # Limit to first 10 for readability
                if violation_type == "character_length":
                    logger.error(f"  #{i+1} estimate_id: {problem['estimate_id']}, "
                               f"field: {problem['field']}, "
                               f"value_length: {problem['value_length']}, "
                               f"max_length: {problem['max_length']}, "
                               f"sample: {problem['sample_value']}")
                else:
                    logger.error(f"  #{i+1} estimate_id: {problem['estimate_id']}, "
                               f"field: {problem['field']}, "
                               f"issue: {problem['issue']}")
            
            if len(problem_records) > 10:
                logger.error(f"  ... and {len(problem_records) - 10} more records with similar issues")
        else:
            logger.error(f"No obvious {violation_type} violations found in record data. "
                        f"Issue might be with data type conversion or database schema mismatch.")
            
            # Log a sample of estimate_ids for debugging
            sample_ids = [r.get('estimate_id', 'unknown') for r in records[:5]]
            logger.error(f"Sample estimate_ids in this batch: {sample_ids}")

async def test_character_length_violation():
    """Test character length violation logging"""
    print("\n=== Testing Character Length Violation Logging ===")
    
    sync = MockSalesProSync()
    
    # Mock records with one having a field that's too long
    test_records = [
        {
            'estimate_id': 'EST123',
            'customer_name': 'John Doe',
            'phone': '555-1234'
        },
        {
            'estimate_id': 'EST456', 
            'customer_name': 'Jane Smith',
            'phone': '555-5678901234567890'  # This would be too long for varchar(10)
        },
        {
            'estimate_id': 'EST789',
            'customer_name': 'Bob Johnson', 
            'phone': '555-9999'
        }
    ]
    
    # Mock PostgreSQL error message
    error_msg = 'value too long for type character varying(10) column "phone"'
    
    await sync._log_constraint_violation_details(test_records, error_msg, "character_length")

async def test_not_null_violation():
    """Test not-null constraint violation logging"""
    print("\n=== Testing Not-Null Violation Logging ===")
    
    sync = MockSalesProSync()
    
    # Mock records with null values
    test_records = [
        {
            'estimate_id': 'EST123',
            'customer_name': 'John Doe',
            'required_field': 'value'
        },
        {
            'estimate_id': 'EST456',
            'customer_name': 'Jane Smith', 
            'required_field': None  # This violates not-null
        },
        {
            'estimate_id': 'EST789',
            'customer_name': 'Bob Johnson',
            'required_field': ''  # This also violates not-null 
        }
    ]
    
    error_msg = 'null value in column "required_field" violates not-null constraint'
    
    await sync._log_constraint_violation_details(test_records, error_msg, "not_null")

def test_individual_record_logging():
    """Test individual record field length and null field logging"""
    print("\n=== Testing Individual Record Logging ===")
    
    sync = MockSalesProSync()
    
    # Test record with various field lengths
    test_record = {
        'estimate_id': 'EST123',
        'customer_name': 'John Doe',
        'description': 'This is a very long description that exceeds normal field length limits and should be logged with appropriate detail',
        'phone': '555-1234567890123456789',
        'email': 'john.doe@example.com',
        'null_field': None,
        'empty_field': '',
        'normal_field': 'OK'
    }
    
    print("Testing field length logging:")
    sync._log_record_field_lengths(test_record, 'EST123')
    
    print("\nTesting null field logging:")
    sync._log_record_null_fields(test_record, 'EST123')

async def main():
    """Run all tests"""
    print("Testing Enhanced PostgreSQL Error Logging")
    print("=" * 50)
    
    await test_character_length_violation()
    await test_not_null_violation() 
    test_individual_record_logging()
    
    print("\n" + "=" * 50)
    print("Enhanced error logging test completed!")
    print("\nThe new error logging will provide:")
    print("✅ Specific estimate_id for each problematic record")
    print("✅ Field name causing the constraint violation")
    print("✅ Actual vs. maximum field lengths for varchar errors")
    print("✅ Sample field values (truncated for readability)")
    print("✅ Null/empty field identification")
    print("✅ Multiple record analysis in single batch failures")

if __name__ == "__main__":
    asyncio.run(main())
