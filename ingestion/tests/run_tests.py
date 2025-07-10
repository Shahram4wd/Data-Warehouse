#!/usr/bin/env python3
"""
Test runner for the ingestion module following import refactoring guidelines
"""
import os
import sys
import subprocess
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

def run_unit_tests():
    """Run unit tests"""
    print("Running unit tests...")
    print("=" * 50)
    
    # Test base module
    print("Testing base module...")
    base_test_dir = project_root / "ingestion" / "tests" / "unit" / "test_base"
    
    test_files = [
        "test_performance_cleanup.py",
        "test_report_metrics.py"
    ]
    
    for test_file in test_files:
        test_path = base_test_dir / test_file
        if test_path.exists():
            print(f"  Running {test_file}...")
            try:
                result = subprocess.run([sys.executable, str(test_path)], 
                                      capture_output=True, text=True, cwd=str(project_root))
                if result.returncode == 0:
                    print(f"    ✅ {test_file} passed")
                else:
                    print(f"    ❌ {test_file} failed")
                    print(f"    Error: {result.stderr}")
            except Exception as e:
                print(f"    ❌ {test_file} error: {e}")
    
    # Test HubSpot module
    print("\nTesting HubSpot module...")
    hubspot_test_dir = project_root / "ingestion" / "tests" / "unit" / "test_hubspot"
    
    hubspot_test_files = [
        "test_duration_logic.py",
        # "test_hubspot_duration.py"  # This one requires Django setup
    ]
    
    for test_file in hubspot_test_files:
        test_path = hubspot_test_dir / test_file
        if test_path.exists():
            print(f"  Running {test_file}...")
            try:
                result = subprocess.run([sys.executable, str(test_path)], 
                                      capture_output=True, text=True, cwd=str(project_root))
                if result.returncode == 0:
                    print(f"    ✅ {test_file} passed")
                else:
                    print(f"    ❌ {test_file} failed")
                    print(f"    Error: {result.stderr}")
            except Exception as e:
                print(f"    ❌ {test_file} error: {e}")

def run_performance_tests():
    """Run performance tests"""
    print("\nRunning performance tests...")
    print("=" * 50)
    
    perf_test_dir = project_root / "ingestion" / "tests" / "performance"
    
    test_files = [
        "test_comprehensive.py"
    ]
    
    for test_file in test_files:
        test_path = perf_test_dir / test_file
        if test_path.exists():
            print(f"  Running {test_file}...")
            try:
                result = subprocess.run([sys.executable, str(test_path)], 
                                      capture_output=True, text=True, cwd=str(project_root))
                if result.returncode == 0:
                    print(f"    ✅ {test_file} passed")
                else:
                    print(f"    ❌ {test_file} failed")
                    print(f"    Error: {result.stderr}")
            except Exception as e:
                print(f"    ❌ {test_file} error: {e}")

def run_integration_tests():
    """Run integration tests"""
    print("\nRunning integration tests...")
    print("=" * 50)
    print("Note: Integration tests require Django setup and may not run in this environment")
    
    integration_test_dir = project_root / "ingestion" / "tests" / "integration"
    
    test_files = [
        "test_hubspot_appointments_duration.py"
    ]
    
    for test_file in test_files:
        test_path = integration_test_dir / test_file
        if test_path.exists():
            print(f"  Found {test_file} (requires Django setup)")

def main():
    """Main test runner"""
    print("Data Warehouse Ingestion Test Suite")
    print("Following import refactoring guidelines")
    print("=" * 60)
    
    try:
        run_unit_tests()
        run_performance_tests()
        run_integration_tests()
        
        print("\n" + "=" * 60)
        print("✅ Test suite completed!")
        print("\nTest file locations:")
        print("  Unit tests: ingestion/tests/unit/")
        print("  Performance tests: ingestion/tests/performance/")
        print("  Integration tests: ingestion/tests/integration/")
        
    except Exception as e:
        print(f"❌ Test suite failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
