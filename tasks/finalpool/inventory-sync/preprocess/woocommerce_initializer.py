import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime
from typing import Dict, List, Optional, Tuple
import sys
import os

# 添加项目根目录到Python路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

from woocommerce_client import WooCommerceClient, WooCommerceInventoryManager
from database_setup import generate_sample_products
from clear_all_products import main as clear_all_products
from token_key_session import all_token_key_session

class WooCommerceStoreInitializer:
    """WooCommerce商店初始化器 - 从空账户开始设置6城市3RegionInventory系统
    
    支持城市：New York、Boston(East)，Dallas、Houston(South)，LA、San Francisco(West)
    """
    
    def __init__(self):
        """
        初始化器
        
        Args:
            site_url: WooCommerce网站URL
            username: WooCommerce管理员用户名
            password: WooCommerce管理员密码
        """
        self.site_url = all_token_key_session.woocommerce_site_url.rstrip('/')
        self.username = all_token_key_session.woocommerce_admin_username
        self.password = all_token_key_session.woocommerce_admin_password
        self.wc_client = None
        self.consumer_key = None
        self.consumer_secret = None
        
        print(f"🚀 初始化WooCommerce商店: {self.site_url}")
    
    def setup_api_credentials(self) -> Tuple[bool, str]:
        """
        设置API凭据 - 通过WordPress REST API创建WooCommerce API密钥
        """
        print("🔑 设置API凭据...")
        
        # 首先尝试通过WordPress REST API登录
        login_url = f"{self.site_url}/wp-json/jwt-auth/v1/token"
        login_data = {
            "username": self.username,
            "password": self.password
        }
        
        try:
            response = requests.post(login_url, json=login_data)
            if response.status_code == 200:
                token_data = response.json()
                jwt_token = token_data.get('token')
                print("✅ JWT认证成功")
                
                # 使用JWT token创建WooCommerce API密钥
                return self._create_wc_api_keys(jwt_token)
            else:
                # 如果JWT不可用，尝试基础认证方式
                print("⚠️ JWT认证不可用，尝试其他方式...")
                return self._create_api_keys_basic_auth()
                
        except Exception as e:
            print(f"❌ API凭据设置失败: {e}")
            return False, str(e)
    
    def _create_wc_api_keys(self, jwt_token: str) -> Tuple[bool, str]:
        """使用JWT token创建WooCommerce API密钥"""
        api_keys_url = f"{self.site_url}/wp-json/wc/v3/system_status/tools/create_api_key"
        
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Content-Type": "application/json"
        }
        
        key_data = {
            "description": "Multi-City Inventory Sync System",
            "user_id": 1,  # 管理员用户ID
            "permissions": "read_write"
        }
        
        try:
            response = requests.post(api_keys_url, json=key_data, headers=headers)
            if response.status_code == 200:
                api_data = response.json()
                self.consumer_key = api_data.get('consumer_key')
                self.consumer_secret = api_data.get('consumer_secret')
                
                print(f"✅ API密钥创建成功")
                print(f"   Consumer Key: {self.consumer_key[:20]}...")
                print(f"   Consumer Secret: {self.consumer_secret[:20]}...")
                
                # 初始化WooCommerce客户端
                self.wc_client = WooCommerceClient(
                    self.site_url, 
                    self.consumer_key, 
                    self.consumer_secret
                )
                
                return True, "API密钥创建成功"
            else:
                return False, f"API密钥创建失败: {response.text}"
                
        except Exception as e:
            return False, f"创建API密钥时出错: {e}"
    
    def _create_api_keys_basic_auth(self) -> Tuple[bool, str]:
        """使用基础认证创建API密钥（备用方法）"""
        print("🔧 使用基础认证方式...")
        
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        
        if consumer_key and consumer_secret:
            self.consumer_key = consumer_key
            self.consumer_secret = consumer_secret
            
            # 初始化WooCommerce客户端
            self.wc_client = WooCommerceClient(
                self.site_url, 
                self.consumer_key, 
                self.consumer_secret
            )
            
            # 测试API连接
            success, response = self.wc_client.list_products(per_page=1)
            if success:
                print("✅ API连接测试成功")
                return True, "API密钥设置成功"
            else:
                print(f"❌ API连接测试失败: {response}")
                return False, "API连接测试失败"
        else:
            return False, "未提供有效的API密钥"
    
    def create_product_categories(self) -> Dict[str, int]:
        """创建商品分类"""
        print("📂 创建商品分类...")
        
        categories = [
            {"name": "Electronic Products", "description": "Mobile phones, computers, digital devices, etc."},
            {"name": "Clothing, Shoes & Accessories", "description": "Clothing, shoes, accessories, etc."},
            {"name": "Home & Living", "description": "Furniture, home appliances, household items, etc."},
            {"name": "Sports & Outdoors", "description": "Sports equipment, outdoor gear, etc."},
            {"name": "Beauty & Personal Care", "description": "Cosmetics, skincare, personal care products, etc."}
        ]
        
        created_categories = {}
        
        for category in categories:
            # 创建分类的API调用
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
                print(f"  ✅ 创建分类: {category['name']} (ID: {category_id})")
            else:
                print(f"  ❌ 创建分类失败: {category['name']} - {response.get('error', '未知错误')}")
        
        return created_categories
    
    def create_sample_products(self, categories: Dict[str, int]) -> List[Dict]:
        """创建示例商品"""
        print("🛍️ 创建示例商品...")
        
        # 获取示例商品数据
        sample_products = generate_sample_products()
        created_products = []
        
        # 分类映射
        category_mapping = {
            "Electronic Products": categories.get("Electronic Products"),
            "Clothing, Shoes & Accessories": categories.get("Clothing, Shoes & Accessories"), 
            "Home & Living": categories.get("Home & Living")
        }
        
        for product_id, name, category, price, description in sample_products:
            category_id = category_mapping.get(category, categories.get("Electronic Products"))
            
            # 生成合理的初始库存、销量和发布时间
            import random
            from datetime import datetime, timedelta
            
            initial_stock = random.randint(50, 200)
            
            # 根据商品类型设置不同的销量范围
            if category == "Electronic Products":
                initial_sales = random.randint(100, 500)  # Electronic Products 销量高
                # Electronic Products 近期销量也相对较高
                sales_30_days = random.randint(int(initial_sales * 0.1), int(initial_sales * 0.3))
                # Electronic Products 较新，发布时间在最近6个月内
                days_ago = random.randint(30, 180)
            elif category == "Clothing, Shoes & Accessories":
                initial_sales = random.randint(80, 300)   # 服装销量中等
                # 服装30天销量波动较大（季节性）
                sales_30_days = random.randint(int(initial_sales * 0.05), int(initial_sales * 0.4))
                # 服装产品发布时间在最近1年内
                days_ago = random.randint(60, 365)
            else:
                initial_sales = random.randint(20, 150)   # 其他商品销量较低
                # 其他商品30天销量相对稳定
                sales_30_days = random.randint(int(initial_sales * 0.03), int(initial_sales * 0.2))
                # 其他商品可能更早发布，在最近2年内
                days_ago = random.randint(90, 730)
            
            # 计算发布时间
            publish_date = datetime.now() - timedelta(days=days_ago)
            publish_date_str = publish_date.strftime("%Y-%m-%dT%H:%M:%S")
            
            product_data = {
                "name": "(Test Product) "+name,
                "type": "simple",
                "regular_price": str(price),
                "description": description,
                "short_description": f"High quality {name}, in stock",
                "sku": product_id,
                "manage_stock": True,
                "stock_quantity": initial_stock,
                "stock_status": "instock",
                "date_created": publish_date_str,  # 设置发布时间
                "status": "publish",  # 确保商品已发布
                "categories": [{"id": category_id}] if category_id else [],
                "images": [],  # 可以后续添加图片
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
                print(f"  ✅ 创建商品: {name} (WC ID: {wc_product_id}, SKU: {product_id})")
            else:
                print(f"  ❌ 创建商品失败: {name} - {response.get('error', '未知错误')}")
                created_products.append({
                    'original_id': product_id,
                    'name': name,
                    'sku': product_id,
                    'success': False,
                    'error': response.get('error', '未知错误')
                })
        
        return created_products
    
    def setup_regional_inventory_system(self, base_products: List[Dict]) -> Dict:
        """设置RegionInventory系统"""
        print("🗺️ 设置RegionInventory系统...")
        
        if not self.wc_client:
            return {"error": "WooCommerce客户端未初始化"}
        
        # 初始化库存管理器
        wc_manager = WooCommerceInventoryManager(self.wc_client)
        
        # 为每个区域创建商品变体
        regional_setup_results = {}
        
        # 将基础商品转换为区域商品格式
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
            # 为每个区域初始化商品
            regional_products = wc_manager.initialize_regional_products(products_for_regions)
            regional_setup_results['regional_products'] = regional_products
            
            # 创建商品映射表
            product_mapping = {}
            for region, products in regional_products.items():
                product_mapping[region] = {}
                for product in products:
                    if product['success']:
                        product_mapping[region][product['original_id']] = str(product['wc_id'])
            
            regional_setup_results['product_mapping'] = product_mapping
        
        return regional_setup_results
    
    def configure_store_settings(self) -> bool:
        """配置商店基础设置"""
        print("⚙️ 配置商店基础设置...")
        
        try:
            # 配置库存管理设置
            settings_data = {
                "manage_stock": "yes",
                "notifications": "yes",
                "stock_email_recipient": "admin@example.com",
                "low_stock_amount": 5,
                "out_of_stock_amount": 0,
                "out_of_stock_visibility": "visible"
            }
            
            # 注意：WooCommerce设置API可能需要特殊权限
            print("  ℹ️ 库存管理设置需要在WooCommerce后台手动配置")
            print("  📍 路径: WooCommerce > 设置 > 产品 > 库存")
            print("  ✅ 建议启用库存管理和低库存通知")
            
            return True
            
        except Exception as e:
            print(f"  ⚠️ 自动配置失败: {e}")
            print("  📝 请手动在WooCommerce后台配置库存设置")
            return False
    
    def run_full_initialization(self) -> Dict:
        """运行完整的商店初始化流程"""
        print("🚀 开始完整的WooCommerce商店初始化...")
        print("=" * 60)
        
        results = {
            "success": False,
            "steps": {},
            "errors": []
        }
        
        try:
            # 步骤1: 设置API凭据
            print("\n📋 步骤1: 设置API凭据")
            api_success, api_message = self.setup_api_credentials()
            results["steps"]["api_setup"] = {"success": api_success, "message": api_message}
            
            if not api_success:
                results["errors"].append(f"API设置失败: {api_message}")
                return results
            
            # 步骤2: 创建商品分类
            print("\n📋 步骤2: 创建商品分类")
            categories = self.create_product_categories()
            results["steps"]["categories"] = {"success": len(categories) > 0, "data": categories}
            
            # 步骤3: 创建示例商品
            print("\n📋 步骤3: 创建示例商品")
            products = self.create_sample_products(categories)
            successful_products = [p for p in products if p['success']]
            results["steps"]["products"] = {
                "success": len(successful_products) > 0, 
                "data": products,
                "count": len(successful_products)
            }
            
            # 步骤4: 设置RegionInventory系统
            print("\n📋 步骤4: 设置RegionInventory系统")
            regional_setup = self.setup_regional_inventory_system(successful_products)
            results["steps"]["regional_setup"] = {"success": "product_mapping" in regional_setup, "data": regional_setup}
            
            # 步骤5: 配置商店设置
            print("\n📋 步骤5: 配置商店设置")
            settings_success = self.configure_store_settings()
            results["steps"]["store_settings"] = {"success": settings_success}
            
            # 检查整体成功状态
            results["success"] = all([
                api_success,
                len(categories) > 0,
                len(successful_products) > 0,
                "product_mapping" in regional_setup
            ])
            
            if results["success"]:
                print("\n🎉 WooCommerce商店初始化完成！")
                print("=" * 60)
                print(f"✅ 创建了 {len(categories)} 个商品分类")
                print(f"✅ 创建了 {len(successful_products)} 个基础商品") 
                print(f"✅ 设置了 3 个区域的库存系统")
                print("✅ 系统已准备好进行库存同步")
                
                # 保存配置信息
                print(results)
                self._save_configuration(results)
            else:
                print("\n❌ 初始化过程中出现问题，请检查错误信息")
            
        except Exception as e:
            results["errors"].append(f"初始化过程异常: {e}")
            print(f"❌ 初始化失败: {e}")
        
        return results
    
    def _save_configuration(self, results: Dict):
        """保存配置信息到文件"""
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
            print(f"📝 配置信息已保存到: {config_file}")
        except Exception as e:
            print(f"⚠️ 保存配置文件失败: {e}")

def main():
    """主函数 - 交互式初始化"""
    print("🛒 WooCommerce 6城市库存系统初始化器")
    print("支持城市：New York、Boston(East)，Dallas、Houston(South)，LA、San Francisco(West)")
    print("=" * 60)
    
    # 清理原有商品
    clear_all_products()

    # 开始初始化
    initializer = WooCommerceStoreInitializer()
    results = initializer.run_full_initialization()
    
    if results["success"]:
        print("\n🎯 下一步操作:")
        print("1. 运行数据库初始化: database_setup")
        print("2. 执行库存同步: inventory_sync")
        print("3. 运行完整测试: evaluation.main")
    else:
        print("\n🔧 故障排除:")
        print("1. 检查网站URL是否正确")
        print("2. 确认用户名和密码是否正确")
        print("3. 确保WooCommerce插件已安装并激活")
        print("4. 检查网站是否支持REST API")

    return results

if __name__ == "__main__":
    main()
