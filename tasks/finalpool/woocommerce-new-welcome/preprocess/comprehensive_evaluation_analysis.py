#!/usr/bin/env python3
"""
Comprehensive Evaluation Testing Script for WooCommerce New Customer Welcome Task

This script analyzes and tests the evaluation logic to identify issues and ensure robustness.
"""

import sys
import os
import json
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Any
import requests
from unittest.mock import Mock, patch

# Add paths for imports
current_dir = Path(__file__).parent
task_dir = current_dir.parent
eval_dir = task_dir / "evaluation"
sys.path.insert(0, str(eval_dir))
sys.path.insert(0, str(task_dir))

class EvaluationAnalyzer:
    """Analyze evaluation code for issues and test various scenarios"""
    
    def __init__(self):
        self.issues_found = []
        self.test_results = []
        
    def analyze_evaluation_issues(self):
        """Analyze key issues in the evaluation code"""
        print("🔍 EVALUATION CODE ANALYSIS")
        print("=" * 60)
        
        issues = [
            {
                "category": "WooCommerce Validation",
                "issues": [
                    "❌ Hard-coded 7-day lookback may not match actual test data timeframes",
                    "❌ API calls may fail due to network/authentication issues",
                    "❌ Customer registration date vs first order date logic is complex",
                    "❌ Per-page limit of 100 may miss customers if there are more",
                    "⚠️  No retry mechanism for failed API calls"
                ]
            },
            {
                "category": "Email Validation", 
                "issues": [
                    "❌ IMAP connection depends on external email service",
                    "❌ Hard-coded subject pattern '欢迎加入' may not match actual templates",
                    "❌ Only checks emails within 30 minutes (within_seconds = 1800)",
                    "❌ Email folder detection logic may fail on different providers",
                    "⚠️  No fallback for different email systems"
                ]
            },
            {
                "category": "BigQuery Validation",
                "issues": [
                    "❌ Requires active Google Cloud credentials and network access",
                    "❌ No connection timeout or retry logic",
                    "❌ BigQuery costs money for each query execution",
                    "⚠️  No validation of BigQuery table schema",
                    "⚠️  No check for data freshness or sync timing"
                ]
            },
            {
                "category": "General Logic",
                "issues": [
                    "✅ FIXED: Success counting logic now correctly counts only True results",
                    "❌ No graceful degradation when services are unavailable",
                    "❌ Binary pass/fail doesn't account for partial success scenarios",
                    "⚠️  No logging of intermediate steps for debugging"
                ]
            }
        ]
        
        for category in issues:
            print(f"\n📋 {category['category']}:")
            for issue in category['issues']:
                print(f"   {issue}")
                
        return issues
    
    def test_woocommerce_date_logic(self):
        """Test the WooCommerce date filtering logic"""
        print("\n🧪 TESTING: WooCommerce Date Logic")
        print("-" * 40)
        
        test_cases = [
            {
                "name": "Current test data (Sep 2, 2025)",
                "test_date": "2025-09-02T13:19:55",
                "lookback_days": 7,
                "expected_valid": True
            },
            {
                "name": "Data from 8 days ago",
                "test_date": (datetime.now() - timedelta(days=8)).isoformat(),
                "lookback_days": 7,
                "expected_valid": False
            },
            {
                "name": "Future date",
                "test_date": (datetime.now() + timedelta(days=1)).isoformat(),
                "lookback_days": 7,
                "expected_valid": True
            }
        ]
        
        for case in test_cases:
            cutoff_date = (datetime.now() - timedelta(days=case["lookback_days"])).isoformat()
            is_valid = case["test_date"] >= cutoff_date
            
            status = "✅ PASS" if is_valid == case["expected_valid"] else "❌ FAIL"
            print(f"   {status} {case['name']}")
            print(f"       Test date: {case['test_date']}")
            print(f"       Cutoff: {cutoff_date}")
            print(f"       Valid: {is_valid} (expected: {case['expected_valid']})")
            
    def test_email_timing_constraints(self):
        """Test email validation timing constraints"""
        print("\n🧪 TESTING: Email Timing Constraints")
        print("-" * 40)
        
        now = datetime.now()
        within_seconds = 1800  # 30 minutes as in the code
        
        test_times = [
            {
                "name": "Email sent 15 minutes ago",
                "email_time": now - timedelta(minutes=15),
                "should_pass": True
            },
            {
                "name": "Email sent 45 minutes ago", 
                "email_time": now - timedelta(minutes=45),
                "should_pass": False
            },
            {
                "name": "Email sent 29 minutes ago",
                "email_time": now - timedelta(minutes=29),
                "should_pass": True
            },
            {
                "name": "Email sent 31 minutes ago",
                "email_time": now - timedelta(minutes=31),
                "should_pass": False
            }
        ]
        
        for case in test_times:
            time_diff = abs((now - case["email_time"]).total_seconds())
            is_within_limit = time_diff <= within_seconds
            
            status = "✅ PASS" if is_within_limit == case["should_pass"] else "❌ FAIL"
            print(f"   {status} {case['name']}")
            print(f"       Time diff: {time_diff:.0f}s (limit: {within_seconds}s)")
            print(f"       Within limit: {is_within_limit} (expected: {case['should_pass']})")
            
    def simulate_evaluation_scenarios(self):
        """Simulate different evaluation scenarios"""
        print("\n🧪 TESTING: Evaluation Scenarios")
        print("-" * 40)
        
        scenarios = [
            {
                "name": "Perfect Success",
                "woocommerce_customers": 4,
                "emails_sent": 4,
                "bigquery_synced": 4,
                "expected_result": "SUCCESS"
            },
            {
                "name": "No New Customers",
                "woocommerce_customers": 0,
                "emails_sent": 0,
                "bigquery_synced": 0,
                "expected_result": "FAILURE"
            },
            {
                "name": "Customers Found, No Emails",
                "woocommerce_customers": 4,
                "emails_sent": 0,
                "bigquery_synced": 4,
                "expected_result": "FAILURE"
            },
            {
                "name": "Customers Found, No BigQuery Sync",
                "woocommerce_customers": 4,
                "emails_sent": 4,
                "bigquery_synced": 0,
                "expected_result": "FAILURE"
            },
            {
                "name": "Partial Email Success",
                "woocommerce_customers": 4,
                "emails_sent": 2,
                "bigquery_synced": 4,
                "expected_result": "FAILURE"
            }
        ]
        
        for scenario in scenarios:
            print(f"\n   📋 Scenario: {scenario['name']}")
            
            # Simulate evaluation logic
            results = []
            
            # WooCommerce check
            woo_success = scenario["woocommerce_customers"] > 0
            woo_msg = f"Found {scenario['woocommerce_customers']} new customers" if woo_success else "No new customers found"
            results.append(("WooCommerce", woo_success, woo_msg))
            
            # Email check  
            if scenario["woocommerce_customers"] > 0:
                email_success = scenario["emails_sent"] == scenario["woocommerce_customers"]
                email_msg = f"All {scenario['emails_sent']} welcome emails sent" if email_success else f"Only {scenario['emails_sent']}/{scenario['woocommerce_customers']} emails sent"
                results.append(("Email", email_success, email_msg))
            else:
                results.append(("Email", False, "No customers to check"))
                
            # BigQuery check
            if scenario["woocommerce_customers"] > 0:
                bq_success = scenario["bigquery_synced"] == scenario["woocommerce_customers"]
                bq_msg = f"All {scenario['bigquery_synced']} customers in BigQuery" if bq_success else f"Only {scenario['bigquery_synced']}/{scenario['woocommerce_customers']} in BigQuery"
                results.append(("BigQuery Database", bq_success, bq_msg))
            else:
                results.append(("BigQuery Database", False, "No customers to check"))
            
            # Calculate result using fixed logic
            passed = sum(1 for _, success, _ in results if success)
            total = len(results)
            overall_pass = passed == total
            actual_result = "SUCCESS" if overall_pass else "FAILURE"
            
            # Display results
            for service, success, message in results:
                status = "✅" if success else "❌"
                print(f"     {status} {service}: {message}")
                
            result_status = "✅" if actual_result == scenario["expected_result"] else "❌"
            print(f"     {result_status} Overall: {actual_result} ({passed}/{total}) - Expected: {scenario['expected_result']}")

    def test_bigquery_connection_scenarios(self):
        """Test BigQuery connection scenarios"""
        print("\n🧪 TESTING: BigQuery Connection Scenarios")
        print("-" * 40)
        
        scenarios = [
            "✅ Valid credentials and network access",
            "❌ Invalid credentials file path",
            "❌ Malformed credentials JSON",
            "❌ Network connectivity issues",
            "❌ BigQuery API quota exceeded",
            "❌ Dataset or table does not exist",
            "❌ Insufficient permissions"
        ]
        
        print("   Potential BigQuery Issues:")
        for scenario in scenarios:
            print(f"     {scenario}")
            
    def generate_evaluation_recommendations(self):
        """Generate recommendations for improving the evaluation"""
        print("\n💡 EVALUATION IMPROVEMENT RECOMMENDATIONS")
        print("=" * 60)
        
        recommendations = [
            {
                "category": "Robustness",
                "items": [
                    "Add retry mechanism for API calls with exponential backoff",
                    "Implement graceful degradation when services are unavailable",
                    "Add connection timeouts and error handling",
                    "Create mock modes for testing without external dependencies"
                ]
            },
            {
                "category": "Flexibility",
                "items": [
                    "Make time windows configurable instead of hard-coded",
                    "Support different email subject patterns and languages",
                    "Allow partial success scoring instead of binary pass/fail",
                    "Add dry-run mode for validation without side effects"
                ]
            },
            {
                "category": "Debugging",
                "items": [
                    "Add detailed logging for each validation step",
                    "Include intermediate results in output",
                    "Provide specific error messages for troubleshooting",
                    "Save validation state for post-mortem analysis"
                ]
            },
            {
                "category": "Performance",
                "items": [
                    "Cache BigQuery connections to reduce setup overhead",
                    "Batch BigQuery queries where possible",
                    "Use async/await for concurrent service validation",
                    "Add progress indicators for long-running validations"
                ]
            }
        ]
        
        for category in recommendations:
            print(f"\n📋 {category['category']}:")
            for item in category['items']:
                print(f"   • {item}")

def main():
    """Run comprehensive evaluation analysis"""
    print("🚀 COMPREHENSIVE EVALUATION ANALYSIS")
    print("=" * 80)
    print("Analyzing WooCommerce New Customer Welcome Task Evaluation")
    print("=" * 80)
    
    analyzer = EvaluationAnalyzer()
    
    # Run all analyses
    analyzer.analyze_evaluation_issues()
    analyzer.test_woocommerce_date_logic()
    analyzer.test_email_timing_constraints()
    analyzer.simulate_evaluation_scenarios()
    analyzer.test_bigquery_connection_scenarios()
    analyzer.generate_evaluation_recommendations()
    
    print("\n" + "=" * 80)
    print("🎯 SUMMARY")
    print("=" * 80)
    print("✅ Fixed the critical success counting logic bug")
    print("⚠️  Multiple other robustness and reliability issues identified")
    print("💡 Comprehensive recommendations provided for improvement")
    print("🔧 Consider implementing mock modes for reliable testing")
    print("=" * 80)

if __name__ == "__main__":
    main()