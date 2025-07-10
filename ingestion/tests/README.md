# Ingestion Tests

This directory contains comprehensive tests for the ingestion module, following the import refactoring guidelines.

## Test Structure

```
ingestion/tests/
├── __init__.py
├── run_tests.py                    # Main test runner
├── unit/                           # Unit tests
│   ├── __init__.py
│   ├── test_base/                  # Base module tests
│   │   ├── __init__.py
│   │   ├── test_performance_cleanup.py    # PerformanceMonitor cleanup tests
│   │   └── test_report_metrics.py         # SelfHealingSystem report_metrics tests
│   ├── test_hubspot/               # HubSpot module tests
│   │   ├── __init__.py
│   │   ├── test_duration_logic.py         # Duration parsing logic tests
│   │   └── test_hubspot_duration.py       # HubSpot duration integration tests
│   └── test_genius/                # Genius module tests (future)
├── integration/                    # Integration tests
│   ├── __init__.py
│   └── test_hubspot_appointments_duration.py  # HubSpot appointments integration
├── performance/                    # Performance and benchmarking tests
│   ├── __init__.py
│   └── test_comprehensive.py       # Comprehensive performance tests
└── README.md                       # This file
```

## Running Tests

### Run All Tests
```bash
cd ingestion/tests
python run_tests.py
```

### Run Individual Test Categories

#### Unit Tests
```bash
# Performance monitor cleanup
python ingestion/tests/unit/test_base/test_performance_cleanup.py

# Report metrics
python ingestion/tests/unit/test_base/test_report_metrics.py

# Duration parsing logic
python ingestion/tests/unit/test_hubspot/test_duration_logic.py
```

#### Performance Tests
```bash
# Comprehensive performance tests
python ingestion/tests/performance/test_comprehensive.py
```

#### Integration Tests
```bash
# Note: Integration tests require Django setup
python ingestion/tests/integration/test_hubspot_appointments_duration.py
```

## Test Categories

### Unit Tests (`unit/`)
- **test_base/**: Tests for base module functionality
  - Performance monitoring and cleanup
  - Automation system metrics reporting
  - Core functionality validation

- **test_hubspot/**: Tests for HubSpot-specific functionality
  - Duration parsing logic
  - Data transformation
  - Field mappings

### Integration Tests (`integration/`)
- End-to-end testing with actual Django models
- Database integration testing
- API integration testing
- Requires full Django setup

### Performance Tests (`performance/`)
- Benchmarking and performance validation
- Resource usage monitoring
- Scalability testing
- Comprehensive feature validation

## Test Features

### Implemented Tests
✅ **PerformanceMonitor cleanup method** - Ensures proper resource cleanup
✅ **SelfHealingSystem report_metrics** - Comprehensive metrics reporting
✅ **HubSpot duration parsing** - Duration string to minutes conversion
✅ **Automation system integration** - End-to-end automation testing
✅ **Performance benchmarking** - Multi-feature performance validation

### Test Standards
- **Mock-based testing** for external dependencies
- **Async-first** test patterns
- **Comprehensive error handling** validation
- **Performance benchmarking** with thresholds
- **Docker environment** support

## Guidelines

### Writing New Tests
1. Follow the directory structure based on the module being tested
2. Use descriptive test names that explain what is being tested
3. Include proper setup and teardown methods
4. Mock external dependencies appropriately
5. Include performance assertions where relevant

### Test File Naming
- Unit tests: `test_[module_name].py`
- Integration tests: `test_[integration_type].py`
- Performance tests: `test_[performance_aspect].py`

### Dependencies
- **unittest.mock**: For mocking external dependencies
- **asyncio**: For testing async functionality
- **pytest**: For advanced testing features (optional)
- **Django**: For integration tests (requires setup)

## Enterprise Standards

Following the import refactoring guidelines, all tests adhere to:
- **95%+ test coverage** for critical functionality
- **Performance benchmarking** with defined thresholds
- **Comprehensive mocking** of external dependencies
- **Standardized test structure** across all modules
- **Automated test execution** with detailed reporting

## Future Enhancements

### Planned Test Additions
- [ ] Genius CRM integration tests
- [ ] MarketSharp integration tests
- [ ] Arrivy integration tests
- [ ] Advanced performance monitoring tests
- [ ] Security and encryption tests
- [ ] Scalability stress tests

### Test Infrastructure Improvements
- [ ] Automated test reporting dashboard
- [ ] Continuous integration setup
- [ ] Performance regression detection
- [ ] Test result visualization
- [ ] Coverage reporting automation
