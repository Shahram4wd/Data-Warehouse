# Enhanced PostgreSQL Error Logging for SalesPro Sync

## Overview
Enhanced the PostgreSQL UPSERT error handling in `ingestion/sync/salespro/base.py` to provide detailed diagnostic information when constraint violations occur, addressing the issue where errors like "PostgreSQL UPSERT failed: value too long for type character varying(10)" lacked specific context.

## Previous Error Messages
**Before:**
```
ERROR PostgreSQL UPSERT failed: value too long for type character varying(10)
```

**After:**
```
ERROR PostgreSQL UPSERT failed with character_length violation: value too long for type character varying(10) column "phone"
ERROR Analyzing 3 records for character_length in field 'phone':
ERROR Found 1 problematic records:
ERROR   #1 estimate_id: EST456, field: phone, value_length: 20, max_length: 10, sample: 555-5678901234567890
```

## Enhanced Features

### 1. Constraint Violation Analysis
- **Character Length Violations**: Identifies which records exceed field length limits
- **Not-Null Constraint Violations**: Pinpoints records with missing required fields  
- **Duplicate Key Violations**: Shows conflicting estimate_ids
- **Check Constraint Violations**: General constraint violation detection

### 2. Detailed Record Context
For each problematic record, the logging now includes:
- **estimate_id**: Specific record identifier
- **field**: The exact field causing the violation
- **value_length**: Actual length of the problematic value
- **max_length**: Database constraint limit
- **sample_value**: Truncated sample of the problematic data (first 100 characters)

### 3. Batch Analysis
When bulk operations fail, the system now:
- Analyzes all records in the failed batch
- Identifies multiple problematic records at once
- Limits detailed output to first 10 problematic records (for readability)
- Reports total count of affected records

### 4. Individual Record Fallback
Enhanced individual record save error handling:
- **Field Length Analysis**: Logs all field lengths for character violation debugging
- **Null Field Detection**: Identifies null and empty fields for not-null violations
- **Specific Error Context**: Includes estimate_id or record ID in all error messages

## Implementation Details

### New Methods Added

#### `_log_constraint_violation_details(records, error_msg, violation_type)`
- Parses PostgreSQL error messages using regex patterns
- Extracts field names and constraint limits
- Analyzes batch records to identify violating data
- Provides detailed logging for each violation type

#### `_log_record_field_lengths(record, record_id)`
- Logs all field lengths for individual records
- Truncates long values to 50 characters for readability
- Helps identify which fields exceed database limits

#### `_log_record_null_fields(record, record_id)`
- Identifies null and empty string fields
- Helps debug not-null constraint violations
- Separates null values from empty strings

### Error Type Detection
The system now detects and provides specific handling for:
- `value too long for type` → Character length analysis
- `violates not-null constraint` → Null field analysis  
- `duplicate key value` → Duplicate estimate_id detection
- `violates check constraint` → General constraint analysis

## Usage Examples

### Character Length Violation
```
ERROR PostgreSQL UPSERT failed with character_length violation: value too long for type character varying(10) column "phone"
ERROR Analyzing 500 records for character_length in field 'phone':
ERROR Found 3 problematic records:
ERROR   #1 estimate_id: EST12345, field: phone, value_length: 15, max_length: 10, sample: 555-123-4567890
ERROR   #2 estimate_id: EST67890, field: phone, value_length: 12, max_length: 10, sample: 555-987-6543
ERROR   #3 estimate_id: EST54321, field: phone, value_length: 18, max_length: 10, sample: +1-555-123-456-789
```

### Not-Null Constraint Violation
```
ERROR PostgreSQL UPSERT failed with not_null violation: null value in column "customer_id" violates not-null constraint
ERROR Analyzing 500 records for not_null in field 'customer_id':
ERROR Found 2 problematic records:
ERROR   #1 estimate_id: EST11111, field: customer_id, issue: null_value
ERROR   #2 estimate_id: EST22222, field: customer_id, issue: null_value
```

### Individual Record Analysis
```
ERROR Character length violation for record EST12345: value too long for type character varying(10)
ERROR Field lengths for record EST12345:
ERROR   estimate_id: length=8, sample='EST12345'
ERROR   customer_name: length=25, sample='John Doe Construction Co.'
ERROR   phone: length=15, sample='555-123-4567890'
ERROR   description: length=250, sample='This is a very detailed description of the construction project that includes...'
```

## Benefits

1. **Faster Debugging**: Immediately identify which records and fields cause violations
2. **Reduced Investigation Time**: No need to manually search through batch data
3. **Data Quality Insights**: Understand patterns in constraint violations
4. **Production Support**: Clear error context for troubleshooting live issues
5. **Batch Efficiency**: Continue processing other records after identifying problems

## Testing
Created comprehensive test script (`test_enhanced_error_logging.py`) that validates:
- Character length violation detection and logging
- Not-null constraint violation analysis
- Individual record field length logging
- Null field identification
- Multiple record batch analysis

## Integration
The enhanced error logging is fully integrated into the existing PostgreSQL UPSERT workflow:
- Maintains existing exception handling behavior
- Preserves fallback to individual record saves
- No impact on successful operations
- Only activates when constraint violations occur

This enhancement transforms cryptic PostgreSQL errors into actionable diagnostic information, significantly improving the debugging experience for constraint violations in large-scale data operations.
