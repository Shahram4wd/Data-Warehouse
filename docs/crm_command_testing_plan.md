# CRM Command Testing Implementation Plan

## Overview

This document outlines the comprehensive testing strategy for CRM sync management commands, fully aligned with the `crm_sync_guide.md` architecture and leveraging the existing Docker containerization.

## Architecture Alignment with CRM Sync Guide

### 1. **SyncHistory Framework Compliance**
All tests MUST validate that commands:
- ✅ Use the standardized `SyncHistory` table for sync tracking
- ✅ Record sync operations with proper metadata
- ✅ Support delta sync timestamps for incremental synchronization
- ✅ Provide audit trails for compliance and debugging
- ❌ Do NOT use custom sync tracking solutions

### 2. **Layered Architecture Testing**
Following the CRM sync guide's layered approach:
```
┌─────────────────┐
│ Management      │  ← Test command-line interface & argument parsing
│ Commands        │
├─────────────────┤
│ Sync Engines    │  ← Test orchestration & workflow management
├─────────────────┤
│ API Clients     │  ← Test external API communication (mocked)
├─────────────────┤
│ Processors      │  ← Test data transformation & validation
├─────────────────┤
│ Models          │  ← Test database persistence layer
└─────────────────┘
```

## Docker-Based Testing Strategy

### Container Usage
- **Primary**: Use existing `test` container via `docker-compose`
- **Database**: PostgreSQL container for isolated testing
- **Redis**: For Celery/caching tests if needed
- **No External APIs**: Mock all CRM API calls for reliability

### Test Execution Pattern
```bash
# Run all CRM command tests
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/ -v

# Run specific CRM tests  
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/test_arrivy.py -v

# Run with coverage
docker-compose run --rm test python -m pytest ingestion/tests/crm_commands/ --cov=ingestion.management.commands --cov-report=html
```

## Test Structure

```
ingestion/tests/crm_commands/
├── __init__.py
├── conftest.py                     # Docker-aware fixtures
├── base/
│   ├── __init__.py
│   ├── command_test_base.py       # Base test utilities
│   ├── sync_history_validator.py  # SyncHistory compliance tests
│   └── mock_responses.py          # CRM API mock responses
├── test_arrivy.py                 # Arrivy command tests
├── test_callrail.py              # CallRail command tests
├── test_five9.py                 # Five9 command tests
├── test_genius.py                # Genius (DB) command tests
├── test_gsheet.py                # Google Sheets command tests
├── test_hubspot.py               # HubSpot command tests
├── test_leadconduit.py           # LeadConduit command tests
├── test_salespro.py              # SalesPro (DB) command tests
└── test_salesrabbit.py           # SalesRabbit command tests
```

## CRM Systems and Commands

### Target CRM Systems
1. **arrivy** - API sync commands (7 commands)
2. **callrail** - API sync commands (10 commands)  
3. **five9** - API sync commands (1 command)
4. **genius** - Database sync commands (db_* pattern)
5. **gsheet** - Google Sheets sync commands (3 commands)
6. **hubspot** - API sync commands (10 commands)
7. **leadconduit** - API sync commands (2 commands)
8. **salespro** - Database sync commands (db_* pattern)
9. **salesrabbit** - API sync commands (3 commands)

### Standard Flag Requirements
All commands MUST support these flags:
- ✅ `--dry-run` - Preview mode with no database writes
- ✅ `--full` - Full sync instead of delta sync
- ✅ `--debug` - Enable verbose logging
- ✅ `--batch-size` - Control batch processing size
- ✅ `--force` - Force overwrite existing records
- ✅ `--quiet` - Suppress non-error output
- ✅ `--start-date` - Start date for sync (YYYY-MM-DD)
- ✅ `--end-date` - End date for sync (where applicable)

## Testing Phases

### Phase 1: Test Infrastructure (Docker-Optimized)
**Duration**: 1-2 days
**Goal**: Create reusable Docker-based test framework

