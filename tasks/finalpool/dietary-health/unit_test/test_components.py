#!/usr/bin/env python3
"""
Unit tests for dietary-health evaluation components
Tests specific functions and edge cases in isolation
"""

import sys
import unittest
import tempfile
import os
import hashlib
import re
from pathlib import Path

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

# Import evaluation functions
from check_local import check_local

class TestCheckLocal(unittest.TestCase):
    """Test the check_local function components"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create ground truth workspace
        self.gt_workspace = self.temp_path / "groundtruth"
        self.gt_workspace.mkdir()
        
        # Create perfect ground truth analysis.md
        self.perfect_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g"""
        
        with open(self.gt_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(self.perfect_analysis)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_perfect_file_passes(self):
        """Test that identical file passes validation"""
        agent_workspace = self.temp_path / "agent_perfect"
        agent_workspace.mkdir()
        
        # Create identical analysis.md
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(self.perfect_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertTrue(success, f"Perfect file should pass: {error}")
        self.assertIsNone(error)
    
    def test_missing_agent_file_fails(self):
        """Test that missing analysis.md in agent workspace fails"""
        agent_workspace = self.temp_path / "agent_missing"
        agent_workspace.mkdir()
        # Don't create analysis.md
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "analysis.md file not found in agent workspace")
    
    def test_missing_groundtruth_file_fails(self):
        """Test that missing groundtruth file fails"""
        agent_workspace = self.temp_path / "agent_test"
        agent_workspace.mkdir()
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write("some content")
        
        # Empty groundtruth workspace
        empty_gt = self.temp_path / "empty_gt"
        empty_gt.mkdir()
        
        success, error = check_local(str(agent_workspace), str(empty_gt), {})
        self.assertFalse(success)
        self.assertEqual(error, "Groundtruth analysis.md file not found")
    
    def test_content_pattern_matching_passes(self):
        """Test that correct content patterns pass even with different formatting"""
        agent_workspace = self.temp_path / "agent_pattern"
        agent_workspace.mkdir()
        
        # Create analysis with same content but different formatting
        different_format = """# Nutritional Analysis Report

## Carbohydrates Analysis
Carbohydrates: Below expectations
Expected: 162.5g-195g
Actual: 135.5g

## Protein Analysis  
Protein: Excessive intake
Expected: 97.5g
Actual: 146.9g

Some additional text here."""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(different_format)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertTrue(success, f"Pattern matching should pass: {error}")
        self.assertIsNone(error)
    
    def test_missing_carbohydrate_analysis_fails(self):
        """Test that missing carbohydrate analysis fails"""
        agent_workspace = self.temp_path / "agent_no_carbs"
        agent_workspace.mkdir()
        
        # Analysis missing carbohydrate information
        incomplete_analysis = """# Today's Meal Nutritional Analysis

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g

Some other content here."""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(incomplete_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct carbohydrate analysis")
    
    def test_missing_protein_analysis_fails(self):
        """Test that missing protein analysis fails"""
        agent_workspace = self.temp_path / "agent_no_protein"
        agent_workspace.mkdir()
        
        # Analysis missing protein information
        incomplete_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

Some other content here."""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(incomplete_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct protein analysis")
    
    def test_missing_both_analyses_fails(self):
        """Test that missing both analyses fails with combined error"""
        agent_workspace = self.temp_path / "agent_no_nutrients"
        agent_workspace.mkdir()
        
        # Analysis missing both nutrients
        incomplete_analysis = """# Today's Meal Nutritional Analysis

This is just some random content without the required nutritional analysis."""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(incomplete_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct carbohydrate analysis, correct protein analysis")
    
    def test_wrong_carbohydrate_values_fails(self):
        """Test that wrong carbohydrate values fail"""
        agent_workspace = self.temp_path / "agent_wrong_carbs"
        agent_workspace.mkdir()
        
        # Analysis with wrong carbohydrate values
        wrong_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Meets expectations. Expected: 100g-150g | Actual: 120g

- **Protein**: Excessive intake. Expected: 97.5g | Actual: 146.9g"""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(wrong_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct carbohydrate analysis")
    
    def test_wrong_protein_values_fails(self):
        """Test that wrong protein values fail"""
        agent_workspace = self.temp_path / "agent_wrong_protein"
        agent_workspace.mkdir()
        
        # Analysis with wrong protein values
        wrong_analysis = """# Today's Meal Nutritional Analysis

- **Carbohydrates**: Below expectations. Expected: 162.5g-195g | Actual: 135.5g

- **Protein**: Low intake. Expected: 80g | Actual: 100g"""
        
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write(wrong_analysis)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct protein analysis")

class TestRegexPatterns(unittest.TestCase):
    """Test the regex patterns used in evaluation"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Extract the patterns from check_local.py
        self.carb_pattern = r"Carbohydrates.*?Below expectations.*?Expected:\s*162\.5g-195g.*?Actual:\s*135\.5g"
        self.protein_pattern = r"Protein.*?Excessive intake.*?Expected:\s*97\.5g.*?Actual:\s*146\.9g"
        
    def test_carbohydrate_pattern_matches_variations(self):
        """Test that carbohydrate pattern matches various formats"""
        test_cases = [
            "Carbohydrates: Below expectations. Expected: 162.5g-195g | Actual: 135.5g",
            "**Carbohydrates**: Below expectations\nExpected: 162.5g-195g\nActual: 135.5g",
            "Carbohydrates - Below expectations (Expected: 162.5g-195g, Actual: 135.5g)",
            "CARBOHYDRATES: below expectations. Expected: 162.5g-195g Actual: 135.5g"
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                match = re.search(self.carb_pattern, case, re.IGNORECASE | re.DOTALL)
                self.assertIsNotNone(match, f"Pattern should match: {case}")
    
    def test_protein_pattern_matches_variations(self):
        """Test that protein pattern matches various formats"""
        test_cases = [
            "Protein: Excessive intake. Expected: 97.5g | Actual: 146.9g",
            "**Protein**: Excessive intake\nExpected: 97.5g\nActual: 146.9g",
            "Protein - Excessive intake (Expected: 97.5g, Actual: 146.9g)",
            "PROTEIN: excessive intake. Expected: 97.5g Actual: 146.9g"
        ]
        
        for case in test_cases:
            with self.subTest(case=case):
                match = re.search(self.protein_pattern, case, re.IGNORECASE | re.DOTALL)
                self.assertIsNotNone(match, f"Pattern should match: {case}")
    
    def test_patterns_reject_wrong_values(self):
        """Test that patterns reject wrong values"""
        wrong_carb_cases = [
            "Carbohydrates: Meets expectations. Expected: 100g-150g | Actual: 120g",
            "Carbohydrates: Below expectations. Expected: 162.5g-195g | Actual: 180g",
            "Carbohydrates: Low intake. Expected: 162.5g-195g | Actual: 135.5g"
        ]
        
        for case in wrong_carb_cases:
            with self.subTest(case=case):
                match = re.search(self.carb_pattern, case, re.IGNORECASE | re.DOTALL)
                self.assertIsNone(match, f"Pattern should NOT match wrong values: {case}")
        
        wrong_protein_cases = [
            "Protein: Low intake. Expected: 97.5g | Actual: 146.9g",
            "Protein: Excessive intake. Expected: 80g | Actual: 146.9g",
            "Protein: Excessive intake. Expected: 97.5g | Actual: 100g"
        ]
        
        for case in wrong_protein_cases:
            with self.subTest(case=case):
                match = re.search(self.protein_pattern, case, re.IGNORECASE | re.DOTALL)
                self.assertIsNone(match, f"Pattern should NOT match wrong values: {case}")

class TestFileOperations(unittest.TestCase):
    """Test file operations and edge cases"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_hash_comparison_works(self):
        """Test MD5 hash comparison functionality"""
        content = "Test content for hashing"
        
        # Create two identical files
        file1 = self.temp_path / "file1.md"
        file2 = self.temp_path / "file2.md"
        
        with open(file1, "w", encoding="utf-8") as f:
            f.write(content)
        with open(file2, "w", encoding="utf-8") as f:
            f.write(content)
        
        # Calculate hashes
        with open(file1, 'rb') as f:
            hash1 = hashlib.md5(f.read()).hexdigest()
        with open(file2, 'rb') as f:
            hash2 = hashlib.md5(f.read()).hexdigest()
        
        self.assertEqual(hash1, hash2)
    
    def test_different_files_have_different_hashes(self):
        """Test that different files have different hashes"""
        file1 = self.temp_path / "file1.md"
        file2 = self.temp_path / "file2.md"
        
        with open(file1, "w", encoding="utf-8") as f:
            f.write("Content A")
        with open(file2, "w", encoding="utf-8") as f:
            f.write("Content B")
        
        with open(file1, 'rb') as f:
            hash1 = hashlib.md5(f.read()).hexdigest()
        with open(file2, 'rb') as f:
            hash2 = hashlib.md5(f.read()).hexdigest()
        
        self.assertNotEqual(hash1, hash2)
    
    def test_nonexistent_workspace_handling(self):
        """Test handling of non-existent workspace directories"""
        success, error = check_local("/nonexistent/path", "/also/nonexistent", {})
        self.assertFalse(success)
        self.assertIn("not found", error.lower())
    
    def test_empty_file_handling(self):
        """Test handling of empty analysis.md file"""
        agent_workspace = self.temp_path / "agent_empty"
        agent_workspace.mkdir()
        gt_workspace = self.temp_path / "gt"
        gt_workspace.mkdir()
        
        # Create empty files
        with open(agent_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write("")
        with open(gt_workspace / "analysis.md", "w", encoding="utf-8") as f:
            f.write("# Some content")
        
        success, error = check_local(str(agent_workspace), str(gt_workspace), {})
        self.assertFalse(success)
        self.assertEqual(error, "Analysis.md is missing: correct carbohydrate analysis, correct protein analysis")

def run_unit_tests():
    """Run all unit tests with colored output"""
    
    print("🥗 Dietary Health - Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestCheckLocal))
    suite.addTests(loader.loadTestsFromTestCase(TestRegexPatterns))
    suite.addTests(loader.loadTestsFromTestCase(TestFileOperations))
    
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