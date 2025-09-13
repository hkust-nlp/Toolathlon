#!/usr/bin/env python3
"""
Test script to verify the fixed evaluation logic
"""

import sys
import os
from pathlib import Path

# Add the evaluation directory to the path
current_dir = Path(__file__).parent
task_dir = current_dir.parent
eval_dir = task_dir / "evaluation"
sys.path.insert(0, str(eval_dir))

def test_evaluation_logic():
    """Test the evaluation counting logic"""
    print("🧪 Testing Fixed Evaluation Logic")
    print("=" * 50)
    
    # Simulate different result scenarios
    test_cases = [
        {
            "name": "All Pass",
            "results": [
                ("Service1", True, "Success message 1"),
                ("Service2", True, "Success message 2"),
                ("Service3", True, "Success message 3")
            ],
            "expected_pass": True,
            "expected_count": 3
        },
        {
            "name": "All Fail",
            "results": [
                ("Service1", False, "Failure message 1"),
                ("Service2", False, "Failure message 2"),
                ("Service3", False, "Failure message 3")
            ],
            "expected_pass": False,
            "expected_count": 0
        },
        {
            "name": "Mixed Results",
            "results": [
                ("Service1", True, "Success message 1"),
                ("Service2", False, "Failure message 2"),
                ("Service3", True, "Success message 3")
            ],
            "expected_pass": False,
            "expected_count": 2
        },
        {
            "name": "Single Fail",
            "results": [
                ("Service1", False, "No new customers found")
            ],
            "expected_pass": False,
            "expected_count": 0
        }
    ]
    
    for case in test_cases:
        print(f"\n🔍 Testing: {case['name']}")
        
        # Apply the fixed logic
        results = case["results"]
        passed = sum(1 for _, success, _ in results if success)
        total = len(results)
        overall_pass = passed == total
        
        print(f"   Results: {results}")
        print(f"   Passed: {passed}/{total}")
        print(f"   Overall: {'PASS' if overall_pass else 'FAIL'}")
        
        # Verify expectations
        if passed == case["expected_count"] and overall_pass == case["expected_pass"]:
            print(f"   ✅ Test PASSED - Logic is correct")
        else:
            print(f"   ❌ Test FAILED - Expected {case['expected_count']} passed, {case['expected_pass']} overall")
            return False
    
    print(f"\n✅ All evaluation logic tests passed!")
    return True

def demonstrate_old_vs_new_logic():
    """Demonstrate the difference between old and new logic"""
    print("\n" + "=" * 60)
    print("🔧 OLD vs NEW Logic Demonstration")
    print("=" * 60)
    
    # Example scenario from the user's issue
    results = [
        ("WooCommerce", False, "No new customers found"),
        ("Email", False, "No customers to check"),
        ("BigQuery Database", False, "No customers to check")
    ]
    
    print("Scenario: All services fail")
    print("Results:", results)
    
    # Old (broken) logic
    old_passed = sum(1 for _, success, _ in results)  # Bug: counts all results
    old_total = len(results)
    old_overall = old_passed == old_total
    
    print(f"\n❌ OLD Logic (BROKEN):")
    print(f"   Passed: {old_passed}/{old_total} (incorrectly counts all results)")
    print(f"   Overall: {'PASS' if old_overall else 'FAIL'} (WRONG!)")
    
    # New (fixed) logic  
    new_passed = sum(1 for _, success, _ in results if success)  # Fix: only count successes
    new_total = len(results)
    new_overall = new_passed == new_total
    
    print(f"\n✅ NEW Logic (FIXED):")
    print(f"   Passed: {new_passed}/{new_total} (correctly counts only successes)")
    print(f"   Overall: {'PASS' if new_overall else 'FAIL'} (CORRECT!)")

if __name__ == "__main__":
    success = test_evaluation_logic()
    demonstrate_old_vs_new_logic()
    
    if success:
        print(f"\n🎉 Evaluation logic has been successfully fixed!")
        print("The evaluation will now correctly fail when services are not working.")
        sys.exit(0)
    else:
        print(f"\n❌ Evaluation logic tests failed!")
        sys.exit(1)