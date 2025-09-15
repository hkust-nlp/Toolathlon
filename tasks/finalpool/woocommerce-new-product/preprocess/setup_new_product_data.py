import json
import time
from datetime import datetime, timedelta
from typing import Dict
import sys
import os

# 动态添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

class NewProductEmailSetupV2:
    """新品邮件任务设置器 V2 - 优化客户创建逻辑"""

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

            # 2. 清理客户（只删除非测试客户）
            print("👥 清理非测试客户...")

            # 定义我们的40个测试客户邮箱列表
            our_test_emails = {
                "samuel.garcia.welcome@mcp.com",
                "henryn.welcome@mcp.com",
                "robert.collins.welcome@mcp.com",
                "allenm.welcome@mcp.com",
                "floresj.welcome@mcp.com",
                "mary.edwards57.welcome@mcp.com",
                "slewis.welcome@mcp.com",
                "nwilson.welcome@mcp.com",
                "johnsonr.welcome@mcp.com",
                "deborahw99.welcome@mcp.com",
                "timothyc57.welcome@mcp.com",
                "kathleen_kelly.welcome@mcp.com",
                "ramosa.welcome@mcp.com",
                "edavis.welcome@mcp.com",
                "amanda_chavez.welcome@mcp.com",
                "emurphy.welcome@mcp.com",
                "anthonyo.welcome@mcp.com",
                "marie.walker.welcome@mcp.com",
                "samuel_sanders77.welcome@mcp.com",
                "alexanderr.welcome@mcp.com",
                "betty.cooper.welcome@mcp.com",
                "adamsc.welcome@mcp.com",
                "martha.hill.welcome@mcp.com",
                "michael.reed.welcome@mcp.com",
                "emorris.welcome@mcp.com",
                "timothy_gomez54.welcome@mcp.com",
                "maryt92.welcome@mcp.com",
                "mendozas52.welcome@mcp.com",
                "melissa.martin95.welcome@mcp.com",
                "thomas_sanchez8.welcome@mcp.com",
                "harrisc.welcome@mcp.com",
                "scottm.welcome@mcp.com",
                "tyler_roberts72.welcome@mcp.com",
                "tnelson.welcome@mcp.com",
                "sthomas.welcome@mcp.com",
                "bennettr.welcome@mcp.com",
                "mcruz.welcome@mcp.com",
                "lewiss.welcome@mcp.com",
                "alvarezm51.welcome@mcp.com",
                "stewarte98.welcome@mcp.com"
            }

            success, all_customers = self.wc_client.get_all_customers()

            deleted_customers = 0
            failed_customers = 0
            preserved_customers = 0

            if success and all_customers:
                print(f"🔍 检查 {len(all_customers)} 个客户...")

                for customer in all_customers:
                    customer_id = customer.get('id')
                    customer_email = customer.get('email', 'Unknown')

                    # 检查是否是我们的测试客户
                    if customer_email.lower() in our_test_emails:
                        print(f"   🛡️ 保留测试客户: {customer_email} (ID: {customer_id})")
                        preserved_customers += 1
                        continue

                    # 删除非测试客户
                    try:
                        success, result = self.wc_client.delete_customer(str(customer_id), force=True)
                        if success:
                            print(f"   ✅ 删除客户: {customer_email} (ID: {customer_id})")
                            deleted_customers += 1
                        else:
                            print(f"   ❌ 删除失败: {customer_email} - {result}")
                            failed_customers += 1
                    except Exception as e:
                        print(f"   ❌ 删除客户 {customer_email} 时出错: {e}")
                        failed_customers += 1

                    time.sleep(0.3)

                print(f"📊 客户处理统计:")
                print(f"   保留测试客户: {preserved_customers} 个")
                print(f"   删除其他客户: {deleted_customers} 个")
                print(f"   删除失败: {failed_customers} 个")
            else:
                print("👥 商店中没有客户需要处理")

            # 3. 清理分类
            print("🏷️ 清理商品分类...")
            success, categories = self.wc_client.get_product_categories()

            deleted_categories = 0
            failed_categories = 0

            if success and categories:
                test_category_names = [
                    "Electronics", "Smart Home", "Accessories", "Office Supplies",
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
                    "preserved": preserved_customers,
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
            print(f"   客户: 删除 {deleted_customers} 个，保留 {preserved_customers} 个，失败 {failed_customers} 个")
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
        """Create product categories"""
        print("📂 Creating product categories...")

        categories = [
            {"name": "Electronics", "description": "Smartphones, computers, digital devices, etc."},
            {"name": "Smart Home", "description": "Smart devices, home automation, etc."},
            {"name": "Accessories", "description": "Chargers, cables, and other accessories"},
            {"name": "Office Supplies", "description": "Office equipment, stationery, etc."}
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
                print(f"  ✅ Created category: {category['name']} (ID: {category_id})")
            else:
                print(f"  ❌ Category creation failed: {category['name']} - {response.get('error', 'Unknown error')}")

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
        print("🛒 Starting to create test products...")

        current_date = datetime.now()

        # New product data (English versions)
        draft_products = [
            {
                "name": "Smart Watch Pro Max",
                "type": "simple",
                "status": "draft",
                "regular_price": "299.99",
                "description": "Next-generation smartwatch with health monitoring, fitness tracking, and AI assistant features",
                "short_description": "Flagship wearable device",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-10-01"},
                    {"key": "pre_order_discount", "value": "10"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=1)).isoformat(),
                "date_modified": (current_date - timedelta(hours=10)).isoformat()
            },
            {
                "name": "Wireless Noise-Canceling Headphones Ultra",
                "type": "simple",
                "status": "pending",
                "regular_price": "159.99",
                "description": "Premium active noise-canceling headphones with 48-hour battery life and Hi-Res audio certification",
                "short_description": "Ultimate audio experience",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-15"},
                    {"key": "pre_order_discount", "value": "15"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=3)).isoformat(),
                "date_modified": (current_date - timedelta(hours=5)).isoformat()
            },
            {
                "name": "Smart Home Control Hub",
                "type": "simple",
                "status": "draft",
                "regular_price": "89.99",
                "description": "Central hub for whole-home smart automation, supports multiple protocols and voice control",
                "short_description": "Make your home smarter",
                "categories": [{"id": categories.get("Smart Home")}] if categories.get("Smart Home") else [],
                "meta_data": [
                    {"key": "launch_date", "value": "2025-09-20"},
                    {"key": "pre_order_discount", "value": "20"},
                    {"key": "product_type", "value": "new_product"}
                ],
                "date_created": (current_date - timedelta(days=4)).isoformat(),
                "date_modified": (current_date - timedelta(hours=15)).isoformat()
            }
        ]

        # Sale product data (English versions)
        sale_products = [
            {
                "name": "Bluetooth Speaker Mini",
                "type": "simple",
                "status": "publish",
                "regular_price": "29.99",
                "sale_price": "19.99",
                "description": "Portable Bluetooth speaker with 360-degree surround sound and IPX7 waterproof rating",
                "short_description": "Your portable music companion",
                "categories": [{"id": categories.get("Electronics")}] if categories.get("Electronics") else [],
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
                "name": "USB-C Cable Set",
                "type": "simple",
                "status": "publish",
                "regular_price": "9.99",
                "sale_price": "5.99",
                "description": "High-speed charging cable set including 3ft, 6ft, and 10ft lengths",
                "short_description": "One set for all your needs",
                "categories": [{"id": categories.get("Accessories")}] if categories.get("Accessories") else [],
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
                "name": "Wireless Charging Pad",
                "type": "simple",
                "status": "publish",
                "regular_price": "19.99",
                "sale_price": "14.99",
                "description": "15W fast wireless charging pad supporting multiple devices simultaneously",
                "short_description": "Say goodbye to cables",
                "categories": [{"id": categories.get("Accessories")}] if categories.get("Accessories") else [],
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
                "name": "Laptop Stand",
                "type": "simple",
                "status": "publish",
                "regular_price": "15.99",
                "sale_price": "9.99",
                "description": "Ergonomic design with adjustable height and angle, made from premium aluminum alloy",
                "short_description": "Improve your workspace ergonomics",
                "categories": [{"id": categories.get("Office Supplies")}] if categories.get("Office Supplies") else [],
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

    def create_test_customers_v2(self) -> Dict:
        """
        创建或更新测试客户的订阅偏好 V2
        新逻辑：
        1. 使用 .welcome 后缀而不是时间戳
        2. 检查客户是否已存在，存在则跳过创建
        3. 基于customer_emails.txt中的40位真实客户信息

        策略：如果客户不存在则创建，如果存在则跳过
        随机分配订阅偏好：
        - 60% 订阅新品提醒 + 折扣提醒
        - 20% 只订阅折扣提醒
        - 15% 只订阅新品提醒
        - 5% 不订阅任何提醒

        Returns:
            创建/更新结果字典
        """
        print("👥 开始创建或更新测试客户的订阅偏好 (V2 逻辑)...")

        # 40位真实客户数据 - 使用 .welcome 后缀
        customers_data = [
            ("Samuel", "Garcia", "samuel.garcia.welcome@mcp.com"),
            ("Henry", "Nguyen", "henryn.welcome@mcp.com"),
            ("Robert", "Collins", "robert.collins.welcome@mcp.com"),
            ("Mark", "Allen", "allenm.welcome@mcp.com"),
            ("Joshua", "Flores", "floresj.welcome@mcp.com"),
            ("Mary", "Edwards", "mary.edwards57.welcome@mcp.com"),
            ("Stephen", "Lewis", "slewis.welcome@mcp.com"),
            ("Nicholas", "Wilson", "nwilson.welcome@mcp.com"),
            ("Robert", "Johnson", "johnsonr.welcome@mcp.com"),
            ("Deborah", "Wright", "deborahw99.welcome@mcp.com"),
            ("Timothy", "Carter", "timothyc57.welcome@mcp.com"),
            ("Kathleen", "Kelly", "kathleen_kelly.welcome@mcp.com"),
            ("Andrew", "Ramos", "ramosa.welcome@mcp.com"),
            ("Edward", "Davis", "edavis.welcome@mcp.com"),
            ("Amanda", "Chavez", "amanda_chavez.welcome@mcp.com"),
            ("Eric", "Murphy", "emurphy.welcome@mcp.com"),
            ("Anthony", "Ortiz", "anthonyo.welcome@mcp.com"),
            ("Marie", "Walker", "marie.walker.welcome@mcp.com"),
            ("Samuel", "Sanders", "samuel_sanders77.welcome@mcp.com"),
            ("Alexander", "Roberts", "alexanderr.welcome@mcp.com"),
            ("Betty", "Cooper", "betty.cooper.welcome@mcp.com"),
            ("Christina", "Adams", "adamsc.welcome@mcp.com"),
            ("Martha", "Hill", "martha.hill.welcome@mcp.com"),
            ("Michael", "Reed", "michael.reed.welcome@mcp.com"),
            ("Emily", "Morris", "emorris.welcome@mcp.com"),
            ("Timothy", "Gomez", "timothy_gomez54.welcome@mcp.com"),
            ("Mary", "Torres", "maryt92.welcome@mcp.com"),
            ("Shirley", "Mendoza", "mendozas52.welcome@mcp.com"),
            ("Melissa", "Martin", "melissa.martin95.welcome@mcp.com"),
            ("Thomas", "Sanchez", "thomas_sanchez8.welcome@mcp.com"),
            ("Christina", "Harris", "harrisc.welcome@mcp.com"),
            ("Scott", "Martin", "scottm.welcome@mcp.com"),
            ("Tyler", "Roberts", "tyler_roberts72.welcome@mcp.com"),
            ("Thomas", "Nelson", "tnelson.welcome@mcp.com"),
            ("Steven", "Thomas", "sthomas.welcome@mcp.com"),
            ("Raymond", "Bennett", "bennettr.welcome@mcp.com"),
            ("Melissa", "Cruz", "mcruz.welcome@mcp.com"),
            ("Sharon", "Lewis", "lewiss.welcome@mcp.com"),
            ("Mary", "Alvarez", "alvarezm51.welcome@mcp.com"),
            ("Emily", "Stewart", "stewarte98.welcome@mcp.com")
        ]

        # 订阅偏好分配：确保有足够的订阅用户用于测试
        subscription_patterns = [
            # 60% 订阅新品+折扣 (24个客户)
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            {"new_product_alerts": True, "discount_alerts": True},
            # 20% 只订阅折扣 (8个客户)
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            {"new_product_alerts": False, "discount_alerts": True},
            # 15% 只订阅新品 (6个客户)
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            {"new_product_alerts": True, "discount_alerts": False},
            # 5% 不订阅 (2个客户)
            {"new_product_alerts": False, "discount_alerts": False},
            {"new_product_alerts": False, "discount_alerts": False}
        ]

        created_count = 0
        updated_count = 0
        failed_count = 0

        print(f"🎯 开始处理 {len(customers_data)} 个客户...")

        for i, (first_name, last_name, email) in enumerate(customers_data):
            print(f"\n📝 处理客户 {i+1}/{len(customers_data)}: {email}")

            # 分配订阅偏好
            subscription_pref = subscription_patterns[i] if i < len(subscription_patterns) else subscription_patterns[0]
            print(f"📋 设置订阅偏好: {subscription_pref}")

            # 检查客户是否已经存在
            print(f"🔍 检查客户是否已存在: {email}")

            try:
                search_success, existing_customer = self.wc_client.search_customer_by_email(email)

                if search_success and existing_customer:
                    print(f"ℹ️ 客户已存在，跳过创建: {email} (ID: {existing_customer.get('id')})")

                    # 更新现有客户的订阅偏好
                    customer_id = existing_customer.get('id')
                    update_data = {
                        "meta_data": [
                            {
                                "key": "subscription_preferences",
                                "value": json.dumps(subscription_pref)
                            }
                        ]
                    }

                    update_success, update_result = self.wc_client.update_customer(str(customer_id), update_data)
                    if update_success:
                        print(f"✅ 更新客户订阅偏好成功: {email}")
                        updated_count += 1

                        # 添加到created_customers列表用于统计
                        self.created_customers.append({
                            'id': customer_id,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'new_product_alerts': subscription_pref.get('new_product_alerts', False),
                            'discount_alerts': subscription_pref.get('discount_alerts', False),
                            'action': 'updated'
                        })
                    else:
                        print(f"❌ 更新客户订阅偏好失败: {email} - {update_result}")
                        failed_count += 1
                else:
                    # 客户不存在，创建新客户
                    print(f"🆕 创建新客户: {email}")
                    customer_data = {
                        "email": email,
                        "first_name": first_name,
                        "last_name": last_name,
                        "meta_data": [
                            {
                                "key": "subscription_preferences",
                                "value": json.dumps(subscription_pref)
                            }
                        ],
                        "billing": {
                            "email": email,
                            "first_name": first_name,
                            "last_name": last_name
                        }
                    }

                    create_success, create_result = self.wc_client.create_customer(customer_data)
                    if create_success:
                        customer_id = create_result.get('id')
                        print(f"✅ 创建客户成功: {email} (ID: {customer_id})")
                        created_count += 1

                        # 添加到created_customers列表用于统计
                        self.created_customers.append({
                            'id': customer_id,
                            'email': email,
                            'first_name': first_name,
                            'last_name': last_name,
                            'new_product_alerts': subscription_pref.get('new_product_alerts', False),
                            'discount_alerts': subscription_pref.get('discount_alerts', False),
                            'action': 'created'
                        })
                    else:
                        print(f"❌ 创建客户失败: {email} - {create_result}")
                        failed_count += 1

            except Exception as e:
                print(f"❌ 处理客户 {email} 时出错: {e}")
                failed_count += 1

            time.sleep(0.2)  # 避免API限制

        # 统计订阅情况
        new_product_count = len([c for c in self.created_customers if c.get('new_product_alerts', False)])
        discount_count = len([c for c in self.created_customers if c.get('discount_alerts', False)])

        print(f"\n📊 客户处理完成:")
        print(f"   新建客户: {created_count} 个")
        print(f"   更新客户: {updated_count} 个")
        print(f"   处理失败: {failed_count} 个")
        print(f"   新品订阅: {new_product_count} 个客户")
        print(f"   折扣订阅: {discount_count} 个客户")

        success = failed_count == 0

        if not success:
            print("❌ 新品邮件任务测试数据设置失败！")
        else:
            print("✅ 新品邮件任务测试数据设置成功！")

        return {
            "created_customers": created_count,
            "updated_customers": updated_count,
            "failed_customers": failed_count,
            "new_product_subscribers": new_product_count,
            "discount_subscribers": discount_count,
            "success": success
        }

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

    print(f"🚀 初始化新品邮件任务设置器 V2: {site_url}")

    setup = NewProductEmailSetupV2(site_url, consumer_key, consumer_secret)

    # 1. 清理现有商品和分类数据
    print("\n" + "="*60)
    print("第一步：清理商店中的商品和分类数据")
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

    # 4. 创建或更新客户订阅偏好 (使用V2逻辑)
    print("\n" + "="*60)
    print("第四步：创建或更新客户订阅偏好 (V2 逻辑)")
    print("="*60)

    customer_result = setup.create_test_customers_v2()

    # 5. 保存结果
    if product_result.get('success') and customer_result.get('success'):
        print("\n✅ 新品邮件任务测试数据设置完成！")

        # 保存预期结果到任务目录
        expected_results = setup.get_expected_results()
        results_dir = task_dir
        expected_results_path = os.path.join(results_dir, 'expected_results.json')
        with open(expected_results_path, 'w', encoding='utf-8') as f:
            json.dump(expected_results, f, indent=2, ensure_ascii=False)
        print(f"📄 预期结果已保存到 {expected_results_path}")

        # 保存清理结果到任务目录
        clear_results_path = os.path.join(results_dir, 'clear_results.json')
        with open(clear_results_path, 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print(f"📄 清理结果已保存到 {clear_results_path}")

        # 保存完整设置结果到任务目录
        full_setup_result = {
            "clear_result": clear_result,
            "categories": categories,
            "product_result": product_result,
            "customer_result": customer_result,
            "expected_results": expected_results,
            "setup_timestamp": datetime.now().isoformat()
        }

        setup_results_path = os.path.join(results_dir, 'setup_results.json')
        with open(setup_results_path, 'w', encoding='utf-8') as f:
            json.dump(full_setup_result, f, indent=2, ensure_ascii=False)
        print(f"📄 完整设置结果已保存到 {setup_results_path}")

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

        setup = NewProductEmailSetupV2(site_url, consumer_key, consumer_secret)
        clear_result = setup.clear_all_data()

        clear_results_path = os.path.join(task_dir, 'clear_results.json')
        with open(clear_results_path, 'w', encoding='utf-8') as f:
            json.dump(clear_result, f, indent=2, ensure_ascii=False)
        print(f"📄 清理结果已保存到 {clear_results_path}")

    else:
        # 完整流程：清理 + 创建测试数据
        main()