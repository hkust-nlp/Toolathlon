import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
from pathlib import Path

# 添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.append(task_dir)

from preprocess.woocommerce_client import WooCommerceClient, ImageManager, add_woocommerce_extensions

class TestProductSetup:
    """测试产品设置器 - 为更新商品主图任务创建测试数据"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str, 
                 wp_username: str = None, wp_password: str = None):
        """
        初始化测试产品设置器
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
            wp_username: WordPress管理员用户名 (用于媒体上传)
            wp_password: WordPress管理员密码 (用于媒体上传)
        """
        self.wc_client = add_woocommerce_extensions(
            WooCommerceClient(site_url, consumer_key, consumer_secret, wp_username=wp_username, wp_password=wp_password)
        )
        self.image_manager = ImageManager(self.wc_client)
        self.created_products = []
        self.created_attributes = []
        self.created_orders = []
        # 使用时间戳生成唯一的图片ID
        import time
        timestamp = int(time.time())
        self.image_ids = {
            "红色": 16 + timestamp,
            "蓝色": 34 + timestamp,
            "绿色": 35 + timestamp,
            "黄色": 36 + timestamp,
        }
        print(f"🎨 图片ID已初始化（时间戳: {timestamp}）: {self.image_ids}")
    
    def clear_all_products(self) -> Dict:
        """清理商店中的所有商品、属性和媒体"""
        print("🧹 开始清理商店中的所有商品和相关数据...")
        
        try:
            # 1. 删除所有商品
            print("📦 清理商品...")
            all_products = self.wc_client.get_all_products()

            print(f"   🔄 清理商品: {all_products}")
            deleted_products = 0
            failed_products = 0
            
            if all_products:
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
            
            # 2. 清理自定义属性
            print("🏷️ 清理商品属性...")
            success, attributes = self.wc_client.get_product_attributes()
            deleted_attributes = 0
            failed_attributes = 0
            
            if success and attributes:
                test_attribute_names = ["颜色", "尺寸", "材质", "Color", "Size", "Material"]
                
                for attr in attributes:
                    attr_name = attr.get('name', '')
                    attr_id = attr.get('id')
                    
                    if attr_name in test_attribute_names:
                        try:
                            delete_url = f"{self.wc_client.api_base}/products/attributes/{attr_id}"
                            response = self.wc_client.session.delete(delete_url, params={'force': True})
                            
                            if response.status_code in [200, 204]:
                                print(f"   ✅ 删除属性: {attr_name} (ID: {attr_id})")
                                deleted_attributes += 1
                            else:
                                print(f"   ⚠️ 跳过属性: {attr_name}")
                        except Exception as e:
                            print(f"   ❌ 删除属性 {attr_name} 时出错: {e}")
                            failed_attributes += 1
                        
                        time.sleep(0.3)
            

            # 3. 清理订单
            print("🗑️ 开始删除所有订单...")
    
            page = 1
            per_page = 50
            total_deleted = 0
            while True:
                # 获取订单列表
                success, orders = self.wc_client._make_request('GET', 'orders', params={"page": page, "per_page": per_page})
                if not success:
                    print(f"⚠️ 获取订单失败: {orders}")
                    break

                if not orders:
                    # 没有更多订单
                    break

                for order in orders:
                    order_id = order['id']
                    success, response = self.wc_client.delete_order(order_id)
                    if success:
                        total_deleted += 1
                    else:
                        print(f"⚠️ 删除订单 {order_id} 失败: {response}")

                page += 1

            clear_result = {
                "success": failed_products == 0 and failed_attributes == 0,
                "products": {
                    "total_found": len(all_products) if all_products else 0,
                    "deleted": deleted_products,
                    "failed": failed_products
                },
                "attributes": {
                    "deleted": deleted_attributes,
                    "failed": failed_attributes
                },
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\n📊 清理完成:")
            print(f"   商品: 删除 {deleted_products} 个，失败 {failed_products} 个")
            print(f"   属性: 删除 {deleted_attributes} 个，失败 {failed_attributes} 个")
            print(f"   订单: 删除 {total_deleted} 个")
            
            return clear_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 清理过程中出错: {e}")
            return error_result
    
    def setup_product_attributes(self) -> Dict:
        """设置商品属性（颜色、尺寸等）"""
        print("🏷️ 设置商品属性...")
        
        attributes_to_create = [
            {
                "name": "颜色",
                "slug": "color",
                "type": "select",
                "order_by": "menu_order",
                "has_archives": True,
                "terms": [
                    {"name": "红色", "slug": "red"},
                    {"name": "蓝色", "slug": "blue"},
                    {"name": "绿色", "slug": "green"},
                    {"name": "黄色", "slug": "yellow"},
                ]
            },
        ]
        
        created_attributes = []
        
        for attr_data in attributes_to_create:
            # 创建属性
            print(f"   创建属性: {attr_data['name']}")
            
            attribute_info = {
                "name": attr_data["name"],
                "slug": attr_data["slug"],
                "type": attr_data["type"],
                "order_by": attr_data["order_by"],
                "has_archives": attr_data["has_archives"]
            }
            
            success, attr_result = self.wc_client.create_product_attribute(attribute_info)
            
            if success:
                attr_id = attr_result.get('id')
                print(f"     ✅ 属性创建成功 (ID: {attr_id})")
                
                # 创建属性项
                created_terms = []
                for term_data in attr_data["terms"]:
                    print(f"     创建属性项: {term_data['name']}")
                    
                    success_term, term_result = self.wc_client.create_attribute_term(
                        str(attr_id), term_data
                    )
                    
                    if success_term:
                        created_terms.append({
                            "id": term_result.get('id'),
                            "name": term_result.get('name'),
                            "slug": term_result.get('slug')
                        })
                        print(f"       ✅ 属性项创建成功: {term_data['name']}")
                    else:
                        print(f"       ❌ 属性项创建失败: {term_data['name']} - {term_result}")
                    
                    time.sleep(0.3)
                
                created_attributes.append({
                    "id": attr_id,
                    "name": attr_result.get('name'),
                    "slug": attr_result.get('slug'),
                    "terms": created_terms
                })
                
                self.created_attributes.append(created_attributes[-1])
                
            else:
                print(f"     ❌ 属性创建失败: {attr_data['name']} - {attr_result}")
            
            time.sleep(0.5)
        
        return {
            "success": len(created_attributes) > 0,
            "created_attributes": created_attributes,
            "total_created": len(created_attributes)
        }
    
    def create_test_products(self, delete_existing_orders=True) -> Dict:
        """
        创建测试商品
        包括：
        1. 可变商品（有不同规格和对应图片）
        2. 模拟上周销量数据
        
        Args:
            delete_existing_orders: 是否在创建新订单前删除现有订单（默认True）
        
        Returns:
            创建结果字典
        """
        print("🛒 开始创建测试商品...")
        
        #1. 上传测试图片
        print("🎨 创建并上传测试图片...")
        test_images = self.image_manager.create_test_images(6)
        uploaded_images = self.image_manager.upload_test_images(test_images)
        self.uploaded_images = uploaded_images
        
        if not uploaded_images:
            return {"success": False, "error": "无法上传测试图片"}
        
        # 更新图片ID为真实的媒体ID
        print("🔄 更新图片ID映射...")
        self.image_ids = {}
        for img in uploaded_images:
            color = img.get('color', '')
            media_id = img.get('media_id')
            if color and media_id:
                self.image_ids[color] = media_id
                print(f"   {color}: {media_id}")
        
        print(f"✅ 图片ID已更新: {self.image_ids}")
        
        # 2. 获取属性信息
        color_attr = next((attr for attr in self.created_attributes if attr['name'] == '颜色'), None)
        
        if not color_attr:
            return {"success": False, "error": "缺少必要的商品属性"}
        
        # 3. 定义测试商品数据
        test_products = self._generate_variable_product_data(color_attr)

        print(f"   🔄 测试商品数据: {test_products}")
        
        created_count = 0
        failed_count = 0
        
        for product_data in test_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                product_type = result.get('type', 'simple')
                
                created_product_info = {
                    'id': product_id,
                    'name': product_name,
                    'type': product_type,
                    'variations': []
                }
                
                print(f"✅ 创建商品: {product_name} (ID: {product_id}, Type: {product_type})")
                
                # 验证产品状态
                product_status = result.get('status', 'unknown')
                if product_status != 'publish':
                    print(f"⚠️ 产品状态为: {product_status}，尝试更新为 publish")
                    update_data = {"status": "publish"}
                    success_update, update_result = self.wc_client._make_request('PUT', f'products/{product_id}', data=update_data)
                    if success_update:
                        print(f"✅ 产品状态已更新为 publish")
                    else:
                        print(f"❌ 更新产品状态失败: {update_result}")
                
                # 如果是可变商品，创建变体
                if product_type == 'variable':
                    variations_info = self._create_product_variations(
                        product_id, product_data, color_attr
                    )
                    created_product_info['variations'] = variations_info
                
                self.created_products.append(created_product_info)
                created_count += 1
            else:
                print(f"❌ 创建商品失败: {product_data.get('name')} - {result}")
                failed_count += 1
            
            # 避免API限制
            time.sleep(1.0)
        
        # 4. 创建模拟订单数据
        if created_count > 0:
            print("📊 创建模拟销量数据...")
            # 根据参数决定是否删除现有订单
            if delete_existing_orders:
                self._delete_existing_orders()
            else:
                print("ℹ️ 保留现有订单，新订单将添加到现有订单中")
            # 使用42作为默认随机种子保证可重现性，如需真随机可传递None
            self._create_mock_orders(random_seed=42)
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "variable_products_count": len([p for p in self.created_products if p.get('type') == 'variable'])
        }
        
        print(f"商品创建完成:")
        print(f"   成功创建: {created_count} 个商品")
        print(f"   创建失败: {failed_count} 个商品")
        print(f"   可变商品: {setup_result['variable_products_count']} 个")
        
        return setup_result
    
    def _generate_variable_product_data(self, color_attr: Dict) -> List[Dict]:
        """生成可变商品数据"""
        import random
        current_date = datetime.now()
        
        # 多种不同类型的商品，增加测试的真实性
        product_templates = [
            {
                "name": "彩虹运动鞋",
                "description": "舒适轻便的运动鞋，多种颜色可选，适合日常运动和休闲穿着",
                "short_description": "时尚彩虹运动鞋",
                "base_price": "199.99",
                "days_ago": 45
            },
            {
                "name": "时尚背包",
                "description": "大容量多功能背包，采用优质材料制作，有多种颜色可选",
                "short_description": "多色时尚背包",
                "base_price": "129.99",
                "days_ago": 30
            },
            {
                "name": "无线蓝牙耳机",
                "description": "高音质无线蓝牙耳机，支持降噪功能，多种色彩外观",
                "short_description": "彩色蓝牙耳机",
                "base_price": "299.99",
                "days_ago": 60
            }
        ]
        
        products = []
        
        for template in product_templates:
            product = {
                "name": template["name"],
                "type": "variable", 
                "description": template["description"],
                "short_description": template["short_description"],
                "regular_price": "",
                "manage_stock": False,
                "stock_status": "instock",
                "status": "publish",  # 确保产品是发布状态
                "date_created": (current_date - timedelta(days=template["days_ago"])).isoformat(),
                "images": None,
                "attributes": [
                    {
                        "id": color_attr['id'],
                        "name": color_attr['name'],
                        "position": 0,
                        "visible": True,
                        "variation": True,
                        "options": [term['name'] for term in color_attr['terms']]
                    }
                ],
                "meta_data": [
                    {"key": "test_product_type", "value": "variable_product"},
                    {"key": "base_price", "value": template["base_price"]},
                    {"key": "created_days_ago", "value": str(template["days_ago"])}
                ]
            }
            products.append(product)
        
        return products
    
    def _create_product_variations(self, product_id: int, product_data: Dict, 
                                   color_attr: Dict) -> List[Dict]:
        """为商品创建变体"""
        import random
        
        print(f"   🔄 为商品 {product_id} 创建变体...")
        
        variations_info = []
        variation_counter = 0
        
        # 获取商品的基础价格
        base_price = "199.99"  # 默认价格
        for meta in product_data.get('meta_data', []):
            if meta.get('key') == 'base_price':
                base_price = meta.get('value', '199.99')
                break
        
        product_name = product_data.get('name', '')
        
        # 为每个商品创建所有颜色的变体
        for color_term in color_attr['terms']:
            color_name = color_term['name']
            
            # 根据商品类型设定库存和价格变化
            stock_quantity = random.randint(10, 25)
            
            # 价格可能有小幅波动
            price_float = float(base_price)
            price_variation = random.uniform(0.95, 1.05)  # ±5%的价格变化
            final_price = round(price_float * price_variation, 2)
            
            variation_data = {
                "regular_price": str(final_price),
                "stock_quantity": stock_quantity,
                "manage_stock": True,
                "stock_status": "instock",
                "attributes": [
                    {
                        "id": color_attr['id'],
                        "name": color_attr['name'],
                        "option": color_term['name']
                    }
                ],
                "meta_data": [
                    {"key": "test_variation_color", "value": color_term['name']},
                    {"key": "base_price", "value": base_price},
                    {"key": "price_variation_factor", "value": str(round(price_variation, 3))}
                ]
            }
            
            # 只有当颜色对应的图片ID存在时才添加图片
            if color_name in self.image_ids and self.image_ids[color_name]:
                variation_data["image"] = {
                    "id": self.image_ids[color_name]
                }
                print(f"     🖼️ 设置变体图片: {color_name} -> ID {self.image_ids[color_name]}")
            else:
                print(f"     ⚠️ 未找到颜色 {color_name} 对应的图片ID")
            
            success, variation_result = self.wc_client.create_variation(str(product_id), variation_data)
            
            if success:
                variation_info = {
                    'id': variation_result.get('id'),
                    'color': color_term['name'],
                    'price': str(final_price),
                    'image_id': self.image_ids.get(color_name),  # 使用真实的图片ID
                    'stock_quantity': stock_quantity
                }
                variations_info.append(variation_info)
                print(f"     ✅ 创建变体: {color_term['name']} - ¥{final_price} (ID: {variation_result.get('id')})")
                variation_counter += 1
            else:
                print(f"     ❌ 创建变体失败: {color_term['name']} - {variation_result}")
            
            time.sleep(0.5)
        
        print(f"   📊 {product_name} 共创建了 {variation_counter} 个变体")
        return variations_info
    
    def _create_mock_orders(self, random_seed=None):
        """创建并上传模拟订单数据（模拟上周的销量）
        
        Args:
            random_seed: 随机种子，None表示使用真随机，数字表示可重现的随机结果
        """
        import random
        
        # 设置随机种子
        if random_seed is not None:
            random.seed(random_seed)
            print(f"📦 创建模拟销量数据（随机种子: {random_seed}）...")
        else:
            print("📦 创建模拟销量数据（真随机模式）...")
        
        print("   🎲 使用随机受欢迎程度分配，任何变体都可能成为最佳销售")

        today = datetime.now()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)

        # 创建所有订单的计划列表，然后打乱顺序
        all_orders_plan = []

        for product in self.created_products:
            if product.get('type') == 'variable' and product.get('variations'):
                variations = product['variations']
                product_name = product.get('name', '')
                
                # 根据商品类型设定基础销量倍数
                if '运动鞋' in product_name:
                    product_multiplier = 1.0  # 运动鞋销量标准
                elif '背包' in product_name:
                    product_multiplier = 0.7  # 背包销量较低
                elif '耳机' in product_name:
                    product_multiplier = 1.2  # 耳机销量较高
                else:
                    product_multiplier = 1.0
                
                # 为每个变体随机分配受欢迎程度，创造随机的销量分布
                popularity_levels = ['高热门', '中热门', '普通', '冷门']
                variation_popularity = random.sample(popularity_levels, min(len(variations), len(popularity_levels)))
                
                # 如果变体数量超过热门级别数量，其余的随机分配
                if len(variations) > len(popularity_levels):
                    additional_popularity = [random.choice(popularity_levels) for _ in range(len(variations) - len(popularity_levels))]
                    variation_popularity.extend(additional_popularity)
                
                print(f"🛍️ 为商品 '{product_name}' 创建订单 (销量倍数: {product_multiplier})")
                print(f"   📊 变体受欢迎程度分配: {dict(zip([v.get('color', f'变体{i}') for i, v in enumerate(variations)], variation_popularity))}")

                for i, variation in enumerate(variations):
                    # 根据随机分配的受欢迎程度确定销量范围
                    popularity = variation_popularity[i]
                    
                    if popularity == '高热门':
                        base_sales_range = (6, 9)  # 最高销量
                    elif popularity == '中热门':
                        base_sales_range = (4, 5)   # 中等销量
                    elif popularity == '普通':
                        base_sales_range = (2, 3)    # 普通销量
                    else:  # 冷门
                        base_sales_range = (1, 2)    # 较低销量
                    
                    # 应用商品类型倍数
                    min_sales = max(1, int(base_sales_range[0] * product_multiplier))
                    max_sales = max(2, int(base_sales_range[1] * product_multiplier))
                    base_sales = random.randint(min_sales, max_sales)
                    
                    print(f"   🎯 {variation.get('color', f'变体{i}')} ({popularity}): 计划 {base_sales} 个订单")
                    
                    # 为每个订单生成随机的日期和时间
                    for order_num in range(base_sales):
                        # 生成上周内的随机日期时间
                        random_day = random.randint(0, 6)  # 周一到周日
                        random_hour = random.randint(8, 22)  # 8点到22点
                        random_minute = random.randint(0, 59)
                        random_second = random.randint(0, 59)
                        
                        order_date = last_monday + timedelta(
                            days=random_day,
                            hours=random_hour,
                            minutes=random_minute,
                            seconds=random_second
                        )
                        
                        # 随机数量：大部分是1个，偶尔2-3个
                        quantity = random.choices([1, 2, 3], weights=[70, 25, 5])[0]
                        
                        all_orders_plan.append({
                            'product': product,
                            'variation': variation,
                            'variation_index': i,
                            'variation_popularity': variation_popularity[i],  # 保存受欢迎程度信息
                            'order_date': order_date,
                            'quantity': quantity,
                            'order_number': order_num
                        })

        # 打乱订单创建顺序（按日期时间排序，但加入一些随机性）
        print(f"📋 计划创建 {len(all_orders_plan)} 个订单...")
        
        # 先按日期排序，然后加入一些随机打乱
        all_orders_plan.sort(key=lambda x: x['order_date'])
        
        # 分组打乱：每3-5个订单为一组进行局部打乱，保持大致的时间顺序但增加随机性
        shuffled_orders = []
        group_size = random.randint(3, 5)
        for i in range(0, len(all_orders_plan), group_size):
            group = all_orders_plan[i:i+group_size]
            random.shuffle(group)
            shuffled_orders.extend(group)
        
        print(f"🔀 订单顺序已打乱，开始创建...")

        # 执行订单创建
        successful_orders = 0
        failed_orders = 0
        
        for order_plan in shuffled_orders:
            product = order_plan['product']
            variation = order_plan['variation']
            variation_index = order_plan['variation_index']
            variation_popularity_info = order_plan['variation_popularity']
            order_date = order_plan['order_date']
            quantity = order_plan['quantity']
            product_name = product.get('name', '')
            
            # 构造 WooCommerce 订单数据
            order_data = {
                "status": "completed",
                "customer_id": 1,
                "payment_method": "bacs",
                "payment_method_title": "Direct Bank Transfer",
                # 注意：date_created 是只读字段，API会忽略此值并使用当前时间
                # "date_created": order_date.isoformat(),
                "line_items": [
                    {
                        "product_id": product['id'],
                        "variation_id": variation['id'],
                        "quantity": quantity,
                        "price": variation['price']
                    }
                ],
                "meta_data": [
                    {"key": "test_order", "value": "true"},
                    {"key": "test_week", "value": f"{last_monday.date()}_to_{last_sunday.date()}"},
                    {"key": "original_date_created", "value": order_date.isoformat()},  # 存储原始日期
                    {"key": "simulated_historical_order", "value": "true"},
                    {"key": "variation_color", "value": variation.get('color', '')},
                    {"key": "quantity_ordered", "value": str(quantity)},
                    {"key": "variation_index", "value": str(variation_index)},
                    {"key": "variation_popularity", "value": variation_popularity_info}
                ]
            }

            # 调用 create_order 上传订单
            success, response = self.wc_client.create_order(order_data)

            # print("success", success)
            # print("response", response)

            if success:
                wc_order_id = response.get('id')
                successful_orders += 1
                print(f"✅ 订单 #{wc_order_id} 创建成功 - {variation.get('color', '')} x{quantity} @ {order_date.strftime('%m-%d %H:%M')}")
                
                # 尝试更新订单的历史创建日期
                try:
                    self._update_order_historical_date(wc_order_id, order_date.isoformat())
                except Exception as e:
                    print(f"⚠️ 更新订单 #{wc_order_id} 历史日期失败: {e}")
            else:
                wc_order_id = None
                failed_orders += 1
                print(f"❌ 创建订单失败: {response}")

            # 保存已创建订单信息               
            self.created_orders.append({
                'product_id': product['id'],
                'product_name': product_name,
                'variation_id': variation['id'],
                'sales_count': quantity,  # 现在记录实际数量
                'order_date': order_date.isoformat(),
                'variation_color': variation.get('color', ''),
                'variation_index': variation_index,
                'variation_popularity': variation_popularity_info,
                'expected_top_seller': False,  # 现在不能简单根据索引判断
                'wc_order_id': wc_order_id,
                'quantity': quantity
            })
            
            # 添加延迟避免API限制
            time.sleep(0.8)

        # 统计每个变体的详细销量信息
        variation_stats = {}
        total_quantity = 0
        
        for order in self.created_orders:
            if order['wc_order_id']:  # 只统计成功创建的订单
                color = order['variation_color']
                quantity = order['quantity']
                popularity = order.get('variation_popularity', '普通')
                product_name = order.get('product_name', '未知商品')
                
                key = f"{product_name}-{color}"
                if key not in variation_stats:
                    variation_stats[key] = {
                        'product_name': product_name,
                        'color': color,
                        'popularity': popularity,
                        'orders': 0, 
                        'total_quantity': 0,
                        'variation_id': order['variation_id']
                    }
                variation_stats[key]['orders'] += 1
                variation_stats[key]['total_quantity'] += quantity
                total_quantity += quantity
        
        # 按销量排序
        sorted_sales = sorted(variation_stats.items(), key=lambda x: x[1]['total_quantity'], reverse=True)
        
        print(f"\n📊 模拟销量数据创建完成:")
        print(f"   ✅ 成功创建: {successful_orders} 个订单")
        print(f"   ❌ 创建失败: {failed_orders} 个订单")
        print(f"   📦 总销量: {total_quantity} 件商品")
        print(f"   📅 时间范围: {last_monday.date()} 到 {last_sunday.date()}")
        
        print(f"\n🏆 所有变体销量排行:")
        for i, (key, stats) in enumerate(sorted_sales, 1):
            popularity_emoji = {
                '高热门': '🔥', '中热门': '⭐', '普通': '👍', '冷门': '💤'
            }.get(stats['popularity'], '📦')
            
            print(f"   {i}. {stats['product_name']} - {stats['color']} {popularity_emoji}: "
                  f"{stats['total_quantity']} 件 ({stats['orders']} 个订单)")
        
        if sorted_sales:
            top_seller_info = sorted_sales[0][1]
            print(f"\n🥇 实际最佳销售变体: {top_seller_info['product_name']} - {top_seller_info['color']} "
                  f"(预设: {top_seller_info['popularity']})")
            
            # 按商品分组显示最佳销售变体
            product_top_sellers = {}
            for key, stats in sorted_sales:
                product_name = stats['product_name']
                if product_name not in product_top_sellers:
                    product_top_sellers[product_name] = stats
            
            print(f"\n🎯 各商品最佳销售变体:")
            for product_name, stats in product_top_sellers.items():
                print(f"   📱 {product_name}: {stats['color']} ({stats['total_quantity']} 件)")
        
        # 详细订单列表（可选，调试时使用）
        if len(self.created_orders) <= 20:  # 只在订单数量较少时显示详细信息
            print(f"\n📋 详细订单列表:")
            for order in self.created_orders:
                if order['wc_order_id']:
                    order_time = datetime.fromisoformat(order['order_date'])
                    print(f"   订单#{order['wc_order_id']}: {order['variation_color']} x{order['quantity']} @ {order_time.strftime('%m-%d %H:%M')}")
        else:
            print(f"\n📋 订单列表过长，已省略详细信息（共 {len(self.created_orders)} 条记录）")
    
    def _delete_existing_orders(self):
        """删除现有的所有订单，确保创建订单前有干净的环境"""
        print("🗑️ 删除现有订单...")
        
        try:
            page = 1
            per_page = 50
            total_deleted = 0
            start_time = time.time()
            
            while True:
                # 获取订单列表
                success, orders = self.wc_client._make_request('GET', 'orders', params={"page": page, "per_page": per_page})
                if not success:
                    print(f"⚠️ 获取订单失败: {orders}")
                    break

                if not orders or len(orders) == 0:
                    # 没有更多订单
                    break

                print(f"   📋 第 {page} 页，找到 {len(orders)} 个订单")
                
                for i, order in enumerate(orders, 1):
                    order_id = order['id']
                    order_status = order.get('status', 'unknown')
                    success, response = self.wc_client.delete_order(order_id)
                    if success:
                        total_deleted += 1
                        print(f"   ✅ 删除订单 #{order_id} ({order_status}) [{i}/{len(orders)}]")
                    else:
                        print(f"   ❌ 删除订单 #{order_id} 失败: {response}")
                    
                    # 添加短暂延迟避免API限制
                    time.sleep(0.3)

                page += 1
                
                # 安全检查：避免无限循环
                if page > 50:  # 最多处理50页，每页50个订单 = 2500个订单
                    print("⚠️ 达到最大页数限制，停止删除")
                    break

            elapsed_time = time.time() - start_time
            if total_deleted > 0:
                print(f"✅ 成功删除 {total_deleted} 个现有订单 (用时: {elapsed_time:.1f} 秒)")
            else:
                print("ℹ️ 没有找到需要删除的订单")
                
        except Exception as e:
            print(f"❌ 删除订单过程中出错: {e}")
    
    def _update_order_historical_date(self, order_id: int, historical_date: str):
        """
        通过WooCommerce REST API更新订单元数据后，再通过数据库直接更新创建日期
        
        Args:
            order_id: WooCommerce订单ID
            historical_date: 历史日期 (ISO格式)
        """
        try:
            # 方法1：通过 REST API 更新元数据（这个总是有效的）
            update_data = {
                "meta_data": [
                    {"key": "original_date_created", "value": historical_date},
                    {"key": "simulated_historical_order", "value": "true"},
                    {"key": "date_update_attempted", "value": datetime.now().isoformat()}
                ]
            }
            
            success, result = self.wc_client.update_order(str(order_id), update_data)

            if success:
                print(f"✅ 订单 #{order_id} 元数据已更新，历史日期: {historical_date}")
            else:
                print(f"⚠️ 更新订单 #{order_id} 元数据失败: {result}")
                
            # 方法2：如果可能的话，尝试直接更新数据库（需要数据库访问权限）
            # 这部分可以通过WordPress插件或直接数据库访问来实现
            # 由于我们没有直接的数据库访问权限，这里只记录需要更新的订单
            
        except Exception as e:
            print(f"❌ 更新订单 #{order_id} 历史日期时出错: {e}")
    
    def get_expected_results(self) -> Dict:
        """获取预期结果，用于评估"""
        expected_updates = {}
        
        # 计算每个变体的实际销量
        variation_sales = {}
        for order in self.created_orders:
            if order['wc_order_id']:  # 只统计成功创建的订单
                variation_id = order['variation_id']
                quantity = order['quantity']
                if variation_id not in variation_sales:
                    variation_sales[variation_id] = 0
                variation_sales[variation_id] += quantity
        
        for product in self.created_products:
            if product.get('type') == 'variable' and product.get('variations'):
                variations = product['variations']
                if variations:
                    # 计算每个变体的销量并找出最佳销售变体
                    variation_sales_data = []
                    for variation in variations:
                        variation_id = variation['id']
                        total_sales = variation_sales.get(variation_id, 0)
                        variation_sales_data.append({
                            'variation': variation,
                            'total_sales': total_sales
                        })
                    
                    # 按销量排序
                    variation_sales_data.sort(key=lambda x: x['total_sales'], reverse=True)
                    
                    if variation_sales_data:
                        top_variation_data = variation_sales_data[0]
                        top_variation = top_variation_data['variation']
                        
                        expected_updates[product['id']] = {
                            'product_name': product['name'],
                            'expected_top_variation_id': top_variation['id'],
                            'expected_featured_image_id': top_variation.get('image_id'),
                            'expected_color': top_variation.get('color', ''),
                            'expected_sales_quantity': top_variation_data['total_sales'],
                            'current_featured_image_id': None,  # 当前主图（初始为None或默认图片）
                            'all_variations_sales': [
                                {
                                    'variation_id': vd['variation']['id'],
                                    'color': vd['variation'].get('color', ''),
                                    'sales': vd['total_sales']
                                }
                                for vd in variation_sales_data
                            ]
                        }
        
        # 统计总体信息
        total_orders = len([o for o in self.created_orders if o['wc_order_id']])
        total_quantity = sum(o['quantity'] for o in self.created_orders if o['wc_order_id'])
        
        today = datetime.now()
        last_monday = today - timedelta(days=today.weekday() + 7)
        last_sunday = last_monday + timedelta(days=6)
        
        return {
            "expected_updates": expected_updates,
            "total_products_to_update": len(expected_updates),
            "analysis_period": {
                "description": "上周（周一到周日）",
                "start_date": last_monday.date().isoformat(),
                "end_date": last_sunday.date().isoformat(),
                "note": "基于随机受欢迎程度和实际模拟销量数据确定最佳销售变体，任何变体都可能成为最佳销售"
            },
            "created_test_data": {
                "products_count": len(self.created_products),
                "variations_total": sum(len(p.get('variations', [])) for p in self.created_products),
                "total_orders": total_orders,
                "total_quantity_sold": total_quantity,
                "average_order_quantity": round(total_quantity / total_orders, 2) if total_orders > 0 else 0
            },
            "sales_summary": {
                variation_id: sales for variation_id, sales in variation_sales.items()
            }
        }
    
    def cleanup_test_data(self) -> Dict:
        """清理所有测试数据"""
        print("🧹 开始清理测试数据...")
        
        cleanup_results = {
            "products": {"deleted": 0, "failed": 0},
            "images": {"deleted": 0, "failed": 0},
            "attributes": {"deleted": 0, "failed": 0}
        }
        
        # 1. 删除商品（会自动删除变体）
        for product in self.created_products:
            product_id = product.get('id')
            product_name = product.get('name')
            
            success, result = self.wc_client.delete_product(str(product_id), force=True)
            if success:
                print(f"✅ 删除商品: {product_name} (ID: {product_id})")
                cleanup_results["products"]["deleted"] += 1
            else:
                print(f"❌ 删除商品失败: {product_name} - {result}")
                cleanup_results["products"]["failed"] += 1
            
            time.sleep(0.3)
        
        # 2. 清理属性
        for attr in self.created_attributes:
            attr_id = attr.get('id')
            attr_name = attr.get('name')
            
            try:
                delete_url = f"{self.wc_client.api_base}/products/attributes/{attr_id}"
                response = self.wc_client.session.delete(delete_url, params={'force': True})
                
                if response.status_code in [200, 204]:
                    print(f"✅ 删除属性: {attr_name} (ID: {attr_id})")
                    cleanup_results["attributes"]["deleted"] += 1
                else:
                    print(f"❌ 删除属性失败: {attr_name}")
                    cleanup_results["attributes"]["failed"] += 1
            except Exception as e:
                print(f"❌ 删除属性 {attr_name} 时出错: {e}")
                cleanup_results["attributes"]["failed"] += 1
            
            time.sleep(0.3)
        
        print(f"\n📊 清理完成:")
        print(f"   商品: 删除 {cleanup_results['products']['deleted']} 个")
        print(f"   图片: 删除 {cleanup_results['images']['deleted']} 个")
        print(f"   属性: 删除 {cleanup_results['attributes']['deleted']} 个")
        
        return cleanup_results


def main():
    """主函数 - 用于独立运行测试数据设置"""
    import sys
    
    # 检查命令行参数
    delete_orders = True  # 默认删除现有订单
    if len(sys.argv) > 1:
        if sys.argv[1] == "--keep-orders":
            delete_orders = False
            print("🔧 参数: 保留现有订单")
        elif sys.argv[1] == "--delete-orders":
            delete_orders = True
            print("🔧 参数: 删除现有订单")
        elif sys.argv[1] == "--help":
            print("📖 使用方法:")
            print("  python setup_test_products.py                # 默认删除现有订单")
            print("  python setup_test_products.py --delete-orders # 明确删除现有订单")
            print("  python setup_test_products.py --keep-orders   # 保留现有订单")
            print("  python setup_test_products.py --help         # 显示此帮助")
            return True
    
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 初始化测试产品设置器: {site_url}")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    
    try:
        # 1. 清理现有数据
        print("\n" + "="*60)
        print("第一步：清理商店中的现有数据")
        print("="*60)
        
        clear_result = setup.clear_all_products()
        if not clear_result.get('success'):
            print("⚠️ 清理未完全成功，但继续下一步...")
        
        time.sleep(3)
        
        # 2. 设置商品属性
        print("\n" + "="*60)
        print("第二步：设置商品属性")
        print("="*60)
        
        attr_result = setup.setup_product_attributes()
        if not attr_result.get('success'):
            print("❌ 属性设置失败！")
            return False
        
        time.sleep(2)
        
        # 3. 创建测试商品
        print("\n" + "="*60)
        print("第三步：创建测试商品和数据")
        print("="*60)
        
        product_result = setup.create_test_products(delete_existing_orders=delete_orders)
        
        if product_result.get('success'):
            print("✅ 测试数据设置完成！")
            
            # 保存预期结果
            expected_results = setup.get_expected_results()
            results_path = str(Path(__file__).parent.parent) + "/groundtruth_workspace/expected_results.json"
            with open(results_path, 'w', encoding='utf-8') as f:
                json.dump(expected_results, f, indent=2, ensure_ascii=False)
            print("📄 预期结果已保存到 expected_results.json")
            
            return True
        else:
            print("❌ 测试商品创建失败！")
            return False
            
    except Exception as e:
        print(f"❌ 设置过程中出错: {e}")
        return False


def clear_store_only():
    """仅清理商店"""
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 连接到商店: {site_url}")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    clear_result = setup.clear_all_products()
    
    return clear_result.get('success', False)


if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--clear-only":
        clear_store_only()
    else:
        main()