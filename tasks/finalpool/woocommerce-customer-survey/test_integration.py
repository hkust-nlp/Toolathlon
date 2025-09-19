#!/usr/bin/env python3
"""
Test integration of the new WooCommerce utilities

This script tests that the new generic utilities work correctly
and maintain backward compatibility with existing tasks.
"""

import sys
import os
from pathlib import Path

# Add project root to path
current_dir = Path(__file__).parent
project_root = current_dir.parent.parent.parent.parent
sys.path.insert(0, str(project_root))

def test_imports():
    """Test that all imports work correctly"""
    try:
        print("🧪 Testing imports...")

        # Test individual imports
        from utils.app_specific.woocommerce.client import WooCommerceClient
        print("   ✅ WooCommerceClient import successful")

        from utils.app_specific.woocommerce.order_generator import (
            OrderDataGenerator, CustomerData, ProductData, OrderGenerationConfig
        )
        print("   ✅ Order generator classes import successful")

        from utils.app_specific.woocommerce.order_manager import OrderManager
        print("   ✅ OrderManager import successful")

        # Test convenience imports
        from utils.app_specific.woocommerce import (
            setup_customer_survey_environment,
            create_customer_survey_orders,
            create_product_analysis_orders
        )
        print("   ✅ Convenience functions import successful")

        return True
    except Exception as e:
        print(f"   ❌ Import failed: {e}")
        return False

def test_order_generation():
    """Test order data generation"""
    try:
        print("\n🧪 Testing order generation...")

        from utils.app_specific.woocommerce import create_customer_survey_orders

        # Generate orders
        all_orders, completed_orders = create_customer_survey_orders(seed=12345)

        print(f"   ✅ Generated {len(all_orders)} total orders")
        print(f"   ✅ Generated {len(completed_orders)} completed orders")

        # Verify order structure
        if all_orders:
            order = all_orders[0]
            required_fields = ['order_id', 'customer_email', 'customer_name', 'status',
                             'product_name', 'product_price', 'quantity']
            for field in required_fields:
                if field not in order:
                    raise ValueError(f"Missing required field: {field}")
            print("   ✅ Order structure validation passed")

        # Verify completed orders are subset of all orders
        completed_ids = set(order['order_id'] for order in completed_orders)
        all_completed_ids = set(order['order_id'] for order in all_orders if order['status'] == 'completed')

        if completed_ids == all_completed_ids:
            print("   ✅ Completed orders filtering is correct")
        else:
            raise ValueError("Completed orders filtering mismatch")

        return True
    except Exception as e:
        print(f"   ❌ Order generation test failed: {e}")
        return False

def test_order_data_generator():
    """Test OrderDataGenerator class directly"""
    try:
        print("\n🧪 Testing OrderDataGenerator class...")

        from utils.app_specific.woocommerce.order_generator import (
            OrderDataGenerator, OrderGenerationConfig
        )

        generator = OrderDataGenerator()
        config = OrderGenerationConfig(
            order_count=5,
            completed_percentage=0.6,
            date_range_days=7,
            time_seed=54321
        )

        orders = generator.generate_orders(config)
        print(f"   ✅ Generated {len(orders)} orders with custom config")

        # Test statistics
        stats = generator.get_order_statistics(orders)
        print(f"   ✅ Statistics: {stats['total_orders']} orders, {stats['unique_customers']} customers")

        # Test WooCommerce format conversion
        if orders:
            wc_order = generator.create_woocommerce_order_data(orders[0])
            required_wc_fields = ['status', 'total', 'billing', 'line_items', 'meta_data']
            for field in required_wc_fields:
                if field not in wc_order:
                    raise ValueError(f"Missing WooCommerce field: {field}")
            print("   ✅ WooCommerce format conversion successful")

        return True
    except Exception as e:
        print(f"   ❌ OrderDataGenerator test failed: {e}")
        return False

def test_backward_compatibility():
    """Test that existing task code still works"""
    try:
        print("\n🧪 Testing backward compatibility...")

        # Import the updated task code - fail immediately if import fails
        task_module_path = str(current_dir.parent / "preprocess")
        sys.path.insert(0, task_module_path)

        from main import create_order_data, WooCommerceOrderManager

        # Test order data creation
        orders = create_order_data()
        print(f"   ✅ create_order_data() returned {len(orders)} orders")

        # Verify order structure matches expected format
        if orders:
            order = orders[0]
            expected_fields = ['order_id', 'customer_email', 'customer_name', 'status',
                             'date_created', 'product_name', 'product_price', 'quantity']
            for field in expected_fields:
                if field not in order:
                    raise ValueError(f"Missing expected field: {field}")
            print("   ✅ Order structure maintains compatibility")

        # Test manager class can be instantiated
        manager = WooCommerceOrderManager("https://test.com", "test_key", "test_secret")
        print("   ✅ WooCommerceOrderManager instantiation successful")

        return True
    except Exception as e:
        print(f"   ❌ Backward compatibility test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Testing WooCommerce utilities integration...")
    print("=" * 60)

    tests = [
        ("Import Tests", test_imports),
        ("Order Generation Tests", test_order_generation),
        ("OrderDataGenerator Tests", test_order_data_generator),
        ("Backward Compatibility Tests", test_backward_compatibility)
    ]

    passed = 0
    total = len(tests)

    for test_name, test_func in tests:
        print(f"\n📋 {test_name}")
        if test_func():
            passed += 1
            print(f"✅ {test_name} PASSED")
        else:
            print(f"❌ {test_name} FAILED")

    print("\n" + "=" * 60)
    print(f"🎯 Test Results: {passed}/{total} tests passed")

    if passed == total:
        print("🎉 All tests passed! Integration successful.")
        return True
    else:
        print("⚠️  Some tests failed. Please review the issues above.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)