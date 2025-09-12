"""
BigQuery Database Validation Test

This script tests the BigQuery database validation functionality
for the WooCommerce new customer welcome task.
"""

import sys
import os
from pathlib import Path

# Add the evaluation directory to the path
current_dir = Path(__file__).parent
eval_dir = current_dir.parent / "evaluation"
sys.path.insert(0, str(eval_dir))

from main import DatabaseValidator

def test_bigquery_validation():
    """Test BigQuery database validation"""
    print("🧪 Testing BigQuery Database Validation")
    print("=" * 50)
    
    try:
        # Initialize validator
        validator = DatabaseValidator()
        print("✅ DatabaseValidator initialized successfully")
        
        # Test getting statistics
        print("\n📊 Testing database statistics...")
        stats = validator.get_database_stats()
        print(f"Statistics result: {stats}")
        
        if stats:
            print("✅ Successfully retrieved BigQuery statistics")
            print(f"   - Total customers: {stats.get('total_customers', 0)}")
            print(f"   - New customers (7 days): {stats.get('new_customers_7_days', 0)}")
            print(f"   - Welcome emails sent: {stats.get('welcome_emails_sent', 0)}")
            print(f"   - Pending emails: {stats.get('pending_welcome_emails', 0)}")
        else:
            print("⚠️  No statistics returned (database may be empty)")
        
        # Test checking for a sample customer
        print("\n👤 Testing customer lookup...")
        sample_emails = [
            "new.customer1@example.com",
            "new.customer2@example.com", 
            "new.customer3@example.com",
            "new.customer4@example.com",
            "nonexistent@example.com"
        ]
        
        for email in sample_emails:
            exists = validator.verify_customer_in_db(email)
            status = "✅ Found" if exists else "❌ Not found"
            print(f"   {status}: {email}")
            
            if exists:
                # Check email status
                email_sent = validator.verify_welcome_email_marked(email)
                email_status = "📧 Sent" if email_sent else "⏳ Pending"
                print(f"      Welcome email: {email_status}")
        
        print("\n✅ BigQuery validation test completed successfully")
        return True
        
    except Exception as e:
        print(f"❌ BigQuery validation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_bigquery_validation()
    sys.exit(0 if success else 1)