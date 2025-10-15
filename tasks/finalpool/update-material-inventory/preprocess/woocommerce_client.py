#!/usr/bin/env python3


import requests
from requests.auth import HTTPBasicAuth
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class WooCommerceClient:
    """WooCommerce API Client"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize WooCommerce client
        
        Args:
            site_url: WooCommerce site URL (e.g., https://your-site.com)
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """Setup logging"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def test_connection(self) -> bool:
        """Test API connection"""
        try:
            response = self.session.get(f"{self.api_base}/system_status")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"Connection test failed: {e}")
            return False
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """
        Create product
        
        Args:
            product_data: Product data
            
        Returns:
            (Success flag, Result data)
        """
        try:
            response = self.session.post(
                f"{self.api_base}/products",
                json=product_data,
                timeout=30
            )
            
            if response.status_code == 201:
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def update_product(self, product_id: str, update_data: Dict) -> Tuple[bool, Dict]:
        """
        Update product
        
        Args:
            product_id: Product ID
            update_data: Update data
            
        Returns:
            (Success flag, Result data)
        """
        try:
            response = self.session.put(
                f"{self.api_base}/products/{product_id}",
                json=update_data,
                timeout=30
            )
            
            if response.status_code == 200:
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """
        Get product information
        
        Args:
            product_id: Product ID
            
        Returns:
            (Success flag, Product data)
        """
        try:
            response = self.session.get(f"{self.api_base}/products/{product_id}")
            
            if response.status_code == 200:
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        try:
            all_products = []
            page = 1
            per_page = 100
            
            while True:
                response = self.session.get(
                    f"{self.api_base}/products",
                    params={
                        'page': page,
                        'per_page': per_page,
                        'status': 'any'
                    }
                )
                
                if response.status_code != 200:
                    break
                
                products = response.json()
                if not products:
                    break
                
                all_products.extend(products)
                
                # Check if there are more pages
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                
                page += 1
            
            return all_products
            
        except Exception as e:
            self.logger.error(f"Failed to get product list: {e}")
            return []
    
    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """
        Delete product
        
        Args:
            product_id: Product ID
            force: Whether to force delete
            
        Returns:
            (Success flag, Result data)
        """
        try:
            params = {'force': 'true'} if force else {}
            response = self.session.delete(
                f"{self.api_base}/products/{product_id}",
                params=params
            )
            
            if response.status_code in [200, 204]:
                return True, response.json() if response.text else {}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """
        Create order
        
        Args:
            order_data: Order data
            
        Returns:
            (Success flag, Result data)
        """
        try:
            response = self.session.post(
                f"{self.api_base}/orders",
                json=order_data,
                timeout=30
            )
            
            if response.status_code == 201:
                return True, response.json()
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def get_all_orders(self) -> List[Dict]:
        """Get all orders"""
        try:
            all_orders = []
            page = 1
            per_page = 100
            
            while True:
                response = self.session.get(
                    f"{self.api_base}/orders",
                    params={
                        'page': page,
                        'per_page': per_page,
                        'status': 'any'
                    }
                )
                
                if response.status_code != 200:
                    break
                
                orders = response.json()
                if not orders:
                    break
                
                all_orders.extend(orders)
                
                # Check if there are more pages
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                
                page += 1
            
            return all_orders
            
        except Exception as e:
            self.logger.error(f"Failed to get order list: {e}")
            return []
    
    def delete_order(self, order_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """
        Delete order
        
        Args:
            order_id: Order ID
            force: Whether to force delete
            
        Returns:
            (Success flag, Result data)
        """
        try:
            params = {'force': 'true'} if force else {}
            response = self.session.delete(
                f"{self.api_base}/orders/{order_id}",
                params=params
            )
            
            if response.status_code in [200, 204]:
                return True, response.json() if response.text else {}
            else:
                error_msg = f"HTTP {response.status_code}: {response.text}"
                return False, error_msg
                
        except Exception as e:
            return False, str(e)
    
    def clear_all_orders(self) -> Tuple[bool, int]:
        """
        Clear all orders
        
        Returns:
            (Success flag, Number of deleted orders)
        """
        try:
            self.logger.info("🧹 Starting to clear all orders...")
            
            # Get all orders
            orders = self.get_all_orders()
            deleted_count = 0
            
            for order in orders:
                order_id = str(order.get('id'))
                order_number = order.get('number', order_id)
                
                success, result = self.delete_order(order_id, force=True)
                if success:
                    deleted_count += 1
                    self.logger.info(f"🗑️ Deleted order: #{order_number} (ID: {order_id})")
                else:
                    self.logger.warning(f"⚠️ Failed to delete order: #{order_number} - {result}")
            
            self.logger.info(f"✅ Cleared all orders, {deleted_count} orders deleted")
            return True, deleted_count
            
        except Exception as e:
            self.logger.error(f"Failed to clear orders: {e}")
            return False, 0