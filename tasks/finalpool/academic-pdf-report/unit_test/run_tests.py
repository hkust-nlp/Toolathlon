#!/usr/bin/env python3
"""
Enhanced end-to-end test runner for academic-pdf-report evaluation with detailed validation
"""

import sys
import subprocess
from pathlib import Path
import pandas as pd
import json
# Add evaluation directory to Python path for importing task_utils
base_dir = Path(__file__).parent
evaluation_dir = base_dir.parent / "evaluation"
sys.path.insert(0, str(evaluation_dir))

try:
    from task_utils import normalize_affiliation
except ImportError as e:
    print(f"Warning: Could not import task_utils: {e}")
# Color codes for output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    END = '\033[0m'

def colored_print(text, color=Colors.WHITE, bold=False):
    """Print colored text"""
    prefix = Colors.BOLD if bold else ""
    print(f"{prefix}{color}{text}{Colors.END}")

def validate_excel_structure(excel_path, expected_rows, expected_columns):
    """Validate Excel file structure with detailed checks"""
    colored_print(f"  📋 Validating Excel structure:", Colors.CYAN, bold=True)
    
    try:
        df = pd.read_excel(excel_path)
        
        # Check columns
        missing_cols = [col for col in expected_columns if col not in df.columns]
        extra_cols = [col for col in df.columns if col not in expected_columns]
        
        if missing_cols:
            colored_print(f"    ❌ Missing columns: {missing_cols}", Colors.RED)
            return False
        elif extra_cols:
            colored_print(f"    ⚠️  Extra columns found: {extra_cols}", Colors.YELLOW)
        else:
            colored_print(f"    ✅ All required columns present: {list(df.columns)}", Colors.GREEN)
        
        # Check row count
        if len(df) != expected_rows:
            colored_print(f"    ❌ Row count mismatch: {len(df)} (expected {expected_rows})", Colors.RED)
            return False
        else:
            colored_print(f"    ✅ Correct row count: {len(df)}", Colors.GREEN)
        
        return True
        
    except Exception as e:
        colored_print(f"    ❌ Excel reading error: {e}", Colors.RED)
        return False

def validate_data_completeness(excel_path):
    """Check data completeness with detailed field analysis"""
    colored_print(f"  📊 Validating data completeness:", Colors.CYAN, bold=True)
    
    try:
        df = pd.read_excel(excel_path)
        issues = []
        
        for idx, row in df.iterrows():
            row_issues = []
            
            # Check each field
            if pd.isna(row.get("Title")) or not str(row.get("Title", "")).strip():
                row_issues.append("Title missing")
            
            if pd.isna(row.get("First Author")) or not str(row.get("First Author", "")).strip():
                row_issues.append("Author missing")
                
            if pd.isna(row.get("Affiliation")) or not str(row.get("Affiliation", "")).strip():
                row_issues.append("Affiliation missing")
                
            if pd.isna(row.get("Personal Website")) or not str(row.get("Personal Website", "")).strip():
                row_issues.append("Website missing")
            
            if row_issues:
                issue_msg = f"Row {idx+1}: {', '.join(row_issues)}"
                issues.append(issue_msg)
                colored_print(f"    ❌ {issue_msg}", Colors.RED)
            else:
                colored_print(f"    ✅ Row {idx+1}: All fields filled", Colors.GREEN)
        
        if not issues:
            colored_print(f"    ✅ All rows have complete data", Colors.GREEN)
            return True, []
        else:
            return False, issues
            
    except Exception as e:
        colored_print(f"    ❌ Data validation error: {e}", Colors.RED)
        return False, [f"Data validation error: {e}"]

