import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

from woocommerce_client import WooCommerceClient, WooCommerceInventoryManager
from database_setup import generate_sample_products
from clear_all_products import main as clear_all_products
from token_key_session import all_token_key_session

class WooCommerceStoreInitializer:
    """
    WooCommerce Store Initializer - Set up 6-city, 3-region inventory system from a blank account.

    Supported cities: New York, Boston (East), Dallas, Houston (South), LA, San Francisco (West)
    """

    def __init__(self):
        """
        Initializer - uses preconfigured API credentials.
        """
        self.site_url = all_token_key_session.woocommerce_site_url.rstrip('/')
        self.wc_client = None
        self.consumer_key = None
        self.consumer_secret = None

        print(f"🚀 Initializing WooCommerce store: {self.site_url}")

    def setup_api_credentials(self) -> Tuple[bool, str]:
        """
        Set up API credentials - uses preconfigured API keys directly.
        """
        print("🔑 Using preconfigured API credentials...")

        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret

        if consumer_key and consumer_secret:
            self.consumer_key = consumer_key
            self.consumer_secret = consumer_secret

            # Initialize WooCommerce client
            self.wc_client = WooCommerceClient(
                self.site_url,
                self.consumer_key,
                self.consumer_secret
            )

            # Test API connection
            success, response = self.wc_client.list_products(per_page=1)
            if success:
                print("✅ API connection test succeeded")
                return True, "API credentials set successfully"
            else:
                print(f"❌ API connection test failed: {response}")
                return False, "API connection test failed"
        else:
            return False, "Valid API credentials not provided"

    def create_product_categories(self) -> Dict[str, int]:
        """Create product categories"""
        print("📂 Creating product categories...")

        categories = [
            {"name": "Electronic Products", "description": "Mobile phones, computers, digital devices, etc."},
            {"name": "Clothing, Shoes & Accessories", "description": "Clothing, shoes, accessories, etc."},
            {"name": "Home & Living", "description": "Furniture, home appliances, household items, etc."},
            {"name": "Sports & Outdoors", "description": "Sports equipment, outdoor gear, etc."},
            {"name": "Beauty & Personal Care", "description": "Cosmetics, skincare, personal care products, etc."}
        ]

        created_categories = {}

        for category in categories:
            # Create category via API
            category_data = {
                "name": category["name"],
                "description": category["description"],
                "display": "default",
                "image": None,
                "menu_order": 0,
                "parent": 0
            }

            success, response = self.wc_client._make_request('POST', 'products/categories', data=category_data)

            if success:
                category_id = response.get('id')
                created_categories[category["name"]] = category_id
                print(f"  ✅ Created category: {category['name']} (ID: {category_id})")
            else:
                print(f"  ❌ Failed to create category: {category['name']} - {response.get('error', 'Unknown error')}")

        return created_categories

    def create_sample_products(self, categories: Dict[str, int]) -> List[Dict]:
        """Create sample products"""
        print("🛍️ Creating sample products...")

        # Get sample product data
        sample_products = generate_sample_products()
        created_products = []

        # Category mapping
        category_mapping = {
            "Electronic Products": categories.get("Electronic Products"),
            "Clothing, Shoes & Accessories": categories.get("Clothing, Shoes & Accessories"),
            "Home & Living": categories.get("Home & Living")
        }

        for product_id, name, category, price, description in sample_products:
            category_id = category_mapping.get(category, categories.get("Electronic Products"))

            # Generate realistic initial stock, sales, and publish date
            import random
            from datetime import datetime, timedelta

            initial_stock = random.randint(50, 200)

            # Set different sales ranges depending on product type
            if category == "Electronic Products":
                initial_sales = random.randint(100, 500)  # Higher sales for electronics
                sales_30_days = random.randint(int(initial_sales * 0.1), int(initial_sales * 0.3))
                days_ago = random.randint(30, 180)  # Published within last 6 months
            elif category == "Clothing, Shoes & Accessories":
                initial_sales = random.randint(80, 300)   # Medium sales for clothing
                sales_30_days = random.randint(int(initial_sales * 0.05), int(initial_sales * 0.4))
                days_ago = random.randint(60, 365)        # Published within last year
            else:
                initial_sales = random.randint(20, 150)   # Lower sales for others
                sales_30_days = random.randint(int(initial_sales * 0.03), int(initial_sales * 0.2))
                days_ago = random.randint(90, 730)        # Published within last 2 years

            # Calculate publish date
            publish_date = datetime.now() - timedelta(days=days_ago)
            publish_date_str = publish_date.strftime("%Y-%m-%dT%H:%M:%S")

            product_data = {
                "name": "(Test Product) " + name,
                "type": "simple",
                "regular_price": str(price),
                "description": description,
                "short_description": f"High quality {name}, in stock",
                "sku": product_id,
                "manage_stock": True,
                "stock_quantity": initial_stock,
                "stock_status": "instock",
                "date_created": publish_date_str,  # Set publish time
                "status": "publish",  # Ensure product is published
                "categories": [{"id": category_id}] if category_id else [],
                "images": [],  # Images can be added later
                "attributes": [],
                "meta_data": [
                    {"key": "original_product_id", "value": product_id},
                    {"key": "created_by", "value": "inventory_sync_system"},
                    {"key": "creation_date", "value": datetime.now().isoformat()},
                    {"key": "publish_date", "value": publish_date_str},
                    {"key": "days_since_publish", "value": str(days_ago)},
                    {"key": "total_sales", "value": str(initial_sales)},
                    {"key": "_total_sales", "value": str(initial_sales)},
                    {"key": "sales_last_30_days", "value": str(sales_30_days)},
                    {"key": "_sales_last_30_days", "value": str(sales_30_days)}
                ]
            }

            success, response = self.wc_client.create_product(product_data)

            if success:
                wc_product_id = response.get('id')
                created_products.append({
                    'original_id': product_id,
                    'wc_id': wc_product_id,
                    'name': name,
                    'sku': product_id,
                    'category': category,
                    'price': price,
                    'success': True
                })
                print(f"  ✅ Created product: {name} (WC ID: {wc_product_id}, SKU: {product_id})")
            else:
                print(f"  ❌ Failed to create product: {name} - {response.get('error', 'Unknown error')}")
                created_products.append({
                    'original_id': product_id,
                    'name': name,
                    'sku': product_id,
                    'success': False,
                    'error': response.get('error', 'Unknown error')
                })

        return created_products

    def setup_regional_inventory_system(self, base_products: List[Dict]) -> Dict:
        """Set up RegionInventory system"""
        print("🗺️ Setting up RegionInventory system...")

        if not self.wc_client:
            return {"error": "WooCommerce client not initialized"}

        # Initialize inventory manager
        wc_manager = WooCommerceInventoryManager(self.wc_client)

        # Create product variants for each region
        regional_setup_results = {}

        # Convert base products to regional product format
        products_for_regions = []
        for product in base_products:
            if product['success']:
                products_for_regions.append({
                    'id': product['original_id'],
                    'name': product['name'],
                    'price': product['price'],
                    'description': f"Regional inventory product - {product['name']}",
                    'category': product.get('category', 'Uncategorized')
                })

        if products_for_regions:
            # Initialize products for each region
            regional_products = wc_manager.initialize_regional_products(products_for_regions)
            regional_setup_results['regional_products'] = regional_products

            # Create product mapping table
            product_mapping = {}
            for region, products in regional_products.items():
                product_mapping[region] = {}
                for product in products:
                    if product['success']:
                        product_mapping[region][product['original_id']] = str(product['wc_id'])

            regional_setup_results['product_mapping'] = product_mapping

        return regional_setup_results

    def configure_store_settings(self) -> bool:
        """Configure basic store settings"""
        print("⚙️ Configuring basic store settings...")

        try:
            # Configure inventory management settings
            settings_data = {
                "manage_stock": "yes",
                "notifications": "yes",
                "stock_email_recipient": "admin@example.com",
                "low_stock_amount": 5,
                "out_of_stock_amount": 0,
                "out_of_stock_visibility": "visible"
            }

            # Note: WooCommerce settings API may require special permissions
            print("  ℹ️ Inventory management settings should be configured manually via WooCommerce admin panel.")
            print("  📍 Path: WooCommerce > Settings > Products > Inventory")
            print("  ✅ It's recommended to enable stock management and low stock notifications.")

            return True

        except Exception as e:
            print(f"  ⚠️ Automatic configuration failed: {e}")
            print("  📝 Please configure inventory settings manually in WooCommerce Admin")
            return False

    def run_full_initialization(self) -> Dict:
        """Run full store initialization process"""
        print("🚀 Starting full WooCommerce store initialization...")
        print("=" * 60)

        results = {
            "success": False,
            "steps": {},
            "errors": []
        }

        try:
            # Step 1: Set up API credentials
            print("\n📋 Step 1: Set up API credentials")
            api_success, api_message = self.setup_api_credentials()
            results["steps"]["api_setup"] = {"success": api_success, "message": api_message}

            if not api_success:
                results["errors"].append(f"API setup failed: {api_message}")
                return results

            # Step 2: Create product categories
            print("\n📋 Step 2: Create product categories")
            categories = self.create_product_categories()
            results["steps"]["categories"] = {"success": len(categories) > 0, "data": categories}

            # Step 3: Create sample products
            print("\n📋 Step 3: Create sample products")
            products = self.create_sample_products(categories)
            successful_products = [p for p in products if p['success']]
            results["steps"]["products"] = {
                "success": len(successful_products) > 0,
                "data": products,
                "count": len(successful_products)
            }

            # Step 4: Set up RegionInventory system
            print("\n📋 Step 4: Set up RegionInventory system")
            regional_setup = self.setup_regional_inventory_system(successful_products)
            results["steps"]["regional_setup"] = {"success": "product_mapping" in regional_setup, "data": regional_setup}

            # Step 5: Configure store settings
            print("\n📋 Step 5: Configure store settings")
            settings_success = self.configure_store_settings()
            results["steps"]["store_settings"] = {"success": settings_success}

            # Check overall success
            results["success"] = all([
                api_success,
                len(categories) > 0,
                len(successful_products) > 0,
                "product_mapping" in regional_setup
            ])

            if results["success"]:
                print("\n🎉 WooCommerce store initialization completed!")
                print("=" * 60)
                print(f"✅ {len(categories)} product categories created")
                print(f"✅ {len(successful_products)} base products created")
                print(f"✅ Region inventory system set for 3 regions")
                print("✅ System is ready for inventory synchronization")
                print(results)
                self._save_configuration(results)
            else:
                print("\n❌ There were errors during initialization, please check error messages.")

        except Exception as e:
            results["errors"].append(f"Exception during initialization: {e}")
            print(f"❌ Initialization failed: {e}")

        return results

    def _save_configuration(self, results: Dict):
        """Save configuration information to file"""
        config_data = {
            "site_url": self.site_url,
            "consumer_key": self.consumer_key,
            "consumer_secret": self.consumer_secret,
            "initialization_date": datetime.now().isoformat(),
            "product_mapping": results["steps"]["regional_setup"]["data"].get("product_mapping", {}),
            "categories": results["steps"]["categories"]["data"],
            "products": results["steps"]["products"]["data"]
        }

        config_file = all_token_key_session.woocommerce_config_file
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            print(f"📝 Configuration information saved to: {config_file}")
        except Exception as e:
            print(f"⚠️ Failed to save configuration file: {e}")

def main():
    """Main function - interactive initializer"""
    print("🛒 WooCommerce 6-City Inventory System Initializer")
    print("Supported cities: New York, Boston (East), Dallas, Houston (South), LA, San Francisco (West)")
    print("=" * 60)

    # Clear existing products
    clear_all_products()

    # Start initialization
    initializer = WooCommerceStoreInitializer()
    results = initializer.run_full_initialization()

    if results["success"]:
        print("\n🎯 Next steps:")
        print("1. Run database initialization: database_setup")
        print("2. Start inventory sync: inventory_sync")
        print("3. Run full evaluation: evaluation.main")
    else:
        print("\n🔧 Troubleshooting:")
        print("1. Check that the site URL is correct")
        print("2. Confirm username and password are correct")
        print("3. Ensure WooCommerce plugin is installed and active")
        print("4. Confirm that the site supports REST API")

    return results

if __name__ == "__main__":
    main()
