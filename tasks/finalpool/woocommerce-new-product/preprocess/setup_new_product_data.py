import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os

# 动态添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

class NewProductEmailSetup:
    """新品邮件任务设置器 - 为评估创建测试数据"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化新品邮件设置器
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.created_products = []
        self.created_customers = []
    
    def clear_all_data(self) -> Dict:
        """
        清理商店中的所有商品、客户和分类
        
        Returns:
            清理结果字典
        """
        print("🧹 开始清理商店中的所有数据...")
        
        try:
            # 1. 获取并删除所有商品
            print("📦 清理所有商品...")
            all_products = self.wc_client.get_all_products()
            
            deleted_products = 0
            failed_products = 0
            
            if all_products:
                print(f"🗑️ 准备删除 {len(all_products)} 个商品...")
                
                for product in all_products:
                    product_id = product.get('id')
                    product_name = product.get('name', 'Unknown')
                    
                    try:
                        success, result = self.wc_client.delete_product(str(product_id), force=True)
                        if success:
                            print(f"   ✅ 删除商品: {product_name} (ID: {product_id})")
                            deleted_products += 1
                        else:
                            print(f"   ❌ 删除失败: {product_name} - {result}")
                            failed_products += 1
                    except Exception as e:
                        print(f"   ❌ 删除商品 {product_name} 时出错: {e}")
                        failed_products += 1
                    
                    time.sleep(0.3)
            else:
                print("📦 商店中没有商品需要删除")
            
            # 2. 获取并删除客户（改进的客户清理逻辑）
            print("👥 清理测试客户...")
            deleted_customers = 0
            failed_customers = 0
            
            try:
                success, customers = self.wc_client.get_all_customers()
                if success and customers:
                    print(f"🔍 找到 {len(customers)} 个客户，开始检查测试客户...")
                    
                    for customer in customers:
                        customer_id = customer.get('id')
                        customer_email = customer.get('email', 'Unknown')
                        customer_username = customer.get('username', '')
                        
                        # 改进的测试客户识别逻辑
                        is_test_customer = False
                        
                        # 检查邮箱域名
                        test_domains = ['@example.com', '@mcp.com', '@test.com']
                        for domain in test_domains:
                            if domain in customer_email:
                                is_test_customer = True
                                break
                        
                        # 检查用户名是否是测试用户名（包括带时间戳的）
                        test_username_prefixes = ['johndoe', 'janesmith', 'bobwilson', 'alicejones', 'charliebrown']
                        if customer_username in test_username_prefixes or any(customer_username.startswith(f"{prefix}_") for prefix in test_username_prefixes):
                            is_test_customer = True
                        
                        # 检查邮箱是否包含测试关键词或时间戳
                        test_keywords = ['john.doe_', 'jane.smith_', 'bob.wilson_', 'alice.jones_', 'charlie.brown_']
                        for keyword in test_keywords:
                            if keyword in customer_email:
                                is_test_customer = True
                                break
                        
                        if is_test_customer:
                            try:
                                delete_success, delete_result = self.wc_client.delete_customer(str(customer_id), force=True)
                                if delete_success:
                                    print(f"   ✅ 删除测试客户: {customer_email} (ID: {customer_id})")
                                    deleted_customers += 1
                                else:
                                    error_msg = delete_result.get('error', '未知错误')
                                    # 如果是用户名已存在错误，我们认为删除成功（避免重复删除）
                                    if 'username' in str(error_msg).lower() and 'exists' in str(error_msg).lower():
                                        print(f"   ℹ️ 客户已处理: {customer_email} (可能已删除)")
                                        deleted_customers += 1
                                    else:
                                        print(f"   ❌ 删除客户失败: {customer_email} - {error_msg}")
                                        failed_customers += 1
                            except Exception as e:
                                print(f"   ❌ 删除客户 {customer_email} 时出错: {e}")
                                failed_customers += 1
                            
                            time.sleep(0.3)
                        else:
                            print(f"   ⏭️ 跳过非测试客户: {customer_email}")
                else:
                    print("👥 没有找到客户或获取客户列表失败")
            except Exception as e:
                print(f"   ⚠️ 客户清理过程出错: {e}")
            
            # 3. 清理分类
            print("🏷️ 清理商品分类...")
            success, categories = self.wc_client.get_product_categories()
            
            deleted_categories = 0
            failed_categories = 0
            
            if success and categories:
                test_category_names = [
                    "电子产品", "智能家居", "配件", "办公用品", "测试分类"
                ]
                
                for category in categories:
                    category_name = category.get('name', '')
                    category_id = category.get('id')
                    
                    if (category_name in test_category_names or 
                        category.get('count', 0) == 0):
                        
                        try:
                            delete_url = f"{self.wc_client.api_base}/products/categories/{category_id}"
                            response = self.wc_client.session.delete(
                                delete_url, 
                                params={'force': True}
                            )
                            
                            if response.status_code in [200, 204]:
                                print(f"   ✅ 删除分类: {category_name} (ID: {category_id})")
                                deleted_categories += 1
                            else:
                                print(f"   ⚠️ 跳过分类: {category_name}")
                                
                        except Exception as e:
                            print(f"   ❌ 删除分类 {category_name} 时出错: {e}")
                            failed_categories += 1
                        
                        time.sleep(0.3)
            
            clear_result = {
                "success": failed_products == 0 and failed_customers == 0 and failed_categories == 0,
                "products": {
                    "total_found": len(all_products) if all_products else 0,
                    "deleted": deleted_products,
                    "failed": failed_products
                },
                "customers": {
                    "deleted": deleted_customers,
                    "failed": failed_customers
                },
                "categories": {
                    "deleted": deleted_categories,
                    "failed": failed_categories
                },
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\n📊 清理完成:")
            print(f"   商品: 删除 {deleted_products} 个，失败 {failed_products} 个")
            print(f"   客户: 删除 {deleted_customers} 个，失败 {failed_customers} 个")
            print(f"   分类: 删除 {deleted_categories} 个，失败 {failed_categories} 个")
            
            if clear_result["success"]:
                print("✅ 数据清理成功！")
            else:
                print("⚠️ 数据清理部分完成，有部分项目清理失败")
            
            return clear_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 清理过程中出错: {e}")
            return error_result
    
    def create_product_categories(self) -> Dict:
        """创建商品分类"""
        print("📂 创建商品分类...")
        
        categories = [
            {"name": "电子产品", "description": "手机、电脑、数码设备等"},
            {"name": "智能家居", "description": "智能设备、家居控制等"},
            {"name": "配件", "description": "充电器、数据线等配件"},
            {"name": "办公用品", "description": "办公设备、文具等"}
        ]
        
        created_categories = {}
        
        for category in categories:
            category_data = {
                "name": category["name"],
                "description": category["description"],
                "display": "default",
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
    
    def create_test_products(self, categories: Dict) -> Dict:
        """
        创建测试商品
        包括：
        1. 新品商品（draft/pending状态，未来30天内发布）
        2. 折扣商品（有sale_price设置的商品）
        
        Returns:
            创建结果字典
        """
        print("🛒 开始创建测试商品...")
        
        current_date = datetime.now()
        
        # 新品商品数据（来自initial_workspace/products_draft.json的格式）
        draft_products = [
            {
                "name": "智能手表 Pro Max",
                "type": "simple",
                "status": "draft",
                "regular_price": "2999",
                "description": "新一代智能手表，支持健康监测、运动追踪和智能助手功能",
                "short_description": "旗舰级智能穿戴设备",
                "categories": [{"id": categories.get("电子产品")}] if categories.get("电子产品") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-10-01"},
                    {"key": "pre_order_discount", "value": "10"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=1)).isoformat(),
                "date_modified": (current_date - timedelta(hours=10)).isoformat()
            },
            {
                "name": "无线降噪耳机 Ultra",
                "type": "simple", 
                "status": "pending",
                "regular_price": "1599",
                "description": "旗舰级主动降噪耳机，48小时续航，Hi-Res音质认证",
                "short_description": "极致音质体验",
                "categories": [{"id": categories.get("电子产品")}] if categories.get("电子产品") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-15"},
                    {"key": "pre_order_discount", "value": "15"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=3)).isoformat(),
                "date_modified": (current_date - timedelta(hours=5)).isoformat()
            },
            {
                "name": "智能家居控制中心",
                "type": "simple",
                "status": "draft", 
                "regular_price": "899",
                "description": "全屋智能家居控制中枢，支持多种协议，语音控制",
                "short_description": "让家更智能",
                "categories": [{"id": categories.get("智能家居")}] if categories.get("智能家居") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-20"},
                    {"key": "pre_order_discount", "value": "20"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=4)).isoformat(),
                "date_modified": (current_date - timedelta(hours=15)).isoformat()
            }
        ]
        
        # 折扣商品数据（来自initial_workspace/products_sale.json的格式）
        sale_products = [
            {
                "name": "蓝牙音箱 Mini",
                "type": "simple",
                "status": "publish",
                "regular_price": "299",
                "sale_price": "199", 
                "description": "便携式蓝牙音箱，360度环绕音效，IPX7防水",
                "short_description": "随身音乐伴侣",
                "categories": [{"id": categories.get("电子产品")}] if categories.get("电子产品") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=1)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=15)).isoformat(),
                "date_created": (current_date - timedelta(days=60)).isoformat(),
                "date_modified": (current_date - timedelta(days=1)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "USB-C 数据线套装",
                "type": "simple",
                "status": "publish",
                "regular_price": "99",
                "sale_price": "59",
                "description": "高速充电数据线套装，包含1米、2米、3米三种长度",
                "short_description": "一套满足所有需求", 
                "categories": [{"id": categories.get("配件")}] if categories.get("配件") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=3)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=7)).isoformat(),
                "date_created": (current_date - timedelta(days=90)).isoformat(),
                "date_modified": (current_date - timedelta(days=3)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "无线充电板",
                "type": "simple",
                "status": "publish",
                "regular_price": "199", 
                "sale_price": "149",
                "description": "15W快速无线充电，支持多设备同时充电",
                "short_description": "告别线缆束缚",
                "categories": [{"id": categories.get("配件")}] if categories.get("配件") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=2)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=20)).isoformat(),
                "date_created": (current_date - timedelta(days=120)).isoformat(),
                "date_modified": (current_date - timedelta(days=2)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            },
            {
                "name": "笔记本支架",
                "type": "simple",
                "status": "publish",
                "regular_price": "159",
                "sale_price": "99",
                "description": "人体工学设计，可调节高度和角度，铝合金材质",
                "short_description": "改善办公姿势",
                "categories": [{"id": categories.get("办公用品")}] if categories.get("办公用品") else [],
                "on_sale": True,
                "date_on_sale_from": (current_date - timedelta(days=5)).isoformat(),
                "date_on_sale_to": (current_date + timedelta(days=10)).isoformat(),
                "date_created": (current_date - timedelta(days=200)).isoformat(),
                "date_modified": (current_date - timedelta(days=5)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "sale_product"}
                ]
            }
        ]
        
        all_products = draft_products + sale_products
        
        created_count = 0
        failed_count = 0
        
        for product_data in all_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                product_type = 'unknown'
                
                # 提取产品类型
                meta_data = product_data.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') == 'product_type':
                        product_type = meta.get('value', 'unknown')
                        break
                
                self.created_products.append({
                    'id': product_id,
                    'name': product_name,
                    'type': product_type,
                    'status': product_data.get('status'),
                    'regular_price': product_data.get('regular_price'),
                    'sale_price': product_data.get('sale_price')
                })
                print(f"✅ 创建商品: {product_name} (ID: {product_id}, 类型: {product_type})")
                created_count += 1
            else:
                print(f"❌ 创建商品失败: {product_data.get('name')} - {result}")
                failed_count += 1
            
            time.sleep(0.5)
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "new_products_count": len([p for p in self.created_products if p.get('type') == 'new_product']),
            "sale_products_count": len([p for p in self.created_products if p.get('type') == 'sale_product'])
        }
        
        print(f"📊 商品创建完成:")
        print(f"   成功创建: {created_count} 个商品")
        print(f"   创建失败: {failed_count} 个商品")
        print(f"   新品商品: {setup_result['new_products_count']} 个")
        print(f"   折扣商品: {setup_result['sale_products_count']} 个")
        
        return setup_result
    def clear_existing_test_customers_thoroughly(self) -> Dict:
        """
        更彻底的测试客户清理方法
        专门用于解决重复客户问题
        """
        print("🧹 开始彻底清理测试客户...")
        
        deleted_count = 0
        failed_count = 0
        
        try:
            success, customers = self.wc_client.get_all_customers(per_page=100)
            if success and customers:
                print(f"🔍 获取到 {len(customers)} 个客户，开始清理...")
                
                for customer in customers:
                    customer_id = customer.get('id')
                    customer_email = customer.get('email', '')
                    customer_username = customer.get('username', '')
                    
                    # 更全面的测试客户检测
                    is_test_customer = (
                        '@example.com' in customer_email or 
                        '@test.com' in customer_email or
                        '@mcp.com' in customer_email or
                        'john.doe' in customer_email or
                        'jane.smith' in customer_email or
                        'bob.wilson' in customer_email or
                        'alice.jones' in customer_email or
                        'charlie.brown' in customer_email or
                        any(customer_username.startswith(f"{prefix}_") or customer_username == prefix for prefix in ['johndoe', 'janesmith', 'bobwilson', 'alicejones', 'charliebrown']) or
                        # 检测带有时间戳的邮箱
                        '_' in customer_email and any(name in customer_email for name in ['john.doe', 'jane.smith', 'bob.wilson', 'alice.jones', 'charlie.brown'])
                    )
                    
                    if is_test_customer:
                        try:
                            delete_success, delete_result = self.wc_client.delete_customer(str(customer_id), force=True)
                            if delete_success:
                                print(f"   ✅ 删除测试客户: {customer_email} (ID: {customer_id})")
                                deleted_count += 1
                            else:
                                # 处理特定错误
                                error_msg = str(delete_result.get('error', ''))
                                if 'not found' in error_msg.lower() or '404' in error_msg:
                                    print(f"   ℹ️ 客户已不存在: {customer_email}")
                                    deleted_count += 1
                                else:
                                    print(f"   ❌ 删除客户失败: {customer_email} - {error_msg}")
                                    failed_count += 1
                        except Exception as e:
                            print(f"   ❌ 删除客户 {customer_email} 时出错: {e}")
                            failed_count += 1
                        
                        time.sleep(0.2)
                
            result = {
                "deleted_customers": deleted_count,
                "failed_customers": failed_count,
                "success": failed_count == 0
            }
            
            print(f"📊 客户清理统计: 成功删除 {deleted_count} 个，失败 {failed_count} 个")
            return result
            
        except Exception as e:
            print(f"❌ 客户清理过程出错: {e}")
            return {
                "deleted_customers": deleted_count,
                "failed_customers": failed_count + 1,
                "success": False,
                "error": str(e)
            }
    
    import time
    def create_test_customers(self) -> Dict:
        """
        创建测试客户
        包括：
        1. 订阅新品提醒的客户
        2. 只订阅折扣提醒的客户  
        3. 全部订阅的客户
        4. 不订阅的客户
        
        Returns:
            创建结果字典
        """
        print("👥 开始创建测试客户...")
        timestamp = int(time.time())
        # 测试客户数据（来自initial_workspace/customers.json的格式）
        test_customers = [
            {
                "email": f"john.doe_{timestamp}@example.com",
                "first_name": "John",
                "last_name": "Doe",
                "username": f"johndoe_{timestamp}",
                "meta_data": [
                    {
                        "key": "subscription_preferences",
                        "value": json.dumps({
                            "new_product_alerts": True,
                            "discount_alerts": True
                        })
                    }
                ],
                "billing": {
                    "email": f"john.doe_{timestamp}@example.com",
                    "first_name": "John",
                    "last_name": "Doe"
                }
            },
            {
                "email": f"jane.smith_{timestamp}@example.com",
                "first_name": "Jane",
                "last_name": "Smith", 
                "username": f"janesmith_{timestamp}",
                "meta_data": [
                    {
                        "key": "subscription_preferences",
                        "value": json.dumps({
                            "new_product_alerts": True,
                            "discount_alerts": True
                        })
                    }
                ],
                "billing": {
                    "email": f"jane.smith_{timestamp}@example.com",
                    "first_name": "Jane",
                    "last_name": "Smith"
                }
            },
            {
                "email": f"bob.wilson_{timestamp}@example.com", 
                "first_name": "Bob",
                "last_name": "Wilson",
                "username": f"bobwilson_{timestamp}",
                "meta_data": [
                    {
                        "key": "subscription_preferences",
                        "value": json.dumps({
                            "new_product_alerts": False,
                            "discount_alerts": True
                        })
                    }
                ],
                "billing": {
                    "email": f"bob.wilson_{timestamp}@example.com",
                    "first_name": "Bob",
                    "last_name": "Wilson"
                }
            },
            {
                "email": f"alice.jones_{timestamp}@example.com",
                "first_name": "Alice", 
                "last_name": "Jones",
                "username": f"alicejones_{timestamp}",
                "meta_data": [
                    {
                        "key": "subscription_preferences",
                        "value": json.dumps({
                            "new_product_alerts": True,
                            "discount_alerts": False
                        })
                    }
                ],
                "billing": {
                    "email": f"alice.jones_{timestamp}@example.com",
                    "first_name": "Alice",
                    "last_name": "Jones"
                }
            },
            {
                "email": f"charlie.brown_{timestamp}@example.com",
                "first_name": "Charlie",
                "last_name": "Brown", 
                "username": f"charliebrown_{timestamp}",
                "meta_data": [
                    {
                        "key": "subscription_preferences",
                        "value": json.dumps({
                            "new_product_alerts": False,
                            "discount_alerts": False
                        })
                    }
                ],
                "billing": {
                    "email": f"charlie.brown_{timestamp}@example.com",
                    "first_name": "Charlie",
                    "last_name": "Brown"
                }
            }
        ]
        
        created_count = 0
        failed_count = 0
        
        for customer_data in test_customers:
            success, result = self.wc_client.create_customer(customer_data)
            if success:
                customer_id = result.get('id')
                customer_email = result.get('email')
                
                # 解析订阅偏好
                subscription_prefs = {"new_product_alerts": False, "discount_alerts": False}
                for meta in customer_data.get('meta_data', []):
                    if meta.get('key') == 'subscription_preferences':
                        try:
                            subscription_prefs = json.loads(meta.get('value', '{}'))
                        except:
                            pass
                        break
                
                self.created_customers.append({
                    'id': customer_id,
                    'email': customer_email,
                    'first_name': customer_data.get('first_name'),
                    'last_name': customer_data.get('last_name'),
                    'new_product_alerts': subscription_prefs.get('new_product_alerts', False),
                    'discount_alerts': subscription_prefs.get('discount_alerts', False)
                })
                print(f"✅ 创建客户: {customer_email} (ID: {customer_id})")
                created_count += 1
            else:
                print(f"❌ 创建客户失败: {customer_data.get('email')} - {result}")
                failed_count += 1
            
            time.sleep(0.5)
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_customers": self.created_customers,
            "new_product_subscribers": len([c for c in self.created_customers if c.get('new_product_alerts')]),
            "discount_subscribers": len([c for c in self.created_customers if c.get('discount_alerts')])
        }
        
        print(f"📊 客户创建完成:")
        print(f"   成功创建: {created_count} 个客户")
        print(f"   创建失败: {failed_count} 个客户")
        print(f"   新品订阅: {setup_result['new_product_subscribers']} 个客户")
        print(f"   折扣订阅: {setup_result['discount_subscribers']} 个客户")
        
        return setup_result
    
    def get_expected_results(self) -> Dict:
        """获取预期结果，用于评估"""
        new_product_subscribers = [c for c in self.created_customers if c.get('new_product_alerts')]
        all_customers = self.created_customers
        new_products = [p for p in self.created_products if p.get('type') == 'new_product']
        sale_products = [p for p in self.created_products if p.get('type') == 'sale_product']
        
        return {
            "expected_new_products_count": len(new_products),
            "expected_sale_products_count": len(sale_products),
            "expected_appointment_emails": len(new_product_subscribers),
            "expected_discount_emails": len(all_customers),
            "new_product_subscriber_emails": [c.get('email') for c in new_product_subscribers],
            "all_customer_emails": [c.get('email') for c in all_customers],
            "new_products": new_products,
            "sale_products": sale_products,
            "total_customers": len(all_customers),
            "total_products": len(self.created_products)
        }


def main():
    """主函数 - 用于独立运行测试数据设置"""
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 初始化新品邮件任务设置器: {site_url}")
    
    setup = NewProductEmailSetup(site_url, consumer_key, consumer_secret)
    
    # 1. 先做一轮彻底的客户清理（新增）
    print("\n" + "="*60)
    print("第零步：彻底清理测试客户（防止重复）")
    print("="*60)
    
    customer_cleanup_result = setup.clear_existing_test_customers_thoroughly()
    print(f"📊 客户清理结果: {customer_cleanup_result}")
    
    # 等待清理操作完成
    print("⏳ 等待5秒，确保客户清理操作完成...")
    time.sleep(5)
    
    # 2. 清理现有数据
    print("\n" + "="*60)
    print("第一步：清理商店中的所有现有数据")
    print("="*60)
    
    clear_result = setup.clear_all_data()
    
    if not clear_result.get('success'):
        print("⚠️ 数据清理未完全成功，但继续创建测试数据...")
        print(f"清理详情: {clear_result}")
    
    # 等待清理操作完成
    print("⏳ 等待3秒，确保清理操作完成...")
    time.sleep(3)
    
    # 2. 创建商品分类
    print("\n" + "="*60)
    print("第二步：创建商品分类")
    print("="*60)
    
    categories = setup.create_product_categories()
    
    # 3. 创建测试商品
    print("\n" + "="*60)
    print("第三步：创建测试商品")
    print("="*60)
    
    product_result = setup.create_test_products(categories)
    
    # 4. 创建测试客户
    print("\n" + "="*60)
    print("第四步：创建测试客户")
    print("="*60)
    
    customer_result = setup.create_test_customers()
    
    # 5. 保存结果
    if product_result.get('success') and customer_result.get('success'):
        print("\n✅ 新品邮件任务测试数据设置完成！")
        
        # 保存预期结果
        expected_results = setup.get_expected_results()
        with open('expected_results.json', 'w', encoding='utf-8') as f:
            json.dump(expected_results, f, indent=2, ensure_ascii=False)
        print("📄 预期结果已保存到 expected_results.json")
        
        # 保存清理结果
        with open('clear_results.json', 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print("📄 清理结果已保存到 clear_results.json")
        
        # 保存完整设置结果
        full_setup_result = {
            "customer_cleanup_result": customer_cleanup_result,
            "clear_result": clear_result,
            "categories": categories,
            "product_result": product_result,
            "customer_result": customer_result,
            "expected_results": expected_results,
            "setup_timestamp": datetime.now().isoformat()
        }
        
        with open('setup_results.json', 'w', encoding='utf-8') as f:
            json.dump(full_setup_result, f, indent=2, ensure_ascii=False)
        print("📄 完整设置结果已保存到 setup_results.json")
        
        return True
    else:
        print("❌ 新品邮件任务测试数据设置失败！")
        return False


if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-only":
        # 仅清理数据
        from token_key_session import all_token_key_session
        
        site_url = all_token_key_session.woocommerce_site_url
        consumer_key = all_token_key_session.woocommerce_api_key
        consumer_secret = all_token_key_session.woocommerce_api_secret
        
        setup = NewProductEmailSetup(site_url, consumer_key, consumer_secret)
        clear_result = setup.clear_all_data()
        
        with open('clear_results.json', 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print("📄 清理结果已保存到 clear_results.json")
        
    else:
        # 完整流程：清理 + 创建测试数据
        main()