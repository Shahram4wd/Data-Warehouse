# CRM Command Testing Framework

Clean, focused testing framework for CRM management commands using Docker test container.

## Structure

```
ingestion/tests/
├── __init__.py                     # Package init
├── README.md                       # This file
├── run_crm_tests.py               # Main test runner
└── crm_commands/                   # CRM command tests
    ├── __init__.py
    ├── conftest.py                 # pytest fixtures
    ├── base/                       # Testing framework
    │   ├── command_test_base.py    # Base test utilities
    │   ├── sync_history_validator.py # SyncHistory compliance
    │   └── mock_responses.py       # Mock API responses
    ├── test_framework_validation.py # Framework validation
    ├── test_arrivy.py              # Arrivy CRM tests
    ├── test_callrail.py            # CallRail CRM tests (planned)
    ├── test_five9.py               # Five9 CRM tests (planned)
    ├── test_genius.py              # Genius CRM tests (planned)
    ├── test_gsheet.py              # GSheet CRM tests (planned)
    ├── test_hubspot.py             # HubSpot CRM tests (planned)
    ├── test_leadconduit.py         # LeadConduit CRM tests (planned)
    ├── test_salespro.py            # SalesPro CRM tests (planned)
    └── test_salesrabbit.py         # SalesRabbit CRM tests (planned)
```

## Running Tests (Test Container Only)

### All CRM Tests
```bash
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/ -v
```

### Specific CRM System
```bash
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/test_arrivy.py -v
```

### Framework Validation
```bash
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/test_framework_validation.py -v
```

### Test Runner Script
```bash
docker-compose run --rm test python ingestion/tests/run_crm_tests.py
```

### With Coverage
```bash
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/ --cov=ingestion.management.commands --cov-report=html
```

## Key Features

- ✅ **Docker Test Container**: All tests run in dedicated test environment
- ✅ **No External APIs**: All CRM APIs are mocked for reliability
- ✅ **Flag Standardization**: Validates standardized command flags
- ✅ **SyncHistory Compliance**: Enforces CRM sync guide requirements  
- ✅ **Comprehensive Coverage**: Tests all aspects of CRM commands
- ✅ **Fast Execution**: No network calls, optimized for speed
- ✅ **CI/CD Ready**: Designed for automated testing pipelines

## Test Categories

### 1. Command Import Tests
- Verify all CRM commands can be imported
- Catch missing dependencies early

### 2. Flag Standardization Tests  
- Ensure all commands have required flags:
  - `--dry-run`, `--full`, `--debug`, `--batch-size`
  - `--quiet`, `--force`, `--start-date`, `--end-date`

### 3. Dry-Run Safety Tests
- Verify dry-run prevents database writes
- Validate output indicates no changes made

### 4. API Error Handling Tests
- Authentication failures
- Network timeouts  
- Rate limiting
- Invalid responses

### 5. SyncHistory Compliance Tests (MANDATORY)
- Verify all commands create SyncHistory records
- Validate required field population
- Ensure compliance with crm_sync_guide.md

### 6. Orchestration Tests
- Test `*_all` commands delegate correctly
- Verify flag passing to individual commands
- Validate error handling for command failures

## Writing New Tests

Follow the pattern in `test_arrivy.py`:

```python
class TestNewCRMCommands:
    def setup_method(self):
        self.command_runner = CommandTestBase()
        self.sync_validator = SyncHistoryComplianceValidator(self.command_runner)
        self.mock_responses = CRMMockResponses.get_newcrm_responses()
    
    def test_commands_exist_and_importable(self):
        # Test command imports
        pass
    
    def test_commands_have_required_flags(self):
        # Test flag standardization
        pass
    
    # Add more tests following established patterns...
```

## Design Philosophy

- **Clean & Focused**: Only CRM command testing, no legacy baggage
- **Docker Native**: Designed specifically for test container execution
- **Fast & Reliable**: Mocked APIs, no external dependencies
- **Comprehensive**: Covers all aspects of CRM command functionality
- **Maintainable**: Clear patterns, good documentation
- **CI/CD Ready**: Automated, predictable test execution
