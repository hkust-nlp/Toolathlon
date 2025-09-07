import requests
from requests.auth import HTTPBasicAuth
import json
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import sys
import os
import imaplib
import email

# 动态添加当前目录到路径
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

from woocommerce_client import WooCommerceClient

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
                    
                    # 避免API限制
                    time.sleep(0.3)
            else:
                print("📦 商店中没有商品需要删除")
            
            # 3. 获取并删除自定义分类
            print("🏷️ 清理商品分类...")
            success, categories = self.wc_client.get_product_categories()
            
            deleted_categories = 0
            failed_categories = 0
            
            if success and categories:
                # 只删除可能是测试创建的分类
                test_category_names = [
                    "奥特莱斯", "清仓", "奥特莱斯/清仓", 
                    "Outlet", "Clearance", "测试分类"
                ]
                
                for category in categories:
                    category_name = category.get('name', '')
                    category_id = category.get('id')
                    
                    # 只删除测试相关的分类，避免删除系统默认分类
                    if (category_name in test_category_names or 
                        category.get('count', 0) == 0):  # 空分类也可以删除
                        
                        try:
                            # 使用DELETE请求删除分类
                            delete_url = f"{self.wc_client.api_base}/products/categories/{category_id}"
                            response = self.wc_client.session.delete(
                                delete_url, 
                                params={'force': True}
                            )
                            
                            if response.status_code in [200, 204]:
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
        
        category_data = {
            "name": "奥特莱斯",
            "description": "奥特莱斯商品分类"
        }
        success, result = self.wc_client.create_category(category_data)
        if success:
            print("✅ 创建分类: 奥特莱斯")
        else:
            print(f"❌ 创建分类失败: {result}")

        # 定义测试商品数据
        test_products = self._generate_test_product_data()
        
        created_count = 0
        failed_count = 0
        
        for product_data in test_products:
            success, result = self.wc_client.create_product(product_data)
            if success:
                product_id = result.get('id')
                product_name = result.get('name')
                # 提取产品类型
                product_type = 'unknown'
                meta_data = product_data.get('meta_data', [])
                for meta in meta_data:
                    if meta.get('key') == 'product_type':
                        product_type = meta.get('value', 'unknown')
                        break
                
                self.created_products.append({
                    'id': product_id,
                    'name': product_name,
                    'type': product_type
                })
                print(f"✅ 创建商品: {product_name} (ID: {product_id})")
                created_count += 1
            else:
                print(f"❌ 创建商品失败: {product_data.get('name')} - {result}")
                failed_count += 1
            
            # 避免API限制
            time.sleep(0.5)
        
        setup_result = {
            "success": failed_count == 0,
            "created_count": created_count,
            "failed_count": failed_count,
            "created_products": self.created_products,
            "low_selling_expected": len([p for p in test_products if self._is_low_selling_product(p)]),
            "normal_selling_expected": len([p for p in test_products if not self._is_low_selling_product(p)])
        }
        
        print(f"📊 商品创建完成:")
        print(f"   成功创建: {created_count} 个商品")
        print(f"   创建失败: {failed_count} 个商品")
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
                "name": "过时手机壳 iPhone X",
                "type": "simple",
                "regular_price": "29.99",
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
                "name": "老款蓝牙耳机",
                "type": "simple", 
                "regular_price": "89.99",
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
                "name": "过季运动鞋 2022款",
                "type": "simple",
                "regular_price": "159.99",
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
                "name": "旧版平板保护套",
                "type": "simple",
                "regular_price": "39.99",
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
                "name": "库存积压充电器",
                "type": "simple",
                "regular_price": "49.99",
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
                "name": "热销iPhone 15手机壳",
                "type": "simple",
                "regular_price": "39.99",
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
                "name": "新款无线充电器",
                "type": "simple",
                "regular_price": "79.99", 
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
                "name": "经典款运动鞋",
                "type": "simple",
                "regular_price": "199.99",
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
        
        products.extend(low_selling_products)
        products.extend(normal_selling_products)
        
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
        清空邮箱 - 删除 Sent 和 Inbox 文件夹中的所有邮件
        
        Returns:
            清理结果字典
        """
        print("📧 开始清空邮箱...")
        
        try:
            # 从token配置文件读取邮箱配置
            from token_key_session import all_token_key_session
            
            config_path = all_token_key_session.emails_config_file
            with open(config_path, 'r') as f:
                config = json.load(f)
            
            # 连接 IMAP 服务器
            if config.get('use_ssl', False):
                mail = imaplib.IMAP4_SSL(config['imap_server'], config['imap_port'])
            else:
                mail = imaplib.IMAP4(config['imap_server'], config['imap_port'])
                if config.get('use_starttls', False):
                    mail.starttls()
            
            # 登录
            mail.login(config['email'], config['password'])
            
            # 清空的文件夹列表
            folders_to_clear = ['INBOX', 'Sent']
            clear_results = {}
            
            for folder in folders_to_clear:
                print(f"🗂️ 清理文件夹: {folder}")
                
                try:
                    # 选择文件夹
                    status, _ = mail.select(folder)
                    if status != "OK":
                        print(f"   ⚠️ 无法选择文件夹 {folder}")
                        clear_results[folder] = {
                            "success": False,
                            "error": f"无法选择文件夹 {folder}",
                            "deleted_count": 0
                        }
                        continue
                    
                    # 搜索所有邮件
                    status, messages = mail.search(None, "ALL")
                    if status != "OK":
                        print(f"   ⚠️ 无法搜索文件夹 {folder} 中的邮件")
                        clear_results[folder] = {
                            "success": False,
                            "error": f"无法搜索文件夹 {folder}",
                            "deleted_count": 0
                        }
                        continue
                    
                    email_ids = messages[0].split()
                    total_emails = len(email_ids)
                    
                    if total_emails == 0:
                        print(f"   📭 文件夹 {folder} 已经为空")
                        clear_results[folder] = {
                            "success": True,
                            "deleted_count": 0,
                            "message": "文件夹已为空"
                        }
                        continue
                    
                    print(f"   📬 发现 {total_emails} 封邮件，开始删除...")
                    
                    # 标记所有邮件为删除
                    deleted_count = 0
                    failed_count = 0
                    
                    for email_id in email_ids:
                        try:
                            # 标记邮件为删除
                            mail.store(email_id, '+FLAGS', '\\Deleted')
                            deleted_count += 1
                        except Exception as e:
                            print(f"   ❌ 删除邮件 {email_id.decode()} 失败: {e}")
                            failed_count += 1
                    
                    # 执行删除
                    mail.expunge()
                    
                    print(f"   ✅ 文件夹 {folder}: 删除 {deleted_count} 封邮件，失败 {failed_count} 封")
                    
                    clear_results[folder] = {
                        "success": failed_count == 0,
                        "deleted_count": deleted_count,
                        "failed_count": failed_count,
                        "total_found": total_emails
                    }
                    
                except Exception as e:
                    print(f"   ❌ 清理文件夹 {folder} 时出错: {e}")
                    clear_results[folder] = {
                        "success": False,
                        "error": str(e),
                        "deleted_count": 0
                    }
            
            # 关闭连接
            mail.logout()
            
            # 计算总结果
            total_deleted = sum(result.get('deleted_count', 0) for result in clear_results.values())
            all_success = all(result.get('success', False) for result in clear_results.values())
            
            final_result = {
                "success": all_success,
                "total_deleted": total_deleted,
                "folders": clear_results,
                "timestamp": datetime.now().isoformat()
            }
            
            print(f"📊 邮箱清理完成:")
            print(f"   总共删除: {total_deleted} 封邮件")
            
            if all_success:
                print("✅ 邮箱清理成功！")
            else:
                print("⚠️ 邮箱清理部分完成，有部分文件夹清理失败")
            
            return final_result
            
        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
            print(f"❌ 邮箱清理过程中出错: {e}")
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
        print("⚠️ 邮箱清理未完全成功，但继续后续操作...")
        print(f"邮箱清理详情: {mailbox_result}")
    
    # 等待一下，确保邮箱操作完成
    print("⏳ 等待2秒，确保邮箱清理操作完成...")
    time.sleep(2)
    
    # 2. 清理商店中的所有商品
    print("\n" + "="*60)
    print("第二步：清理商店中的所有现有商品")
    print("="*60)
    
    clear_result = setup.clear_all_products()
    
    if not clear_result.get('success'):
        print("⚠️ 商品清理未完全成功，但继续创建测试商品...")
        print(f"清理详情: {clear_result}")
    
    # 等待一下，确保删除操作完成
    print("⏳ 等待3秒，确保清理操作完成...")
    time.sleep(3)
    
    # 3. 然后创建测试商品
    print("\n" + "="*60)
    print("第三步：创建测试商品")
    print("="*60)
    
    result = setup.create_test_products()
    
    if result.get('success'):
        print("✅ 测试商品设置完成！")
        
        # 保存预期结果
        expected_results = setup.get_expected_results()
        with open('expected_results.json', 'w', encoding='utf-8') as f:
            json.dump(expected_results, f, indent=2, ensure_ascii=False)
        print("📄 预期结果已保存到 expected_results.json")
        
        # 保存清理结果（包括邮箱清理结果）
        all_clear_results = {
            "mailbox_clear": mailbox_result,
            "store_clear": clear_result
        }
        with open('clear_results.json', 'w', encoding='utf-8') as f:
            json.dump(all_clear_results, f, indent=2, ensure_ascii=False)
        print("📄 清理结果（邮箱+商店）已保存到 clear_results.json")
        
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
    with open('clear_results.json', 'w', encoding='utf-8') as f:
        json.dump(clear_result, f, indent=2, ensure_ascii=False)
    print("📄 清理结果已保存到 clear_results.json")
    
    if clear_result.get('success'):
        print("🎉 商店清理完成！")
        return True
    else:
        print("⚠️ 商店清理部分完成")
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
    with open('mailbox_clear_results.json', 'w', encoding='utf-8') as f:
        json.dump(mailbox_result, f, indent=2, ensure_ascii=False)
    print("📄 邮箱清理结果已保存到 mailbox_clear_results.json")
    
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
        else:
            print("使用方法:")
            print("  python setup_test_products.py                 # 完整流程（清理邮箱+商店+创建测试商品）")
            print("  python setup_test_products.py --clear-only    # 仅清理商店")
            print("  python setup_test_products.py --clear-mailbox-only  # 仅清理邮箱")
    else:
        # 完整流程：清理邮箱 + 清理商店 + 创建测试商品
        main()
