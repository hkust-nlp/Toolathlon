import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple


class WooCommerceClient:
    """WooCommerce API客户端"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化WooCommerce API客户端
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.site_url = site_url.rstrip('/')
        self.api_base = f"{self.site_url}/wp-json/wc/v3"
        self.consumer_key = consumer_key
        self.consumer_secret = consumer_secret
        
        # 创建session
        self.session = requests.Session()
        self.session.auth = HTTPBasicAuth(consumer_key, consumer_secret)
        self.session.headers.update({
            'Content-Type': 'application/json',
            'User-Agent': 'NewProductEmail-Setup/1.0'
        })
        
        print(f"🔗 WooCommerce客户端已初始化: {self.site_url}")
    
    def _make_request(self, method: str, endpoint: str, data=None, params=None) -> Tuple[bool, Dict]:
        """
        发送API请求
        
        Args:
            method: HTTP方法 (GET, POST, PUT, DELETE)
            endpoint: API端点
            data: 请求数据
            params: URL参数
            
        Returns:
            (成功状态, 响应数据/错误信息)
        """
        # 确保endpoint不以斜杠开头
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
                return False, {"error": f"不支持的HTTP方法: {method}"}
            
            # 检查响应状态
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
            return False, {"error": f"请求异常: {str(e)}"}
        except Exception as e:
            return False, {"error": f"未知错误: {str(e)}"}
    
    def test_connection(self) -> Tuple[bool, str]:
        """测试API连接"""
        success, response = self._make_request('GET', 'system_status')
        if success:
            return True, "API连接测试成功"
        else:
            return False, f"API连接测试失败: {response.get('error', '未知错误')}"
    
    # 商品相关方法
    def create_product(self, product_data: Dict) -> Tuple[bool, Dict]:
        """创建商品"""
        return self._make_request('POST', 'products', data=product_data)
    
    def get_product(self, product_id: str) -> Tuple[bool, Dict]:
        """获取单个商品"""
        return self._make_request('GET', f'products/{product_id}')
    
    def get_all_products(self, per_page: int = 100) -> List[Dict]:
        """获取所有商品"""
        all_products = []
        page = 1
        
        while True:
            success, response = self._make_request('GET', 'products', params={
                'per_page': per_page,
                'page': page
            })
            
            if not success:
                print(f"获取商品列表失败: {response.get('error', '未知错误')}")
                break
            
            if not response or len(response) == 0:
                break
            
            all_products.extend(response)
            
            # 如果返回的商品数量少于per_page，说明已经到最后一页
            if len(response) < per_page:
                break
                
            page += 1
            time.sleep(0.1)  # 避免API限制
        
        return all_products
    
    def update_product(self, product_id: str, product_data: Dict) -> Tuple[bool, Dict]:
        """更新商品"""
        return self._make_request('PUT', f'products/{product_id}', data=product_data)
    
    def delete_product(self, product_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """删除商品"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'products/{product_id}', params=params)
    
    def list_products(self, per_page: int = 10, page: int = 1, **kwargs) -> Tuple[bool, List[Dict]]:
        """列出商品"""
        params = {
            'per_page': per_page,
            'page': page,
            **kwargs
        }
        return self._make_request('GET', 'products', params=params)
    
    # 分类相关方法
    def create_category(self, category_data: Dict) -> Tuple[bool, Dict]:
        """创建商品分类"""
        return self._make_request('POST', 'products/categories', data=category_data)
    
    def get_product_categories(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """获取商品分类列表"""
        return self._make_request('GET', 'products/categories', params={'per_page': per_page})
    
    def delete_category(self, category_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """删除商品分类"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'products/categories/{category_id}', params=params)
    
    # 客户相关方法
    def create_customer(self, customer_data: Dict) -> Tuple[bool, Dict]:
        """创建客户"""
        return self._make_request('POST', 'customers', data=customer_data)
    
    def get_customer(self, customer_id: str) -> Tuple[bool, Dict]:
        """获取单个客户"""
        return self._make_request('GET', f'customers/{customer_id}')
    
    def get_all_customers(self, per_page: int = 100) -> Tuple[bool, List[Dict]]:
        """获取所有客户"""
        all_customers = []
        page = 1
        
        while True:
            success, response = self._make_request('GET', 'customers', params={
                'per_page': per_page,
                'page': page
            })
            
            if not success:
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
        """更新客户"""
        return self._make_request('PUT', f'customers/{customer_id}', data=customer_data)
    
    def delete_customer(self, customer_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """删除客户"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'customers/{customer_id}', params=params)
    
    # 订单相关方法
    def create_order(self, order_data: Dict) -> Tuple[bool, Dict]:
        """创建订单"""
        return self._make_request('POST', 'orders', data=order_data)
    
    def get_order(self, order_id: str) -> Tuple[bool, Dict]:
        """获取单个订单"""
        return self._make_request('GET', f'orders/{order_id}')
    
    def list_orders(self, per_page: int = 10, **kwargs) -> Tuple[bool, List[Dict]]:
        """列出订单"""
        params = {
            'per_page': per_page,
            **kwargs
        }
        return self._make_request('GET', 'orders', params=params)
    
    def update_order(self, order_id: str, order_data: Dict) -> Tuple[bool, Dict]:
        """更新订单"""
        return self._make_request('PUT', f'orders/{order_id}', data=order_data)
    
    def delete_order(self, order_id: str, force: bool = False) -> Tuple[bool, Dict]:
        """删除订单"""
        params = {'force': force} if force else None
        return self._make_request('DELETE', f'orders/{order_id}', params=params)


def test_client():
    """测试客户端功能"""
    # 这里需要实际的WooCommerce站点信息
    site_url = "http://localhost:10003/store85"
    consumer_key = "ck_woocommerce_token_newpr0d1ct5ty"
    consumer_secret = "cs_woocommerce_token_newpr0d1ct5ty"
    
    client = WooCommerceClient(site_url, consumer_key, consumer_secret)
    
    # 测试连接
    success, message = client.test_connection()
    print(f"连接测试: {message}")
    
    if success:
        # 测试获取商品列表
        success, products = client.list_products(per_page=5)
        if success:
            print(f"获取到 {len(products)} 个商品")
        else:
            print(f"获取商品失败: {products}")


if __name__ == "__main__":
    test_client()