#!/usr/bin/env python3
"""
Product Recall Task - Data Setup
Create recalled products, customer info and order history
"""

import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
import random

# Dynamically add current directory to path
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient, ProductRecallDataSetup

class RecallTaskSetup:
    """Product recall task data setup"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize recall task setup
        
        Args:
            site_url: WooCommerce website URL
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.data_setup = ProductRecallDataSetup(self.wc_client)
        
        # Test customer data - add timestamp to avoid email conflicts
        timestamp = int(time.time())
        self.test_customers = [
            {
                "first_name": "John",
                "last_name": "Smith",
                "email": f"test_recall_johnsmith_{timestamp}@test.com",
                "phone": "555-888-0001",
                "billing": {
                    "first_name": "John",
                    "last_name": "Smith",
                    "address_1": "123 Main Street",
                    "city": "New York",
                    "state": "NY",
                    "postcode": "10001",
                    "country": "US",
                    "email": f"test_recall_johnsmith_{timestamp}@test.com",
                    "phone": "555-888-0001"
                },
                "shipping": {
                    "first_name": "John",
                    "last_name": "Smith",
                    "address_1": "123 Main Street",
                    "city": "New York",
                    "state": "NY",
                    "postcode": "10001",
                    "country": "US"
                }
            },
            {
                "first_name": "Lisa",
                "last_name": "Johnson",
                "email": f"test_recall_lisajohnson_{timestamp}@test.com",
                "phone": "555-888-0002",
                "billing": {
                    "first_name": "Lisa",
                    "last_name": "Johnson",
                    "address_1": "456 Oak Avenue",
                    "city": "Los Angeles",
                    "state": "CA", 
                    "postcode": "90210",
                    "country": "US",
                    "email": f"test_recall_lisajohnson_{timestamp}@test.com",
                    "phone": "555-888-0002"
                },
                "shipping": {
                    "first_name": "Lisa",
                    "last_name": "Johnson",
                    "address_1": "456 Oak Avenue",
                    "city": "Los Angeles",
                    "state": "CA",
                    "postcode": "90210",
                    "country": "US"
                }
            },
            {
                "first_name": "Michael",
                "last_name": "Brown",
                "email": f"test_recall_michaelbrown_{timestamp}@test.com",
                "phone": "555-888-0003",
                "billing": {
                    "first_name": "Michael",
                    "last_name": "Brown",
                    "address_1": "789 Pine Street",
                    "city": "Chicago",
                    "state": "IL",
                    "postcode": "60601",
                    "country": "US",
                    "email": f"test_recall_michaelbrown_{timestamp}@test.com",
                    "phone": "555-888-0003"
                },
                "shipping": {
                    "first_name": "Michael",
                    "last_name": "Brown",
                    "address_1": "789 Pine Street",
                    "city": "Chicago",
                    "state": "IL",
                    "postcode": "60601",
                    "country": "US"
                }
            },
            {
                "first_name": "Sarah",
                "last_name": "Davis",
                "email": f"test_recall_sarahdavis_{timestamp}@test.com",
                "phone": "555-888-0004",
                "billing": {
                    "first_name": "Sarah",
                    "last_name": "Davis",
                    "address_1": "321 Elm Street",
                    "city": "Miami",
                    "state": "FL",
                    "postcode": "33101",
                    "country": "US",
                    "email": f"test_recall_sarahdavis_{timestamp}@test.com",
                    "phone": "555-888-0004"
                },
                "shipping": {
                    "first_name": "Sarah",
                    "last_name": "Davis",
                    "address_1": "321 Elm Street",
                    "city": "Miami",
                    "state": "FL",
                    "postcode": "33101",
                    "country": "US"
                }
            },
            {
                "first_name": "David",
                "last_name": "Wilson",
                "email": f"test_recall_davidwilson_{timestamp}@test.com",
                "phone": "555-888-0005",
                "billing": {
                    "first_name": "David",
                    "last_name": "Wilson",
                    "address_1": "654 Maple Avenue",
                    "city": "Seattle",
                    "state": "WA",
                    "postcode": "98101",
                    "country": "US",
                    "email": f"test_recall_davidwilson_{timestamp}@test.com",
                    "phone": "555-888-0005"
                },
                "shipping": {
                    "first_name": "David",
                    "last_name": "Wilson",
                    "address_1": "654 Maple Avenue",
                    "city": "Seattle",
                    "state": "WA",
                    "postcode": "98101",
                    "country": "US"
                }
            },
            {
                "first_name": "Jessica",
                "last_name": "Miller",
                "email": f"test_recall_jessicamiller_{timestamp}@test.com",
                "phone": "555-888-0006",
                "billing": {
                    "first_name": "Jessica",
                    "last_name": "Miller",
                    "address_1": "987 Cedar Street",
                    "city": "Denver",
                    "state": "CO",
                    "postcode": "80201",
                    "country": "US",
                    "email": f"test_recall_jessicamiller_{timestamp}@test.com",
                    "phone": "555-888-0006"
                },
                "shipping": {
                    "first_name": "Jessica",
                    "last_name": "Miller",
                    "address_1": "987 Cedar Street",
                    "city": "Denver",
                    "state": "CO",
                    "postcode": "80201",
                    "country": "US"
                }
            }
        ]
    
    def create_test_customers(self) -> Dict:
        """
        Create test customers
        
        Returns:
            Creation result dictionary
        """
        print("👥 Creating test customers...")
        
        created_count = 0
        failed_count = 0
        
        for customer_data in self.test_customers:
            success, result = self.wc_client.create_customer(customer_data)
            if success:
                customer_id = result.get('id')
                customer_email = result.get('email')
                customer_name = f"{result.get('first_name', '')} {result.get('last_name', '')}"
                
                self.data_setup.created_customers.append({
                    'id': customer_id,
                    'email': customer_email,
                    'name': customer_name,
                    'billing_info': customer_data.get('billing', {}),
                    'shipping_info': customer_data.get('shipping', {})
                })
                
                print(f"✅ Created customer: {customer_name} ({customer_email}) - ID: {customer_id}")
                created_count += 1
            else:
                print(f"❌ Failed to create customer: {customer_data.get('email')} - {result}")
                failed_count += 1
            
            time.sleep(0.5)
        
        customer_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_customers": self.data_setup.created_customers
        }
        
        print(f"📊 Customer creation completed:")
        print(f"   Successfully created: {created_count} customers")
        print(f"   Failed to create: {failed_count} customers")
        
        return customer_result
    
    def create_historical_orders(self) -> Dict:
        """
        Create historical orders containing recalled products
        
        Returns:
            Creation result dictionary
        """
        print("📋 Creating historical orders with recalled products...")
        
        if not self.data_setup.created_products or not self.data_setup.created_customers:
            print("❌ Need to create products and customers first")
            return {"success": False, "error": "Missing product or customer data"}
        
        # Get recalled products
        recalled_products = [p for p in self.data_setup.created_products if p.get('is_recalled')]
        if not recalled_products:
            print("❌ No recalled products found")
            return {"success": False, "error": "No recalled products"}
        
        created_count = 0
        failed_count = 0
        
        # Create 1-2 orders for each customer containing recalled products
        for customer in self.data_setup.created_customers:
            num_orders = random.randint(1, 2)  # 1-2 orders per customer
            
            for i in range(num_orders):
                # Randomly select recalled product
                selected_product = random.choice(recalled_products)
                
                # Randomly select other products (optional)
                other_products = [p for p in self.data_setup.created_products if not p.get('is_recalled')]
                include_other = random.choice([True, False])
                
                line_items = [
                    {
                        "product_id": selected_product['id'],
                        "quantity": random.randint(1, 2),
                        "name": selected_product['name'],
                        "sku": selected_product.get('sku', ''),
                        "price": "999.99"
                    }
                ]
                
                total_amount = float(line_items[0]['price']) * line_items[0]['quantity']
                
                # Possibly add other products
                if include_other and other_products:
                    other_product = random.choice(other_products)
                    other_item = {
                        "product_id": other_product['id'],
                        "quantity": 1,
                        "name": other_product['name'],
                        "sku": other_product.get('sku', ''),
                        "price": "199.99"
                    }
                    line_items.append(other_item)
                    total_amount += float(other_item['price'])
                
                # Create order data
                order_date = datetime.now() - timedelta(days=random.randint(30, 150))
                
                order_data = {
                    "status": "completed",
                    "customer_id": customer['id'],
                    "billing": customer['billing_info'],
                    "shipping": customer['shipping_info'],
                    "line_items": line_items,
                    "total": str(total_amount),
                    "date_created": order_date.isoformat(),
                    "meta_data": [
                        {"key": "contains_recalled_product", "value": "true"},
                        {"key": "recalled_product_ids", "value": str(selected_product['id'])},
                        {"key": "order_source", "value": "test_data"}
                    ]
                }
                
                success, result = self.wc_client.create_order(order_data)
                if success:
                    order_id = result.get('id')
                    order_number = result.get('number', order_id)
                    
                    order_info = {
                        'id': order_id,
                        'number': order_number,
                        'customer_id': customer['id'],
                        'customer_email': customer['email'],
                        'customer_name': customer['name'],
                        'date_created': order_date.isoformat(),
                        'status': 'completed',
                        'total': total_amount,
                        'recalled_product_id': selected_product['id'],
                        'recalled_product_name': selected_product['name'],
                        'line_items': line_items
                    }
                    
                    self.data_setup.created_orders.append(order_info)
                    
                    print(f"✅ Created order: #{order_number} - {customer['name']} - contains {selected_product['name']}")
                    created_count += 1
                else:
                    print(f"❌ Failed to create order: customer {customer['name']} - {result}")
                    failed_count += 1
                
                time.sleep(0.8)  # Order creation needs longer interval
        
        order_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_orders": self.data_setup.created_orders,
            "orders_with_recalled_products": len(self.data_setup.created_orders)
        }
        
        print(f"📊 Order creation completed:")
        print(f"   Successfully created: {created_count} orders")
        print(f"   Failed to create: {failed_count} orders")
        print(f"   Orders with recalled products: {order_result['orders_with_recalled_products']} orders")
        
        return order_result
    
    def run_full_setup(self) -> Dict:
        """
        Run complete data setup process
        
        Returns:
            Setup result dictionary
        """
        print("=" * 60)
        print("🎯 Product Recall Task - Complete Data Setup")
        print("=" * 60)
        
        # 1. Clear existing data
        print("\nStep 1: Thoroughly clear existing data")
        print("-" * 40)
        clear_result = self.data_setup.clear_all_data()
        
        # Wait for cleanup to complete, ensure WooCommerce database fully syncs
        print("⏳ Waiting 8 seconds to ensure WooCommerce cleanup operations are fully synced...")
        time.sleep(8)
        
        # Verify cleanup results
        print("🔍 Verifying cleanup results...")
        remaining_products = self.wc_client.get_all_products()
        remaining_orders = self.wc_client.get_all_orders()
        
        if remaining_products:
            print(f"⚠️ Still have {len(remaining_products)} products not cleaned, performing second cleanup...")
            # Second cleanup
            secondary_clear = self.data_setup.clear_all_data()
            time.sleep(5)
        else:
            print("✅ Product cleanup completed")
            
        if remaining_orders:
            print(f"⚠️ Still have {len(remaining_orders)} orders not cleaned")
        else:
            print("✅ Order cleanup completed")
        
        # 2. Create recalled products
        print("\nStep 2: Create recalled products")
        print("-" * 40)
        product_result = self.data_setup.create_recalled_products()
        
        if not product_result.get('success'):
            print("❌ Product creation failed, stopping setup")
            return {"success": False, "step": "create_products", "error": product_result}
        
        # 3. Create test customers
        print("\nStep 3: Create test customers")
        print("-" * 40)
        customer_result = self.create_test_customers()
        
        if not customer_result.get('success'):
            print("❌ Customer creation failed, stopping setup")
            return {"success": False, "step": "create_customers", "error": customer_result}
        
        # 4. Create historical orders
        print("\nStep 4: Create historical orders")
        print("-" * 40)
        order_result = self.create_historical_orders()
        
        # 5. Generate setup report
        setup_summary = {
            "success": (product_result.get('success') and 
                       customer_result.get('success') and 
                       order_result.get('success')),
            "timestamp": datetime.now().isoformat(),
            "summary": {
                "recalled_products": product_result.get('recalled_products_count', 0),
                "normal_products": product_result.get('normal_products_count', 0),
                "test_customers": customer_result.get('created_count', 0),
                "historical_orders": order_result.get('created_count', 0),
                "orders_with_recalled_products": order_result.get('orders_with_recalled_products', 0)
            },
            "details": {
                "products": product_result,
                "customers": customer_result,
                "orders": order_result
            }
        }
        
        # Save customer info to JSON file for evaluation use
        customer_info = {
            "test_customer_emails": [c.get('email') for c in self.data_setup.created_customers],
            "test_customer_names": [c.get('name') for c in self.data_setup.created_customers],
            "total_test_customers": len(self.data_setup.created_customers),
            "created_at": datetime.now().isoformat()
        }
        
        customer_info_file = os.path.join(os.path.dirname(__file__), '..', 'test_customers_info.json')
        try:
            with open(customer_info_file, 'w', encoding='utf-8') as f:
                json.dump(customer_info, f, indent=2, ensure_ascii=False)
            print(f"✅ Test customer info saved to: {customer_info_file}")
        except Exception as e:
            print(f"⚠️ Failed to save test customer info: {e}")
        
        print("\n" + "=" * 60)
        print("📊 Setup Completion Summary")
        print("=" * 60)
        print(f"Recalled products count: {setup_summary['summary']['recalled_products']}")
        print(f"Normal products count: {setup_summary['summary']['normal_products']}")
        print(f"Test customers count: {setup_summary['summary']['test_customers']}")
        print(f"Historical orders count: {setup_summary['summary']['historical_orders']}")
        print(f"Orders with recalled products: {setup_summary['summary']['orders_with_recalled_products']}")
        
        if setup_summary['success']:
            print("\n✅ Product recall task data setup completed!")
        else:
            print("\n⚠️ Product recall task data setup partially completed")
        
        return setup_summary


def main():
    """Main function - for standalone recall task data setup"""
    # Read configuration from token configuration file
    try:
        from token_key_session import all_token_key_session
        
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
    except ImportError:
        print("❌ token_key_session configuration file not found")
        return False
    
    print(f"🚀 Initializing product recall task setup: {site_url}")
    
    setup = RecallTaskSetup(site_url, consumer_key, consumer_secret)
    
    # Run complete setup
    result = setup.run_full_setup()
    
    return result.get('success', False)


if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)