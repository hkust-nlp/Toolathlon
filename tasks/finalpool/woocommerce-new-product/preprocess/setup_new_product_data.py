import json
import time
from datetime import datetime, timedelta
from typing import Dict
import sys
import os

# Dynamically add the current directory to sys.path
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

class NewProductEmailSetupV2:
    """New Product Email Task Setup V2 - Optimized Customer Creation Logic"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize the New Product Email Setup.

        Args:
            site_url: WooCommerce site URL
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.created_products = []
        self.created_customers = []

    def clear_all_data(self) -> Dict:
        """
        Delete all products, customers, and categories from the store.

        Returns:
            dict with clear result
        """
        print("🧹 Start clearing all data from the store...")

        try:
            # 1. Get and delete all products
            print("📦 Clearing all products...")
            all_products = self.wc_client.get_all_products()

            deleted_products = 0
            failed_products = 0

            if all_products:
                print(f"🗑️ Ready to delete {len(all_products)} products...")

                for product in all_products:
                    product_id = product.get('id')
                    product_name = product.get('name', 'Unknown')

                    try:
                        success, result = self.wc_client.delete_product(str(product_id), force=True)
                        if success:
                            print(f"   ✅ Deleted product: {product_name} (ID: {product_id})")
                            deleted_products += 1
                        else:
                            print(f"   ❌ Failed to delete: {product_name} - {result}")
                            failed_products += 1
                    except Exception as e:
                        print(f"   ❌ Exception when deleting product {product_name}: {e}")
                        failed_products += 1

                    time.sleep(0.3)
            else:
                print("📦 No products to delete in the store.")

            # 2. Delete customers (only non-test customers)
            print("👥 Clearing non-test customers...")

            # Define our set of 40 test customer emails
            our_test_emails = {
                "samuel.garcia.welcome@mcptest.com",
                "henryn.welcome@mcptest.com",
                "robert.collins.welcome@mcptest.com",
                "allenm.welcome@mcptest.com",
                "floresj.welcome@mcptest.com",
                "mary.edwards57.welcome@mcptest.com",
                "slewis.welcome@mcptest.com",
                "nwilson.welcome@mcptest.com",
                "johnsonr.welcome@mcptest.com",
                "deborahw99.welcome@mcptest.com",
                "timothyc57.welcome@mcptest.com",
                "kathleen_kelly.welcome@mcptest.com",
                "ramosa.welcome@mcptest.com",
                "edavis.welcome@mcptest.com",
                "amanda_chavez.welcome@mcptest.com",
                "emurphy.welcome@mcptest.com",
                "anthonyo.welcome@mcptest.com",
                "marie.walker.welcome@mcptest.com",
                "samuel_sanders77.welcome@mcptest.com",
                "alexanderr.welcome@mcptest.com",
                "betty.cooper.welcome@mcptest.com",
                "adamsc.welcome@mcptest.com",
                "martha.hill.welcome@mcptest.com",
                "michael.reed.welcome@mcptest.com",
                "emorris.welcome@mcptest.com",
                "timothy_gomez54.welcome@mcptest.com",
                "maryt92.welcome@mcptest.com",
                "mendozas52.welcome@mcptest.com",
                "melissa.martin95.welcome@mcptest.com",
                "thomas_sanchez8.welcome@mcptest.com",
                "harrisc.welcome@mcptest.com",
                "scottm.welcome@mcptest.com",
                "tyler_roberts72.welcome@mcptest.com",
                "tnelson.welcome@mcptest.com",
                "sthomas.welcome@mcptest.com",
                "bennettr.welcome@mcptest.com",
                "mcruz.welcome@mcptest.com",
                "lewiss.welcome@mcptest.com",
                "alvarezm51.welcome@mcptest.com",
                "stewarte98.welcome@mcptest.com"
            }

            success, all_customers = self.wc_client.get_all_customers()

            deleted_customers = 0
            failed_customers = 0
            preserved_customers = 0

            if success and all_customers:
                print(f"🔍 Checking {len(all_customers)} customers...")

                for customer in all_customers:
                    customer_id = customer.get('id')
                    customer_email = customer.get('email', 'Unknown')

                    # Check if this customer is in our test email set
                    if customer_email.lower() in our_test_emails:
                        print(f"   🛡️ Preserving test customer: {customer_email} (ID: {customer_id})")
                        preserved_customers += 1
                        continue

                    # Delete non-test customer
                    try:
                        success, result = self.wc_client.delete_customer(str(customer_id), force=True)
                        if success:
                            print(f"   ✅ Deleted customer: {customer_email} (ID: {customer_id})")
                            deleted_customers += 1
                        else:
                            print(f"   ❌ Failed to delete customer: {customer_email} - {result}")
                            failed_customers += 1
                    except Exception as e:
                        print(f"   ❌ Exception when deleting customer {customer_email}: {e}")
                        failed_customers += 1

                    time.sleep(0.3)

                print(f"📊 Customer summary stats:")
                print(f"   Preserved test customers: {preserved_customers}")
                print(f"   Deleted other customers: {deleted_customers}")
                print(f"   Failed deletes: {failed_customers}")
            else:
                print("👥 No customers to process in the store.")

            # 3. Delete product categories
            print("🏷️ Clearing product categories...")
            success, categories = self.wc_client.get_product_categories()

            deleted_categories = 0
            failed_categories = 0

            if success and categories:
                test_category_names = [
                    "Electronics", "Smart Home", "Accessories", "Office Supplies",
                ]

                for category in categories:
                    category_name = category.get('name', '')
                    category_id = category.get('id')

                    if (category_name in test_category_names or
                        category.get('count', 0) == 0):

                        try:
                            delete_url = f"{self.wc_client.api_base}/products/categories/{category_id}"
                            response = self.wc_client.session.delete(
                                delete_url,
                                params={'force': True}
                            )

                            if response.status_code in [200, 204]:
                                print(f"   ✅ Deleted category: {category_name} (ID: {category_id})")
                                deleted_categories += 1
                            else:
                                print(f"   ⚠️ Skipped category: {category_name}")

                        except Exception as e:
                            print(f"   ❌ Exception when deleting category {category_name}: {e}")
                            failed_categories += 1

                        time.sleep(0.3)

            clear_result = {
                "success": failed_products == 0 and failed_customers == 0 and failed_categories == 0,
                "products": {
                    "total_found": len(all_products) if all_products else 0,
                    "deleted": deleted_products,
                    "failed": failed_products
                },
                "customers": {
                    "deleted": deleted_customers,
                    "preserved": preserved_customers,
                    "failed": failed_customers
                },
                "categories": {
                    "deleted": deleted_categories,
                    "failed": failed_categories
                },
                "timestamp": datetime.now().isoformat()
            }

            print(f"\n📊 Clear finished:")
            print(f"   Products: deleted {deleted_products}, failed {failed_products}")
            print(f"   Customers: deleted {deleted_customers}, preserved {preserved_customers}, failed {failed_customers}")
            print(f"   Categories: deleted {deleted_categories}, failed {failed_categories}")

            if clear_result["success"]:
                print("✅ Data clear successful!")
            else:
                print("⚠️ Data clear partially finished, some items failed to clear")

            return clear_result

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ Exception during clear: {e}")
            return error_result

    def create_product_categories(self) -> Dict:
        """Create product categories"""
        print("📂 Creating product categories...")

        categories = [
            {"name": "Electronics", "description": "Smartphones, computers, digital devices, etc."},
            {"name": "Smart Home", "description": "Smart devices, home automation, etc."},
            {"name": "Accessories", "description": "Chargers, cables, and other accessories"},
            {"name": "Office Supplies", "description": "Office equipment, stationery, etc."}
        ]

        created_categories = {}

        for category in categories:
            category_data = {
                "name": category["name"],
                "description": category["description"],
                "display": "default",
                "menu_order": 0,
                "parent": 0
            }

            success, response = self.wc_client._make_request('POST', 'products/categories', data=category_data)

            if success:
                category_id = response.get('id')
                created_categories[category["name"]] = category_id
                print(f"  ✅ Created category: {category['name']} (ID: {category_id})")
            else:
                print(f"  ❌ Category creation failed: {category['name']} - {response.get('error', 'Unknown error')}")

        return created_categories

    def create_test_products(self, categories: Dict) -> Dict:
        """
        Create test products.
        Including:
        1. New products (draft/pending status, published within next 30 days)
        2. Sale products (products with sale_price set)

        Returns:
            dict with creation result
        """
        print("🛒 Starting to create test products...")

        current_date = datetime.now()

        # New product data (English versions)
        draft_products = [
            {
                "name": "Smart Watch Pro Max",
                "type": "simple",
                "status": "draft",
                "regular_price": "299.99",
                "description": "Next-generation smartwatch with health monitoring, fitness tracking, and AI assistant features",
                "short_description": "Flagship wearable device",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-10-01"},
                    {"key": "pre_order_discount", "value": "10"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=1)).isoformat(),
                "date_modified": (current_date - timedelta(hours=10)).isoformat()
            },
            {
                "name": "Wireless Noise-Canceling Headphones Ultra",
                "type": "simple",
                "status": "pending",
                "regular_price": "159.99",
                "description": "Premium active noise-canceling headphones with 48-hour battery life and Hi-Res audio certification",
                "short_description": "Ultimate audio experience",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-15"},
                    {"key": "pre_order_discount", "value": "15"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=3)).isoformat(),
                "date_modified": (current_date - timedelta(hours=5)).isoformat()
            },
            {
                "name": "Smart Home Control Hub",
                "type": "simple",
                "status": "draft",
                "regular_price": "89.99",
                "description": "Central hub for whole-home smart automation, supports multiple protocols and voice control",
                "short_description": "Make your home smarter",
                "categories": [{"id": categories.get("Smart Home")}] if categories.get("Smart Home") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-20"},
                    {"key": "pre_order_discount", "value": "20"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=4)).isoformat(),
                "date_modified": (current_date - timedelta(hours=15)).isoformat()
            }
        ]

        # Sale product data (English versions)
        sale_products = [
            {
                "name": "Bluetooth Speaker Mini",
                "type": "simple",
                "status": "publish",
                "regular_price": "29.99",
                "sale_price": "19.99",
                "description": "Portable Bluetooth speaker with 360-degree surround sound and IPX7 waterproof rating",
                "short_description": "Your portable music companion",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=1)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=15)).isoformat(),
                "date_created": (current_date - timedelta(days=60)).isoformat(),
                "date_modified": (current_date - timedelta(days=1)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "USB-C Cable Set",
                "type": "simple",
                "status": "publish",
                "regular_price": "9.99",
                "sale_price": "5.99",
                "description": "High-speed charging cable set including 3ft, 6ft, and 10ft lengths",
                "short_description": "One set for all your needs",
                "categories": [{"id": categories.get("Accessories")}] if categories.get("Accessories") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=3)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=7)).isoformat(),
                "date_created": (current_date - timedelta(days=90)).isoformat(),
                "date_modified": (current_date - timedelta(days=3)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "Wireless Charging Pad",
                "type": "simple",
                "status": "publish",
                "regular_price": "19.99",
                "sale_price": "14.99",
                "description": "15W fast wireless charging pad supporting multiple devices simultaneously",
                "short_description": "Say goodbye to cables",
                "categories": [{"id": categories.get("Accessories")}] if categories.get("Accessories") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=2)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=20)).isoformat(),
                "date_created": (current_date - timedelta(days=120)).isoformat(),
                "date_modified": (current_date - timedelta(days=2)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "Laptop Stand",
                "type": "simple",
                "status": "publish",
                "regular_price": "15.99",
                "sale_price": "9.99",
                "description": "Ergonomic design with adjustable height and angle, made from premium aluminum alloy",
                "short_description": "Improve your workspace ergonomics",
                "categories": [{"id": categories.get("Office Supplies")}] if categories.get("Office Supplies") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=5)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=10)).isoformat(),
                "date_created": (current_date - timedelta(days=200)).isoformat(),
                "date_modified": (current_date - timedelta(days=5)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            }
        ]

        all_products = draft_products + sale_products

        created_count = 0
        failed_count = 0

        for product_data in all_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                product_type = 'unknown'

                # Extract product type
                meta_data = product_data.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') == 'product_type':
                        product_type = meta.get('value', 'unknown')
                        break

                self.created_products.append({
                    'id': product_id,
                    'name': product_name,
                    'type': product_type,
                    'status': product_data.get('status'),
                    'regular_price': product_data.get('regular_price'),
                    'sale_price': product_data.get('sale_price')
                })
                print(f"✅ Created product: {product_name} (ID: {product_id}, type: {product_type})")
                created_count += 1
            else:
                print(f"❌ Failed to create product: {product_data.get('name')} - {result}")
                failed_count += 1

            time.sleep(0.5)

        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "new_products_count": len([p for p in self.created_products if p.get('type') == 'new_product']),
            "sale_products_count": len([p for p in self.created_products if p.get('type') == 'sale_product'])
        }

        print(f"📊 Product creation finished:")
        print(f"   Successfully created: {created_count} products")
        print(f"   Failed creation: {failed_count} products")
        print(f"   New product count: {setup_result['new_products_count']}")
        print(f"   Sale product count: {setup_result['sale_products_count']}")

        return setup_result

    def create_test_customers_v2(self) -> Dict:
        """
        Create or update test customers' subscription preferences (V2 logic).
        New logic:
        1. Use '.welcome' suffix instead of timestamp
        2. Check if customer exists before creating. If exists, skip creation.
        3. Use 40 real customers from customer_emails.txt

        Strategy: If customer doesn't exist, create; if exists, skip creation.
        Randomly assign subscription preferences:
        - 60% subscribe to new product + discount alerts
        - 20% only discount alerts
        - 15% only new product alerts
        - 5% no alerts

        Returns:
            dict with create/update result
        """
        print("👥 Start creating or updating test customers' subscription preferences (V2 logic)...")

        # 40 real customer data - Using .welcome suffix
        customers_data = [
            ("Samuel", "Garcia", "samuel.garcia.welcome@mcptest.com"),
            ("Henry", "Nguyen", "henryn.welcome@mcptest.com"),
            ("Robert", "Collins", "robert.collins.welcome@mcptest.com"),
            ("Mark", "Allen", "allenm.welcome@mcptest.com"),
            ("Joshua", "Flores", "floresj.welcome@mcptest.com"),
            ("Mary", "Edwards", "mary.edwards57.welcome@mcptest.com"),
            ("Stephen", "Lewis", "slewis.welcome@mcptest.com"),
            ("Nicholas", "Wilson", "nwilson.welcome@mcptest.com"),
            ("Robert", "Johnson", "johnsonr.welcome@mcptest.com"),
            ("Deborah", "Wright", "deborahw99.welcome@mcptest.com"),
            ("Timothy", "Carter", "timothyc57.welcome@mcptest.com"),
            ("Kathleen", "Kelly", "kathleen_kelly.welcome@mcptest.com"),
            ("Andrew", "Ramos", "ramosa.welcome@mcptest.com"),
            ("Edward", "Davis", "edavis.welcome@mcptest.com"),
            ("Amanda", "Chavez", "amanda_chavez.welcome@mcptest.com"),
            ("Eric", "Murphy", "emurphy.welcome@mcptest.com"),
            ("Anthony", "Ortiz", "anthonyo.welcome@mcptest.com"),
            ("Marie", "Walker", "marie.walker.welcome@mcptest.com"),
            ("Samuel", "Sanders", "samuel_sanders77.welcome@mcptest.com"),
            ("Alexander", "Roberts", "alexanderr.welcome@mcptest.com"),
            ("Betty", "Cooper", "betty.cooper.welcome@mcptest.com"),
            ("Christina", "Adams", "adamsc.welcome@mcptest.com"),
            ("Martha", "Hill", "martha.hill.welcome@mcptest.com"),
            ("Michael", "Reed", "michael.reed.welcome@mcptest.com"),
            ("Emily", "Morris", "emorris.welcome@mcptest.com"),
            ("Timothy", "Gomez", "timothy_gomez54.welcome@mcptest.com"),
            ("Mary", "Torres", "maryt92.welcome@mcptest.com"),
            ("Shirley", "Mendoza", "mendozas52.welcome@mcptest.com"),
            ("Melissa", "Martin", "melissa.martin95.welcome@mcptest.com"),
            ("Thomas", "Sanchez", "thomas_sanchez8.welcome@mcptest.com"),
            ("Christina", "Harris", "harrisc.welcome@mcptest.com"),
            ("Scott", "Martin", "scottm.welcome@mcptest.com"),
            ("Tyler", "Roberts", "tyler_roberts72.welcome@mcptest.com"),
            ("Thomas", "Nelson", "tnelson.welcome@mcptest.com"),
            ("Steven", "Thomas", "sthomas.welcome@mcptest.com"),
            ("Raymond", "Bennett", "bennettr.welcome@mcptest.com"),
            ("Melissa", "Cruz", "mcruz.welcome@mcptest.com"),
            ("Sharon", "Lewis", "lewiss.welcome@mcptest.com"),
            ("Mary", "Alvarez", "alvarezm51.welcome@mcptest.com"),
            ("Emily", "Stewart", "stewarte98.welcome@mcptest.com")
        ]

        # Assign subscription patterns: make sure there are enough
        subscription_patterns = [
            # 60% subscribe new product + discount (24 customers)
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            # 20% only discount alerts (8 customers)
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            # 15% only new product alerts (6 customers)
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            # 5% neither (2 customers)
            {"new_product_alerts": False, "discount_alerts": False},
            {"new_product_alerts": False, "discount_alerts": False}
        ]

        created_count = 0
        updated_count = 0
        failed_count = 0

        print(f"🎯 Processing {len(customers_data)} customers...")

        for i, (first_name, last_name, email) in enumerate(customers_data):
            print(f"\n📝 Processing customer {i+1}/{len(customers_data)}: {email}")

            # Assign subscription preference
            subscription_pref = subscription_patterns[i] if i < len(subscription_patterns) else subscription_patterns[0]
            print(f"📋 Set subscription preference: {subscription_pref}")

            # Check if customer already exists
            print(f"🔍 Checking if customer exists: {email}")

            try:
                search_success, existing_customer = self.wc_client.search_customer_by_email(email)

                if search_success and existing_customer:
                    print(f"ℹ️ Customer already exists, skipping creation: {email} (ID: {existing_customer.get('id')})")

                    # Update existing customer's subscription preference
                    customer_id = existing_customer.get('id')
                    update_data = {
                        # Not sending meta_data, as it's not supported, just leaving as placeholder
                        # so the model should not send any one the so called subscription emails
                        # if it sends in accident, that's a mistake.
                    }

                    update_success, update_result = self.wc_client.update_customer(str(customer_id), update_data)
                    if update_success:
                        print(f"✅ Updated customer subscription preference: {email}")
                        updated_count += 1

                        self.created_customers.append({
                            'id': customer_id,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'new_product_alerts': subscription_pref.get('new_product_alerts', False),
                            'discount_alerts': subscription_pref.get('discount_alerts', False),
                            'action': 'updated'
                        })
                    else:
                        print(f"❌ Failed to update customer: {email} - {update_result}")
                        failed_count += 1
                else:
                    # Customer does not exist, create new customer
                    print(f"🆕 Creating new customer: {email}")
                    customer_data = {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        # No meta_data, as it's not supported
                        # so the model should not send any one the so called subscription emails
                        # if it sends in accident, that's a mistake.
                        "billing": {
                            "email": email,
                            "first_name": first_name,
                            "last_name": last_name
                        }
                    }

                    create_success, create_result = self.wc_client.create_customer(customer_data)
                    if create_success:
                        customer_id = create_result.get('id')
                        print(f"✅ Successfully created customer: {email} (ID: {customer_id})")
                        created_count += 1

                        self.created_customers.append({
                            'id': customer_id,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'new_product_alerts': subscription_pref.get('new_product_alerts', False),
                            'discount_alerts': subscription_pref.get('discount_alerts', False),
                            'action': 'created'
                        })
                    else:
                        print(f"❌ Failed to create customer: {email} - {create_result}")
                        failed_count += 1

            except Exception as e:
                print(f"❌ Exception processing customer {email}: {e}")
                failed_count += 1

            time.sleep(0.2)  # Avoid API rate limits

        # Count subscription stats
        new_product_count = len([c for c in self.created_customers if c.get('new_product_alerts', False)])
        discount_count = len([c for c in self.created_customers if c.get('discount_alerts', False)])

        print(f"\n📊 Customer processing complete:")
        print(f"   Created customers: {created_count}")
        print(f"   Updated customers: {updated_count}")
        print(f"   Failed: {failed_count}")
        print(f"   New product alert subscribers: {new_product_count}")
        print(f"   Discount alert subscribers: {discount_count}")

        success = failed_count == 0

        if not success:
            print("❌ Failed to set up test data for new product email task!")
        else:
            print("✅ Test data setup for new product email task successful!")

        return {
            "created_customers": created_count,
            "updated_customers": updated_count,
            "failed_customers": failed_count,
            "new_product_subscribers": new_product_count,
            "discount_subscribers": discount_count,
            "success": success
        }

    def get_expected_results(self) -> Dict:
        """Get the expected results for evaluation."""
        new_product_subscribers = [c for c in self.created_customers if c.get('new_product_alerts')]
        all_customers = self.created_customers
        new_products = [p for p in self.created_products if p.get('type') == 'new_product']
        sale_products = [p for p in self.created_products if p.get('type') == 'sale_product']

        return {
            "expected_new_products_count": len(new_products),
            "expected_sale_products_count": len(sale_products),
            "expected_appointment_emails": len(new_product_subscribers),
            "expected_discount_emails": len(all_customers),
            "new_product_subscriber_emails": [c.get('email') for c in new_product_subscribers],
            "all_customer_emails": [c.get('email') for c in all_customers],
            "new_products": new_products,
            "sale_products": sale_products,
            "total_customers": len(all_customers),
            "total_products": len(self.created_products)
        }


def main():
    """Main function - used for standalone test data setup."""
    # Read config from token config file
    from token_key_session import all_token_key_session

    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret

    print(f"🚀 Initializing New Product Email Setup V2: {site_url}")

    setup = NewProductEmailSetupV2(site_url, consumer_key, consumer_secret)

    # 1. Clear existing products and categories
    print("\n" + "="*60)
    print("Step 1: Clear products and categories in store")
    print("="*60)

    clear_result = setup.clear_all_data()

    if not clear_result.get('success'):
        print("⚠️ Data clear not fully successful, but continue with test data creation...")
        print(f"Clear detail: {clear_result}")

    # Wait for clear operation to finish
    print("⏳ Waiting 3 seconds to ensure clear operation is complete...")
    time.sleep(3)

    # 2. Create product categories
    print("\n" + "="*60)
    print("Step 2: Create product categories")
    print("="*60)

    categories = setup.create_product_categories()

    # 3. Create test products
    print("\n" + "="*60)
    print("Step 3: Create test products")
    print("="*60)

    product_result = setup.create_test_products(categories)

    # 4. Create or update customer subscription preferences (V2 logic)
    print("\n" + "="*60)
    print("Step 4: Create or update customer subscription preferences (V2 logic)")
    print("="*60)

    customer_result = setup.create_test_customers_v2()

    # 5. Save results
    if product_result.get('success') and customer_result.get('success'):
        print("\n✅ Test data setup for new product email task completed!")

        # Save expected results to task directory
        expected_results = setup.get_expected_results()
        results_dir = task_dir
        expected_results_path = os.path.join(results_dir, 'expected_results.json')
        with open(expected_results_path, 'w', encoding='utf-8') as f:
            json.dump(expected_results, f, indent=2, ensure_ascii=False)
        print(f"📄 Expected results saved to {expected_results_path}")

        # Save clear result to task directory
        clear_results_path = os.path.join(results_dir, 'clear_results.json')
        with open(clear_results_path, 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print(f"📄 Clear result saved to {clear_results_path}")

        # Save full setup result to task directory
        full_setup_result = {
            "clear_result": clear_result,
            "categories": categories,
            "product_result": product_result,
            "customer_result": customer_result,
            "expected_results": expected_results,
            "setup_timestamp": datetime.now().isoformat()
        }

        setup_results_path = os.path.join(results_dir, 'setup_results.json')
        with open(setup_results_path, 'w', encoding='utf-8') as f:
            json.dump(full_setup_result, f, indent=2, ensure_ascii=False)
        print(f"📄 Full setup result saved to {setup_results_path}")

        return True
    else:
        print("❌ Test data setup for new product email task failed!")
        return False


if __name__ == "__main__":
    import sys

    # Check command line arguments
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-only":
        # Only clear data
        from token_key_session import all_token_key_session

        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret

        setup = NewProductEmailSetupV2(site_url, consumer_key, consumer_secret)
        clear_result = setup.clear_all_data()

        clear_results_path = os.path.join(task_dir, 'clear_results.json')
        with open(clear_results_path, 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print(f"📄 Clear result saved to {clear_results_path}")

    else:
        # Full workflow: clear + create test data
        main()