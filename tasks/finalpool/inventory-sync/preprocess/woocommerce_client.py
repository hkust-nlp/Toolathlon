import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple

class WooCommerceClient:
    """WooCommerce API客户端"""
    
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
    
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """创建商品"""
        return self._make_request('POST', 'products', data=product_data)
    
    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """更新商品信息"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)
    
    def update_product_stock(self, product_id: str, stock_quantity: int, manage_stock: bool = True) -> Tuple[bool, Dict]:
        """
        更新商品库存
        
        Args:
            product_id: 商品ID
            stock_quantity: 库存数量
            manage_stock: 是否启用库存管理
        """
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": manage_stock,
            "stock_status": "instock" if stock_quantity > 0 else "outofstock"
        }
        return self.update_product(product_id, data)
    
    def update_product_meta(self, product_id: str, meta_data: List[Dict]) -> Tuple[bool, Dict]:
        """
        更新商品元数据
        
        Args:
            product_id: 商品ID
            meta_data: 元数据列表 [{"key": "键", "value": "值"}]
        """
        data = {"meta_data": meta_data}
        return self.update_product(product_id, data)
    
    def update_total_sales(self, product_id: str, total_sales: int) -> Tuple[bool, Dict]:
        """更新商品总销量"""
        meta_data = [
            {"key": "total_sales", "value": str(total_sales)},
            {"key": "_total_sales", "value": str(total_sales)}  # WordPress内部字段
        ]
        return self.update_product_meta(product_id, meta_data)
    
    def update_product_with_sales(self, product_id: str, stock_quantity: int, total_sales: int) -> Tuple[bool, Dict]:
        """同时更新商品库存和销量"""
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
        批量更新商品
        
        Args:
            updates: 更新数据列表 [{"id": "商品ID", "stock_quantity": 数量}]
        """
        batch_data = {
            "update": updates
        }
        return self._make_request('POST', 'products/batch', data=batch_data)
    
    def get_product_variations(self, product_id: str) -> Tuple[bool, List[Dict]]:
        """获取商品变体列表"""
        success, data = self._make_request('GET', f'products/{product_id}/variations')
        return success, data if isinstance(data, list) else []
    
    def update_variation_stock(self, product_id: str, variation_id: str, stock_quantity: int) -> Tuple[bool, Dict]:
        """更新商品变体库存"""
        data = {
            "stock_quantity": stock_quantity,
            "manage_stock": True,
            "stock_status": "instock" if stock_quantity > 0 else "outofstock"
        }
        return self._make_request('PUT', f'products/{product_id}/variations/{variation_id}', data=data)

