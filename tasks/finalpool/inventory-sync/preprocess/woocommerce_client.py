import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class WooCommerceClient:
    """WooCommerce API Client"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, version: str = "v3"):
        """
        Initialize WooCommerce API client

        Args:
            site_url: The base URL of your WooCommerce site (e.g., https://your-site.com)
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
            version: API version (default: v3)
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/{version}"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth

        # API rate limit: avoid exceeding rate limit
        self.request_delay = 0.5  # 500ms between each request
        self.last_request_time = 0

    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Dict]:
        """
        Make an API request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: URL parameters

        Returns:
            (success_flag, response_data)
        """
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        url = f"{self.api_base}/{endpoint.lstrip('/')}"

        try:
            headers = {"Content-Type": "application/json"}

            if method.upper() == 'GET':
                response = self.session.get(url, params=params, headers=headers)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params, headers=headers)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params, headers=headers)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params, headers=headers)
            else:
                return False, {"error": f"Unsupported HTTP method: {method}"}

            self.last_request_time = time.time()

            response.raise_for_status()
            return True, response.json()

        except requests.exceptions.RequestException as e:
            error_msg = f"API request failed: {str(e)}"
            if hasattr(e.response, 'text'):
                error_msg += f" - {e.response.text}"
            return False, {"error": error_msg}

    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """Get product information"""
        return self._make_request('GET', f'products/{product_id}')

    def list_products(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """Get product list"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'products', params=params)
        return success, data if isinstance(data, list) else []

    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """Create a product"""
        return self._make_request('POST', 'products', data=product_data)

    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """Update product information"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)

    def update_product_stock(self, product_id: str, stock_quantity: int, manage_stock: bool = True) -> Tuple[bool, Dict]:
        """
        Update product stock

        Args:
            product_id: Product ID
            stock_quantity: Stock quantity
            manage_stock: Whether to enable stock management
        """
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": manage_stock,
            "stock_status": "instock" if stock_quantity > 0 else "outofstock"
        }
        return self.update_product(product_id, data)

    def update_product_meta(self, product_id: str, meta_data: List[Dict]) -> Tuple[bool, Dict]:
        """
        Update product meta data

        Args:
            product_id: Product ID
            meta_data: List of meta data [{"key": "field_name", "value": "value"}]
        """
        data = {"meta_data": meta_data}
        return self.update_product(product_id, data)

    def update_total_sales(self, product_id: str, total_sales: int) -> Tuple[bool, Dict]:
        """Update product total sales"""
        meta_data = [
            {"key": "total_sales", "value": str(total_sales)},
            {"key": "_total_sales", "value": str(total_sales)}  # WordPress internal field
        ]
        return self.update_product_meta(product_id, meta_data)

    def update_product_with_sales(self, product_id: str, stock_quantity: int, total_sales: int) -> Tuple[bool, Dict]:
        """Update product stock and sales at the same time"""
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": True,
            "stock_status": "instock" if stock_quantity > 0 else "outofstock",
            "meta_data": [
                {"key": "total_sales", "value": str(total_sales)},
                {"key": "_total_sales", "value": str(total_sales)},
                {"key": "last_sync", "value": datetime.now().isoformat()},
                {"key": "sync_source", "value": "inventory_system"}
            ]
        }
        return self.update_product(product_id, data)

    def batch_update_products(self, updates: List[Dict]) -> Tuple[bool, Dict]:
        """
        Batch update products

        Args:
            updates: A list of update data [{"id": "product_id", "stock_quantity": qty}]
        """
        batch_data = {
            "update": updates
        }
        return self._make_request('POST', 'products/batch', data=batch_data)

    def get_product_variations(self, product_id: str) -> Tuple[bool, List[Dict]]:
        """Get product variation list"""
        success, data = self._make_request('GET', f'products/{product_id}/variations')
        return success, data if isinstance(data, list) else []

    def update_variation_stock(self, product_id: str, variation_id: str, stock_quantity: int) -> Tuple[bool, Dict]:
        """Update product variation stock"""
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": True,
            "stock_status": "instock" if stock_quantity > 0 else "outofstock"
        }
        return self._make_request('PUT', f'products/{product_id}/variations/{variation_id}', data=data)

