"""
Test Runner - A1 Agentic System

Comprehensive test runner with coverage reporting and performance metrics.
"""

import pytest
import sys
import asyncio
from pathlib import Path
import time
import json

def run_unit_tests():
    """Run unit tests with coverage."""
    print("🧪 Running Unit Tests...")
    
    exit_code = pytest.main([
        'tests/unit/',
        '-v',
        '--tb=short',
        '--cov=.',
        '--cov-report=term-missing',
        '--cov-report=html:htmlcov',
        '--cov-fail-under=80',
        '--asyncio-mode=auto'
    ])
    
    return exit_code == 0

def run_integration_tests():
    """Run integration tests."""
    print("🔗 Running Integration Tests...")
    
    exit_code = pytest.main([
        'tests/integration/',
        '-v',
        '--tb=short',
        '--asyncio-mode=auto'
    ])
    
    return exit_code == 0

def run_e2e_tests():
    """Run end-to-end tests."""
    print("🎯 Running End-to-End Tests...")
    
    exit_code = pytest.main([
        'tests/e2e/',
        '-v',
        '--tb=short',
        '--asyncio-mode=auto'
    ])
    
    return exit_code == 0

def run_performance_tests():
    """Run performance benchmarks."""
    print("⚡ Running Performance Tests...")
    
    performance_config = {
        'max_execution_time': 30.0,  # seconds
        'max_memory_usage': 512,     # MB
        'target_throughput': 10      # contracts per minute
    }
    
    exit_code = pytest.main([
        'tests/',
        '-v',
        '-m', 'performance',
        '--tb=short',
        '--asyncio-mode=auto'
    ])
    
    return exit_code == 0

def generate_test_report():
    """Generate comprehensive test report."""
    print("📊 Generating Test Report...")
    
    report = {
        'timestamp': time.time(),
        'test_suites': {
            'unit': {'status': 'unknown', 'coverage': 0},
            'integration': {'status': 'unknown'},
            'e2e': {'status': 'unknown'},
            'performance': {'status': 'unknown'}
        },
        'overall_status': 'unknown',
        'recommendations': []
    }
    
    report_path = Path('test_report.json')
    with open(report_path, 'w') as f:
        json.dump(report, f, indent=2)
    
    print(f"📋 Test report saved to: {report_path}")
    return report

def main():
    """Main test runner."""
    print("🚀 A1 Agentic System - Test Suite Runner")
    print("=" * 50)
    
    start_time = time.time()
    results = {}
    
    test_suites = [
        ('Unit Tests', run_unit_tests),
        ('Integration Tests', run_integration_tests),
        ('End-to-End Tests', run_e2e_tests),
        ('Performance Tests', run_performance_tests)
    ]
    
    for suite_name, test_func in test_suites:
        print(f"\n{'=' * 20} {suite_name} {'=' * 20}")
        
        suite_start = time.time()
        try:
            success = test_func()
            results[suite_name] = {
                'success': success,
                'duration': time.time() - suite_start,
                'status': 'PASSED' if success else 'FAILED'
            }
        except Exception as e:
            results[suite_name] = {
                'success': False,
                'duration': time.time() - suite_start,
                'status': 'ERROR',
                'error': str(e)
            }
        
        print(f"✅ {suite_name}: {results[suite_name]['status']} ({results[suite_name]['duration']:.2f}s)")
    
    total_time = time.time() - start_time
    passed_suites = sum(1 for r in results.values() if r['success'])
    total_suites = len(results)
    
    print(f"\n{'=' * 50}")
    print(f"📈 Test Summary:")
    print(f"   Total Suites: {total_suites}")
    print(f"   Passed: {passed_suites}")
    print(f"   Failed: {total_suites - passed_suites}")
    print(f"   Success Rate: {passed_suites/total_suites*100:.1f}%")
    print(f"   Total Time: {total_time:.2f}s")
    
    generate_test_report()
    
    if passed_suites == total_suites:
        print("🎉 All tests passed!")
        sys.exit(0)
    else:
        print("❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
