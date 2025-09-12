import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

class WooCommerceClient:
    """WooCommerce API客户端 - 用于产品召回任务"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, version: str = "v3"):
        """
        初始化WooCommerce客户端
        
        Args:
            site_url: WooCommerce网站URL (例如: https://your-site.com)
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
            version: API版本 (默认: v3)
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/{version}"
        self.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session = requests.Session()
        self.session.auth = self.auth
        
        # API调用限制 (避免超过速率限制)
        self.request_delay = 0.5  # 每次请求间隔500ms
        self.last_request_time = 0
    
    def _make_request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Tuple[bool, Dict]:
        """
        发送API请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点
            data: 请求数据
            params: URL参数
            
        Returns:
            (成功标志, 响应数据)
        """
        # 控制请求频率
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
                return False, {"error": f"不支持的HTTP方法: {method}"}
            
            self.last_request_time = time.time()
            
            response.raise_for_status()
            return True, response.json()
            
        except requests.exceptions.RequestException as e:
            error_msg = f"API请求失败: {str(e)}"
            if hasattr(e.response, 'text'):
                error_msg += f" - {e.response.text}"
            return False, {"error": error_msg}
    
    # Product related methods
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """获取商品信息"""
        return self._make_request('GET', f'products/{product_id}')
    
    def list_products(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """获取商品列表"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'products', params=params)
        return success, data if isinstance(data, list) else []
    
    def get_all_products(self) -> List[Dict]:
        """获取所有商品（分页获取）"""
        all_products = []
        page = 1
        per_page = 100
        
        while True:
            success, products = self.list_products(page=page, per_page=per_page)
            if not success or not products:
                break
            
            all_products.extend(products)
            
            # 如果返回的商品数量少于per_page，说明已经是最后一页
            if len(products) < per_page:
                break
            
            page += 1
        
        print(f"📦 获取到 {len(all_products)} 个商品")
        return all_products
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """Created product"""
        return self._make_request('POST', 'products', data=product_data)
    
    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """更新商品信息"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)
    
    def delete_product(self, product_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """删除商品"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'products/{product_id}', params=params)
    
    # Category related methods
    def get_product_categories(self) -> Tuple[bool, List[Dict]]:
        """获取商品分类列表"""
        return self._make_request('GET', 'products/categories')
    
    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """Created product分类"""
        return self._make_request('POST', 'products/categories', data=category_data)
    
    # Order related methods
    def get_order(self, order_id: str) -> Tuple[bool, Dict]:
        """获取订单信息"""
        return self._make_request('GET', f'orders/{order_id}')
    
    def list_orders(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """获取订单列表"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'orders', params=params)
        return success, data if isinstance(data, list) else []
    
    def get_all_orders(self, status: str = None) -> List[Dict]:
        """获取所有订单（分页获取）"""
        all_orders = []
        page = 1
        per_page = 100
        
        while True:
            params = {}
            if status:
                params['status'] = status
                
            success, orders = self.list_orders(page=page, per_page=per_page, **params)
            if not success or not orders:
                break
            
            all_orders.extend(orders)
            
            # 如果返回的订单数量少于per_page，说明已经是最后一页
            if len(orders) < per_page:
                break
            
            page += 1
        
        print(f"📋 获取到 {len(all_orders)} 个订单")
        return all_orders
    
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """创建订单"""
        return self._make_request('POST', 'orders', data=order_data)
    
    def update_order(self, order_id: str, order_data: Dict) -> Tuple[bool, Dict]:
        """更新订单信息"""
        return self._make_request('PUT', f'orders/{order_id}', data=order_data)
    
    def delete_order(self, order_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """删除订单"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'orders/{order_id}', params=params)
    
    # Customer related methods
    def get_customer(self, customer_id: str) -> Tuple[bool, Dict]:
        """获取客户信息"""
        return self._make_request('GET', f'customers/{customer_id}')
    
    def list_customers(self, page: int = 1, per_page: int = 100, **kwargs) -> Tuple[bool, List[Dict]]:
        """获取客户列表"""
        params = {
            'page': page,
            'per_page': per_page,
            **kwargs
        }
        success, data = self._make_request('GET', 'customers', params=params)
        return success, data if isinstance(data, list) else []
    
    def create_customer(self, customer_data: Dict) -> Tuple[bool, Dict]:
        """创建客户"""
        return self._make_request('POST', 'customers', data=customer_data)
    
    def update_customer(self, customer_id: str, customer_data: Dict) -> Tuple[bool, Dict]:
        """更新客户信息"""
        return self._make_request('PUT', f'customers/{customer_id}', data=customer_data)
    
    def delete_customer(self, customer_id: str, force: bool = True) -> Tuple[bool, Dict]:
        """Delete customer"""
        params = {'force': force} if force else {}
        return self._make_request('DELETE', f'customers/{customer_id}', params=params)
    
    # Batch operations
    def batch_update_products(self, updates: List[Dict]) -> Tuple[bool, Dict]:
        """批量更新商品"""
        batch_data = {
            "update": updates
        }
        return self._make_request('POST', 'products/batch', data=batch_data)


class ProductRecallDataSetup:
    """产品召回数据初始化器"""
    
    def __init__(self, wc_client: WooCommerceClient):
        """
        初始化数据设置器
        
        Args:
            wc_client: WooCommerce客户端实例
        """
        self.wc_client = wc_client
        self.created_products = []
        self.created_customers = []
        self.created_orders = []
        self.recalled_product_model = "Smartphone Model X1"
    
    def clear_all_data(self) -> Dict:
        """
        彻底清理商店中的所有数据
        
        Returns:
            清理结果字典
        """
        print("🧹 Starting thorough cleanup of all store data...")
        
        results = {
            "products": {"deleted": 0, "failed": 0},
            "orders": {"deleted": 0, "failed": 0},
            "customers": {"deleted": 0, "failed": 0},
            "categories": {"deleted": 0, "failed": 0},
            "success": True,
            "timestamp": datetime.now().isoformat()
        }
        
        try:
            # 1. Batch delete all orders
            print("📋 Batch deleting all orders...")
            results["orders"] = self._batch_delete_orders()
            
            # 2. Batch delete all products 
            print("📦 Batch deleting all products...")
            results["products"] = self._batch_delete_products()
            
            # 3. Delete custom categories
            print("📂 Deleting custom categories...")
            results["categories"] = self._batch_delete_categories()
            
            # 4. Delete test customers
            print("👥 Deleting test customers...")
            results["customers"] = self._delete_test_customers()
            
            # 判断整体成功状态
            if (results["products"]["failed"] > 0 or 
                results["orders"]["failed"] > 0 or 
                results["customers"]["failed"] > 0 or
                results["categories"]["failed"] > 0):
                results["success"] = False
            
            print(f"\n📊 Thorough cleanup completed:")
            print(f"   Products: deleted {results['products']['deleted']}, failed {results['products']['failed']}")
            print(f"   Orders: deleted {results['orders']['deleted']}, failed {results['orders']['failed']}")
            print(f"   Categories: deleted {results['categories']['deleted']}, failed {results['categories']['failed']}")
            print(f"   Customers: deleted {results['customers']['deleted']}, failed {results['customers']['failed']}")
            
            return results
            
        except Exception as e:
            results["success"] = False
            results["error"] = str(e)
            print(f"❌ Error during cleanup process: {e}")
            return results
    
    def _batch_delete_products(self) -> Dict:
        """批量删除所有商品"""
        all_products = self.wc_client.get_all_products()
        if not all_products:
            return {"deleted": 0, "failed": 0}
        
        deleted_count = 0
        failed_count = 0
        batch_size = 50  # 批量大小
        
        print(f"   Found {len(all_products)} products, starting batch deletion...")
        
        # 分批删除
        for i in range(0, len(all_products), batch_size):
            batch = all_products[i:i + batch_size]
            batch_updates = [{"id": product["id"]} for product in batch]
            
            try:
                success, result = self.wc_client.batch_update_products([])
                # 使用单独的批量删除请求
                batch_data = {"delete": batch_updates}
                success, result = self.wc_client._make_request('POST', 'products/batch', data=batch_data)
                
                if success and "delete" in result:
                    for item in result["delete"]:
                        if "error" not in item:
                            deleted_count += 1
                        else:
                            failed_count += 1
                            print(f"     ❌ Failed to delete product: {item.get('id')} - {item['error']['message']}")
                else:
                    failed_count += len(batch)
                    print(f"     ❌ Batch deletion failed: {result}")
                
                print(f"   Batch {i//batch_size + 1}: processing {len(batch)} products")
                time.sleep(1)  # 避免API限制
                
            except Exception as e:
                failed_count += len(batch)
                print(f"   ❌ Batch deletion error: {e}")
        
        return {"deleted": deleted_count, "failed": failed_count}
    
    def _batch_delete_orders(self) -> Dict:
        """批量删除所有订单"""
        all_orders = self.wc_client.get_all_orders()
        if not all_orders:
            return {"deleted": 0, "failed": 0}
        
        deleted_count = 0
        failed_count = 0
        
        print(f"   找到 {len(all_orders)} 个订单，开始逐个删除...")
        
        # 订单通常需要逐个删除，因为批量操作可能不稳定
        for order in all_orders:
            try:
                success, result = self.wc_client.delete_order(str(order["id"]), force=True)
                if success:
                    deleted_count += 1
                    if deleted_count % 10 == 0:
                        print(f"     已删除 {deleted_count} 个订单...")
                else:
                    failed_count += 1
                    print(f"     ❌ Failed to delete order: {order['id']} - {result}")
                
                time.sleep(0.2)  # 控制删除速度
                
            except Exception as e:
                failed_count += 1
                print(f"     ❌ Error deleting order: {order['id']} - {e}")
        
        return {"deleted": deleted_count, "failed": failed_count}
    
    def _batch_delete_categories(self) -> Dict:
        """删除自定义分类（保留默认分类）"""
        try:
            success, all_categories = self.wc_client.get_product_categories()
            if not success or not all_categories:
                return {"deleted": 0, "failed": 0}
            
            # 过滤掉默认分类
            deletable_categories = [
                cat for cat in all_categories 
                if cat.get('id') != 15 and cat.get('slug') != 'uncategorized'
            ]
            
            if not deletable_categories:
                print("   No custom categories to delete")
                return {"deleted": 0, "failed": 0}
            
            deleted_count = 0
            failed_count = 0
            
            print(f"   找到 {len(deletable_categories)} 个自定义分类...")
            
            for category in deletable_categories:
                try:
                    success, result = self.wc_client._make_request(
                        'DELETE', f'products/categories/{category["id"]}', params={'force': True}
                    )
                    if success:
                        deleted_count += 1
                        print(f"     ✅ Delete category: {category.get('name')}")
                    else:
                        failed_count += 1
                        print(f"     ❌ Failed to delete category: {category.get('name')} - {result}")
                    
                    time.sleep(0.3)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"     ❌ Error deleting category: {category.get('name')} - {e}")
            
            return {"deleted": deleted_count, "failed": failed_count}
            
        except Exception as e:
            print(f"   ❌ Failed to get category list: {e}")
            return {"deleted": 0, "failed": 0}
    
    def _delete_test_customers(self) -> Dict:
        """删除测试客户"""
        try:
            success, customers = self.wc_client.list_customers(per_page=100)
            if not success:
                return {"deleted": 0, "failed": 0}
            
            # 只删除召回任务的测试客户
            test_customers = [
                c for c in customers 
                if c.get('email', '').startswith('test_recall_')
            ]
            
            if not test_customers:
                print("   No test customers found for recall task")
                return {"deleted": 0, "failed": 0}
            
            deleted_count = 0
            failed_count = 0
            
            print(f"   找到 {len(test_customers)} 个测试客户...")
            
            for customer in test_customers:
                try:
                    success, result = self.wc_client.delete_customer(str(customer["id"]), force=True)
                    if success:
                        deleted_count += 1
                        print(f"     ✅ Delete customer: {customer.get('email')}")
                    else:
                        failed_count += 1
                        print(f"     ❌ Failed to delete customer: {customer.get('email')} - {result}")
                    
                    time.sleep(0.3)
                    
                except Exception as e:
                    failed_count += 1
                    print(f"     ❌ Error deleting customer: {customer.get('email')} - {e}")
            
            return {"deleted": deleted_count, "failed": failed_count}
            
        except Exception as e:
            print(f"   ❌ Failed to get customer list: {e}")
            return {"deleted": 0, "failed": 0}
    
    def create_recalled_products(self) -> Dict:
        """
        Creating products that need to be recalled
        
        Returns:
            创建结果字典
        """
        print("📱 Creating products that need to be recalled...")
        
        # 定义召回产品数据
        recalled_products = [
            {
                "name": f"{self.recalled_product_model} - Black Edition",
                "type": "simple",
                "regular_price": "999.99",
                "description": "Smartphone, needs to be recalled due to battery issues",
                "short_description": "Premium smartphone",
                "sku": "PHONE-X1-BLACK",
                "stock_quantity": 9,  # 已售完
                "manage_stock": True,
                "stock_status": "outofstock",
                "date_created": (datetime.now() - timedelta(days=180)).isoformat(),
                "meta_data": [
                    {"key": "recall_reason", "value": "Battery safety hazard"},
                    {"key": "recall_status", "value": "need_recall"},
                    {"key": "total_sales", "value": "150"},
                    {"key": "_total_sales", "value": "150"}
                ]
            },
            {
                "name": f"{self.recalled_product_model} - White Edition",
                "type": "simple",
                "regular_price": "999.99",
                "description": "Smartphone, needs to be recalled due to battery issues",
                "short_description": "Premium smartphone",
                "sku": "PHONE-X1-WHITE",
                "stock_quantity": 8,  # 已售完
                "manage_stock": True,
                "stock_status": "outofstock",
                "date_created": (datetime.now() - timedelta(days=180)).isoformat(),
                "meta_data": [
                    {"key": "recall_reason", "value": "Battery safety hazard"},
                    {"key": "recall_status", "value": "need_recall"},
                    {"key": "total_sales", "value": "120"},
                    {"key": "_total_sales", "value": "120"}
                ]
            },
            {
                "name": f"{self.recalled_product_model} - Blue Edition",
                "type": "simple",
                "regular_price": "999.99",
                "description": "Smartphone, needs to be recalled due to battery issues",
                "short_description": "Premium smartphone",
                "sku": "PHONE-X1-BLUE",
                "stock_quantity": 6,  # 已售完
                "manage_stock": True,
                "stock_status": "outofstock",
                "date_created": (datetime.now() - timedelta(days=180)).isoformat(),
                "meta_data": [
                    {"key": "recall_reason", "value": "Battery safety hazard"},
                    {"key": "recall_status", "value": "need_recall"},
                    {"key": "total_sales", "value": "90"},
                    {"key": "_total_sales", "value": "90"}
                ]
            }
        ]
        
        # 创建正常商品（作为对照）
        normal_products = [
            {
                "name": "Smartphone Model Y2",
                "type": "simple",
                "regular_price": "799.99",
                "description": "Normal smartphone for sale",
                "short_description": "High value smartphone",
                "sku": "PHONE-Y2",
                "stock_quantity": 50,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (datetime.now() - timedelta(days=90)).isoformat(),
            },
            {
                "name": "Premium Bluetooth Headphones",
                "type": "simple",
                "regular_price": "199.99",
                "description": "High quality bluetooth headphones",
                "short_description": "Noise-canceling bluetooth headphones",
                "sku": "HEADPHONE-PREMIUM",
                "stock_quantity": 30,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (datetime.now() - timedelta(days=60)).isoformat(),
            }
        ]
        
        all_products = recalled_products + normal_products
        
        created_count = 0
        failed_count = 0
        
        for product_data in all_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                is_recalled = any(meta.get('key') == 'recall_status' for meta in product_data.get('meta_data', []))
                
                self.created_products.append({
                    'id': product_id,
                    'name': product_name,
                    'sku': result.get('sku'),
                    'is_recalled': is_recalled,
                    'recall_reason': product_data.get('meta_data', [{}])[0].get('value') if is_recalled else None
                })
                
                print(f"✅ Created product: {product_name} (ID: {product_id})")
                created_count += 1
            else:
                print(f"❌ Created product失败: {product_data.get('name')} - {result}")
                failed_count += 1
            
            time.sleep(0.5)
        
        create_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "recalled_products_count": len([p for p in self.created_products if p.get('is_recalled')]),
            "normal_products_count": len([p for p in self.created_products if not p.get('is_recalled')])
        }
        
        # 保存召回产品信息到JSON文件，供evaluation使用
        recalled_products_info = {
            "recalled_skus": [p.get('sku') for p in self.created_products if p.get('is_recalled')],
            "recalled_product_names": [p.get('name') for p in self.created_products if p.get('is_recalled')],
            "recalled_product_ids": [p.get('id') for p in self.created_products if p.get('is_recalled')],
            "total_recalled_products": len([p for p in self.created_products if p.get('is_recalled')]),
            "created_at": datetime.now().isoformat()
        }
        
        # 保存到当前目录的recalled_products_info.json
        recall_info_file = os.path.join(os.path.dirname(__file__), '..', 'recalled_products_info.json')
        try:
            with open(recall_info_file, 'w', encoding='utf-8') as f:
                json.dump(recalled_products_info, f, indent=2, ensure_ascii=False)
            print(f"✅ Recalled product info saved to: {recall_info_file}")
        except Exception as e:
            print(f"⚠️ Failed to save recalled product info: {e}")
        
        print(f"📊 Product creation completed:")
        print(f"   成功创建: {created_count} 个商品")
        print(f"   召回商品: {create_result['recalled_products_count']} 个")
        print(f"   正常商品: {create_result['normal_products_count']} 个")
        
        return create_result
    
    # def get_expected_results(self) -> Dict:
    #     """获取预期结果，用于评估"""
    #     recalled_products = [p for p in self.created_products if p.get('is_recalled')]
    #     normal_products = [p for p in self.created_products if not p.get('is_recalled')]
        
    #     return {
    #         "recalled_product_model": self.recalled_product_model,
    #         "expected_recalled_count": len(recalled_products),
    #         "expected_normal_count": len(normal_products),
    #         "expected_recalled_ids": [p.get('id') for p in recalled_products],
    #         "expected_normal_ids": [p.get('id') for p in normal_products],
    #         "total_test_products": len(self.created_products),
    #         "all_created_products": self.created_products,
    #         "created_customers": self.created_customers,
    #         "created_orders": self.created_orders
    #     }