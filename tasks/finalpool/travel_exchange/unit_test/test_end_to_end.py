#!/usr/bin/env python3
"""
End-to-end tests for travel exchange evaluation
Tests the complete evaluation process including main.py orchestration
"""

import sys
import unittest
import tempfile
import json
import subprocess
from pathlib import Path

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

class TestEndToEndEvaluation(unittest.TestCase):
    """Test complete evaluation workflow using main.py"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create dummy res_log file
        self.res_log_file = self.temp_path / "res_log.json"
        with open(self.res_log_file, "w") as f:
            json.dump({"dummy": "log"}, f)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_perfect_workspace_passes_evaluation(self):
        """Test that perfect workspace passes complete evaluation"""
        agent_workspace = self.temp_path / "agent_perfect"
        agent_workspace.mkdir()
        
        # Create perfect total_cost.json
        perfect_data = {"total": 39891}
        output_file = agent_workspace / "total_cost.json"
        with open(output_file, 'w') as f:
            json.dump(perfect_data, f)
        
        # Test via command line
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Perfect workspace should pass. Stderr: {result.stderr}")
        self.assertIn("Pass test!", result.stdout)
    
    def test_within_tolerance_passes_evaluation(self):
        """Test that result within tolerance passes evaluation"""
        agent_workspace = self.temp_path / "agent_tolerance"
        agent_workspace.mkdir()
        
        # Create result within tolerance (500 CNY difference)
        tolerance_data = {"total": 39391}
        output_file = agent_workspace / "total_cost.json"
        with open(output_file, 'w') as f:
            json.dump(tolerance_data, f)
        
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, "Result within tolerance should pass")
        self.assertIn("Pass test!", result.stdout)
    
    def test_outside_tolerance_fails_evaluation(self):
        """Test that result outside tolerance fails evaluation"""
        agent_workspace = self.temp_path / "agent_fail"
        agent_workspace.mkdir()
        
        # Create result outside tolerance (2000 CNY difference)
        fail_data = {"total": 37891}
        output_file = agent_workspace / "total_cost.json"
        with open(output_file, 'w') as f:
            json.dump(fail_data, f)
        
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, "Result outside tolerance should fail")
        self.assertIn("Test failed", result.stderr)
        self.assertIn("exceeds 1000", result.stderr)
    
    def test_missing_file_fails_evaluation(self):
        """Test that missing total_cost.json fails evaluation"""
        agent_workspace = self.temp_path / "agent_missing"
        agent_workspace.mkdir()
        # Don't create total_cost.json
        
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, "Missing file should fail evaluation")
        # The original main.py will fail when trying to read the file

class TestEvaluationRobustness(unittest.TestCase):
    """Test evaluation robustness with various scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_different_number_formats(self):
        """Test evaluation with different number formats"""
        from check_local_enhanced import evaluate_travel_exchange
        
        number_formats = [
            (39891, "integer"),
            (39891.0, "float with .0"),
            (39891.50, "float with decimals"),
            (39890.9999, "float close to integer"),
        ]
        
        for total, description in number_formats:
            with self.subTest(format=description):
                agent_workspace = self.temp_path / f"agent_{description.replace(' ', '_')}"
                agent_workspace.mkdir()
                
                data = {"total": total}
                output_file = agent_workspace / "total_cost.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f)
                
                success, error = evaluate_travel_exchange(str(agent_workspace))
                self.assertTrue(success, f"{description} should pass: {error}")
    
    def test_boundary_values(self):
        """Test evaluation at tolerance boundaries"""
        from check_local_enhanced import evaluate_travel_exchange
        
        boundary_cases = [
            (38891, "lower boundary", True),    # exactly 1000 below
            (40891, "upper boundary", True),    # exactly 1000 above
            (38890, "just below lower", False), # 1001 below
            (40892, "just above upper", False), # 1001 above
        ]
        
        for total, description, should_pass in boundary_cases:
            with self.subTest(case=description):
                agent_workspace = self.temp_path / f"agent_{description.replace(' ', '_')}"
                agent_workspace.mkdir()
                
                data = {"total": total}
                output_file = agent_workspace / "total_cost.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f)
                
                success, error = evaluate_travel_exchange(str(agent_workspace))
                if should_pass:
                    self.assertTrue(success, f"{description} should pass: {error}")
                else:
                    self.assertFalse(success, f"{description} should fail")
    
    def test_json_structure_variations(self):
        """Test evaluation with various JSON structures"""
        from check_local_enhanced import evaluate_travel_exchange
        
        structure_cases = [
            # Valid cases
            ({"total": 39891}, "minimal structure", True),
            ({"total": 39891, "currency": "CNY"}, "with extra field", True),
            ({"total": 39891, "breakdown": {"andrew": 20000, "lau": 19891}}, "with nested data", True),
            
            # Invalid cases
            ({"cost": 39891}, "wrong field name", False),
            ({"total": "39891"}, "string instead of number", False),
            ([39891], "array instead of object", False),
            (39891, "number instead of object", False),
            ({}, "empty object", False),
        ]
        
        for data, description, should_pass in structure_cases:
            with self.subTest(case=description):
                agent_workspace = self.temp_path / f"agent_{description.replace(' ', '_')}"
                agent_workspace.mkdir()
                
                output_file = agent_workspace / "total_cost.json"
                with open(output_file, 'w') as f:
                    json.dump(data, f)
                
                success, error = evaluate_travel_exchange(str(agent_workspace))
                if should_pass:
                    self.assertTrue(success, f"{description} should pass: {error}")
                else:
                    self.assertFalse(success, f"{description} should fail")

class TestTaskComplexity(unittest.TestCase):
    """Analyze task complexity and validation completeness"""
    
    def test_task_evaluation_completeness(self):
        """Document task evaluation strengths and limitations"""
        strengths = [
            "Simple output format validation (JSON with 'total' field)",
            "Tolerance-based evaluation (±1000 CNY)",
            "Clear pass/fail criteria",
            "Handles different number formats (int/float)"
        ]
        
        limitations = [
            "No validation of calculation methodology",
            "No verification of exchange rate usage",
            "No intermediate step validation",
            "No validation of input file processing",
            "Hardcoded expected value without dynamic verification",
            "No verification that all expenses were included",
            "No validation of currency conversion accuracy"
        ]
        
        print("\n📊 Task Evaluation Analysis:")
        print("\n✅ Strengths:")
        for i, strength in enumerate(strengths, 1):
            print(f"  {i}. {strength}")
        
        print("\n⚠️ Limitations:")
        for i, limitation in enumerate(limitations, 1):
            print(f"  {i}. {limitation}")
        
        # This test documents the analysis but always passes
        self.assertTrue(True, "Documentation test")

def run_end_to_end_tests():
    """Run all end-to-end tests with colored output"""
    
    print("🧮 Travel Exchange - End-to-End Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestEndToEndEvaluation))
    suite.addTests(loader.loadTestsFromTestCase(TestEvaluationRobustness))
    suite.addTests(loader.loadTestsFromTestCase(TestTaskComplexity))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL END-TO-END TESTS PASSED ({result.testsRun} tests)")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_end_to_end_tests()
    sys.exit(0 if success else 1)