class WooCommerceInventoryManager:
    """WooCommerce库存管理器"""
    
    def __init__(self, wc_client: WooCommerceClient):
        self.wc_client = wc_client
        self.region_prefixes = {
            "East": "EAST",
            "South": "SOUTH", 
            "West": "WEST"
        }
    
    def initialize_regional_products(self, products: List[Dict]) -> Dict[str, List[Dict]]:
        """
        为每个区域初始化商品
        
        Args:
            products: 商品列表 [{"id": "PROD001", "name": "商品名", "price": 99.99}]
            
        Returns:
            区域商品创建结果
        """
        results = {}
        
        for region, prefix in self.region_prefixes.items():
            print(f"\n🌍 初始化{region}区域商品...")
            results[region] = []
            
            for product in products:
                # 为每个区域创建独立的商品ID
                regional_product_id = f"{prefix}_{product['id']}"
                
                # 根据区域设置不同的初始库存、销量和发布时间
                import random
                from datetime import datetime, timedelta
                
                if region == "East":
                    initial_stock = random.randint(100, 300)  # East库存较多
                    initial_sales = random.randint(50, 150)   # East销量较高
                    # East市场活跃，30天销量相对较高
                    sales_30_days = random.randint(int(initial_sales * 0.15), int(initial_sales * 0.35))
                    # East市场发展较早，Released Time相对较早
                    days_ago = random.randint(180, 500)
                elif region == "South":
                    initial_stock = random.randint(80, 250)   # South库存中等
                    initial_sales = random.randint(30, 100)   # South销量中等
                    # South市场稳定，30天销量中等
                    sales_30_days = random.randint(int(initial_sales * 0.1), int(initial_sales * 0.3))
                    # South市场发展中等
                    days_ago = random.randint(120, 400)
                else:  # West
                    initial_stock = random.randint(60, 200)   # West库存相对较少
                    initial_sales = random.randint(20, 80)    # West销量相对较少
                    # West新兴市场，30天销量增长快
                    sales_30_days = random.randint(int(initial_sales * 0.2), int(initial_sales * 0.4))
                    # West市场较新，Released Time相对较晚
                    days_ago = random.randint(60, 300)
                
                # 计算区域Released Time
                regional_publish_date = datetime.now() - timedelta(days=days_ago)
                regional_publish_str = regional_publish_date.strftime("%Y-%m-%dT%H:%M:%S")
                
                product_data = {
                    "name": f"[{region}] {product['name']}",
                    "type": "simple",
                    "regular_price": str(product.get('price', 0)),
                    "description": f"{product.get('description', '')} - {region}RegionInventory",
                    "short_description": f"{region}区域 - {product['name']}",
                    "sku": regional_product_id,
                    "manage_stock": True,
                    "stock_quantity": initial_stock,
                    "stock_status": "instock",
                    "date_created": regional_publish_str,  # 设置区域Released Time
                    "status": "publish",  # 确保商品已发布
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
                    print(f"  ✅ 创建商品: {product['name']} (WC ID: {wc_product_id}, SKU: {regional_product_id})")
                    results[region].append({
                        'original_id': product['id'],
                        'wc_id': wc_product_id,
                        'sku': regional_product_id,
                        'success': True
                    })
                else:
                    print(f"  ❌ 创建商品失败: {product['name']} - {response.get('error', '未知错误')}")
                    results[region].append({
                        'original_id': product['id'],
                        'sku': regional_product_id,
                        'success': False,
                        'error': response.get('error', '未知错误')
                    })
        
        return results
    
    def sync_regional_inventory(self, region_inventory: Dict[str, Dict[str, int]], product_mapping: Dict[str, Dict[str, str]]) -> Dict:
        """
        同步RegionInventory到WooCommerce
        
        Args:
            region_inventory: RegionInventory数据 {"East": {"PROD001": 100}}
            product_mapping: 商品映射 {"East": {"PROD001": "wc_product_id"}}
            
        Returns:
            同步结果
        """
        sync_results = {}
        
        for region, products in region_inventory.items():
            print(f"\n📦 同步{region}RegionInventory...")
            sync_results[region] = {}
            
            if region not in product_mapping:
                print(f"  ⚠️ 未找到{region}区域的商品映射")
                continue
            
            # 准备批量更新数据
            batch_updates = []
            
            for product_id, quantity in products.items():
                if product_id not in product_mapping[region]:
                    print(f"  ⚠️ 未找到商品映射: {product_id}")
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
                # 执行批量更新
                success, response = self.wc_client.batch_update_products(batch_updates)
                
                if success:
                    updated_products = response.get('update', [])
                    print(f"  ✅ 批量更新成功: {len(updated_products)} 个商品")
                    
                    for update in updated_products:
                        product_name = update.get('name', 'Unknown')
                        stock_qty = update.get('stock_quantity', 0)
                        sync_results[region][update['id']] = {
                            'name': product_name,
                            'quantity': stock_qty,
                            'success': True
                        }
                else:
                    print(f"  ❌ 批量更新失败: {response.get('error', '未知错误')}")
                    sync_results[region]['batch_error'] = response.get('error', '未知错误')
            else:
                print(f"  ⚠️ {region}区域没有需要更新的商品")
        
        return sync_results
    
    def verify_inventory_sync(self, expected_inventory: Dict[str, Dict[str, int]], product_mapping: Dict[str, Dict[str, str]]) -> Dict:
        """
        验证库存同步结果
        
        Args:
            expected_inventory: 期望的库存数据
            product_mapping: 商品映射
            
        Returns:
            验证结果
        """
        verification_results = {}
        
        for region, products in expected_inventory.items():
            print(f"\n🔍 验证{region}RegionInventory...")
            verification_results[region] = {}
            
            if region not in product_mapping:
                continue
            
            for product_id, expected_qty in products.items():
                if product_id not in product_mapping[region]:
                    continue
                
                wc_product_id = product_mapping[region][product_id]
                
                # 获取WooCommerce中的实际库存
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
                    print(f"  {status} {product_data.get('name', 'Unknown')}: 期望 {expected_qty}, 实际 {actual_qty}")
                else:
                    verification_results[region][product_id] = {
                        'expected': expected_qty,
                        'actual': None,
                        'match': False,
                        'error': product_data.get('error', '获取失败')
                    }
                    print(f"  ❌ 获取商品失败: {product_id} - {product_data.get('error', '未知错误')}")
        
        return verification_results

# 配置示例
class WooCommerceConfig:
    """WooCommerce配置类"""
    
    # 测试环境配置 (请替换为实际值)
    SITE_URL = "https://your-test-site.com"
    CONSUMER_KEY = "ck_your_consumer_key_here"
    CONSUMER_SECRET = "cs_your_consumer_secret_here"
    
    # 生产环境配置 (请替换为实际值)
    PROD_SITE_URL = "https://your-production-site.com"
    PROD_CONSUMER_KEY = "ck_your_production_consumer_key_here"
    PROD_CONSUMER_SECRET = "cs_your_production_consumer_secret_here"
    
    @classmethod
    def get_test_client(cls) -> WooCommerceClient:
        """获取测试环境客户端"""
        return WooCommerceClient(
            site_url=cls.SITE_URL,
            consumer_key=cls.CONSUMER_KEY,
            consumer_secret=cls.CONSUMER_SECRET
        )
    
    @classmethod
    def get_production_client(cls) -> WooCommerceClient:
        """获取生产环境客户端"""
        return WooCommerceClient(
            site_url=cls.PROD_SITE_URL,
            consumer_key=cls.PROD_CONSUMER_KEY,
            consumer_secret=cls.PROD_CONSUMER_SECRET
        )

if __name__ == "__main__":
    # 测试示例
    print("🧪 WooCommerce API客户端测试")
    
    # 注意：运行前请先配置正确的API密钥
    try:
        client = WooCommerceConfig.get_test_client()
        
        # 测试获取商品列表
        print("\n📦 获取商品列表...")
        success, products = client.list_products(per_page=5)
        
        if success:
            print(f"✅ 成功获取 {len(products)} 个商品")
            for product in products[:3]:  # 显示前3个
                print(f"  - {product.get('name', 'Unknown')} (ID: {product.get('id')}, 库存: {product.get('stock_quantity', 'N/A')})")
        else:
            print(f"❌ 获取商品列表失败: {products.get('error', '未知错误')}")
    
    except Exception as e:
        print(f"❌ 测试失败: {e}")
        print("请确保已正确配置WooCommerce API密钥")
