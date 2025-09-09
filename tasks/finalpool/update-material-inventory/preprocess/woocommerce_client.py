#!/usr/bin/env python3
"""
WooCommerce客户端 - 用于设置测试产品
"""

import requests
from requests.auth import HTTPBasicAuth
import json
import logging
from typing import Dict, List, Optional, Tuple
from datetime import datetime

class WooCommerceClient:
    """WooCommerce API客户端"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化WooCommerce客户端
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: API消费者密钥
            consumer_secret: API消费者密钥
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        self.logger = self._setup_logging()
    
    def _setup_logging(self):
        """设置日志"""
        logging.basicConfig(level=logging.INFO)
        return logging.getLogger(__name__)
    
    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.session.get(f"{self.api_base}/system_status")
            return response.status_code == 200
        except Exception as e:
            self.logger.error(f"连接测试失败: {e}")
            return False
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """
        创建产品
        
        Args:
            product_data: 产品数据
            
        Returns:
            (成功标志, 结果数据)
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
        更新产品
        
        Args:
            product_id: 产品ID
            update_data: 更新数据
            
        Returns:
            (成功标志, 结果数据)
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
        获取产品信息
        
        Args:
            product_id: 产品ID
            
        Returns:
            (成功标志, 产品数据)
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
        """获取所有产品"""
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
                
                # 检查是否有更多页面
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                
                page += 1
            
            return all_products
            
        except Exception as e:
            self.logger.error(f"获取产品列表失败: {e}")
            return []
    
    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """
        删除产品
        
        Args:
            product_id: 产品ID
            force: 是否强制删除
            
        Returns:
            (成功标志, 结果数据)
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
        创建订单
        
        Args:
            order_data: 订单数据
            
        Returns:
            (成功标志, 结果数据)
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
        """获取所有订单"""
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
                
                # 检查是否有更多页面
                total_pages = int(response.headers.get('X-WP-TotalPages', 1))
                if page >= total_pages:
                    break
                
                page += 1
            
            return all_orders
            
        except Exception as e:
            self.logger.error(f"获取订单列表失败: {e}")
            return []
    
    def delete_order(self, order_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """
        删除订单
        
        Args:
            order_id: 订单ID
            force: 是否强制删除
            
        Returns:
            (成功标志, 结果数据)
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
        清空所有订单
        
        Returns:
            (成功标志, 删除的订单数量)
        """
        try:
            self.logger.info("🧹 开始清空所有订单...")
            
            # 获取所有订单
            orders = self.get_all_orders()
            deleted_count = 0
            
            for order in orders:
                order_id = str(order.get('id'))
                order_number = order.get('number', order_id)
                
                success, result = self.delete_order(order_id, force=True)
                if success:
                    deleted_count += 1
                    self.logger.info(f"🗑️ 删除订单: #{order_number} (ID: {order_id})")
                else:
                    self.logger.warning(f"⚠️ 删除订单失败: #{order_number} - {result}")
            
            self.logger.info(f"✅ 清空完成，共删除 {deleted_count} 个订单")
            return True, deleted_count
            
        except Exception as e:
            self.logger.error(f"清空订单失败: {e}")
            return False, 0