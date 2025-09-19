import requests
from requests.auth import HTTPBasicAuth
from requests_oauthlib import OAuth1
import time
from typing import Dict, List, Optional, Tuple, Any


class WooCommerceClient:
    """General-purpose WooCommerce API client"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str,
                 version: str = "v3", request_delay: float = 0.5):
        """
        Initialize WooCommerce client

        Args:
            site_url: WooCommerce site URL (e.g., https://your-site.com)
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
            version: API version (default: v3)
            request_delay: Delay between requests in seconds
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/{version}"
        self.wp_api_base = f"{self.site_url}/wp-json/wp/v2"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.request_delay = request_delay
        self.last_request_time = 0

    def _make_request(self, method: str, endpoint: str, data: Dict = None,
                     params: Dict = None) -> Tuple[bool, Dict]:
        """
        Make API request

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
        headers = {"Content-Type": "application/json"}

        response = None
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

    def _make_wp_request(self, method: str, endpoint: str, data: Dict = None,
                        params: Dict = None) -> Tuple[bool, Dict]:
        """Make WordPress API request"""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.request_delay:
            time.sleep(self.request_delay - time_since_last)

        url = f"{self.wp_api_base}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}

        # Use OAuth1 authentication for WordPress REST API as well
        auth = OAuth1(self.consumer_key, self.consumer_secret)

        response = None
        if method.upper() == 'GET':
            response = self.session.get(url, params=params, headers=headers, auth=auth)
        elif method.upper() == 'POST':
            response = self.session.post(url, json=data, params=params, headers=headers, auth=auth)
        elif method.upper() == 'PUT':
            response = self.session.put(url, json=data, params=params, headers=headers, auth=auth)
        elif method.upper() == 'DELETE':
            response = self.session.delete(url, params=params, headers=headers, auth=auth)
        else:
            return False, {"error": f"Unsupported HTTP method: {method}"}

        self.last_request_time = time.time()
        response.raise_for_status()
        return True, response.json()

    # Product operations
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """Get product by ID"""
        return self._make_request('GET', f'products/{product_id}')

    def list_products(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """Get products list with pagination"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'products', params=params)
        return success, data if isinstance(data, list) else []

    def get_all_products(self) -> List[Dict]:
        """Get all products using pagination"""
        all_products = []
        page = 1
        per_page = 100

        while True:
            success, products = self.list_products(page=page, per_page=per_page)
            if not success or not products:
                break

            all_products.extend(products)

            if len(products) < per_page:
                break

            page += 1

        return all_products

    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """Create new product"""
        return self._make_request('POST', 'products', data=product_data)

    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """Update product by ID"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)

    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete product by ID"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/{product_id}', params=params)

    def batch_update_products(self, updates: List[Dict]) -> Tuple[bool, Dict]:
        """Batch update products"""
        batch_data = {"update": updates}
        return self._make_request('POST', 'products/batch', data=batch_data)

    def batch_delete_products(self, product_ids: List[Dict], batch_size: int = 50) -> Tuple[bool, Dict]:
        """Batch delete products"""
        for i in range(0, len(product_ids), batch_size):
            batch = product_ids[i:i + batch_size]
            batch_data = {"delete": [{'id': item['id']} for item in batch]}
            success, result = self._make_request('POST', 'products/batch', data=batch_data)
            if not success:
                return False, result
        return True, {}

    def batch_create_products(self, product_data: List[Dict], batch_size: int = 50) -> Tuple[bool, Dict]:
        """Batch create products"""
        for i in range(0, len(product_data), batch_size):
            batch = product_data[i:i + batch_size]
            batch_data = {"create": batch}
            success, result = self._make_request('POST', 'products/batch', data=batch_data)
            if not success:
                return False, result
        return True, {}

    # Category operations
    def get_product_categories(self) -> Tuple[bool, List[Dict]]:
        """Get product categories list"""
        return self._make_request('GET', 'products/categories')

    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """Create product category"""
        return self._make_request('POST', 'products/categories', data=category_data)

    def update_category(self, category_id: str, category_data: Dict) -> Tuple[bool, Dict]:
        """Update product category"""
        return self._make_request('PUT', f'products/categories/{category_id}', data=category_data)

    def delete_category(self, category_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete product category"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/categories/{category_id}', params=params)

    def batch_delete_categories(self, category_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete product categories"""
        deleted_count = 0
        for category_id in category_ids:
            success, result = self.delete_category(str(category_id), force=True)
            if success:
                deleted_count += 1
        return True, {"deleted": deleted_count}

    # Tag operations
    def get_product_tags(self) -> Tuple[bool, List[Dict]]:
        """Get product tags list"""
        return self._make_request('GET', 'products/tags')

    def delete_tag(self, tag_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete product tag"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/tags/{tag_id}', params=params)

    def batch_delete_tags(self, tag_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete product tags"""
        deleted_count = 0
        for tag_id in tag_ids:
            success, result = self.delete_tag(str(tag_id), force=True)
            if success:
                deleted_count += 1
        return True, {"deleted": deleted_count}

    # Attribute operations
    def get_product_attributes(self) -> Tuple[bool, List[Dict]]:
        """Get product attributes list"""
        return self._make_request('GET', 'products/attributes')

    def delete_attribute(self, attribute_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete product attribute"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/attributes/{attribute_id}', params=params)

    def batch_delete_attributes(self, attribute_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete product attributes"""
        deleted_count = 0
        for attribute_id in attribute_ids:
            success, result = self.delete_attribute(str(attribute_id), force=True)
            if success:
                deleted_count += 1
        return True, {"deleted": deleted_count}

    # Coupon operations
    def get_coupons(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """Get coupons list"""
        return self._make_request('GET', 'coupons', params={'per_page': per_page})

    def delete_coupon(self, coupon_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete coupon"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'coupons/{coupon_id}', params=params)

    def batch_delete_coupons(self, coupon_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete coupons"""
        deleted_count = 0
        for coupon_id in coupon_ids:
            success, result = self.delete_coupon(str(coupon_id), force=True)
            if success:
                deleted_count += 1
        return True, {"deleted": deleted_count}

    # Order operations
    def get_orders(self, page: int = 1, per_page: int = 100, status: str = 'any') -> Tuple[bool, List[Dict]]:
        """Get orders list with pagination"""
        params = {'page': page, 'per_page': per_page, 'status': status}
        return self._make_request('GET', 'orders', params=params)

    def get_all_orders(self) -> List[Dict]:
        """Get all orders using pagination"""
        all_orders = []
        page = 1
        per_page = 100

        while True:
            success, orders = self.get_orders(page=page, per_page=per_page)
            if not success or not orders:
                break

            all_orders.extend(orders)

            if len(orders) < per_page:
                break

            page += 1

        return all_orders

    def delete_order(self, order_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete order"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'orders/{order_id}', params=params)

    def batch_delete_orders(self, order_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete orders"""
        deleted_count = 0
        for order_id in order_ids:
            success, result = self.delete_order(str(order_id), force=True)
            if success:
                deleted_count += 1
        return True, {"deleted": deleted_count}

    # Customer operations
    def get_customers(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """Get customers list"""
        return self._make_request('GET', 'customers', params={'per_page': per_page})

    def delete_customer(self, customer_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete customer"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'customers/{customer_id}', params=params)

    def batch_delete_customers(self, customer_ids: List[int], batch_size: int = 20) -> Tuple[bool, Dict]:
        """Batch delete customers (skip admin users)"""
        deleted_count = 0
        skipped_count = 0

        success, customers = self.get_customers()
        if not success:
            return False, {"error": "Cannot get customers list"}

        customer_dict = {c['id']: c for c in customers}

        for customer_id in customer_ids:
            customer = customer_dict.get(customer_id)
            if customer and customer.get('role') == 'administrator':
                skipped_count += 1
                continue

            success, result = self.delete_customer(str(customer_id), force=True)
            if success:
                deleted_count += 1

        return True, {"deleted": deleted_count, "skipped": skipped_count}

    # Shipping operations
    def get_shipping_zones(self) -> Tuple[bool, List[Dict]]:
        """Get shipping zones list"""
        return self._make_request('GET', 'shipping/zones')

    def delete_shipping_zone(self, zone_id: str) -> Tuple[bool, Dict]:
        """Delete shipping zone"""
        return self._make_request('DELETE', f'shipping/zones/{zone_id}')

    def batch_delete_shipping_zones(self, exclude_default: bool = True) -> Tuple[bool, Dict]:
        """Batch delete shipping zones"""
        success, zones = self.get_shipping_zones()
        if not success:
            return False, {"error": "Cannot get shipping zones list"}

        deleted_count = 0
        for zone in zones:
            if exclude_default and zone.get('id') == 0:
                continue

            success, result = self.delete_shipping_zone(str(zone['id']))
            if success:
                deleted_count += 1

        return True, {"deleted": deleted_count}

    # Tax operations
    def get_taxes(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """Get taxes list"""
        return self._make_request('GET', 'taxes', params={'per_page': per_page})

    def delete_tax(self, tax_id: str) -> Tuple[bool, Dict]:
        """Delete tax"""
        return self._make_request('DELETE', f'taxes/{tax_id}')

    def batch_delete_taxes(self) -> Tuple[bool, Dict]:
        """Batch delete taxes"""
        success, taxes = self.get_taxes()
        if not success:
            return False, {"error": "Cannot get taxes list"}

        deleted_count = 0
        for tax in taxes:
            success, result = self.delete_tax(str(tax['id']))
            if success:
                deleted_count += 1

        return True, {"deleted": deleted_count}

    # WordPress posts operations
    def get_posts(self, page: int = 1, per_page: int = 100, status: str = 'publish') -> Tuple[bool, List[Dict]]:
        """Get posts list"""
        params = {'page': page, 'per_page': per_page, 'status': status}
        return self._make_wp_request('GET', 'posts', params=params)

    def delete_post(self, post_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete post"""
        params = {'force': force} if force else {}
        return self._make_wp_request('DELETE', f'posts/{post_id}', params=params)

    def batch_delete_posts(self, exclude_hello_world: bool = True) -> Tuple[bool, Dict]:
        """Batch delete posts"""
        success, posts = self.get_posts()
        if not success:
            return False, {"error": "Cannot get posts list"}

        deleted_count = 0
        skipped_count = 0

        for post in posts:
            if exclude_hello_world and 'hello-world' in post.get('slug', '').lower():
                skipped_count += 1
                continue

            success, result = self.delete_post(str(post['id']), force=True)
            if success:
                deleted_count += 1

        return True, {"deleted": deleted_count, "skipped": skipped_count}

    # Store reset functionality
    def reset_to_empty_store(self, confirm: bool = False) -> Dict[str, Any]:
        """
        Complete reset store to empty state

        Args:
            confirm: Confirm to execute reset (prevent accidental operation)

        Returns:
            Reset result dictionary
        """
        if not confirm:
            return {
                "success": False,
                "error": "Need confirmation parameter confirm=True to execute reset operation",
                "warning": "This operation will delete all store data, irreversible!"
            }

        from datetime import datetime

        reset_results = {
            "timestamp": datetime.now().isoformat(),
            "operations": {}
        }

        # 1. Delete all products
        reset_results["operations"]["products"] = self._reset_delete_all_products()

        # 2. Delete all product categories (except default)
        reset_results["operations"]["categories"] = self._reset_delete_all_categories()

        # 3. Delete all product tags
        reset_results["operations"]["tags"] = self._reset_delete_all_tags()

        # 4. Delete all product attributes
        reset_results["operations"]["attributes"] = self._reset_delete_all_attributes()

        # 5. Delete all coupons
        reset_results["operations"]["coupons"] = self._reset_delete_all_coupons()

        # 6. Delete all orders
        reset_results["operations"]["orders"] = self._reset_delete_all_orders()

        # 7. Delete all customers (keep admin users)
        reset_results["operations"]["customers"] = self._reset_delete_all_customers()

        # 8. Clear shipping settings
        reset_results["operations"]["shipping"] = self._reset_clear_shipping_settings()

        # 9. Clear tax settings
        reset_results["operations"]["taxes"] = self._reset_clear_tax_settings()

        # 10. Delete all blog posts (keep default posts)
        reset_results["operations"]["posts"] = self._reset_delete_all_posts()

        # Calculate overall result
        all_success = all(
            result.get("success", False)
            for result in reset_results["operations"].values()
        )

        reset_results["success"] = all_success
        reset_results["summary"] = self._generate_reset_summary(reset_results["operations"])

        return reset_results

    def _reset_delete_all_products(self) -> Dict:
        """Delete all products using batch operations"""
        all_products = self.get_all_products()
        if not all_products:
            return {"success": True, "deleted": 0, "message": "No products to delete"}

        product_ids = [{"id": product["id"]} for product in all_products]
        success, result = self.batch_delete_products(product_ids, batch_size=50)

        return {
            "success": success,
            "deleted": len(all_products) if success else 0,
            "failed": 0 if success else len(all_products),
            "message": f"Processed {len(all_products)} products"
        }

    def _reset_delete_all_categories(self) -> Dict:
        """Delete all product categories (keep Uncategorized)"""
        success, categories = self.get_product_categories()
        if not success:
            return {"success": False, "error": "Cannot get categories list"}

        # Filter out default category
        deletable_categories = [
            cat["id"] for cat in categories
            if cat.get('slug') != 'uncategorized' and cat.get('name') != 'Uncategorized'
        ]

        if not deletable_categories:
            return {"success": True, "deleted": 0, "skipped": len(categories)}

        success, result = self.batch_delete_categories(deletable_categories)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "skipped": len(categories) - len(deletable_categories),
            "message": f"Processed {len(deletable_categories)} categories"
        }

    def _reset_delete_all_tags(self) -> Dict:
        """Delete all product tags"""
        success, tags = self.get_product_tags()
        if not success:
            return {"success": False, "error": "Cannot get tags list"}

        if not tags:
            return {"success": True, "deleted": 0}

        tag_ids = [tag["id"] for tag in tags]
        success, result = self.batch_delete_tags(tag_ids)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": f"Processed {len(tag_ids)} tags"
        }

    def _reset_delete_all_attributes(self) -> Dict:
        """Delete all product attributes"""
        success, attributes = self.get_product_attributes()
        if not success:
            return {"success": False, "error": "Cannot get attributes list"}

        if not attributes:
            return {"success": True, "deleted": 0}

        attribute_ids = [attr["id"] for attr in attributes]
        success, result = self.batch_delete_attributes(attribute_ids)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": f"Processed {len(attribute_ids)} attributes"
        }

    def _reset_delete_all_coupons(self) -> Dict:
        """Delete all coupons"""
        success, coupons = self.get_coupons()
        if not success:
            return {"success": False, "error": "Cannot get coupons list"}

        if not coupons:
            return {"success": True, "deleted": 0}

        coupon_ids = [coupon["id"] for coupon in coupons]
        success, result = self.batch_delete_coupons(coupon_ids)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": f"Processed {len(coupon_ids)} coupons"
        }

    def _reset_delete_all_orders(self) -> Dict:
        """Delete all orders"""
        all_orders = self.get_all_orders()
        if not all_orders:
            return {"success": True, "deleted": 0}

        order_ids = [order["id"] for order in all_orders]
        success, result = self.batch_delete_orders(order_ids, batch_size=20)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": f"Processed {len(order_ids)} orders"
        }

    def _reset_delete_all_customers(self) -> Dict:
        """Delete all customers (keep admin users)"""
        success, customers = self.get_customers()
        if not success:
            return {"success": False, "error": "Cannot get customers list"}

        if not customers:
            return {"success": True, "deleted": 0, "skipped": 0}

        customer_ids = [customer["id"] for customer in customers]
        success, result = self.batch_delete_customers(customer_ids)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "skipped": result.get("skipped", 0) if success else 0,
            "message": f"Processed {len(customer_ids)} customers"
        }

    def _reset_clear_shipping_settings(self) -> Dict:
        """Clear shipping settings"""
        success, result = self.batch_delete_shipping_zones(exclude_default=True)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": "Shipping zones cleared"
        }

    def _reset_clear_tax_settings(self) -> Dict:
        """Clear tax settings"""
        success, result = self.batch_delete_taxes()

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "message": "Tax rates cleared"
        }

    def _reset_delete_all_posts(self) -> Dict:
        """Delete all blog posts (keep Hello World)"""
        success, result = self.batch_delete_posts(exclude_hello_world=True)

        return {
            "success": success,
            "deleted": result.get("deleted", 0) if success else 0,
            "skipped": result.get("skipped", 0) if success else 0,
            "message": "Blog posts cleared"
        }

    def _generate_reset_summary(self, operations: Dict) -> str:
        """Generate reset summary"""
        summary_lines = []

        for operation, result in operations.items():
            if result.get("success"):
                deleted = result.get("deleted", 0)
                if deleted > 0:
                    summary_lines.append(f"✅ {operation}: deleted {deleted} items")
                else:
                    summary_lines.append(f"✅ {operation}: cleared")
            else:
                summary_lines.append(f"❌ {operation}: failed - {result.get('error', 'unknown error')}")

        return "\n".join(summary_lines)