#!/usr/bin/env python3
"""
Test the flexible evaluation system with various agent output formats
"""

import sys
import unittest
import tempfile
import os
from pathlib import Path

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

from check_local_flexible import check_local_flexible

class TestFlexibleEvaluation(unittest.TestCase):
    """Test flexible evaluation with various agent output formats"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create ground truth workspace
        self.gt_workspace = self.temp_path / "groundtruth"
        self.gt_workspace.mkdir()
        
        with open(self.gt_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write("groundtruth placeholder")
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_exact_match_passes(self):
        """Test that exact match passes"""
        agent_workspace = self.temp_path / "agent_exact"
        agent_workspace.mkdir()
        
        exact_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g"""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(exact_analysis)
        
        success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
        self.assertTrue(success, f"Exact match should pass: {error}")
    
    def test_approximate_values_pass(self):
        """Test that approximate values within tolerance pass"""
        agent_workspace = self.temp_path / "agent_approx"
        agent_workspace.mkdir()
        
        # Values within 5g tolerance
        approx_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 136g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 147g"""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(approx_analysis)
        
        success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
        self.assertTrue(success, f"Approximate values should pass: {error}")
    
    def test_different_number_formats_pass(self):
        """Test various number formats are accepted"""
        test_cases = [
            # Different decimal formats
            ("135.0", "146.0"),
            ("136", "147"),
            ("135.5g", "146.9g"),
            ("135.5 g", "146.9 g"),
            ("135.5 grams", "146.9 grams"),
        ]
        
        for i, (carbs, protein) in enumerate(test_cases):
            with self.subTest(case=i):
                agent_workspace = self.temp_path / f"agent_format_{i}"
                agent_workspace.mkdir()
                
                format_analysis = f"""# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: {carbs}

- **Protein**: Excessive intake. Expected: 97.5g | Actual: {protein}"""
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(format_analysis)
                
                success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
                self.assertTrue(success, f"Format {i} should pass: {error}")
    
    def test_flexible_text_patterns_pass(self):
        """Test that various text patterns are accepted"""
        variations = [
            # Different spacing and formatting
            """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""",
            
            # Different section formatting
            """# Today's Meal Nutritional Analysis

**Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

**Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""",
            
            # With additional content
            """# Today's Meal Nutritional Analysis

Based on the calculations from HowToCook ingredients:

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g
  (需要增加碳水化合物摄入)

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g  
  (蛋白质摄入过多)

Additional notes: Consider adding more carbohydrate sources.""",
        ]
        
        for i, variation in enumerate(variations):
            with self.subTest(variation=i):
                agent_workspace = self.temp_path / f"agent_variation_{i}"
                agent_workspace.mkdir()
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(variation)
                
                success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
                self.assertTrue(success, f"Variation {i} should pass: {error}")
    
    def test_wrong_calculations_fail(self):
        """Test that significantly wrong calculations fail"""
        wrong_cases = [
            # Completely wrong numbers
            ("""# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 200g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""", "Carbohydrate calculation incorrect"),
            
            # Wrong protein calculation
            ("""# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 200g""", "Protein calculation incorrect"),
            
            # Wrong assessment
            ("""# Today's Meal Nutritional Analysis

- **Carbohydrates**: Meets expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""", "should be 'below expectations'"),
        ]
        
        for i, (analysis, expected_error) in enumerate(wrong_cases):
            with self.subTest(case=i):
                agent_workspace = self.temp_path / f"agent_wrong_{i}"
                agent_workspace.mkdir()
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(analysis)
                
                success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
                self.assertFalse(success, f"Wrong case {i} should fail")
                self.assertIn(expected_error.lower(), error.lower(), f"Error should mention {expected_error}")
    
    def test_missing_format_elements_fail(self):
        """Test that missing required format elements fail"""
        format_issues = [
            # Missing heading
            ("""- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g
- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g""", "Missing required heading"),
            
            # Missing expected/actual format
            ("""# Today's Meal Nutritional Analysis
- **Carbohydrates**: Below expectations
- **Protein**: Excessive intake""", "Missing Expected/Actual format"),
        ]
        
        for i, (analysis, expected_error) in enumerate(format_issues):
            with self.subTest(case=i):
                agent_workspace = self.temp_path / f"agent_format_issue_{i}"
                agent_workspace.mkdir()
                
                with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
                    f.write(analysis)
                
                success, error = check_local_flexible(str(agent_workspace), str(self.gt_workspace), {})
                self.assertFalse(success, f"Format issue {i} should fail")
                self.assertIn(expected_error.lower(), error.lower(), f"Error should mention {expected_error}")

def run_flexible_tests():
    """Run all flexible evaluation tests"""
    
    print("🧪 Flexible Evaluation System Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestFlexibleEvaluation))
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Summary
    print("\n" + "=" * 60)
    if result.wasSuccessful():
        print(f"✅ ALL FLEXIBLE EVALUATION TESTS PASSED ({result.testsRun} tests)")
        print("🎯 System ready to evaluate agent outputs with tolerance")
    else:
        print(f"❌ SOME TESTS FAILED: {len(result.failures)} failures, {len(result.errors)} errors")
        for test, error in result.failures + result.errors:
            print(f"   {test}: {error.split(chr(10))[0]}")
    
    return result.wasSuccessful()

if __name__ == "__main__":
    success = run_flexible_tests()
    sys.exit(0 if success else 1)