def analyze_expected_vs_actual(expected_file, excel_path, base_dir):
    """Detailed comparison of expected vs actual data"""
    colored_print(f"  🔍 Analyzing expected vs actual data:", Colors.CYAN, bold=True)
    
    try:
        # Load expected data
        with open(expected_file, 'r', encoding='utf-8') as f:
            content = f.read()
            expected_data = json.loads(content)
        
        df = pd.read_excel(excel_path)
        
        analysis_results = []
        failed_papers = []
        
        for i, expected_paper in enumerate(expected_data["papers"]):
            colored_print(f"    📄 Paper {i+1}: {expected_paper['title'][:50]}...", Colors.BLUE, bold=True)
            
            # Find matching row in Excel
            matching_row = None
            for idx, row in df.iterrows():
                if str(row.get("Title", "")).strip().lower() in expected_paper["title"].lower():
                    matching_row = row
                    break
            
            if matching_row is None:
                colored_print(f"      ❌ Paper not found in Excel", Colors.RED)
                analysis_results.append(False)
                failed_papers.append(f"Paper {i+1}: NOT FOUND")
                continue
            
            paper_valid = True
            paper_issues = []
            
            # Check author
            expected_author = expected_paper["first_author"]
            actual_author = str(matching_row.get("First Author", "")).strip()
            if actual_author.lower() == expected_author.lower():
                colored_print(f"      ✅ Author match: '{actual_author}'", Colors.GREEN)
            else:
                colored_print(f"      ❌ Author mismatch: '{actual_author}' ≠ '{expected_author}'", Colors.RED)
                paper_valid = False
                paper_issues.append("author mismatch")
            
            # Check affiliation requirements
            if "affiliation" in expected_paper:
                actual_affiliation = str(matching_row.get("Affiliation", "")).strip()
                should_contain = expected_paper["affiliation"].get("should_contain", [])
                should_not_contain = expected_paper["affiliation"].get("should_not_contain", [])
                
                colored_print(f"      🏢 Affiliation: '{actual_affiliation}'", Colors.BLUE)
                
                # Normalize for checking
                sys.path.insert(0, str(base_dir.parent / "evaluation"))
                normalized_actual = normalize_affiliation(actual_affiliation)
                
                # Check should_contain
                for required in should_contain:
                    if required.strip():
                        normalized_required = normalize_affiliation(required)
                        if normalized_required in normalized_actual:
                            colored_print(f"        ✅ Contains required: '{required}'", Colors.GREEN)
                        else:
                            colored_print(f"        ❌ Missing required: '{required}'", Colors.RED)
                            paper_valid = False
                            paper_issues.append(f"missing {required}")
                
                # Check should_not_contain
                for forbidden in should_not_contain:
                    if forbidden.strip():
                        normalized_forbidden = normalize_affiliation(forbidden)
                        if normalized_forbidden not in normalized_actual:
                            colored_print(f"        ✅ Correctly excludes: '{forbidden}'", Colors.GREEN)
                        else:
                            colored_print(f"        ❌ Contains forbidden: '{forbidden}'", Colors.RED)
                            paper_valid = False
                            paper_issues.append(f"contains forbidden {forbidden}")
            
            # Check website
            expected_website = expected_paper["personal_website"]
            actual_website = str(matching_row.get("Personal Website", "")).strip()
            if expected_website.lower() in actual_website.lower():
                colored_print(f"      ✅ Website match: '{actual_website}'", Colors.GREEN)
            else:
                colored_print(f"      ❌ Website mismatch: '{actual_website}' should contain '{expected_website}'", Colors.RED)
                paper_valid = False
                paper_issues.append("website mismatch")
            
            analysis_results.append(paper_valid)
            
            if paper_valid:
                colored_print(f"    ✅ Paper {i+1}: VALID", Colors.GREEN, bold=True)
            else:
                colored_print(f"    ❌ Paper {i+1}: INVALID", Colors.RED, bold=True)
                failed_papers.append(f"Paper {i+1}: INVALID ({', '.join(paper_issues)})")
        
        return all(analysis_results), failed_papers
        
    except Exception as e:
        colored_print(f"    ❌ Analysis error: {e}", Colors.RED)
        return False, [f"Analysis error: {e}"]

