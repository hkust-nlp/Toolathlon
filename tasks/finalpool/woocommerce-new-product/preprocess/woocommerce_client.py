import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class WooCommerceClient:
    """WooCommerce API Client"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize WooCommerce API client

        Args:
            site_url: WooCommerce site URL
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret

        # Create session
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NewProductEmail-Setup/1.0'
        })

        print(f"🔗 WooCommerce client initialized: {self.site_url}")

    def _make_request(self, method: str, endpoint: str, data=None, params=None) -> Tuple[bool, Dict]:
        """
        Send API request

        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            endpoint: API endpoint
            data: Request data
            params: URL parameters

        Returns:
            (success flag, response data/error info)
        """
        endpoint = endpoint.lstrip('/')
        url = f"{self.api_base}/{endpoint}"

        try:
            if method.upper() == 'GET':
                response = self.session.get(url, params=params)
            elif method.upper() == 'POST':
                response = self.session.post(url, json=data, params=params)
            elif method.upper() == 'PUT':
                response = self.session.put(url, json=data, params=params)
            elif method.upper() == 'DELETE':
                response = self.session.delete(url, params=params)
            else:
                return False, {"error": f"Unsupported HTTP method: {method}"}

            if response.status_code in [200, 201, 204]:
                try:
                    return True, response.json() if response.content else {}
                except json.JSONDecodeError:
                    return True, {}
            else:
                try:
                    error_data = response.json()
                    return False, {
                        "error": error_data.get('message', f'HTTP {response.status_code}'),
                        "code": error_data.get('code', response.status_code),
                        "data": error_data.get('data', {})
                    }
                except json.JSONDecodeError:
                    return False, {
                        "error": f"HTTP {response.status_code}: {response.text}",
                        "code": response.status_code
                    }

        except requests.exceptions.RequestException as e:
            return False, {"error": f"Request Exception: {str(e)}"}
        except Exception as e:
            return False, {"error": f"Unknown Error: {str(e)}"}

    def test_connection(self) -> Tuple[bool, str]:
        """Test API connection"""
        success, response = self._make_request('GET', 'system_status')
        if success:
            return True, "API connection test successful"
        else:
            return False, f"API connection test failed: {response.get('error', 'Unknown error')}"

    # Product-related methods
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """Create a product"""
        return self._make_request('POST', 'products', data=product_data)

    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """Get a single product"""
        return self._make_request('GET', f'products/{product_id}')

    def get_all_products(self, per_page: int = 100) -> List[Dict]:
        """Get all products"""
        all_products = []
        page = 1

        while True:
            success, response = self._make_request('GET', 'products', params={
                'per_page': per_page,
                'page': page
            })

            if not success:
                print(f"Failed to get product list: {response.get('error', 'Unknown error')}")
                break

            if not response or len(response) == 0:
                break

            all_products.extend(response)

            # If returned products are less than per_page, we've reached the end
            if len(response) < per_page:
                break

            page += 1
            time.sleep(0.1)  # Avoid API rate limiting

        return all_products

    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """Update a product"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)

    def delete_product(self, product_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """Delete a product"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'products/{product_id}', params=params)

    def list_products(self, per_page: int = 10, page: int = 1, **kwargs) -> Tuple[bool, List[Dict]]:
        """List products"""
        params = {
            'per_page': per_page,
            'page': page,
            **kwargs
        }
        return self._make_request('GET', 'products', params=params)

    # Category-related methods
    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """Create a product category"""
        return self._make_request('POST', 'products/categories', data=category_data)

    def get_product_categories(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """Get list of product categories"""
        return self._make_request('GET', 'products/categories', params={'per_page': per_page})

    def delete_category(self, category_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """Delete a product category"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'products/categories/{category_id}', params=params)

    # Customer-related methods
    def create_customer(self, customer_data: Dict) -> Tuple[bool, Dict]:
        """Create a customer"""
        return self._make_request('POST', 'customers', data=customer_data)

    def get_customer(self, customer_id: str) -> Tuple[bool, Dict]:
        """Get a single customer"""
        return self._make_request('GET', f'customers/{customer_id}')

    def search_customer_by_email(self, email: str) -> Tuple[bool, Optional[Dict]]:
        """Search customer by email"""
        # Method 1: Use search parameter
        success, response = self._make_request('GET', 'customers', params={'search': email})
        if success and response:
            for customer in response:
                if customer.get('email', '').lower() == email.lower():
                    return True, customer

        # Method 2: Try the email parameter (supported in some WooCommerce versions)
        success, response = self._make_request('GET', 'customers', params={'email': email})
        if success and response:
            if isinstance(response, list) and len(response) > 0:
                return True, response[0]
            elif isinstance(response, dict):
                return True, response

        # Method 3: Fetch all customers and match (as a last resort)
        success, all_customers = self.get_all_customers(per_page=100)
        if success:
            for customer in all_customers:
                if customer.get('email', '').lower() == email.lower():
                    return True, customer

        return False, None

    def get_all_customers(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """Get all customers"""
        all_customers = []
        page = 1

        while True:
            params = {
                'per_page': per_page,
                'page': page,
                'orderby': 'id',
                'order': 'asc'
            }

            success, response = self._make_request('GET', 'customers', params=params)

            if not success:
                print(f"Failed to get customer list (page {page}): {response.get('error', 'Unknown error')}")
                # Try other approach
                if page == 1:
                    # Try looser parameter set
                    success, response = self._make_request('GET', 'customers', params={'per_page': per_page})
                    if not success:
                        return False, []
                else:
                    return False, []

            if not response or len(response) == 0:
                break

            all_customers.extend(response)

            if len(response) < per_page:
                break

            page += 1
            time.sleep(0.1)

        return True, all_customers

    def update_customer(self, customer_id: str, customer_data: Dict) -> Tuple[bool, Dict]:
        """Update a customer"""
        return self._make_request('PUT', f'customers/{customer_id}', data=customer_data)

    def delete_customer(self, customer_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """Delete a customer"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'customers/{customer_id}', params=params)

    # Order-related methods
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """Create an order"""
        return self._make_request('POST', 'orders', data=order_data)

    def get_order(self, order_id: str) -> Tuple[bool, Dict]:
        """Get a single order"""
        return self._make_request('GET', f'orders/{order_id}')

    def list_orders(self, per_page: int = 10, **kwargs) -> Tuple[bool, List[Dict]]:
        """List orders"""
        params = {
            'per_page': per_page,
            **kwargs
        }
        return self._make_request('GET', 'orders', params=params)

    def update_order(self, order_id: str, order_data: Dict) -> Tuple[bool, Dict]:
        """Update an order"""
        return self._make_request('PUT', f'orders/{order_id}', data=order_data)

    def delete_order(self, order_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """Delete an order"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'orders/{order_id}', params=params)


def test_client():
    """Test client functionality"""
    # Please use real WooCommerce site info here
    site_url = "http://localhost:10003/store97"
    consumer_key = "ck_woocommerce_token_walkers147a"
    consumer_secret = "cs_woocommerce_token_walkers147a"

    client = WooCommerceClient(site_url, consumer_key, consumer_secret)

    # Test connection
    success, message = client.test_connection()
    print(f"Connection test: {message}")

    if success:
        # Test get product list
        success, products = client.list_products(per_page=5)
        if success:
            print(f"Retrieved {len(products)} products")
        else:
            print(f"Failed to get products: {products}")


if __name__ == "__main__":
    test_client()