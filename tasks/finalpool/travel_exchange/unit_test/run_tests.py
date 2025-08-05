#!/usr/bin/env python3
"""
Test runner for travel exchange evaluation unit tests
Run all tests and provide comprehensive reporting
"""

import sys
import unittest
from pathlib import Path

# Add current directory to path for test imports
sys.path.insert(0, str(Path(__file__).parent))

from test_components import run_unit_tests
from test_end_to_end import run_end_to_end_tests

def run_all_tests():
    """Run all unit tests and end-to-end tests"""
    
    print("🧪 TRAVEL EXCHANGE EVALUATION TEST SUITE")
    print("=" * 80)
    print()
    
    # Run component tests
    print("📋 COMPONENT TESTS")
    print("-" * 40)
    component_success = run_unit_tests()
    print()
    
    # Run end-to-end tests  
    print("🔄 END-TO-END TESTS")
    print("-" * 40)
    e2e_success = run_end_to_end_tests()
    print()
    
    # Overall summary
    print("=" * 80)
    print("📊 OVERALL TEST RESULTS")
    print("=" * 80)
    
    if component_success and e2e_success:
        print("✅ ALL TESTS PASSED - Evaluation system working correctly")
        print("💰 Ready to evaluate travel expense calculations")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        if not component_success:
            print("   - Component tests failed")
        if not e2e_success:
            print("   - End-to-end tests failed")
        print()
        print("🔧 Fix the failing tests before using the evaluation system")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)