**Tasks**:
1. ✅ Create Docker-aware `conftest.py` with database fixtures
2. ✅ Build `CommandTestBase` class for common test patterns
3. ✅ Implement `SyncHistoryValidator` for compliance checking
4. ✅ Create mock API response generators for each CRM
5. ✅ Set up test database isolation within containers

**Deliverables**:
- Docker-optimized pytest configuration
- Base test classes with SyncHistory validation
- Mock API response framework
- Test database management utilities

### Phase 2: Flag Standardization and Unit Tests
**Duration**: 2-3 days
**Goal**: Ensure all commands support required flags and handle them correctly

**Tests for Each CRM**:
1. **Command Discovery**
   - All expected commands can be imported
   - Commands have proper help text
   - Commands support required flags

2. **Argument Validation**
   - Valid flag combinations work
   - Invalid flag combinations raise proper errors
   - Date format validation (YYYY-MM-DD)
   - Batch size bounds checking
   - Conflicting flags detection

3. **Flag Behavior**
   - `--full` overrides `--start-date`
   - `--debug` increases logging verbosity
   - `--quiet` reduces output
   - `--dry-run` prevents database writes

**Example Test Structure**:
```python
class TestArrivyCommands(CommandTestBase):
    def test_all_commands_exist(self):
        # Test command discovery
        
    def test_required_flags_supported(self):
        # Test flag availability
        
    def test_flag_validation(self):
        # Test argument parsing
```

### Phase 3: Dry-Run Integration Tests
**Duration**: 2-3 days  
**Goal**: Validate dry-run mode works correctly with mocked APIs

**Tests for Each CRM**:
1. **Dry-Run Database Safety**
   - No records written to database in dry-run mode
   - SyncHistory not modified in dry-run
   - Output indicates dry-run mode active

2. **Dry-Run API Behavior**
   - API calls are made (to validate connectivity)
   - Data processing occurs (to validate logic)
   - Results displayed properly

3. **Error Handling**
   - API authentication errors handled gracefully
   - Network timeout errors handled properly
   - Invalid configuration detected and reported

**Example Test**:
```python
def test_dry_run_no_database_writes(self):
    with mock_crm_api_success():
        initial_count = MyModel.objects.count()
        result = self.run_command('sync_arrivy_entities', '--dry-run')
        final_count = MyModel.objects.count()
        
        assert initial_count == final_count
        assert 'DRY RUN' in result.stdout
        assert result.success
```

### Phase 4: Real Sync Tests with Mocked APIs
**Duration**: 3-4 days
**Goal**: Test actual sync logic with comprehensive API mocking

**Tests for Each CRM**:
1. **Successful Sync Operations**
   - Records created correctly
   - Records updated properly  
   - SyncHistory tracking works
   - Batch processing functions

2. **Data Validation**
   - Field mappings work correctly
   - Data transformation applied properly
   - Business rule validation enforced
   - Invalid data handled appropriately

3. **Delta Sync Compliance**
   - Last sync timestamp used correctly
   - Only modified records processed
   - SyncHistory integration proper
   - Full sync vs delta sync behavior

**Mock API Patterns**:
```python
@pytest.fixture
def mock_arrivy_api():
    with responses.RequestsMock() as rsps:
        rsps.add(responses.GET, 
                'https://api.arrivy.com/entities',
                json={'entities': [...]},
                status=200)
        yield rsps
```

### Phase 5: Orchestration Tests for *_all Commands
**Duration**: 2-3 days
**Goal**: Test that *_all commands properly orchestrate individual commands

**Tests for Each CRM's *_all Command**:
1. **Command Orchestration**
   - Individual commands called in correct dependency order
   - Flags passed through correctly
   - Results aggregated properly
   - Failures handled gracefully

2. **Entity Filtering**
   - `--entities` flag filters correctly
   - Default entity selection works
   - Invalid entity names rejected

3. **Parallel vs Sequential**
   - `--parallel` flag changes execution mode
   - Dependencies respected in parallel mode
   - Error handling works in both modes

### Phase 6: SyncHistory Compliance Validation
**Duration**: 1-2 days
**Goal**: Ensure all commands comply with CRM sync guide requirements

