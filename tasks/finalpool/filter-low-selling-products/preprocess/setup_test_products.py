import requests
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List
import sys
import os
import random

# 动态添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(os.path.dirname(os.path.dirname(task_dir)))
sys.path.insert(0, project_root)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from utils.app_specific.woocommerce.client import WooCommerceClient
from utils.app_specific.poste.local_email_manager import LocalEmailManager

class TestProductSetup:
    """测试产品设置器 - 为评估创建测试数据"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化测试产品设置器
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.created_products = []
    
    def clear_all_products(self) -> Dict:
        """
        清理商店中的所有商品和分类
        
        Returns:
            清理结果字典
        """
        print("🧹 开始清理商店中的所有商品...")
        
        try:
            # 1. 获取所有商品
            print("📦 获取所有商品...")
            all_products = self.wc_client.get_all_products()
            
            deleted_products = 0
            failed_products = 0
            
            # 2. 删除所有商品
            if all_products:
                print(f"🗑️ 准备删除 {len(all_products)} 个商品...")
                
                success, result = self.wc_client.batch_delete_products(all_products)
                if success:
                    print(f"✅ 删除商品: {len(all_products)} 个商品")
                else:
                    print(f"❌ 删除商品失败: {result}")
                    return {"success": False, "deleted_count": 0, "failed_count": len(all_products)}
            else:
                print("📦 商店中没有商品需要删除")
            
            # 3. 获取并删除自定义分类
            print("🏷️ 清理 Product Categories...")
            success, categories = self.wc_client.get_product_categories()
            
            deleted_categories = 0
            failed_categories = 0
            
            if success and categories:                
                for category in categories:
                    category_name = category.get('name', '')
                    category_id = category.get('id')
                    
                    # 只删除测试相关的分类，避免删除系统默认分类
                    if category_name != "Uncategorized":  # 空分类也可以删除
                        try:
                            success, result  = self.wc_client.delete_category(category_id, force=True)
                            
                            if success:
                                print(f"   ✅ 删除分类: {category_name} (ID: {category_id})")
                                deleted_categories += 1
                            else:
                                print(f"   ⚠️ 跳过分类: {category_name} (可能是系统默认分类)")
                                
                        except Exception as e:
                            print(f"   ❌ 删除分类 {category_name} 时出错: {e}")
                            failed_categories += 1
                        
                        time.sleep(0.3)
            
            # 4. 生成清理报告
            clear_result = {
                "success": failed_products == 0 and failed_categories == 0,
                "products": {
                    "total_found": len(all_products) if all_products else 0,
                    "deleted": deleted_products,
                    "failed": failed_products
                },
                "categories": {
                    "deleted": deleted_categories,
                    "failed": failed_categories
                },
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"\n📊 清理完成:")
            print(f"   商品: 删除 {deleted_products} 个，失败 {failed_products} 个")
            print(f"   分类: 删除 {deleted_categories} 个，失败 {failed_categories} 个")
            
            if clear_result["success"]:
                print("✅ 商店清理成功！")
            else:
                print("⚠️ 商店清理部分完成，有部分项目清理失败")
            
            return clear_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 清理过程中出错: {e}")
            return error_result
    
    def create_test_products(self) -> Dict:
        """
        创建测试商品
        包括：
        1. 低销量商品（在库>90天，30天销量<10）
        2. 正常销量商品（对照组）
        
        Returns:
            创建结果字典
        """
        print("🛒 开始创建测试分类和商品...")

        # 定义测试商品数据
        test_products = self._generate_test_product_data()
        
        created_count = 0
        failed_count = 0
        success, result = self.wc_client.batch_create_products(test_products)
        if success:
            print(f"✅ 创建商品: {len(test_products)} 个商品")
        else:
            print(f"❌ 创建商品失败: {result}")
            return {"success": False, "created_count": 0, "failed_count": len(test_products)}
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "low_selling_expected": len([p for p in test_products if self._is_low_selling_product(p)]),
            "normal_selling_expected": len([p for p in test_products if not self._is_low_selling_product(p)])
        }
        
        print(f"📊 商品创建完成:")
        print(f"   预期低销量商品: {setup_result['low_selling_expected']} 个")
        print(f"   预期正常商品: {setup_result['normal_selling_expected']} 个")
        
        return setup_result
    
    def _generate_test_product_data(self) -> List[Dict]:
        """生成测试商品数据"""
        current_date = datetime.now()
        products = []
        
        # 低销量商品（应该被筛选出来）
        low_selling_products = [
            {
                "name": "Phone case iPhone X",
                "type": "simple",
                "regular_price": "29.99",
                "sale_price": "19.99",
                "stock_quantity": 50,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=120)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": "3"},
                    {"key": "_sales_last_30_days", "value": "3"},
                    {"key": "total_sales", "value": "15"},
                    {"key": "_total_sales", "value": "15"}
                ]
            },
            {
                "name": "Bluetooth Headphone",
                "type": "simple",
                "regular_price": "89.99",
                "sale_price": "59.99",
                "stock_quantity": 25,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=150)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": "2"},
                    {"key": "_sales_last_30_days", "value": "2"},
                    {"key": "total_sales", "value": "8"},
                    {"key": "_total_sales", "value": "8"}
                ]
            },
            {
                "name": "Old Sneakers 2022",
                "type": "simple",
                "regular_price": "159.99",
                "sale_price": "72.99",
                "stock_quantity": 30,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=200)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": "5"},
                    {"key": "_sales_last_30_days", "value": "5"},
                    {"key": "total_sales", "value": "22"},
                    {"key": "_total_sales", "value": "22"}
                ]
            },
            {
                "name": "Tablet Case",
                "type": "simple",
                "regular_price": "38.99",
                "sale_price": "24.99",
                "stock_quantity": 40,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=180)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": "1"},
                    {"key": "_sales_last_30_days", "value": "1"},
                    {"key": "total_sales", "value": "6"},
                    {"key": "_total_sales", "value": "6"}
                ]
            },
            {
                "name": "Charger v11",
                "type": "simple",
                "regular_price": "49.99",
                "sale_price": "34.99",
                "stock_quantity": 60,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=250)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": "4"},
                    {"key": "_sales_last_30_days", "value": "4"},
                    {"key": "total_sales", "value": "18"},
                    {"key": "_total_sales", "value": "18"}
                ]
            }
        ]
        
        # 正常销量商品（不应该被筛选）
        normal_selling_products = [
            {
                "name": "iPhone 15 Phone Case",
                "type": "simple",
                "regular_price": "39.99",
                "sale_price": "36.99",  # 小折扣: 约7.5%折扣
                "stock_quantity": 100,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=60)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "normal_selling"},
                    {"key": "sales_last_30_days", "value": "45"},
                    {"key": "_sales_last_30_days", "value": "45"},
                    {"key": "total_sales", "value": "120"},
                    {"key": "_total_sales", "value": "120"}
                ]
            },
            {
                "name": "Wireless Charger",
                "type": "simple",
                "regular_price": "79.99",
                # 无折扣，保持原价
                "stock_quantity": 80,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=30)).isoformat(),
                "meta_data": [
                    {"key": "product_type", "value": "normal_selling"},
                    {"key": "sales_last_30_days", "value": "25"},
                    {"key": "_sales_last_30_days", "value": "25"},
                    {"key": "total_sales", "value": "35"},
                    {"key": "_total_sales", "value": "35"}
                ]
            },
            {
                "name": "Nike Sneakers",
                "type": "simple",
                "regular_price": "199.99",
                "sale_price": "189.99",  # 小折扣: 约5%折扣
                "stock_quantity": 50,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": (current_date - timedelta(days=200)).isoformat(),  # 虽然在库久，但销量好
                "meta_data": [
                    {"key": "product_type", "value": "normal_selling"},
                    {"key": "sales_last_30_days", "value": "15"},  # 30天销量>=10，不符合筛选条件
                    {"key": "_sales_last_30_days", "value": "15"},
                    {"key": "total_sales", "value": "180"},
                    {"key": "_total_sales", "value": "180"}
                ]
            }
        ]
        
        # 干扰项
        extra_normal_selling_products = []
        for id in range(10,400): # 创建~400个新商品
            regprice = 599.99+2*id # 保证价格和上面的不冲突
            stock_quantity = random.randint(10, 200)
            date_created = (current_date - timedelta(days=random.randint(10, 200))).isoformat()
            sales_30_days = random.randint(11, 200) # 肯定不促销
            total_sales = sales_30_days + random.randint(11, 200)
            name = random.choice(["AOC", "Samsung", "LG", "Xiaomi", "Sony"]) + " " + random.choice(["Monitor", "Phone", "TV", "Laptop", "Tablet"]) + " v" + str(id)
            extra_normal_selling_products.append({
                "name": name,
                "type": "simple",
                "regular_price": str(regprice),
                "stock_quantity": stock_quantity,
                "manage_stock": True,
                "stock_status": "instock",
                "date_created": date_created,
                "meta_data": [
                    {"key": "product_type", "value": "low_selling"},
                    {"key": "sales_last_30_days", "value": str(sales_30_days)},
                    {"key": "_sales_last_30_days", "value": str(sales_30_days)},
                    {"key": "total_sales", "value": str(total_sales)},
                    {"key": "_total_sales", "value": str(total_sales)}
                ]
            })

        products.extend(low_selling_products)
        products.extend(normal_selling_products)
        # products.extend(extra_normal_selling_products)

        random.shuffle(products)
        
        return products
    
    def _is_low_selling_product(self, product_data: Dict) -> bool:
        """判断是否为低销量商品"""
        # 检查发布日期
        date_created_str = product_data.get('date_created', '')
        if date_created_str:
            date_created = datetime.fromisoformat(date_created_str.replace('Z', ''))
            days_in_stock = (datetime.now() - date_created).days
        else:
            days_in_stock = 0
        
        # 检查30天销量
        sales_30_days = 0
        meta_data = product_data.get('meta_data', [])
        for meta in meta_data:
            if meta.get('key') == 'sales_last_30_days':
                try:
                    sales_30_days = int(meta.get('value', 0))
                    break
                except (ValueError, TypeError):
                    continue
        
        return days_in_stock > 90 and sales_30_days < 10
    
    def cleanup_test_products(self) -> Dict:
        """清理测试商品"""
        print("🧹 开始清理测试商品...")
        
        deleted_count = 0
        failed_count = 0
        
        for product in self.created_products:
            product_id = product.get('id')
            product_name = product.get('name')
            
            success, result = self.wc_client.delete_product(str(product_id), force=True)
            if success:
                print(f"✅ 删除商品: {product_name} (ID: {product_id})")
                deleted_count += 1
            else:
                print(f"❌ 删除商品失败: {product_name} - {result}")
                failed_count += 1
            
            time.sleep(0.3)
        
        cleanup_result = {
            "success": failed_count == 0,
            "deleted_count": deleted_count,
            "failed_count": failed_count
        }
        
        print(f"📊 清理完成:")
        print(f"   成功删除: {deleted_count} 个商品")
        print(f"   删除失败: {failed_count} 个商品")
        
        return cleanup_result
    
    def get_expected_results(self) -> Dict:
        """获取预期结果，用于评估"""
        # 正确提取产品类型
        low_selling_products = []
        normal_selling_products = []
        
        for product in self.created_products:
            product_type = product.get('type', 'unknown')
            if product_type == 'low_selling':
                low_selling_products.append(product)
            elif product_type == 'normal_selling':
                normal_selling_products.append(product)
        
        return {
            "expected_low_selling_count": len(low_selling_products),
            "expected_normal_count": len(normal_selling_products),
            "expected_low_selling_ids": [p.get('id') for p in low_selling_products],
            "expected_normal_ids": [p.get('id') for p in normal_selling_products],
            "total_test_products": len(self.created_products),
            "all_created_products": self.created_products
        }
    
    def clear_mailbox(self) -> Dict:
        """
        Clear mailbox using general email manager

        Returns:
            Dictionary with clearing results
        """
        print("📧 Starting mailbox clearing...")

        try:
            # Get email configuration from token session
            from token_key_session import all_token_key_session

            config_path = all_token_key_session.emails_config_file

            # Initialize email manager
            email_manager = LocalEmailManager(config_path, verbose=True)

            # Clear both INBOX and Sent folders
            folders_to_clear = ['INBOX', 'Sent']
            clear_results = {}

            for folder in folders_to_clear:
                print(f"🗂️ Clearing folder: {folder}")

                try:
                    if folder == 'INBOX':
                        email_manager.clear_all_emails('INBOX')
                        # Count remaining emails to verify
                        remaining_emails = email_manager.get_all_emails('INBOX')
                        clear_results[folder] = {
                            "success": len(remaining_emails) == 0,
                            "deleted_count": "cleared" if len(remaining_emails) == 0 else 0,
                            "message": f"Folder cleared, {len(remaining_emails)} emails remaining"
                        }
                    else:  # Sent folder
                        email_manager.clear_all_emails('Sent')
                        remaining_emails = email_manager.get_all_emails('Sent')
                        clear_results[folder] = {
                            "success": len(remaining_emails) == 0,
                            "deleted_count": "cleared" if len(remaining_emails) == 0 else 0,
                            "message": f"Folder cleared, {len(remaining_emails)} emails remaining"
                        }

                    print(f"   ✅ Folder {folder}: {clear_results[folder]['message']}")

                except Exception as e:
                    print(f"   ❌ Error clearing folder {folder}: {e}")
                    clear_results[folder] = {
                        "success": False,
                        "error": str(e),
                        "deleted_count": 0
                    }

            # Calculate total results
            all_success = all(result.get('success', False) for result in clear_results.values())

            final_result = {
                "success": all_success,
                "folders": clear_results,
                "timestamp": datetime.now().isoformat()
            }

            print(f"📊 Mailbox clearing complete")

            if all_success:
                print("✅ Mailbox clearing successful!")
            else:
                print("⚠️ Mailbox clearing partially completed")

            return final_result

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ Error during mailbox clearing: {e}")
            return error_result

    def clear_blog_posts(self) -> Dict:
        """
        清理博客文章

        Returns:
            清理结果字典
        """
        print("📝 开始清理博客文章...")

        try:
            # 从token配置文件读取配置
            from token_key_session import all_token_key_session

            site_url = all_token_key_session.woocommerce_site_url
            consumer_key = all_token_key_session.woocommerce_api_key
            consumer_secret = all_token_key_session.woocommerce_api_secret

            wp_api_base = f"{site_url}/wp-json/wp/v2"
            wp_auth = requests.auth.HTTPBasicAuth(consumer_key, consumer_secret)

            # 获取所有文章
            print("📄 获取所有博客文章...")
            response = requests.get(
                f"{wp_api_base}/posts",
                auth=wp_auth,
                params={'per_page': 100, 'status': 'any'}
            )

            if response.status_code != 200:
                return {
                    "success": False,
                    "error": f"无法获取博客文章: HTTP {response.status_code}",
                    "deleted_count": 0,
                    "timestamp": datetime.now().isoformat()
                }

            posts = response.json()
            deleted_count = 0
            failed_count = 0

            # if not posts:
            #     print("📭 没有找到博客文章需要删除")
            #     return {
            #         "success": True,
            #         "deleted_count": 0,
            #         "timestamp": datetime.now().isoformat()
            #     }

            print(f"🗑️ 准备删除 {len(posts)} 篇博客文章...")

            for post in posts:
                post_id = post.get('id')
                post_title = post.get('title', {}).get('rendered', 'Unknown')

                try:
                    # 强制删除文章
                    delete_response = requests.delete(
                        f"{wp_api_base}/posts/{post_id}",
                        auth=wp_auth,
                        params={'force': True}
                    )

                    if delete_response.status_code in [200, 204]:
                        print(f"   ✅ 删除文章: {post_title} (ID: {post_id})")
                        deleted_count += 1
                    else:
                        print(f"   ❌ 删除失败: {post_title} - HTTP {delete_response.status_code}")
                        failed_count += 1

                except Exception as e:
                    print(f"   ❌ 删除文章 {post_title} 时出错: {e}")
                    failed_count += 1

                time.sleep(0.3)  # 避免API限制

            blog_result = {
                "success": failed_count == 0,
                "deleted_count": deleted_count,
                "failed_count": failed_count,
                "total_found": len(posts),
                "timestamp": datetime.now().isoformat()
            }

            print(f"📊 博客清理完成:")
            print(f"   成功删除: {deleted_count} 篇文章")
            print(f"   删除失败: {failed_count} 篇文章")

            if blog_result["success"]:
                print("✅ 博客清理成功！")
            else:
                print("⚠️ 博客清理部分完成，有部分文章清理失败")

            return blog_result

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 博客清理过程中出错: {e}")
            return error_result


def main():
    """主函数 - 用于独立运行测试数据设置"""
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 初始化测试产品设置器: {site_url}")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    
    # 1. 首先清空邮箱
    print("\n" + "="*60)
    print("第一步：清空邮箱")
    print("="*60)
    
    mailbox_result = setup.clear_mailbox()
    
    if not mailbox_result.get('success'):
        print("⚠️ 邮箱清理未完全成功，后续操作失败...")
        print(f"邮箱清理详情: {mailbox_result}")
        return False
    
    # NOTE:  之前我不知道为啥清理不到...现在我知道了，woocommerce并不管理wordpress，博客是附属在wordpress上的...
    # # 2. 清理博客文章
    print("\n" + "="*60)
    print("第二步：清理博客文章 - 清理不了，跳过！")
    print("="*60)

    # blog_result = setup.clear_blog_posts()
    blog_result = {"status":"SKIPPED!"}

    # if not blog_result.get('success'):
    #     print("⚠️ 博客清理未完全成功，但继续执行后续操作...")
    #     print(f"博客清理详情: {blog_result}")

    # 3. 清理商店中的所有商品
    print("\n" + "="*60)
    print("第三步：清理商店中的所有现有商品")
    print("="*60)
    
    clear_result = setup.clear_all_products()
    
    if not clear_result.get('success'):
        print("⚠️ 商品清理未完全成功，不创建测试商品...")
        print(f"清理详情: {clear_result}")
        return False
    
    # 3. 然后创建测试商品
    print("\n" + "="*60)
    print("第四步：创建测试商品")
    print("="*60)
    
    result = setup.create_test_products()
    
    if result.get('success'):
        print("✅ 测试商品设置完成！")
        
        # 保存预期结果
        expected_results = setup.get_expected_results()
        with open(os.path.join(task_dir, 'groundtruth_workspace', 'expected_results.json'), 'w', encoding='utf-8') as f:
            json.dump(expected_results, f, indent=2, ensure_ascii=False)
        print("📄 预期结果已保存到 groundtruth_workspace/expected_results.json")
        
        # 保存清理结果（包括邮箱、博客、商店清理结果）
        all_clear_results = {
            "mailbox_clear": mailbox_result,
            "blog_clear": blog_result,
            "store_clear": clear_result
        }
        with open(os.path.join(task_dir, 'groundtruth_workspace', 'clear_results.json'), 'w', encoding='utf-8') as f:
            json.dump(all_clear_results, f, indent=2, ensure_ascii=False)
        print("📄 清理结果（邮箱+博客+商店）已保存到 groundtruth_workspace/clear_results.json")
        
    else:
        print("❌ 测试商品设置失败！")
        return False
    
    return True


def clear_store_only():
    """仅清理商店 - 独立运行清理功能"""
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 连接到商店: {site_url}")
    print("🧹 开始清理商店...")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    clear_result = setup.clear_all_products()
    
    # 保存清理结果
    with open(os.path.join(task_dir, 'groundtruth_workspace', 'clear_results.json'), 'w', encoding='utf-8') as f:
        json.dump(clear_result, f, indent=2, ensure_ascii=False)
    print("📄 清理结果已保存到 groundtruth_workspace/clear_results.json")
    
    if clear_result.get('success'):
        print("🎉 商店清理完成！")
        return True
    else:
        print("⚠️ 商店清理部分完成")
        return False


def clear_blog_only():
    """仅清理博客 - 独立运行博客清理功能"""
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session

    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret

    print(f"🚀 连接到网站: {site_url}")
    print("📝 开始清理博客文章...")

    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    blog_result = setup.clear_blog_posts()

    # 保存博客清理结果
    with open(os.path.join(task_dir, 'groundtruth_workspace', 'blog_clear_results.json'), 'w', encoding='utf-8') as f:
        json.dump(blog_result, f, indent=2, ensure_ascii=False)
    print("📄 博客清理结果已保存到 groundtruth_workspace/blog_clear_results.json")

    if blog_result.get('success'):
        print("🎉 博客清理完成！")
        return True
    else:
        print("⚠️ 博客清理部分完成")
        return False


def clear_mailbox_only():
    """仅清理邮箱 - 独立运行邮箱清理功能"""
    # 从token配置文件读取配置
    from token_key_session import all_token_key_session
    
    site_url = all_token_key_session.woocommerce_site_url
    consumer_key = all_token_key_session.woocommerce_api_key
    consumer_secret = all_token_key_session.woocommerce_api_secret
    
    print(f"🚀 连接到邮箱服务器...")
    print("📧 开始清理邮箱...")
    
    setup = TestProductSetup(site_url, consumer_key, consumer_secret)
    mailbox_result = setup.clear_mailbox()
    
    # 保存邮箱清理结果
    with open(os.path.join(task_dir, 'groundtruth_workspace', 'mailbox_clear_results.json'), 'w', encoding='utf-8') as f:
        json.dump(mailbox_result, f, indent=2, ensure_ascii=False)
    print("📄 邮箱清理结果已保存到 groundtruth_workspace/mailbox_clear_results.json")
    
    if mailbox_result.get('success'):
        print("🎉 邮箱清理完成！")
        return True
    else:
        print("⚠️ 邮箱清理部分完成")
        return False


if __name__ == "__main__":
    import sys
    
    # 检查命令行参数
    if len(sys.argv) > 1:
        if sys.argv[1] == "--clear-only":
            # 仅清理商店
            clear_store_only()
        elif sys.argv[1] == "--clear-mailbox-only":
            # 仅清理邮箱
            clear_mailbox_only()
        elif sys.argv[1] == "--clear-blog-only":
            # 仅清理博客
            clear_blog_only()
        else:
            print("使用方法:")
            print("  python setup_test_products.py                     # 完整流程（清理邮箱+博客+商店+创建测试商品）")
            print("  python setup_test_products.py --clear-only        # 仅清理商店")
            print("  python setup_test_products.py --clear-mailbox-only # 仅清理邮箱")
            print("  python setup_test_products.py --clear-blog-only   # 仅清理博客")
    else:
        # 完整流程：清理邮箱 + 清理商店 + 创建测试商品
        main()
