#!/usr/bin/env python3
"""
Unit tests for travel exchange evaluation components
Tests specific functions and edge cases in isolation
"""

import sys
import unittest
import tempfile
import json
import os
from pathlib import Path

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

# Import evaluation functions
try:
    from check_local_enhanced import (
        check_file_exists,
        validate_json_structure, 
        check_total_accuracy,
        evaluate_travel_exchange,
        get_evaluation_summary
    )
    ENHANCED_AVAILABLE = True
except ImportError:
    ENHANCED_AVAILABLE = False

class TestFileExistence(unittest.TestCase):
    """Test file existence checking"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_existing_file_passes(self):
        """Test that existing file passes check"""
        test_file = self.temp_path / "total_cost.json"
        test_file.write_text('{"total": 37884}')
        
        exists, error = check_file_exists(str(test_file))
        self.assertTrue(exists)
        self.assertEqual(error, "")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_missing_file_fails(self):
        """Test that missing file fails check"""
        test_file = self.temp_path / "nonexistent.json"
        
        exists, error = check_file_exists(str(test_file))
        self.assertFalse(exists)
        self.assertIn("not found", error)

class TestJsonValidation(unittest.TestCase):
    """Test JSON structure validation"""
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_valid_structure_passes(self):
        """Test that valid JSON structure passes"""
        valid_data = {"total": 37884}
        
        valid, error = validate_json_structure(valid_data)
        self.assertTrue(valid)
        self.assertEqual(error, "")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_valid_structure_with_float_passes(self):
        """Test that valid JSON with float total passes"""
        valid_data = {"total": 37884.50}
        
        valid, error = validate_json_structure(valid_data)
        self.assertTrue(valid)
        self.assertEqual(error, "")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_non_dict_fails(self):
        """Test that non-dictionary data fails"""
        invalid_data = [37884]
        
        valid, error = validate_json_structure(invalid_data)
        self.assertFalse(valid)
        self.assertIn("dictionary", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_missing_total_field_fails(self):
        """Test that missing total field fails"""
        invalid_data = {"cost": 37884}
        
        valid, error = validate_json_structure(invalid_data)
        self.assertFalse(valid)
        self.assertIn("total", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_non_numeric_total_fails(self):
        """Test that non-numeric total fails"""
        invalid_data = {"total": "37884"}
        
        valid, error = validate_json_structure(invalid_data)
        self.assertFalse(valid)
        self.assertIn("number", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_negative_total_fails(self):
        """Test that negative total fails"""
        invalid_data = {"total": -1000}
        
        valid, error = validate_json_structure(invalid_data)
        self.assertFalse(valid)
        self.assertIn("negative", error)

class TestTotalAccuracy(unittest.TestCase):
    """Test total accuracy checking"""
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_exact_match_passes(self):
        """Test that exact match passes"""
        accurate, error = check_total_accuracy(37884, 37884, 1000)
        self.assertTrue(accurate)
        self.assertEqual(error, "")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_within_tolerance_passes(self):
        """Test that values within tolerance pass"""
        test_cases = [
            (39391, "lower boundary"),  # 500 below
            (40391, "upper boundary"),  # 500 above
            (38891, "lower limit"),     # 1000 below
            (40891, "upper limit"),     # 1000 above
        ]
        
        for total, description in test_cases:
            with self.subTest(case=description):
                accurate, error = check_total_accuracy(total, 39891, 1000)
                self.assertTrue(accurate, f"{description} should pass: {error}")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_outside_tolerance_fails(self):
        """Test that values outside tolerance fail"""
        test_cases = [
            (38890, "just below lower limit"),  # 1001 below
            (40892, "just above upper limit"),  # 1001 above
            (37000, "far below"),               # 2891 below
            (42000, "far above"),               # 2109 above
        ]
        
        for total, description in test_cases:
            with self.subTest(case=description):
                accurate, error = check_total_accuracy(total, 39891, 1000)
                self.assertFalse(accurate, f"{description} should fail")
                self.assertIn("exceeding tolerance", error)

class TestFullEvaluation(unittest.TestCase):
    """Test complete evaluation workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_perfect_result_passes(self):
        """Test that perfect result passes full evaluation"""
        # Create perfect total_cost.json
        perfect_data = {"total": 39891}
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(perfect_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertTrue(success, f"Perfect result should pass: {error}")
        self.assertEqual(error, "")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_within_tolerance_passes(self):
        """Test that result within tolerance passes"""
        # Create result within tolerance
        good_data = {"total": 39391}  # 500 below expected
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(good_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertTrue(success, f"Result within tolerance should pass: {error}")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_missing_file_fails(self):
        """Test that missing file fails evaluation"""
        # Don't create any file
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("not found", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_invalid_json_fails(self):
        """Test that invalid JSON fails evaluation"""
        # Create invalid JSON file
        output_file = self.temp_path / "total_cost.json"
        output_file.write_text('{"total": 37884,}')  # Trailing comma makes it invalid
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("Invalid JSON", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_wrong_structure_fails(self):
        """Test that wrong JSON structure fails"""
        # Create JSON with wrong structure
        wrong_data = {"cost": 37884}  # Wrong field name
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(wrong_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("total", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_inaccurate_total_fails(self):
        """Test that inaccurate total fails evaluation"""
        # Create result outside tolerance
        bad_data = {"total": 41000}  # 1109 above expected
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(bad_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("exceeding tolerance", error)

class TestEvaluationSummary(unittest.TestCase):
    """Test evaluation summary functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_summary_with_perfect_result(self):
        """Test summary generation with perfect result"""
        # Create perfect result
        perfect_data = {"total": 39891}
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(perfect_data, f)
        
        summary = get_evaluation_summary(str(self.temp_path))
        
        self.assertTrue(summary["file_exists"])
        self.assertTrue(summary["json_valid"])
        self.assertTrue(summary["structure_valid"])
        self.assertEqual(summary["total_value"], 39891)
        self.assertTrue(summary["accuracy_check"])
        self.assertEqual(summary["difference"], 0)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_summary_with_missing_file(self):
        """Test summary generation with missing file"""
        summary = get_evaluation_summary(str(self.temp_path))
        
        self.assertFalse(summary["file_exists"])
        self.assertFalse(summary["json_valid"])
        self.assertFalse(summary["structure_valid"])
        self.assertIsNone(summary["total_value"])
        self.assertFalse(summary["accuracy_check"])

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_empty_file_fails(self):
        """Test that empty file fails evaluation"""
        output_file = self.temp_path / "total_cost.json"
        output_file.write_text('')  # Empty file
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("JSON", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_large_numbers_work(self):
        """Test that large numbers work correctly"""
        large_data = {"total": 378840}  # 10x expected, should fail
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(large_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertFalse(success)
        self.assertIn("exceeding tolerance", error)
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_float_precision_works(self):
        """Test that float precision works correctly"""
        float_data = {"total": 39891.99}  # Very close to expected
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(float_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertTrue(success, f"Float precision should pass: {error}")
    
    @unittest.skipUnless(ENHANCED_AVAILABLE, "Enhanced evaluation not available")
    def test_additional_fields_allowed(self):
        """Test that additional fields in JSON are allowed"""
        extended_data = {
            "total": 39891,
            "breakdown": {"andrew": 20000, "lau": 17884},
            "currency": "CNY"
        }
        output_file = self.temp_path / "total_cost.json"
        
        with open(output_file, 'w') as f:
            json.dump(extended_data, f)
        
        success, error = evaluate_travel_exchange(str(self.temp_path))
        self.assertTrue(success, f"Additional fields should be allowed: {error}")

def run_unit_tests():
    """Run all unit tests with colored output"""
    
    print("🧮 Travel Exchange - Unit Tests")
    print("=" * 60)
    
    if not ENHANCED_AVAILABLE:
        print("❌ Enhanced evaluation module not available")
        print("   Please check check_local_enhanced.py import")
        return False
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFileExistence))
    suite.addTests(loader.loadTestsFromTestCase(TestJsonValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestTotalAccuracy))
    suite.addTests(loader.loadTestsFromTestCase(TestFullEvaluation))
    suite.addTests(loader.loadTestsFromTestCase(TestEvaluationSummary))
    suite.addTests(loader.loadTestsFromTestCase(TestEdgeCases))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL UNIT TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_unit_tests()
    sys.exit(0 if success else 1)