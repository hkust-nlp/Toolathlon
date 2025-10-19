#!/usr/bin/env python3
"""
Test the evaluation logic in check_local.py.
Mainly tests the handling of blank rows and the reasonableness of Excel format checking.
"""

import pandas as pd
import numpy as np
import tempfile
import os
from pathlib import Path
import sys

# Add the evaluation directory to sys.path
# Correct the path to be relative to the script's location
evaluation_path = Path(__file__).parent / 'evaluation'
sys.path.append(str(evaluation_path.resolve()))
from check_local import check_excel_format, check_data_accuracy, check_local

def create_test_excel_data():
    """Create test Excel data simulating the standard format."""
    # Standard format data (with blank rows)
    standard_data = [
        ['Department', 'Report Period'],
        ['R&D Department', '2025-04 to 2025-06'],
        [np.nan, np.nan],  # blank row
        ['Month', 'Total Amount'],
        ['2025-04', 326.72],
        ['2025-05', 404.56],
        ['2025-06', 353.15],
        [np.nan, np.nan],  # blank row
        ['Total', np.nan],
        ['Total Amount: CNY 1084.43', 1084.43]
    ]
    
    # Compact format data (no blank rows)
    compact_data = [
        ['Department', 'Report Period'],
        ['R&D Department', '2025-04 to 2025-06'],
        ['Month', 'Total Amount'],
        ['2025-04', 326.72],
        ['2025-05', 404.56],
        ['2025-06', 353.15],
        ['Total', np.nan],
        ['Total Amount: CNY 1084.43', 1084.43]
    ]
    
    return standard_data, compact_data

def test_excel_format_with_standard_data():
    """Test Excel data in standard format (with blank rows)."""
    print("=== Test 1: Standard format (with blank rows) ===")
    standard_data, _ = create_test_excel_data()
    df = pd.DataFrame(standard_data)
    
    # The check_excel_format function expects more rows, let's align with its expectation
    # The original groundtruth has 10 rows, let's simulate that
    # The check logic expects at least 8 rows.
    # Let's align the test data to what check_excel_format expects.
    # The logic checks iloc[0], iloc[1], iloc[3], iloc[4-6], iloc[7]
    # This means it expects a fixed structure with at least 8 rows.
    
    # Let's create data that will fail and pass based on current logic
    failing_df = pd.DataFrame(df.values) # Re-index
    
    result, message = check_excel_format(failing_df)
    print(f"Check result: {result}")
    print(f"Message: {message}")
    print(f"DataFrame shape: {failing_df.shape}")
    print("DataFrame content:")
    print(failing_df)
    print()
    
    return result

def test_excel_format_with_compact_data():
    """Test Excel data in compact format (no blank rows)."""
    print("=== Test 2: Compact format (no blank rows) ===")
    _, compact_data = create_test_excel_data()
    df = pd.DataFrame(compact_data)
    
    result, message = check_excel_format(df)
    print(f"Check result: {result}")
    print(f"Message: {message}")
    print(f"DataFrame shape: {df.shape}")
    print("DataFrame content:")
    print(df)
    print()
    
    return result

def test_dropna_approach():
    """Test the approach of removing blank rows using dropna."""
    print("=== Test 3: Remove blank rows using dropna ===")
    standard_data, _ = create_test_excel_data()
    df = pd.DataFrame(standard_data)
    
    print("Original DataFrame:")
    print(df)
    print(f"Original shape: {df.shape}")
    
    # Method 1: Remove rows that are completely blank
    df_dropna_all = df.dropna(how='all').reset_index(drop=True)
    print("\nAfter dropna(how='all').reset_index(drop=True):")
    print(df_dropna_all)
    print(f"New shape: {df_dropna_all.shape}")
    
    # Test format check after removing blank rows
    print("\n--- Test format check after removing blank rows ---")
    result, message = check_excel_format(df_dropna_all)
    print(f"Check result: {result}")
    print(f"Message: {message}")
    print()

def analyze_current_issues():
    """Analyze current issues in the evaluation code."""
    print("=== Analysis of Current Evaluation Code Issues ===")
    
    issues = [
        "1. Hardcoded row indices: The code uses `iloc` to check fixed row indices, making it very sensitive to blank rows.",
        "2. Blank row handling: `check_excel_format` currently cannot handle the standard format with blank rows, as it expects a compact 8-row DataFrame.",
        "3. Poor flexibility: Any deviation from the expected 8-row structure will cause the check to fail, even if the data is semantically correct."
    ]
    
    for issue in issues:
        print(issue)
    
    print("\n=== Suggested Improvements ===")
    suggestions = [
        "1. **Preprocess the DataFrame**: Before checking, use `df.dropna(how='all').reset_index(drop=True)` to remove all completely blank rows and reset the index.",
        "2. **Modify the checking logic**: Adjust the row indices in the `check_excel_format` function to match the structure after cleaning.",
        "3. **Increase robustness**: Make the checking logic more adaptable to different, but semantically equivalent, layouts."
    ]
    
    for suggestion in suggestions:
        print(suggestion)
    print()

def main():
    """Run all tests."""
    print("Start testing the evaluation logic in check_local.py\n")
    
    # Run all tests
    test1_result = test_excel_format_with_standard_data()
    test2_result = test_excel_format_with_compact_data()  
    
    test_dropna_approach()
    analyze_current_issues()
    
    # Summarize test results
    print("=== Test Summary ===")
    print(f"Standard format (with blank rows) check: {'PASS' if test1_result else 'FAIL'}")
    print(f"Compact format (no blank rows) check: {'PASS' if test2_result else 'FAIL'}")
    
    if test1_result and not test2_result:
        print("\n✅ Conclusion: The code only accepts the format with blank rows, which is not expected, as it should be able to handle cleaned data.")
    elif not test1_result and test2_result:
        print("\n✅ Conclusion: The code only accepts the compact format and rejects the standard answer with blank rows. This is the main issue of the current implementation.") 
    elif test1_result and test2_result:
        print("\n✅ The code can handle both formats, which is ideal.")
    else:
        print("\n❌ Conclusion: There is a serious problem; neither format can be handled correctly.")
    
    print("\nThe core issue is that the `check_excel_format` function in `check_local` does not preprocess the input DataFrame (such as removing blank rows), causing hardcoded row indices to fail.")

if __name__ == "__main__":
    # Add the parent directory to sys.path to find the 'evaluation' module
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    main() 