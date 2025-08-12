#!/usr/bin/env python3
"""
End-to-end tests for dietary-health evaluation
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

import check_local

class TestEndToEndEvaluation(unittest.TestCase):
    """Test complete evaluation workflow"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create perfect ground truth workspace
        self.gt_workspace = self.temp_path / "groundtruth"
        self.gt_workspace.mkdir()
        
        self.perfect_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g"""
        
        with open(self.gt_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(self.perfect_analysis)
        
        # Create dummy res_log
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
        
        # Create perfect analysis.md
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(self.perfect_analysis)
        
        # Test via command line
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--groundtruth_workspace", str(self.gt_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Perfect workspace should pass. Stderr: {result.stderr}")
        self.assertIn("Pass all tests!", result.stdout)
        self.assertIn("✅ Local file check passed", result.stdout)
    
    def test_missing_file_fails_evaluation(self):
        """Test that missing analysis.md fails evaluation"""
        agent_workspace = self.temp_path / "agent_missing"
        agent_workspace.mkdir()
        # Don't create analysis.md
        
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--groundtruth_workspace", str(self.gt_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, "Missing file should fail evaluation")
        self.assertIn("❌ Local file check failed", result.stdout)
        self.assertIn("analysis.md file not found", result.stdout)
    
    def test_incomplete_analysis_fails_evaluation(self):
        """Test that incomplete analysis fails evaluation"""
        agent_workspace = self.temp_path / "agent_incomplete"
        agent_workspace.mkdir()
        
        # Create incomplete analysis
        incomplete_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

Missing protein analysis here."""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(incomplete_analysis)
        
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", str(agent_workspace),
            "--groundtruth_workspace", str(self.gt_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, "Incomplete analysis should fail")
        self.assertIn("❌ Local file check failed", result.stdout)
        self.assertIn("Could not find protein", result.stdout)
    
    def test_evaluation_handles_exceptions(self):
        """Test that evaluation handles exceptions gracefully"""
        # Test with non-existent workspace - this now returns a regular error, not exception
        cmd = [
            sys.executable, str(evaluation_dir / "main.py"),
            "--agent_workspace", "/nonexistent/path",
            "--groundtruth_workspace", str(self.gt_workspace),
            "--res_log_file", str(self.res_log_file)
        ]
        
        result = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(result.returncode, 1, "Should fail gracefully")
        # The error is now handled as a normal failure, not an exception
        self.assertIn("❌ Local file check failed", result.stdout)

class TestEvaluationRobustness(unittest.TestCase):
    """Test evaluation robustness with various scenarios"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create ground truth
        self.gt_workspace = self.temp_path / "groundtruth"
        self.gt_workspace.mkdir()
        self.perfect_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g"""
        
        with open(self.gt_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(self.perfect_analysis)
            
        self.res_log = {"dummy": "log"}
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_formatting_variations_pass(self):
        """Test that various formatting variations pass evaluation"""
        formatting_variations = [
            # Extra whitespace
            """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g
            
            """,
            
            # Different markdown formatting
            """## Today's Meal Nutritional Analysis

**Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

**Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""",
            
            # With additional content
            """# Today's Meal Nutritional Analysis

This is the analysis for today's meals.

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g

Additional notes: The meal plan follows the fitness requirements."""
        ]
        
        from check_local import check_local
        
        for i, variation in enumerate(formatting_variations):
            with self.subTest(variation=i):
                agent_workspace = self.temp_path / f"agent_variation_{i}"
                agent_workspace.mkdir()
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(variation)
                
                success, error = check_local(str(agent_workspace), str(self.gt_workspace), self.res_log)
                self.assertTrue(success, f"Variation {i} should pass: {error}")
    
    def test_edge_cases_fail_appropriately(self):
        """Test that edge cases fail with appropriate error messages"""
        from check_local import check_local
        
        edge_cases = [
            # Almost correct but missing key numbers
            ("""# Today's Meal Nutritional Analysis
- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 999g
- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""", "correct carbohydrate analysis"),
            
            # Wrong status but correct numbers
            ("""# Today's Meal Nutritional Analysis
- **Carbohydrates**: Meets expectations. Expected: 162.5g-195g | Actual: 135.5g
- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""", "correct carbohydrate analysis"),
            
            # Completely different content
            ("""# Random Content
This has nothing to do with nutritional analysis.""", "correct carbohydrate analysis, correct protein analysis"),
            
            # Only partial information
            ("""# Today's Meal Nutritional Analysis
- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g""", "correct protein analysis")
        ]
        
        for i, (content, expected_error) in enumerate(edge_cases):
            with self.subTest(case=i):
                agent_workspace = self.temp_path / f"agent_edge_{i}"
                agent_workspace.mkdir()
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(content)
                
                success, error = check_local(str(agent_workspace), str(self.gt_workspace), self.res_log)
                self.assertFalse(success, f"Edge case {i} should fail")
                self.assertIn(expected_error, error, f"Error message should mention '{expected_error}' for case {i}")

class TestTaskComplexity(unittest.TestCase):
    """Analyze task complexity and suggest improvements"""
    
    def test_current_task_limitations(self):
        """Document current task limitations for improvement"""
        limitations = [
            "Only checks 2 nutrients (carbs, protein) out of many important ones",
            "Uses exact hardcoded values instead of calculation validation", 
            "No verification that agent actually used the Excel data",
            "No check for proper format following as specified in format.md",
            "No validation of nutritional reasoning or methodology",
            "Brittle regex patterns that could break with minor format changes",
            "No tolerance for reasonable calculation variations",
            "Missing validation of calorie calculations",
            "No check for fat, fiber, vitamin, mineral analysis",
            "No verification of fitness goal alignment"
        ]
        
        # This test documents limitations but always passes
        print("\n📋 Current Task Limitations:")
        for i, limitation in enumerate(limitations, 1):
            print(f"  {i}. {limitation}")
        
        self.assertTrue(True, "Documentation test")

def run_end_to_end_tests():
    """Run all end-to-end tests with colored output"""
    
    print("🥗 Dietary Health - End-to-End Tests")
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