def validate_expected_failures(actual_failures, expected_failures, validation_type):
    """Validate that actual failures match expected failures"""
    colored_print(f"  🔍 Validating expected {validation_type} failures:", Colors.YELLOW, bold=True)
    
    if not expected_failures:
        colored_print(f"    ℹ️  No expected failures specified for {validation_type}", Colors.BLUE)
        return True
    
    validation_passed = True
    
    for expected_failure in expected_failures:
        found = False
        for actual_failure in actual_failures:
            if expected_failure.lower() in actual_failure.lower():
                found = True
                colored_print(f"    ✅ Found expected failure: '{expected_failure}'", Colors.GREEN)
                break
        
        if not found:
            colored_print(f"    ❌ Missing expected failure: '{expected_failure}'", Colors.RED)
            validation_passed = False
    
    # Check for unexpected failures
    for actual_failure in actual_failures:
        expected = False
        for expected_failure in expected_failures:
            if expected_failure.lower() in actual_failure.lower():
                expected = True
                break
        
        if not expected:
            colored_print(f"    ⚠️  Unexpected failure: '{actual_failure}'", Colors.YELLOW)
    
    return validation_passed

def run_evaluation_tests():
    """Run enhanced evaluation on all test workspaces"""
    
    base_dir = Path(__file__).parent
    evaluation_script = base_dir.parent / "evaluation" / "main.py"
    groundtruth_workspace = base_dir.parent / "groundtruth_workspace"
    expected_file = groundtruth_workspace / "expected_top7.json"
    
    test_cases = [
        ("test_workspace_1", "Perfect Excel file", True, {}),
        ("test_workspace_2", "Missing affiliations", False, {
            "expected_failures": {
                "data_completeness": ["Row 2: Affiliation missing", "Row 4: Affiliation missing"],
                "content_accuracy": ["Paper 2: INVALID", "Paper 4: INVALID"],
                "official_evaluation": ["Model Immunization", "Learning with Expected Signatures"]
            }
        }),
        ("test_workspace_3", "Wrong affiliations (forbidden content)", False, {
            "expected_failures": {
                "data_completeness": ["Row 2: Affiliation missing", "Row 4: Affiliation missing"],
                "content_accuracy": ["Paper 1: INVALID", "Paper 2: INVALID", "Paper 4: INVALID", "Paper 5: INVALID"],
                "official_evaluation": ["Strategy Coopetition", "Model Immunization", "Learning with Expected Signatures", "AutoML-Agent"]
            }
        }),
        ("test_workspace_4", "Missing required affiliation parts", False, {
            "expected_failures": {
                "data_completeness": ["Row 2: Affiliation missing", "Row 4: Affiliation missing"],
                "content_accuracy": ["Paper 1: INVALID", "Paper 2: INVALID", "Paper 3: INVALID", "Paper 4: INVALID", "Paper 5: INVALID"],
                "official_evaluation": ["Strategy Coopetition", "Model Immunization", "Flowing Datasets", "Learning with Expected Signatures", "AutoML-Agent"]
            }
        }),
        ("test_workspace_5", "Wrong structure", False, {
            "expected_failures": {
                "structure": ["Missing columns"],
                "official_evaluation": ["missing required columns"]
            }
        }),
    ]
    
    colored_print("🚀 Running Enhanced End-to-End Evaluation Tests", Colors.MAGENTA, bold=True)
    colored_print("=" * 80, Colors.WHITE)
    
    overall_results = []
    
    for workspace_name, description, expected_result, test_config in test_cases:
        colored_print(f"\n🧪 Testing {workspace_name}: {description}", Colors.CYAN, bold=True)
        colored_print("-" * 60, Colors.WHITE)
        
        agent_workspace = base_dir / workspace_name
        excel_file = agent_workspace / "paper_initial.xlsx"
        
        # Detailed pre-validation with failure tracking
        detailed_results = {
            "structure_valid": False,
            "data_complete": False,
            "content_accurate": False,
            "evaluation_passed": False,
            "actual_failures": {
                "structure": [],
                "data_completeness": [],
                "content_accuracy": [],
                "official_evaluation": []
            }
        }
        
        # 1. Structure validation
        if excel_file.exists():
            expected_columns = ["Title", "First Author", "Affiliation", "Personal Website"]
            detailed_results["structure_valid"] = validate_excel_structure(excel_file, 7, expected_columns)
            if not detailed_results["structure_valid"]:
                detailed_results["actual_failures"]["structure"].append("Missing columns")
        else:
            colored_print(f"  ❌ Excel file not found: {excel_file}", Colors.RED)
            detailed_results["actual_failures"]["structure"].append("File not found")
        
        # 2. Data completeness validation
        if detailed_results["structure_valid"]:
            detailed_results["data_complete"], completeness_failures = validate_data_completeness(excel_file)
            detailed_results["actual_failures"]["data_completeness"] = completeness_failures
        
        # 3. Content accuracy validation  
        if detailed_results["data_complete"]:
            detailed_results["content_accurate"], accuracy_failures = analyze_expected_vs_actual(expected_file, excel_file, base_dir)
            detailed_results["actual_failures"]["content_accuracy"] = accuracy_failures
        
        # 4. Run official evaluation
        colored_print(f"  ⚙️ Running official evaluation script:", Colors.CYAN, bold=True)
        cmd = [
            sys.executable,
            str(evaluation_script),
            "--agent_workspace", str(agent_workspace),
            "--groundtruth_workspace", str(groundtruth_workspace)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            exit_code = result.returncode
            detailed_results["evaluation_passed"] = (exit_code == 0)
            
            # Extract failed papers from official evaluation output
            output_lines = result.stdout.split('\n')
            for line in output_lines:
                if '✗' in line and ('validation failed' in line or 'not filled' in line or 'does not match' in line):
                    # Extract paper name from the line before this error
                    for prev_line in reversed(output_lines[:output_lines.index(line)]):
                        if 'Checking paper:' in prev_line:
                            paper_name = prev_line.split('Checking paper:')[1].strip()
                            detailed_results["actual_failures"]["official_evaluation"].append(paper_name)
                            break
                elif 'missing required columns' in line:
                    detailed_results["actual_failures"]["official_evaluation"].append("missing required columns")
            
            # Show evaluation output with color coding
            for line in output_lines:
                if '✓' in line:
                    colored_print(f"    {line}", Colors.GREEN)
                elif '✗' in line:
                    colored_print(f"    {line}", Colors.RED)
                elif line.strip():
                    colored_print(f"    {line}", Colors.WHITE)
            
        except subprocess.TimeoutExpired:
            colored_print(f"    ❌ TIMEOUT: Test took too long to complete", Colors.RED)
            detailed_results["actual_failures"]["official_evaluation"].append("timeout")
        except Exception as e:
            colored_print(f"    ❌ ERROR: {e}", Colors.RED)
            detailed_results["actual_failures"]["official_evaluation"].append(f"error: {e}")
        
        # Validate expected failures for FAIL test cases
        expected_failures_validation = True
        if not expected_result and "expected_failures" in test_config:
            colored_print(f"\n  🎯 Validating Expected Failure Patterns:", Colors.MAGENTA, bold=True)
            expected_failures = test_config["expected_failures"]
            
            for failure_type, expected_list in expected_failures.items():
                if failure_type in detailed_results["actual_failures"]:
                    actual_list = detailed_results["actual_failures"][failure_type]
                    validation_result = validate_expected_failures(actual_list, expected_list, failure_type)
                    expected_failures_validation = expected_failures_validation and validation_result
        
        # Summary for this test case
        colored_print(f"\n  📊 Test Summary for {workspace_name}:", Colors.BLUE, bold=True)
        
        checks = [
            ("Excel Structure", detailed_results["structure_valid"]),
            ("Data Completeness", detailed_results["data_complete"]), 
            ("Content Accuracy", detailed_results["content_accurate"]),
            ("Official Evaluation", detailed_results["evaluation_passed"])
        ]
        
        for check_name, passed in checks:
            status = "✅ PASS" if passed else "❌ FAIL"
            color = Colors.GREEN if passed else Colors.RED
            colored_print(f"    {status} {check_name}", color)
        
        # Explain the logic
        colored_print(f"\n  💡 Comprehensive Evaluation Logic:", Colors.YELLOW, bold=True)
        colored_print(f"    • ALL validation layers must pass for a complete PASS", Colors.WHITE)
        colored_print(f"    • Excel Structure: Basic file format validation", Colors.WHITE)
        colored_print(f"    • Data Completeness: All required fields must be filled", Colors.WHITE)
        colored_print(f"    • Content Accuracy: Detailed requirement validation", Colors.WHITE)
        colored_print(f"    • Official Evaluation: Main evaluation script result", Colors.WHITE)
        colored_print(f"    • Any single failure = overall FAIL (prevents edge cases)", Colors.YELLOW)
        
        # Calculate comprehensive result
        all_checks_passed = all([
            detailed_results["structure_valid"],
            detailed_results["data_complete"], 
            detailed_results["content_accurate"],
            detailed_results["evaluation_passed"]
        ])
        
        # For tests expected to FAIL, we only need the official evaluation to fail
        # For tests expected to PASS, we need ALL checks to pass
        if expected_result:
            # Test should PASS - require all checks to pass
            actual_result = all_checks_passed
            colored_print(f"\n  🎯 Comprehensive Check: {'PASS' if all_checks_passed else 'FAIL'} (all layers must pass)", Colors.CYAN)
        else:
            # Test should FAIL - need official evaluation to fail AND expected failure patterns to match
            official_failed = not detailed_results["evaluation_passed"]
            actual_result = not (official_failed and expected_failures_validation)  # Should be False (FAIL) if both conditions met
            colored_print(f"\n  🎯 Expected Failure Check: Official eval {'FAILED' if official_failed else 'PASSED'}, Patterns {'MATCH' if expected_failures_validation else 'MISMATCH'}", Colors.CYAN)
        
        test_passed = (actual_result == expected_result)
        
        colored_print(f"\n  🎯 Expected Result: {'PASS' if expected_result else 'FAIL'}", Colors.WHITE)
        colored_print(f"  🎯 Actual Result: {'PASS' if actual_result else 'FAIL'}", Colors.WHITE)
        colored_print(f"  🎯 Test Expectation: {'This test should PASS (all checks)' if expected_result else 'This test should FAIL (with specific patterns)'}", Colors.CYAN)
        
        if test_passed:
            colored_print(f"  ✅ FINAL TEST RESULT: PASS", Colors.GREEN, bold=True)
            if expected_result:
                colored_print(f"     All validation layers passed - comprehensive success!", Colors.GREEN)
            else:
                colored_print(f"     Official evaluation failed with expected patterns!", Colors.GREEN)
        else:
            colored_print(f"  ❌ FINAL TEST RESULT: FAIL", Colors.RED, bold=True)
            if expected_result:
                failed_checks = []
                if not detailed_results["structure_valid"]: failed_checks.append("Excel Structure")
                if not detailed_results["data_complete"]: failed_checks.append("Data Completeness")
                if not detailed_results["content_accurate"]: failed_checks.append("Content Accuracy")
                if not detailed_results["evaluation_passed"]: failed_checks.append("Official Evaluation")
                colored_print(f"     Failed validation layers: {', '.join(failed_checks)}", Colors.RED)
            else:
                if not (not detailed_results["evaluation_passed"]):
                    colored_print(f"     Expected failure but official evaluation incorrectly passed!", Colors.RED)
                if not expected_failures_validation:
                    colored_print(f"     Failure patterns don't match expectations!", Colors.RED)
        
        overall_results.append(test_passed)
    
    # Overall summary
    colored_print(f"\n" + "=" * 80, Colors.WHITE)
    colored_print(f"🏁 Overall Test Results:", Colors.MAGENTA, bold=True)
    
    passed_count = sum(overall_results)
    total_count = len(overall_results)
    
    if passed_count == total_count:
        colored_print(f"🎉 ALL TESTS PASSED! ({passed_count}/{total_count})", Colors.GREEN, bold=True)
    else:
        colored_print(f"⚠️  SOME TESTS FAILED: {passed_count}/{total_count} passed", Colors.YELLOW, bold=True)
    
    colored_print("=" * 80, Colors.WHITE)

if __name__ == "__main__":
    run_evaluation_tests()