**Critical Compliance Tests**:
1. **SyncHistory Usage**
   - All commands create SyncHistory records
   - Proper metadata recorded (operation, source, timestamps)
   - Delta sync timestamps used correctly
   - Error states recorded properly

2. **Forbidden Patterns Detection**
   - No custom sync tracking (synced_at fields)
   - No file-based sync state
   - No in-memory sync state
   - Proper SyncHistory table usage only

3. **Architecture Compliance**
   - Commands follow layered architecture
   - Proper separation of concerns
   - Consistent module structure

### Phase 7: CI/CD Integration
**Duration**: 1 day
**Goal**: Integrate tests into automated pipeline

**Tasks**:
1. Create test runner scripts for Docker
2. Configure test database setup/teardown
3. Add coverage reporting
4. Create test result reporting
5. Set up parallel test execution

**Docker Test Commands**:
```bash
# Full test suite
docker-compose run --rm test ./scripts/run_crm_tests.sh

# Specific CRM
docker-compose run --rm test ./scripts/run_crm_tests.sh arrivy

# With coverage
docker-compose exec test ./scripts/run_crm_tests.sh --coverage

# Fast unit tests only
docker-compose exec test ./scripts/run_crm_tests.sh --unit
```

## Success Criteria

### Phase Completion Criteria
- **Phase 1**: All base test classes created and working in Docker
- **Phase 2**: All commands support required flags with proper validation
- **Phase 3**: All commands work correctly in dry-run mode
- **Phase 4**: All commands sync data correctly with mocked APIs
- **Phase 5**: All *_all commands orchestrate properly
- **Phase 6**: All commands comply with SyncHistory requirements
- **Phase 7**: Tests run automatically in CI/CD pipeline

### Quality Metrics
- **Test Coverage**: >90% for management commands
- **Test Speed**: Full suite runs in <10 minutes in Docker
- **Reliability**: Tests pass consistently (>99% success rate)
- **Maintainability**: New CRM commands can be tested with minimal setup

## Risk Mitigation

### Potential Issues
1. **Docker Performance**: Tests may run slower in containers
   - **Mitigation**: Use optimized test database, parallel execution
   
2. **API Mock Complexity**: Mocking complex CRM APIs accurately
   - **Mitigation**: Start with simple mocks, iterate based on real API behavior
   
3. **Database State**: Tests interfering with each other
   - **Mitigation**: Use transactions, database isolation, proper teardown
   
4. **Command Discovery**: Finding all commands across CRM systems
   - **Mitigation**: Automated command discovery, regular validation

### Rollback Plan
If Docker-based testing proves problematic:
1. Fall back to native pytest with test database
2. Use test database containers separately
3. Maintain mock API approach regardless of container strategy

## Timeline

| Phase | Duration | Start | End | Deliverables |
|-------|----------|-------|-----|--------------|
| 1 | 2 days | Day 1 | Day 2 | Test infrastructure |
| 2 | 3 days | Day 3 | Day 5 | Flag standardization tests |
| 3 | 3 days | Day 6 | Day 8 | Dry-run integration tests |
| 4 | 4 days | Day 9 | Day 12 | Real sync tests |
| 5 | 3 days | Day 13 | Day 15 | Orchestration tests |
| 6 | 2 days | Day 16 | Day 17 | SyncHistory compliance |
| 7 | 1 day | Day 18 | Day 18 | CI/CD integration |

**Total Duration**: ~18 working days (3.5 weeks)

## Starting Point

Begin with **Arrivy** as the pilot CRM system:
1. Implement complete test suite for all 7 Arrivy commands
2. Validate Docker-based testing approach works well
3. Refine base test classes based on Arrivy experience
4. Use Arrivy as template for remaining CRM systems

**Next Steps**:
1. ✅ Create test infrastructure (Phase 1)
2. ✅ Implement Arrivy tests (Phases 2-6)
3. ✅ Validate approach and refine framework
4. 🔄 Scale to remaining CRM systems
