#!/usr/bin/env python3
"""
Unit tests for individual evaluation components
Tests specific functions and edge cases in isolation
"""

import sys
import unittest
import tempfile
import pandas as pd
import numpy as np
from pathlib import Path

# Add evaluation directory to Python path
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

# Import evaluation functions
try:
    from check_local_improved import (
        check_local, 
        check_numerical_columns_with_tolerance,
        check_non_numerical_columns_exact,
        EvaluationError
    )
    IMPROVED_AVAILABLE = True
except ImportError:
    from check_local_enhanced import check_local
    IMPROVED_AVAILABLE = False

class TestLocalValidation(unittest.TestCase):
    """Test local file validation functions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
        
        # Create sample valid data
        self.valid_data = {
            'Time': ['2023-01', '2023-02', '2023-03'] * 3,
            'Appliance types': ['Household Refrigerator'] * 3 + ['Air Conditioner'] * 3 + ['Household Washing Machines'] * 3,
            'Current Period Sales(Ten Thousand Units)': [100.0, 150.0, 200.0] * 3,
            'Accumulated Sales (Ten Thousand Units)': [100.0, 250.0, 450.0] * 3,
            'Year-on-Year Growth (%)': [5.5, 10.2, -2.1] * 3,
            'Accumulated Growth (%)': [5.5, 7.8, 3.2] * 3
        }
        
        # Create ground truth workspace
        self.gt_workspace = self.temp_path / "groundtruth"
        self.gt_workspace.mkdir()
        pd.DataFrame(self.valid_data).to_excel(self.gt_workspace / "Processed.xlsx", index=False)
    
    def tearDown(self):
        """Clean up test fixtures"""
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_perfect_file_passes(self):
        """Test that perfect file passes validation"""
        # Create agent workspace with identical data
        agent_workspace = self.temp_path / "agent_perfect"
        agent_workspace.mkdir()
        pd.DataFrame(self.valid_data).to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace))
        self.assertTrue(success, f"Perfect file should pass: {error}")
    
    def test_missing_file_fails(self):
        """Test that missing file fails validation"""
        agent_workspace = self.temp_path / "agent_missing"
        agent_workspace.mkdir()
        # Don't create the file
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace))
        self.assertFalse(success)
        self.assertIn("not found", error.lower())
    
    def test_missing_columns_fails(self):
        """Test that missing required columns fails validation"""
        agent_workspace = self.temp_path / "agent_missing_cols"
        agent_workspace.mkdir()
        
        # Create data with missing columns
        incomplete_data = {
            'Time': ['2023-01', '2023-02'],
            'Appliance types': ['Household Refrigerator', 'Air Conditioner'],
            'Wrong Column': [100.0, 150.0]  # Missing required columns
        }
        pd.DataFrame(incomplete_data).to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace))
        self.assertFalse(success)
        self.assertIn("missing", error.lower())
    
    def test_missing_appliances_fails(self):
        """Test that missing appliance types fails validation"""
        agent_workspace = self.temp_path / "agent_missing_appliances"
        agent_workspace.mkdir()
        
        # Create data with only 2 of 3 appliance types
        incomplete_appliances = self.valid_data.copy()
        incomplete_appliances = {k: v[:6] for k, v in incomplete_appliances.items()}  # Only first 2 appliance types
        
        pd.DataFrame(incomplete_appliances).to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace))
        self.assertFalse(success)
        self.assertIn("missing appliance", error.lower())
    
    def test_wrong_data_values_fails(self):
        """Test that wrong data values fail validation"""
        agent_workspace = self.temp_path / "agent_wrong_values"
        agent_workspace.mkdir()
        
        # Create data with wrong values
        wrong_data = self.valid_data.copy()
        wrong_data['Current Period Sales(Ten Thousand Units)'] = [999.0] * 9  # All wrong values
        
        pd.DataFrame(wrong_data).to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(self.gt_workspace))
        self.assertFalse(success)
    
    @unittest.skipUnless(IMPROVED_AVAILABLE, "Improved evaluation not available")
    def test_floating_point_tolerance(self):
        """Test floating-point tolerance in improved evaluation"""
        agent_workspace = self.temp_path / "agent_tolerance"
        agent_workspace.mkdir()
        
        # Create data with tiny differences (within tolerance)
        tolerance_data = self.valid_data.copy()
        tolerance_data['Current Period Sales(Ten Thousand Units)'] = [
            x + 1e-7 for x in tolerance_data['Current Period Sales(Ten Thousand Units)']
        ]
        
        pd.DataFrame(tolerance_data).to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        # Should pass with default tolerance
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), numerical_tolerance=1e-6)
        self.assertTrue(success, f"Small differences should be accepted within tolerance: {error}")
        
        # Should fail with very strict tolerance
        success, error = check_local(str(agent_workspace), str(self.gt_workspace), numerical_tolerance=1e-8)
        self.assertFalse(success, "Should fail with very strict tolerance")

class TestNumericalTolerance(unittest.TestCase):
    """Test numerical tolerance functions specifically"""
    
    @unittest.skipUnless(IMPROVED_AVAILABLE, "Improved evaluation not available")
    def test_numerical_tolerance_function(self):
        """Test the numerical tolerance checking function directly"""
        # Create test dataframes
        base_data = pd.DataFrame({
            'Current Period Sales(Ten Thousand Units)': [100.0, 150.0, 200.0],
            'Accumulated Sales (Ten Thousand Units)': [100.0, 250.0, 450.0],
            'Year-on-Year Growth (%)': [5.5, 10.2, -2.1],
            'Accumulated Growth (%)': [5.5, 7.8, 3.2]
        })
        
        # Exact match
        exact_data = base_data.copy()
        success, errors = check_numerical_columns_with_tolerance(exact_data, base_data, tolerance=1e-6)
        self.assertTrue(success, f"Exact match should pass: {errors}")
        
        # Within tolerance
        within_tolerance = base_data.copy()
        within_tolerance.iloc[0, 0] += 1e-7  # Very small difference
        success, errors = check_numerical_columns_with_tolerance(within_tolerance, base_data, tolerance=1e-6)
        self.assertTrue(success, f"Within tolerance should pass: {errors}")
        
        # Outside tolerance
        outside_tolerance = base_data.copy()
        outside_tolerance.iloc[0, 0] += 0.01  # Large difference
        success, errors = check_numerical_columns_with_tolerance(outside_tolerance, base_data, tolerance=1e-6)
        self.assertFalse(success, "Outside tolerance should fail")
    
    @unittest.skipUnless(IMPROVED_AVAILABLE, "Improved evaluation not available")
    def test_categorical_exact_match(self):
        """Test exact matching for categorical columns"""
        base_data = pd.DataFrame({
            'Time': ['2023-01', '2023-02', '2023-03'],
            'Appliance types': ['Household Refrigerator', 'Air Conditioner', 'Household Washing Machines']
        })
        
        # Exact match
        success, errors = check_non_numerical_columns_exact(base_data, base_data)
        self.assertTrue(success, f"Exact match should pass: {errors}")
        
        # Different values
        different_data = base_data.copy()
        different_data.iloc[0, 0] = '2023-12'  # Different time
        success, errors = check_non_numerical_columns_exact(different_data, base_data)
        self.assertFalse(success, "Different categorical values should fail")

class TestEdgeCases(unittest.TestCase):
    """Test edge cases and error conditions"""
    
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)
    
    def tearDown(self):
        import shutil
        shutil.rmtree(self.temp_dir)
    
    def test_nonexistent_workspace(self):
        """Test handling of non-existent workspace"""
        success, error = check_local("/nonexistent/path", "/also/nonexistent")
        self.assertFalse(success)
        self.assertIn("not found", error.lower())
    
    def test_corrupted_excel_file(self):
        """Test handling of corrupted Excel file"""
        agent_workspace = self.temp_path / "agent_corrupted"
        agent_workspace.mkdir()
        
        # Create fake Excel file with invalid content
        with open(agent_workspace / "Processed.xlsx", "w") as f:
            f.write("This is not an Excel file")
        
        gt_workspace = self.temp_path / "gt"
        gt_workspace.mkdir()
        pd.DataFrame({'A': [1]}).to_excel(gt_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(gt_workspace))
        self.assertFalse(success)
    
    def test_empty_excel_file(self):
        """Test handling of empty Excel file"""
        agent_workspace = self.temp_path / "agent_empty"
        agent_workspace.mkdir()
        
        # Create empty DataFrame
        pd.DataFrame().to_excel(agent_workspace / "Processed.xlsx", index=False)
        
        gt_workspace = self.temp_path / "gt"
        gt_workspace.mkdir()
        valid_data = {
            'Time': ['2023-01'],
            'Appliance types': ['Household Refrigerator'],
            'Current Period Sales(Ten Thousand Units)': [100.0],
            'Accumulated Sales (Ten Thousand Units)': [100.0],
            'Year-on-Year Growth (%)': [5.5],
            'Accumulated Growth (%)': [5.5]
        }
        pd.DataFrame(valid_data).to_excel(gt_workspace / "Processed.xlsx", index=False)
        
        success, error = check_local(str(agent_workspace), str(gt_workspace))
        self.assertFalse(success)

def run_unit_tests():
    """Run all unit tests with colored output"""
    
    print("🧪 Excel Data Transformation - Unit Tests")
    print("=" * 60)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add test classes
    suite.addTests(loader.loadTestsFromTestCase(TestLocalValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestNumericalTolerance))
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