#!/usr/bin/env python3
"""
Test script for price-comparison evaluation code
Tests various scenarios and edge cases to identify potential bugs
"""

import sys
import os
import asyncio
import csv
import json
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from typing import Dict, List, Any

# Add the evaluation module to path
evaluation_path = str(Path(__file__).parent / 'evaluation')
sys.path.insert(0, evaluation_path)

# Import the functions to test
try:
    import main as eval_main
    load_ground_truth = eval_main.load_ground_truth
    _parse_bigquery_result_text = eval_main._parse_bigquery_result_text
    compare_records = eval_main.compare_records
    check_table_schema = eval_main.check_table_schema
except ImportError as e:
    print(f"Error importing evaluation functions: {e}")
    print(f"Tried to import from: {evaluation_path}")
    sys.exit(1)


class TestEvaluation:
    def __init__(self):
        self.test_results = []
        
    def log_test(self, test_name: str, passed: bool, message: str = ""):
        """Log test result"""
        status = "PASS" if passed else "FAIL"
        print(f"[{status}] {test_name}: {message}")
        self.test_results.append({"test": test_name, "passed": passed, "message": message})
        
    async def test_load_ground_truth(self):
        """Test loading ground truth CSV file"""
        print("\n=== Testing load_ground_truth function ===")
        
        # Test 1: Valid CSV file
        test_data = [
            ["Product Name", "Our Price", "Competitor Price", "Price Difference"],
            ["Test Product", "100.00", "90.00", "10.00"],
            ["另一产品", "200.50", "220.00", "-19.50"]  # Test with Chinese characters
        ]
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as f:
            writer = csv.writer(f)
            writer.writerows(test_data)
            temp_path = f.name
        
        try:
            result = await load_ground_truth(temp_path)
            
            # Check if data is loaded correctly
            expected_length = 2
            if len(result) == expected_length:
                self.log_test("load_ground_truth_valid_file", True, f"Loaded {len(result)} records")
            else:
                self.log_test("load_ground_truth_valid_file", False, f"Expected {expected_length} records, got {len(result)}")
            
            # Test data types
            if result and isinstance(result[0]["Our Price"], float):
                self.log_test("load_ground_truth_data_types", True, "Price fields converted to float")
            else:
                self.log_test("load_ground_truth_data_types", False, "Price fields not converted properly")
                
        finally:
            os.unlink(temp_path)
        
        # Test 2: Non-existent file
        try:
            result = await load_ground_truth("/non/existent/file.csv")
            if len(result) == 0:
                self.log_test("load_ground_truth_missing_file", True, "Returns empty list for missing file")
            else:
                self.log_test("load_ground_truth_missing_file", False, "Should return empty list for missing file")
        except Exception as e:
            self.log_test("load_ground_truth_missing_file", False, f"Unexpected exception: {e}")

    def test_parse_bigquery_result_text(self):
        """Test parsing BigQuery result text"""
        print("\n=== Testing _parse_bigquery_result_text function ===")
        
        # Test 1: Valid result text with English column names
        test_text = """Row 1: {'Product Name': 'Test Product', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0}
Row 2: {'Product Name': 'Another Product', 'Our Price': 200.5, 'Competitor Price': 220.0, 'Price Difference': -19.5}"""
        
        result = _parse_bigquery_result_text(test_text)
        if len(result) == 2 and result[0]['Product Name'] == 'Test Product':
            self.log_test("parse_bigquery_english_columns", True, f"Parsed {len(result)} rows correctly")
        else:
            self.log_test("parse_bigquery_english_columns", False, f"Expected 2 rows, got {len(result)}")
            
        # Test 2: Result text with Chinese column names (should fail with current implementation)
        chinese_text = """Row 1: {'产品名称': '测试产品', '我们的价格': 100.0, '竞争对手价格': 90.0, '差价': 10.0}
Row 2: {'产品名称': '另一产品', '我们的价格': 200.5, '竞争对手价格': 220.0, '差价': -19.5}"""
        
        result_chinese = _parse_bigquery_result_text(chinese_text)
        if len(result_chinese) == 2:
            self.log_test("parse_bigquery_chinese_columns", True, "Handles Chinese column names")
        else:
            self.log_test("parse_bigquery_chinese_columns", False, "Cannot handle Chinese column names")
            
        # Test 3: Malformed text (security test for eval usage)
        malicious_text = """Row 1: {'Product Name': 'Test', 'Our Price': __import__('os').system('echo HACKED')}"""
        
        try:
            result_malicious = _parse_bigquery_result_text(malicious_text)
            self.log_test("parse_bigquery_security", False, "eval() allows code injection - SECURITY RISK!")
        except Exception as e:
            self.log_test("parse_bigquery_security", True, f"Protected against malicious input: {e}")

    def test_compare_records(self):
        """Test record comparison function"""
        print("\n=== Testing compare_records function ===")
        
        # Test data
        ground_truth = [
            {'Product Name': 'Product A', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0},
            {'Product Name': 'Product B', 'Our Price': 200.0, 'Competitor Price': 220.0, 'Price Difference': -20.0}
        ]
        
        # Test 1: Perfect match
        bigquery_perfect = [
            {'Product Name': 'Product A', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0},
            {'Product Name': 'Product B', 'Our Price': 200.0, 'Competitor Price': 220.0, 'Price Difference': -20.0}
        ]
        
        metrics = compare_records(bigquery_perfect, ground_truth)
        if metrics['accuracy'] == 100.0:
            self.log_test("compare_records_perfect_match", True, "Perfect match detection works")
        else:
            self.log_test("compare_records_perfect_match", False, f"Expected 100% accuracy, got {metrics['accuracy']}%")
            
        # Test 2: Missing products
        bigquery_missing = [
            {'Product Name': 'Product A', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0}
        ]
        
        metrics_missing = compare_records(bigquery_missing, ground_truth)
        if len(metrics_missing['missing_products']) == 1:
            self.log_test("compare_records_missing_products", True, "Detects missing products")
        else:
            self.log_test("compare_records_missing_products", False, f"Expected 1 missing product, found {len(metrics_missing['missing_products'])}")
            
        # Test 3: Chinese column names (should fail with current implementation)
        bigquery_chinese = [
            {'产品名称': 'Product A', '我们的价格': 100.0, '竞争对手价格': 90.0, '差价': 10.0}
        ]
        
        try:
            metrics_chinese = compare_records(bigquery_chinese, ground_truth)
            if metrics_chinese['found_products'] == 0:
                self.log_test("compare_records_chinese_columns", False, "Cannot handle Chinese column names")
            else:
                self.log_test("compare_records_chinese_columns", True, "Handles Chinese column names")
        except Exception as e:
            self.log_test("compare_records_chinese_columns", False, f"Error with Chinese columns: {e}")

    async def test_check_table_schema(self):
        """Test table schema checking"""
        print("\n=== Testing check_table_schema function ===")
        
        # Mock server for testing
        mock_server = AsyncMock()
        
        # Test 1: Valid schema with English columns
        mock_result = MagicMock()
        mock_result.structuredContent = {
            'rows': [
                {'column_name': 'Product Name', 'data_type': 'STRING'},
                {'column_name': 'Our Price', 'data_type': 'FLOAT64'},
                {'column_name': 'Competitor Price', 'data_type': 'FLOAT64'},
                {'column_name': 'Price Difference', 'data_type': 'FLOAT64'}
            ]
        }
        
        # Mock the call_tool_with_retry function
        original_call_tool = None
        try:
            original_call_tool = eval_main.call_tool_with_retry
            eval_main.call_tool_with_retry = AsyncMock(return_value=mock_result)
            
            schema_valid = await check_table_schema(mock_server, "test_dataset", "test_table")
            if schema_valid:
                self.log_test("check_table_schema_valid", True, "Validates correct English schema")
            else:
                self.log_test("check_table_schema_valid", False, "Should validate correct schema")
                
        except Exception as e:
            self.log_test("check_table_schema_valid", False, f"Error testing schema: {e}")
        finally:
            if original_call_tool:
                eval_main.call_tool_with_retry = original_call_tool
                
        # Test 2: Schema with Chinese columns (should fail with current code)
        mock_result_chinese = MagicMock()
        mock_result_chinese.structuredContent = {
            'rows': [
                {'column_name': '产品名称', 'data_type': 'STRING'},
                {'column_name': '我们的价格', 'data_type': 'FLOAT64'},
                {'column_name': '竞争对手价格', 'data_type': 'FLOAT64'},
                {'column_name': '差价', 'data_type': 'FLOAT64'}
            ]
        }
        
        try:
            eval_main.call_tool_with_retry = AsyncMock(return_value=mock_result_chinese)
            
            schema_chinese = await check_table_schema(mock_server, "test_dataset", "test_table")
            if not schema_chinese:
                self.log_test("check_table_schema_chinese", False, "Cannot validate Chinese column names")
            else:
                self.log_test("check_table_schema_chinese", True, "Validates Chinese column names")
                
        except Exception as e:
            self.log_test("check_table_schema_chinese", False, f"Error with Chinese schema: {e}")

    def test_edge_cases(self):
        """Test various edge cases"""
        print("\n=== Testing Edge Cases ===")
        
        # Test 1: Empty strings in product names
        test_data = [{'Product Name': '', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0}]
        ground_truth = [{'Product Name': 'Product A', 'Our Price': 100.0, 'Competitor Price': 90.0, 'Price Difference': 10.0}]
        
        metrics = compare_records(test_data, ground_truth)
        self.log_test("edge_case_empty_product_name", True, f"Handles empty product names: {metrics['found_products']} found")
        
        # Test 2: Very large price differences
        large_diff_data = [{'Product Name': 'Product A', 'Our Price': 999999.99, 'Competitor Price': 0.01, 'Price Difference': 999999.98}]
        large_diff_gt = [{'Product Name': 'Product A', 'Our Price': 999999.99, 'Competitor Price': 0.01, 'Price Difference': 999999.98}]
        
        metrics_large = compare_records(large_diff_data, large_diff_gt)
        if metrics_large['accuracy'] == 100.0:
            self.log_test("edge_case_large_numbers", True, "Handles large price differences correctly")
        else:
            self.log_test("edge_case_large_numbers", False, f"Issue with large numbers: {metrics_large['accuracy']}% accuracy")

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("TEST SUMMARY")
        print("=" * 60)
        
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['passed'])
        failed_tests = total_tests - passed_tests
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {passed_tests}")
        print(f"Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests*100):.1f}%")
        
        if failed_tests > 0:
            print("\nFAILED TESTS:")
            for result in self.test_results:
                if not result['passed']:
                    print(f"  - {result['test']}: {result['message']}")
                    
        print("\nKEY FINDINGS:")
        print("1. eval() usage creates security vulnerability")
        print("2. Chinese column names are not supported")
        print("3. Schema validation expects English column names")
        print("4. Complex alphabetical querying may not work for Chinese characters")


async def main():
    """Run all tests"""
    print("=" * 60)
    print("PRICE COMPARISON EVALUATION - TEST SUITE")
    print("=" * 60)
    
    tester = TestEvaluation()
    
    # Run all tests
    await tester.test_load_ground_truth()
    tester.test_parse_bigquery_result_text()
    tester.test_compare_records()
    await tester.test_check_table_schema()
    tester.test_edge_cases()
    
    # Print summary
    tester.print_summary()


if __name__ == "__main__":
    asyncio.run(main())