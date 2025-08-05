#!/usr/bin/env python3
"""
Test runner for cooking-guidance task evaluation
Runs all unit tests and integration tests
"""

import sys
import subprocess
from pathlib import Path

def run_tests():
    """Run all tests and return overall success status"""
    
    print("🍳 COOKING GUIDANCE EVALUATION TESTS")
    print("=" * 80)
    print()
    
    base_dir = Path(__file__).parent
    success_count = 0
    total_count = 2
    
    # Run component tests
    print("Running component tests...")
    try:
        result = subprocess.run([
            sys.executable, str(base_dir / "test_components.py")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Component tests PASSED")
            success_count += 1
        else:
            print("❌ Component tests FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"❌ Component tests ERROR: {e}")
    
    print()
    
    # Run integration tests
    print("Running integration tests...")
    try:
        result = subprocess.run([
            sys.executable, str(base_dir / "test_end_to_end.py")
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Integration tests PASSED")
            success_count += 1
        else:
            print("❌ Integration tests FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
    except Exception as e:
        print(f"❌ Integration tests ERROR: {e}")
    
    print()
    print("=" * 80)
    print(f"OVERALL RESULT: {success_count}/{total_count} test suites passed")
    
    if success_count == total_count:
        print("🎉 ALL TESTS PASSED!")
        return True
    else:
        print("💥 SOME TESTS FAILED!")
        return False

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)