#!/usr/bin/env python3
"""
WooCommerce客户端 - 用于库存预警任务的WooCommerce连接和产品管理
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
    
    def clear_all_products(self) -> Tuple[bool, int]:
        """
        清空所有产品
        
        Returns:
            (成功标志, 删除的产品数量)
        """
        try:
            self.logger.info("🧹 开始清空所有产品...")
            
            # 获取所有产品
            products = self.get_all_products()
            deleted_count = 0
            
            for product in products:
                product_id = str(product.get('id'))
                product_name = product.get('name', f'产品ID-{product_id}')
                
                success, result = self.delete_product(product_id, force=True)
                if success:
                    deleted_count += 1
                    self.logger.info(f"🗑️ 删除产品: {product_name} (ID: {product_id})")
                else:
                    self.logger.warning(f"⚠️ 删除产品失败: {product_name} - {result}")
            
            self.logger.info(f"✅ 清空完成，共删除 {deleted_count} 个产品")
            return True, deleted_count
            
        except Exception as e:
            self.logger.error(f"清空产品失败: {e}")
            return False, 0
    
    def setup_stock_alert_products(self, products_data: List[Dict]) -> Tuple[bool, List[Dict]]:
        """
        设置库存预警测试产品
        
        Args:
            products_data: 产品数据列表
            
        Returns:
            (成功标志, 创建的产品列表)
        """
        try:
            self.logger.info("📦 开始设置库存预警测试产品...")
            created_products = []
            
            for product_info in products_data:
                # 转换为WooCommerce产品格式
                wc_product = {
                    "name": product_info.get("name"),
                    "sku": product_info.get("sku"),
                    "type": "simple",
                    "regular_price": str(product_info.get("price", 0)),
                    "stock_quantity": product_info.get("stock_quantity", 0),
                    "manage_stock": True,
                    "stock_status": "instock" if product_info.get("stock_quantity", 0) > 0 else "outofstock",
                    "status": "publish",
                    "categories": [
                        {"name": product_info.get("category", "General")}
                    ],
                    "meta_data": [
                        {
                            "key": "stock_threshold",
                            "value": str(product_info.get("stock_threshold", 10))
                        },
                        {
                            "key": "supplier_name", 
                            "value": product_info.get("supplier", {}).get("name", "")
                        },
                        {
                            "key": "supplier_contact",
                            "value": product_info.get("supplier", {}).get("contact", "")
                        },
                        {
                            "key": "supplier_id",
                            "value": product_info.get("supplier", {}).get("supplier_id", "")
                        }
                    ]
                }
                
                success, result = self.create_product(wc_product)
                if success:
                    created_products.append(result)
                    self.logger.info(f"✅ 创建产品: {product_info.get('name')} (库存: {product_info.get('stock_quantity')}, 阈值: {product_info.get('stock_threshold')})")
                else:
                    self.logger.error(f"❌ 创建产品失败: {product_info.get('name')} - {result}")
            
            self.logger.info(f"📊 设置完成，共创建 {len(created_products)} 个测试产品")
            return True, created_products
            
        except Exception as e:
            self.logger.error(f"设置产品失败: {e}")
            return False, []
    
    def get_low_stock_products(self) -> List[Dict]:
        """
        获取库存低于安全阈值的产品
        
        Returns:
            低库存产品列表
        """
        try:
            all_products = self.get_all_products()
            low_stock_products = []
            
            for product in all_products:
                stock_quantity = product.get('stock_quantity', 0)
                
                # 获取库存阈值（从meta_data中）
                stock_threshold = 10  # 默认值
                meta_data = product.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') == 'stock_threshold':
                        try:
                            stock_threshold = int(meta.get('value', 10))
                        except (ValueError, TypeError):
                            stock_threshold = 10
                        break
                
                # 检查是否低于阈值
                if stock_quantity < stock_threshold:
                    low_stock_products.append({
                        'id': product.get('id'),
                        'name': product.get('name'),
                        'sku': product.get('sku'),
                        'stock_quantity': stock_quantity,
                        'stock_threshold': stock_threshold,
                        'supplier_info': self._extract_supplier_info(product.get('meta_data', []))
                    })
            
            self.logger.info(f"🔍 发现 {len(low_stock_products)} 个低库存产品")
            return low_stock_products
            
        except Exception as e:
            self.logger.error(f"获取低库存产品失败: {e}")
            return []
    
    def _extract_supplier_info(self, meta_data: List[Dict]) -> Dict:
        """从产品meta_data中提取供应商信息"""
        supplier_info = {}
        for meta in meta_data:
            key = meta.get('key', '')
            value = meta.get('value', '')
            
            if key == 'supplier_name':
                supplier_info['name'] = value
            elif key == 'supplier_contact':
                supplier_info['contact'] = value
            elif key == 'supplier_id':
                supplier_info['supplier_id'] = value
        
        return supplier_info