class WooCommerceInventoryManager:
    """WooCommerce Inventory Manager"""

    def __init__(self, wc_client: WooCommerceClient):
        self.wc_client = wc_client
        self.region_prefixes = {
            "East": "EAST",
            "South": "SOUTH",
            "West": "WEST"
        }

    def initialize_regional_products(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        """
        Initialize products for each region

        Args:
            products: List of product dicts [{"id": "PROD001", "name": "Product Name", "price": 99.99}]

        Returns:
            Creation results for regional products
        """
        results = {}

        for region, prefix in self.region_prefixes.items():
            print(f"\n🌍 Initializing products for region {region}...")
            results[region] = []

            for product in products:
                # Create a unique product ID for each region
                regional_product_id = f"{prefix}_{product['id']}"

                # Set different initial stock, sales, and publish time according to region
                import random
                from datetime import datetime, timedelta

                if region == "East":
                    initial_stock = random.randint(100, 300)  # East has higher stock
                    initial_sales = random.randint(50, 150)   # East higher sales
                    # 30-day sales for East is relatively high
                    sales_30_days = random.randint(int(initial_sales * 0.15), int(initial_sales * 0.35))
                    # Released time earlier for East
                    days_ago = random.randint(180, 500)
                elif region == "South":
                    initial_stock = random.randint(80, 250)   # South has medium stock
                    initial_sales = random.randint(30, 100)   # South medium sales
                    # 30-day sales for South
                    sales_30_days = random.randint(int(initial_sales * 0.1), int(initial_sales * 0.3))
                    # Released time medium
                    days_ago = random.randint(120, 400)
                else:  # West
                    initial_stock = random.randint(60, 200)   # West has less stock
                    initial_sales = random.randint(20, 80)    # West lower sales
                    # West emerging market, 30-day sales grows faster
                    sales_30_days = random.randint(int(initial_sales * 0.2), int(initial_sales * 0.4))
                    # Released time more recent for West
                    days_ago = random.randint(60, 300)

                # Calculate region's release time
                regional_publish_date = datetime.now() - timedelta(days=days_ago)
                regional_publish_str = regional_publish_date.strftime("%Y-%m-%dT%H:%M:%S")

                product_data = {
                    "name": f"[{region}] {product['name']}",
                    "type": "simple",
                    "regular_price": str(product.get('price', 0)),
                    "description": f"{product.get('description', '')} - {region}RegionInventory",
                    "short_description": f"{region} region - {product['name']}",
                    "sku": regional_product_id,
                    "manage_stock": True,
                    "stock_quantity": initial_stock,
                    "stock_status": "instock",
                    "date_created": regional_publish_str,
                    "status": "publish",
                    "categories": [
                        {"name": product.get('category', 'Uncategorized')}
                    ],
                    "meta_data": [
                        {"key": "region", "value": region},
                        {"key": "original_product_id", "value": product['id']},
                        {"key": "last_sync", "value": datetime.now().isoformat()},
                        {"key": "regional_publish_date", "value": regional_publish_str},
                        {"key": "days_since_regional_launch", "value": str(days_ago)},
                        {"key": "total_sales", "value": str(initial_sales)},
                        {"key": "_total_sales", "value": str(initial_sales)},
                        {"key": "sales_last_30_days", "value": str(sales_30_days)},
                        {"key": "_sales_last_30_days", "value": str(sales_30_days)}
                    ]
                }

                success, response = self.wc_client.create_product(product_data)

                if success:
                    wc_product_id = response.get('id')
                    print(f"  ✅ Created product: {product['name']} (WC ID: {wc_product_id}, SKU: {regional_product_id})")
                    results[region].append({
                        'original_id': product['id'],
                        'wc_id': wc_product_id,
                        'sku': regional_product_id,
                        'success': True
                    })
                else:
                    print(f"  ❌ Failed to create product: {product['name']} - {response.get('error', 'Unknown error')}")
                    results[region].append({
                        'original_id': product['id'],
                        'sku': regional_product_id,
                        'success': False,
                        'error': response.get('error', 'Unknown error')
                    })

        return results

    def sync_regional_inventory(self, region_inventory: Dict[str, Dict[str, int]], product_mapping: Dict[str, Dict[str, str]]) -> Dict:
        """
        Synchronize RegionInventory to WooCommerce

        Args:
            region_inventory: RegionInventory data {"East": {"PROD001": 100}}
            product_mapping: Product mapping {"East": {"PROD001": "wc_product_id"}}

        Returns:
            Sync results
        """
        sync_results = {}

        for region, products in region_inventory.items():
            print(f"\n📦 Syncing {region} RegionInventory...")
            sync_results[region] = {}

            if region not in product_mapping:
                print(f"  ⚠️ No product mapping found for region: {region}")
                continue

            # Prepare batch update data
            batch_updates = []

            for product_id, quantity in products.items():
                if product_id not in product_mapping[region]:
                    print(f"  ⚠️ No mapping found for product: {product_id}")
                    continue

                wc_product_id = product_mapping[region][product_id]

                batch_updates.append({
                    "id": wc_product_id,
                    "stock_quantity": quantity,
                    "manage_stock": True,
                    "stock_status": "instock" if quantity > 0 else "outofstock",
                    "meta_data": [
                        {"key": "last_sync", "value": datetime.now().isoformat()},
                        {"key": "sync_source", "value": "warehouse_system"}
                    ]
                })

            if batch_updates:
                # Perform batch update
                success, response = self.wc_client.batch_update_products(batch_updates)

                if success:
                    updated_products = response.get('update', [])
                    print(f"  ✅ Batch update succeeded: {len(updated_products)} products")

                    for update in updated_products:
                        product_name = update.get('name', 'Unknown')
                        stock_qty = update.get('stock_quantity', 0)
                        sync_results[region][update['id']] = {
                            'name': product_name,
                            'quantity': stock_qty,
                            'success': True
                        }
                else:
                    print(f"  ❌ Batch update failed: {response.get('error', 'Unknown error')}")
                    sync_results[region]['batch_error'] = response.get('error', 'Unknown error')
            else:
                print(f"  ⚠️ No products to update for region {region}")

        return sync_results

    def verify_inventory_sync(self, expected_inventory: Dict[str, Dict[str, int]], product_mapping: Dict[str, Dict[str, str]]) -> Dict:
        """
        Verify inventory sync result

        Args:
            expected_inventory: Expected inventory data
            product_mapping: Product mapping

        Returns:
            Verification result
        """
        verification_results = {}

        for region, products in expected_inventory.items():
            print(f"\n🔍 Verifying {region} RegionInventory...")
            verification_results[region] = {}

            if region not in product_mapping:
                continue

            for product_id, expected_qty in products.items():
                if product_id not in product_mapping[region]:
                    continue

                wc_product_id = product_mapping[region][product_id]

                # Get actual stock from WooCommerce
                success, product_data = self.wc_client.get_product(wc_product_id)

                if success:
                    actual_qty = product_data.get('stock_quantity', 0)
                    is_match = actual_qty == expected_qty

                    verification_results[region][product_id] = {
                        'expected': expected_qty,
                        'actual': actual_qty,
                        'match': is_match,
                        'product_name': product_data.get('name', 'Unknown')
                    }

                    status = "✅" if is_match else "❌"
                    print(f"  {status} {product_data.get('name', 'Unknown')}: Expected {expected_qty}, Actual {actual_qty}")
                else:
                    verification_results[region][product_id] = {
                        'expected': expected_qty,
                        'actual': None,
                        'match': False,
                        'error': product_data.get('error', 'Fetch failed')
                    }
                    print(f"  ❌ Failed to get product: {product_id} - {product_data.get('error', 'Unknown error')}")

        return verification_results

# Example configuration
class WooCommerceConfig:
    """WooCommerce config class"""

    # Test environment config (replace with actual values)
    SITE_URL = "https://your-test-site.com"
    CONSUMER_KEY = "ck_your_consumer_key_here"
    CONSUMER_SECRET = "cs_your_consumer_secret_here"

    # Production environment config (replace with actual values)
    PROD_SITE_URL = "https://your-production-site.com"
    PROD_CONSUMER_KEY = "ck_your_production_consumer_key_here"
    PROD_CONSUMER_SECRET = "cs_your_production_consumer_secret_here"

    @classmethod
    def get_test_client(cls) -> WooCommerceClient:
        """Get test environment client"""
        return WooCommerceClient(
            site_url=cls.SITE_URL,
            consumer_key=cls.CONSUMER_KEY,
            consumer_secret=cls.CONSUMER_SECRET
        )

    @classmethod
    def get_production_client(cls) -> WooCommerceClient:
        """Get production environment client"""
        return WooCommerceClient(
            site_url=cls.PROD_SITE_URL,
            consumer_key=cls.PROD_CONSUMER_KEY,
            consumer_secret=cls.PROD_CONSUMER_SECRET
        )

if __name__ == "__main__":
    # Example test
    print("🧪 WooCommerce API Client test")

    # Note: Please configure correct API keys before running
    try:
        client = WooCommerceConfig.get_test_client()

        # Test getting product list
        print("\n📦 Getting product list...")
        success, products = client.list_products(per_page=5)

        if success:
            print(f"✅ Successfully got {len(products)} products")
            for product in products[:3]:
                print(f"  - {product.get('name', 'Unknown')} (ID: {product.get('id')}, Stock: {product.get('stock_quantity', 'N/A')})")
        else:
            print(f"❌ Failed to get product list: {products.get('error', 'Unknown error')}")

    except Exception as e:
        print(f"❌ Test failed: {e}")
        print("Please make sure your WooCommerce API keys are configured correctly")
