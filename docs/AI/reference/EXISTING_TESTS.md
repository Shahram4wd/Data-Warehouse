# Existing Tests Documentation

**Document Version**: 1.0  
**Last Updated**: 2025  
**Purpose**: Comprehensive catalog of all test files, coverage, and testing strategies

---

## Table of Contents
1. [Testing Overview](#testing-overview)
2. [Test Structure](#test-structure)
3. [Test Categories](#test-categories)
4. [Test Files Catalog](#test-files-catalog)
5. [Testing Infrastructure](#testing-infrastructure)
6. [Running Tests](#running-tests)
7. [Test Data Control](#test-data-control)

---

## Testing Overview

### Testing Philosophy
The Data Warehouse employs a **layered testing strategy**:

1. **Unit Tests**: Fast, isolated, no external dependencies
2. **Integration Tests**: Real API calls with controlled data limits
3. **End-to-End Tests**: Full workflow testing (use with caution)

### Test Safety Levels
- 🟢 **SAFE**: Unit tests, mocked APIs, no real data
- 🟡 **CONTROLLED**: Integration tests with limits (10-100 records)
- 🟠 **CAUTIOUS**: Date-ranged tests (last 7 days)
- 🔴 **DANGEROUS**: Full sync tests (all records, production impact)

### Test Framework
- **Primary**: Django TestCase + pytest
- **Mocking**: unittest.mock
- **Async Testing**: pytest-asyncio
- **Database**: In-memory SQLite for unit tests, PostgreSQL for integration

---

## Test Structure

### Directory Layout
```
ingestion/tests/
├── __init__.py                          # Test package initialization
├── README.md                            # Testing documentation
├── run_crm_tests.py                     # Main test runner
├── test_interface.py                    # Test configuration interface
├── views.py                             # Test execution web UI
├── urls.py                              # Test dashboard routes
│
├── base/                                # Testing infrastructure
│   ├── command_test_base.py             # Base test utilities
│   ├── sync_history_validator.py        # SyncHistory validation
│   └── mock_responses.py                # Mock API responses
│
├── unit/                                # Unit tests
│   └── test_flag_validation.py          # Command flag tests
│
├── integration/                         # Integration tests
│   └── arrivy/
│       └── test_arrivy_individual.py    # Arrivy integration tests
│
├── utils/                               # Test utilities
│   └── test_data_controller.py          # Test data mode controller
│
├── crm_commands/                        # CRM command tests (modular)
│   ├── base/
│   │   ├── command_test_base.py
│   │   ├── sync_history_validator.py
│   │   └── mock_responses.py
│   ├── test_framework_validation.py
│   ├── test_arrivy.py
│   └── test_salesrabbit.py
│
└── [CRM-specific test files]
    ├── test_crm_hubspot.py              # HubSpot tests (10 commands, 41 tests)
    ├── test_crm_arrivy.py               # Arrivy tests (6 commands, 24 tests)
    ├── test_callrail.py                 # CallRail advanced tests (9 commands, 40+ tests)
    ├── test_crm_five9.py                # Five9 tests
    ├── test_crm_marketsharp.py          # MarketSharp tests
    ├── test_crm_leadconduit.py          # LeadConduit tests
    ├── test_crm_gsheet.py               # Google Sheets tests
    ├── test_crm_genius_db.py            # Genius database tests
    ├── test_crm_salespro_db.py          # SalesPro database tests
    ├── test_crm_sync_commands.py        # Import hub for all CRM tests
    ├── test_crm_sync_commands_common.py # Shared CRM test patterns
    └── test_crm_sync_commands_backup.py # Legacy backup
```

---

## Test Categories

### Unit Tests (25+ tests)
**Purpose**: Validate command structure without external dependencies

**What They Test**:
- ✅ Command import and instantiation
- ✅ Argument parser configuration
- ✅ Help text consistency
- ✅ Flag validation (--dry-run, --full, --debug, etc.)
- ✅ Basic functionality checks
- ✅ Inheritance patterns

**Example Test**:
```python
def test_unit_basic_functionality(self):
    """Unit Test: Basic command functionality"""
    self.assertTrue(hasattr(self.command, 'add_arguments'))
    self.assertTrue(hasattr(self.command, 'handle'))
```

**Execution Time**: < 30 seconds per test  
**Data Usage**: MOCKED (no real API calls)  
**Safety Level**: 🟢 SAFE

### Integration Tests (18+ tests)
**Purpose**: Test component interaction with controlled real data

**What They Test**:
- ✅ Engine initialization
- ✅ API client connectivity
- ✅ Real API calls with record limits
- ✅ Flag propagation to engines
- ✅ Component integration
- ✅ Error handling with real scenarios

**Example Test**:
```python
@patch('ingestion.management.commands.sync_five9_contacts.Five9SyncEngine')
def test_integration_dry_run(self, mock_engine_class):
    """Integration Test: Dry-run execution with mocked engine"""
    call_command('sync_five9_contacts', '--dry-run')
    self.assertTrue(mock_engine_class.called)
```

**Execution Time**: 2-5 minutes per test  
**Data Usage**: LIMITED (10-100 records) or CONTROLLED (last 7 days)  
**Safety Level**: 🟡 CONTROLLED

### End-to-End Tests (8+ tests)
**Purpose**: Full workflow validation (⚠️ USE WITH EXTREME CAUTION)

**What They Test**:
- ⚠️ Full sync operations (all records)
- ⚠️ Production-like scenarios
- ⚠️ Performance under load
- ⚠️ Complete data pipeline

**Example Test**:
```python
def test_e2e_full_sync(self):
    """E2E Test: Full sync of all HubSpot contacts"""
    # ⚠️ DANGEROUS: Processes ALL records!
    call_command('sync_hubspot_contacts', '--full')
```

**Execution Time**: 30-120+ minutes per test  
**Data Usage**: FULL_SYNC (all records)  
**Safety Level**: 🔴 DANGEROUS

---

## Test Files Catalog

### 1. `test_interface.py`
**Purpose**: Test configuration interface and test discovery  
**Lines**: ~400  
**Key Classes**:
- `TestType(Enum)`: UNIT, INTEGRATION, E2E
- `DataUsage(Enum)`: MOCKED, LIMITED, CONTROLLED, FULL
- `TestConfiguration(dataclass)`: Test metadata
- `CRMTestInterface`: Central test registry

**Test Configurations**: 50+ defined tests across all CRMs  
**What It Provides**:
- Test discovery by type
- Safety level classification
- Estimated duration
- Data usage information

**Example**:
```python
"integration_hubspot_contacts": TestConfiguration(
    name="HubSpot Contacts Integration Test",
    test_type=TestType.INTEGRATION,
    data_usage=DataUsage.LIMITED,
    max_records=100,
    uses_real_api=True,
    estimated_duration="2-5 min",
    description="Tests HubSpot contacts sync with limited data"
)
```

### 2. `test_crm_hubspot.py`
**Purpose**: Comprehensive HubSpot integration testing  
**Lines**: ~800  
**Commands Tested**: 10  
**Total Tests**: 41

**Test Classes**:
- `TestFive9SyncCommand` (legacy)
- `TestMarketSharpSyncCommand` (legacy)
- `TestLeadConduitSyncCommand`
- `TestLeadConduitAllSyncCommand`
- `TestGSheetMarketingLeadsSyncCommand`
- `TestGSheetMarketingSpendsCommand`
- `TestGSheetAllCommand`
- `TestHubSpotContactsCommand` (15 tests)
- `TestHubSpotDealsCommand` (8 tests)
- `TestHubSpotAllCommand` (6 tests)
- `TestHubSpotAppointmentsCommand` (4 tests)
- `TestHubSpotAssociationsCommand` (4 tests)
- And more...

**What It Tests**:
- ✅ All HubSpot sync commands
- ✅ Unit tests: flag validation, help text
- ✅ Integration tests: dry-run, limited data
- ✅ Orchestration: sync_hubspot_all command
- ✅ Custom objects: genius_users, divisions, zipcodes

**Example Test**:
```python
def test_unit_hubspot_contacts_flag_validation(self):
    """Test that sync_hubspot_contacts has standardized flags"""
    parser = ArgumentParser()
    command = Command()
    command.add_arguments(parser)
    
    # Check for required flags
    self.assertIn('--dry-run', [a.option_strings for a in parser._actions])
    self.assertIn('--full', [a.option_strings for a in parser._actions])
```

### 3. `test_callrail.py`
**Purpose**: Advanced CallRail testing with comprehensive coverage  
**Lines**: ~1000  
**Commands Tested**: 9  
**Total Tests**: 40+

**Test Classes**:
- `TestCallRailCommandStandardization`
- `TestCallRailCallsCommand`
- `TestCallRailCompaniesCommand`
- `TestCallRailTrackersCommand`
- `TestCallRailFormSubmissionsCommand`
- `TestCallRailTextMessagesCommand`
- `TestCallRailAccountsCommand`
- `TestCallRailUsersCommand`
- `TestCallRailTagsCommand`
- `TestCallRailAllCommand`

**What It Tests**:
- ✅ All 9 CallRail sync commands
- ✅ Command standardization (flags, help text)
- ✅ Date range filtering
- ✅ Pagination handling
- ✅ API rate limiting
- ✅ Error scenarios
- ✅ Orchestration command

**Special Features**:
- Tests command discovery
- Validates help text consistency
- Tests flag combinations
- Real API integration tests with safety limits

### 4. `test_crm_arrivy.py`
**Purpose**: Arrivy integration testing  
**Lines**: ~600  
**Commands Tested**: 6  
**Total Tests**: 24

**Test Classes**:
- `TestArrivyBookingsCommand`
- `TestArrivyTasksCommand`
- `TestArrivyEntitiesCommand`
- `TestArrivyGroupsCommand`
- `TestArrivyStatusesCommand`
- `TestArrivyAllCommand`

**What It Tests**:
- ✅ Arrivy bookings sync
- ✅ Tasks sync
- ✅ Entity management
- ✅ Groups sync
- ✅ Status tracking
- ✅ Orchestration (sync_arrivy_all)

### 5. `test_crm_five9.py`
**Purpose**: Five9 contact sync testing  
**Lines**: ~200  
**Commands Tested**: 1  
**Total Tests**: 5

**Test Classes**:
- `TestFive9SyncCommand`

**What It Tests**:
- ✅ Five9 contacts import
- ✅ Flag validation
- ✅ Help text
- ✅ Basic execution

### 6. `test_crm_marketsharp.py`
**Purpose**: MarketSharp integration testing  
**Lines**: ~200  
**Commands Tested**: 1  
**Total Tests**: 5

**Test Classes**:
- `TestMarketSharpSyncCommand`

**What It Tests**:
- ✅ MarketSharp data sync
- ✅ Command structure
- ✅ Flag validation

### 7. `test_crm_leadconduit.py`
**Purpose**: LeadConduit lead sync testing  
**Lines**: ~300  
**Commands Tested**: 2  
**Total Tests**: 10

**Test Classes**:
- `TestLeadConduitSyncCommand`
- `TestLeadConduitAllSyncCommand`

**What It Tests**:
- ✅ LeadConduit lead import
- ✅ All-entity orchestration
- ✅ API authentication
- ✅ Data transformation

### 8. `test_crm_gsheet.py`
**Purpose**: Google Sheets integration testing  
**Lines**: ~400  
**Commands Tested**: 3  
**Total Tests**: 15

**Test Classes**:
- `TestGSheetMarketingLeadsSyncCommand`
- `TestGSheetMarketingSpendsCommand`
- `TestGSheetAllCommand`

**What It Tests**:
- ✅ Marketing leads import from Google Sheets
- ✅ Marketing spend tracking
- ✅ Google API authentication
- ✅ Sheet parsing and validation

### 9. `test_crm_genius_db.py`
**Purpose**: Genius database integration testing  
**Lines**: ~300  
**Commands Tested**: Multiple (prospects, leads, appointments)  
**Total Tests**: 12

**What It Tests**:
- ✅ Direct database connections
- ✅ Raw SQL query execution
- ✅ Genius prospect sync
- ✅ Lead data transformation
- ✅ Appointment scheduling data

### 10. `test_crm_salespro_db.py`
**Purpose**: SalesPro Athena integration testing  
**Lines**: ~400  
**Commands Tested**: 4  
**Total Tests**: 16

**Test Classes**:
- Tests for credit applications
- Tests for customer data
- Tests for estimates
- Tests for lead results

**What It Tests**:
- ✅ AWS Athena query execution
- ✅ Credit application data sync
- ✅ Customer records
- ✅ Estimate data
- ✅ Lead results tracking

### 11. `test_crm_sync_commands_common.py`
**Purpose**: Shared CRM test patterns and utilities  
**Lines**: ~300  
**Total Tests**: 20+

**Test Classes**:
- `TestBaseSyncCommandArchitecture`: Base class patterns
- `TestCommonSyncPatterns`: Shared sync patterns
- `TestCRMSyncDocumentation`: Documentation validation
- `TestSyncEngineIntegration`: Engine integration tests
- `TestPerformanceAndScaling`: Performance tests
- `TestBackwardCompatibility`: Legacy support tests
- `TestConfigurationManagement`: Config tests

**What It Tests**:
- ✅ BaseSyncCommand architecture
- ✅ Common flags across all commands
- ✅ SyncHistory integration
- ✅ Command discovery
- ✅ Help text consistency
- ✅ Error handling patterns
- ✅ Batch processing
- ✅ Performance benchmarks

### 12. `command_test_base.py`
**Purpose**: Base infrastructure for CRM command testing  
**Lines**: ~500  
**What It Provides**:

**Base Classes**:
- `CRMCommandTestBase`: Foundation for all command tests
- `APITestMixin`: API-based command testing
- `DatabaseTestMixin`: Database-based command testing
- `PerformanceTestMixin`: Performance testing utilities
- `BatchProcessingTestMixin`: Batch processing tests
- `FlagTestMixin`: Flag validation utilities

**Key Methods**:
```python
def run_command(self, command_name, *args, **kwargs)
def assert_sync_history_created(self, crm_source, sync_type)
def assert_command_flags(self, command, expected_flags)
def mock_api_response(self, data, status_code=200)
```

**Example Usage**:
```python
class TestMyCommand(CRMCommandTestBase, APITestMixin):
    def test_my_command(self):
        self.run_command('sync_my_command', '--dry-run')
        self.assert_sync_history_created('my_crm', 'my_entity')
```

### 13. `sync_history_validator.py`
**Purpose**: SyncHistory compliance validation  
**Lines**: ~200  
**What It Tests**:
- ✅ SyncHistory record creation
- ✅ Required field population
- ✅ Status transitions (running → success/failed)
- ✅ Metrics accuracy (processed, created, updated, failed)
- ✅ Timestamp validity
- ✅ Error message logging

**Key Class**:
```python
class SyncHistoryValidator:
    def validate_sync_record(self, sync_history_id):
        """Validate a SyncHistory record meets all requirements"""
    
    def assert_metrics_match(self, expected, actual):
        """Assert sync metrics match expectations"""
```

### 14. `mock_responses.py`
**Purpose**: Mock API responses for unit tests  
**Lines**: ~600  
**What It Provides**:

**Mock Data Factories**:
- `MockHubSpotContact()`: Sample HubSpot contact
- `MockCallRailCall()`: Sample CallRail call record
- `MockSalesRabbitLead()`: Sample SalesRabbit lead
- `MockArrivyBooking()`: Sample Arrivy booking
- `MockGeniusProspect()`: Sample Genius prospect

**Response Generators**:
```python
def generate_hubspot_contacts(count=10):
    """Generate N mock HubSpot contacts"""
    return [MockHubSpotContact() for _ in range(count)]

def generate_callrail_pagination_response(page=1, per_page=100):
    """Generate paginated CallRail API response"""
```

### 15. `test_data_controller.py`
**Purpose**: Control test data usage modes  
**Lines**: ~200  
**Key Classes**:

```python
class TestDataMode(Enum):
    MOCKED = "mocked"        # No real data
    MINIMAL = "minimal"      # 1-10 records
    SAMPLE = "sample"        # 50-100 records
    RECENT = "recent"        # Last 7 days
    FULL_SYNC = "full_sync"  # All records (dangerous!)

class TestDataController:
    @staticmethod
    def get_config(mode: TestDataMode) -> Dict:
        """Get configuration for test data mode"""
    
    @staticmethod
    def validate_safety(mode: TestDataMode) -> bool:
        """Validate if test mode is safe to run"""
```

**Test Scenarios**:
```python
class TestScenarios:
    @staticmethod
    def unit_test_scenario():
        """For unit tests - no real data"""
        return TestDataController.get_config(TestDataMode.MOCKED)
    
    @staticmethod
    def integration_test_scenario():
        """For integration tests - minimal real data"""
        return TestDataController.get_config(TestDataMode.SAMPLE)
```

### 16. `views.py` (Test Execution UI)
**Purpose**: Web interface for running tests  
**Lines**: ~400  
**What It Provides**:

**Views**:
- `test_list()`: List all available tests
- `test_detail()`: Test configuration details
- `run_test_form()`: Execute test form
- `test_results()`: View test results

**Features**:
- 🎨 Visual test safety indicators
- ⏱️ Estimated duration display
- 📊 Test result tracking
- 🔒 Safety confirmations for dangerous tests
- 📈 Test execution history

**URL Patterns**:
```
/testing/                # Test list
/testing/<test_name>/    # Test detail
/testing/run/            # Run test form
/testing/results/        # Test results
```

### 17. `integration/arrivy/test_arrivy_individual.py`
**Purpose**: Arrivy integration tests with real API  
**Lines**: ~300  
**What It Tests**:

```python
class TestArrivyIndividualCommands:
    def setup_method(self):
        self.SAFETY_PARAMS = {
            'batch_size': 10,
            'dry_run': True,
        }
        self.start_date = datetime.now() - timedelta(days=7)
```

**Tests**:
- ✅ Bookings sync (last 7 days)
- ✅ Tasks sync (limited records)
- ✅ Real API authentication
- ✅ Error handling
- ✅ Rate limiting

### 18. `unit/test_flag_validation.py`
**Purpose**: Command flag standardization tests  
**Lines**: ~200  
**What It Tests**:
- ✅ All commands have `--dry-run` flag
- ✅ All commands have `--full` flag
- ✅ All commands have `--debug` flag
- ✅ Date-based commands have `--since` flag
- ✅ Batch commands have `--batch-size` flag

**Example**:
```python
def test_all_commands_have_dry_run_flag():
    """Ensure all sync commands support --dry-run"""
    commands = discover_all_sync_commands()
    for cmd in commands:
        parser = get_command_parser(cmd)
        assert has_flag(parser, '--dry-run'), f"{cmd} missing --dry-run"
```

### 19. `crm_commands/test_framework_validation.py`
**Purpose**: Validate testing framework itself  
**Lines**: ~150  
**What It Tests**:
- ✅ Test infrastructure setup
- ✅ Mock response generation
- ✅ SyncHistory validator functionality
- ✅ Test base class methods

### 20. `crm_commands/test_salesrabbit.py`
**Purpose**: SalesRabbit comprehensive testing  
**Lines**: ~500  
**Commands Tested**: 3 (leads, users, all)  
**Total Tests**: 15

**Test Classes**:
- `TestSalesRabbitLeadsCommand`
- `TestSalesRabbitUsersCommand`
- `TestSalesRabbitAllCommand`

---

## Testing Infrastructure

### Test Base Classes

#### `CRMCommandTestBase`
**Purpose**: Foundation for all CRM command tests

**Provides**:
```python
def run_command(self, command_name, *args, **kwargs):
    """Execute a management command and capture output"""

def assert_sync_history_created(self, crm_source, sync_type):
    """Assert SyncHistory record was created"""

def assert_command_output(self, output, expected_text):
    """Assert command output contains expected text"""

def get_latest_sync_history(self, crm_source, sync_type):
    """Retrieve latest SyncHistory for CRM"""
```

#### Mixins

**APITestMixin**:
```python
def mock_api_call(self, endpoint, response_data):
    """Mock external API call"""

def assert_api_called(self, url, times=1):
    """Assert API was called N times"""
```

**DatabaseTestMixin**:
```python
def assert_record_count(self, model_class, expected):
    """Assert database record count"""

def clear_test_data(self, model_class):
    """Clean up test data"""
```

**PerformanceTestMixin**:
```python
def benchmark_sync(self, command, record_count):
    """Benchmark sync performance"""

def assert_sync_duration(self, max_seconds):
    """Assert sync completed within time limit"""
```

### Fixtures

**Common Fixtures**:
```python
@pytest.fixture
def mock_hubspot_client():
    """Mock HubSpot API client"""
    
@pytest.fixture
def sample_crm_data():
    """Generate sample CRM data"""

@pytest.fixture
def test_database():
    """Set up test database"""
```

---

## Running Tests

### Run All Tests
```bash
# Run all tests
python manage.py test ingestion.tests

# Run with pytest
pytest ingestion/tests/

# Run with coverage
pytest --cov=ingestion --cov-report=html ingestion/tests/
```

### Run Specific Test Files
```bash
# Run HubSpot tests
pytest ingestion/tests/test_crm_hubspot.py

# Run CallRail tests
pytest ingestion/tests/test_callrail.py

# Run unit tests only
pytest ingestion/tests/unit/
```

### Run Specific Test Classes
```bash
# Run specific test class
pytest ingestion/tests/test_crm_hubspot.py::TestHubSpotContactsCommand

# Run specific test method
pytest ingestion/tests/test_crm_hubspot.py::TestHubSpotContactsCommand::test_unit_flag_validation
```

### Run by Test Type
```bash
# Run unit tests (fast, safe)
pytest -m unit ingestion/tests/

# Run integration tests (slower, controlled)
pytest -m integration ingestion/tests/

# Run E2E tests (⚠️ DANGEROUS)
pytest -m e2e ingestion/tests/
```

### Run with Test Interface
```bash
# Start Django development server
python manage.py runserver

# Navigate to:
http://localhost:8000/testing/

# Select test, choose data usage level, run
```

### Run via API
```bash
# POST to test execution endpoint
curl -X POST http://localhost:8000/testing/run/ \
  -d "test_name=integration_hubspot_contacts&data_usage=MINIMAL"
```

---

## Test Data Control

### Safety Modes

**MOCKED** (🟢 SAFE):
- No real API calls
- Uses mock responses
- Fastest execution
- Safe for continuous integration

**MINIMAL** (🟡 CONTROLLED):
- Real API calls
- 1-10 records max
- ~30 seconds execution
- Safe for development testing

**SAMPLE** (🟡 CONTROLLED):
- Real API calls
- 50-100 records
- 2-5 minutes execution
- Requires API rate limit awareness

**RECENT** (🟠 CAUTIOUS):
- Real API calls
- Date-filtered (last 7 days)
- 5-15 minutes execution
- May affect production load

**FULL_SYNC** (🔴 DANGEROUS):
- ⚠️ ALL RECORDS
- No limits
- 30-120+ minutes
- **USE ONLY WITH PERMISSION**
- Can impact production systems

### Setting Test Mode

**Via Command Line**:
```bash
python manage.py sync_hubspot_contacts --dry-run --batch-size 10
```

**Via Test Controller**:
```python
config = TestDataController.get_config(TestDataMode.MINIMAL)
call_command('sync_hubspot_contacts', **config)
```

**Via Web UI**:
Select data usage level from dropdown (MOCKED, MINIMAL, SAMPLE, RECENT, FULL_SYNC)

---

## Test Coverage

### Current Coverage by CRM

| CRM Source     | Commands | Unit Tests | Integration Tests | E2E Tests | Total Tests |
|----------------|----------|------------|-------------------|-----------|-------------|
| HubSpot        | 10       | 20         | 15                | 6         | 41          |
| CallRail       | 9        | 18         | 16                | 6         | 40+         |
| Arrivy         | 6        | 12         | 10                | 2         | 24          |
| SalesRabbit    | 3        | 9          | 5                 | 1         | 15          |
| Genius         | 5        | 8          | 4                 | 0         | 12          |
| SalesPro       | 4        | 8          | 6                 | 2         | 16          |
| Google Sheets  | 3        | 9          | 5                 | 1         | 15          |
| LeadConduit    | 2        | 6          | 3                 | 1         | 10          |
| Five9          | 1        | 3          | 2                 | 0         | 5           |
| MarketSharp    | 1        | 3          | 2                 | 0         | 5           |
| **TOTAL**      | **44**   | **96**     | **68**            | **19**    | **183+**    |

### Coverage Goals
- ✅ Unit Test Coverage: 80%+ (achieved)
- ⏳ Integration Test Coverage: 60% (in progress)
- ⏳ E2E Test Coverage: 30% (planned)
- ✅ Critical Path Coverage: 100% (achieved)

---

## Test Development Guidelines

### Writing New Tests

**1. Choose Test Type**:
- Unit: Testing command structure, flags, basic functionality
- Integration: Testing with real APIs but controlled data
- E2E: Testing full workflow (use sparingly)

**2. Use Appropriate Base Class**:
```python
from ingestion.tests.command_test_base import CRMCommandTestBase, APITestMixin

class TestMyCommand(CRMCommandTestBase, APITestMixin):
    def setUp(self):
        super().setUp()
        self.command_name = 'sync_mycrm_myentity'
```

**3. Follow Naming Conventions**:
```python
def test_unit_flag_validation(self):        # Unit test
def test_integration_api_call(self):        # Integration test
def test_e2e_full_workflow(self):           # E2E test
```

**4. Add Safety Guards**:
```python
@pytest.mark.slow
@pytest.mark.integration
def test_integration_real_api(self):
    """Integration test with real API - controlled data"""
    # Use TestDataController
    config = TestDataController.get_config(TestDataMode.MINIMAL)
```

**5. Validate SyncHistory**:
```python
def test_sync_creates_history(self):
    call_command(self.command_name, '--dry-run')
    self.assert_sync_history_created('mycrm', 'myentity')
```

**6. Clean Up**:
```python
def tearDown(self):
    self.clear_test_data(MyModel)
    super().tearDown()
```

### Test Checklist
- [ ] Test inherits from appropriate base class
- [ ] Test name indicates type (unit/integration/e2e)
- [ ] Test uses appropriate data mode
- [ ] Test validates SyncHistory if applicable
- [ ] Test cleans up after itself
- [ ] Test has docstring explaining purpose
- [ ] Test is added to `test_interface.py` if needed
- [ ] Test has appropriate pytest markers

---

## Continuous Integration

### GitHub Actions (Planned)
```yaml
name: Tests
on: [push, pull_request]
jobs:
  unit-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run unit tests
        run: pytest -m unit ingestion/tests/
  
  integration-tests:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - name: Run integration tests
        run: pytest -m integration ingestion/tests/
```

### Pre-commit Hooks
```bash
# Install pre-commit
pip install pre-commit

# Install hooks
pre-commit install

# Runs unit tests before commit
```

---

## Related Documents

- [Architecture Overview](ARCHITECTURE.md)
- [Database Schema Reference](DATABASE_SCHEMA.md)
- [API & Integration Reference](API_INTEGRATIONS.md)
- [Codebase Navigation Map](CODEBASE_MAP.md)
- [Testing README](../../ingestion/tests/README.md)
- [Current CRM Testing Implementation](../current_crm_testing_implementation.md)

---

**Document Maintained By**: Development Team  
**Last Review**: 2025  
**Next Review**: Quarterly
