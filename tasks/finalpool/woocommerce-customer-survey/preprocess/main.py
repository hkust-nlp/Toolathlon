#!/usr/bin/env python3
"""
WooCommerce Customer Survey Task - Preprocess Setup
设置初始工作环境：创建七天内和七天前的订单数据，以及邮件模板
"""
import os
import sys
import json
import shutil
import time
import imaplib
import email
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
import random
from typing import Dict

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# 导入 WooCommerce 通用模块
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
from utils.app_specific.woocommerce import (
    setup_customer_survey_environment,
    OrderManager,
    create_customer_survey_orders
)

# 导入 Google Drive helper
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.app_specific.google_form.ops import clear_google_forms

def clear_mailbox() -> Dict:
    """
    清空邮箱 - 删除 Sent 和 Inbox 文件夹中的所有邮件
    
    Returns:
        清理结果字典
    """
    print("📧 开始清空邮箱...")
    
    try:
        # 导入配置
        from token_key_session import all_token_key_session
        
        # 读取邮件配置文件
        try:
            with open(all_token_key_session.emails_config_file, 'r', encoding='utf-8') as f:
                email_config = json.load(f)
            email_address = email_config.get('email', 'admin@mcp.com')
            email_password = email_config.get('password', 'admin_password')
            imap_server = email_config.get('imap_server', 'localhost')
            imap_port = email_config.get('imap_port', 1143)
        except Exception as e:
            print(f"⚠️ 无法读取邮件配置文件，使用默认配置: {e}")
            email_address = 'admin@mcp.com'
            email_password = 'admin_password'
            imap_server = 'localhost'
            imap_port = 1143
        
        # 连接 IMAP 服务器
        mail = imaplib.IMAP4(imap_server, imap_port)
        
        # 登录
        mail.login(email_address, email_password)
        
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



class WooCommerceOrderManager:
    """WooCommerce 订单管理器 - 使用通用客户端和工具"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化 WooCommerce 订单管理器

        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.order_manager = OrderManager(site_url, consumer_key, consumer_secret)
        self.created_orders = []
    
    def delete_existing_orders(self):
        """删除现有的所有订单，确保创建订单前有干净的环境"""
        print("🗑️ 删除现有订单...")

        try:
            # 使用通用订单管理器的批量删除功能
            result = self.order_manager.clear_all_orders(confirm=True)

            if result['success']:
                deleted_count = result.get('deleted_count', 0)
                print(f"✅ 成功删除 {deleted_count} 个现有订单")
            else:
                error_msg = result.get('error', '未知错误')
                print(f"❌ 删除订单失败: {error_msg}")

        except Exception as e:
            print(f"❌ 删除订单过程中出错: {e}")
    
    def upload_orders_to_woocommerce(self, orders_data):
        """将订单数据上传到 WooCommerce"""
        print("📤 开始上传订单到 WooCommerce...")

        # 使用通用订单管理器的上传功能
        upload_result = self.order_manager.upload_orders(
            orders_data,
            virtual_product_id=1,
            batch_delay=0.8
        )

        # 保持与原接口的兼容性
        self.created_orders = upload_result.get('created_orders', [])

        successful_orders = upload_result.get('successful_orders', 0)
        failed_orders = upload_result.get('failed_orders', 0)

        return successful_orders, failed_orders


def create_order_data():
    """
    创建20个最近的订单（混合送达状态）：70%已完成，30%处理中
    使用通用订单生成器
    """
    print("📦 生成订单数据...")

    # 使用通用订单生成器
    all_orders, completed_orders = create_customer_survey_orders()

    print(f"Created {len(all_orders)} orders")
    print(f"   - Completed orders: {len(completed_orders)}")
    print(f"   - Other status orders: {len(all_orders) - len(completed_orders)}")

    return all_orders

def setup_task_data():
    """
    设置任务数据文件
    
    Args:
        upload_to_woocommerce: 是否上传订单到 WooCommerce (默认True)
    """
    print("📝 设置任务数据文件...")
    
    # 生成订单数据
    orders = create_order_data()
    
    # 保存完整订单数据到本地 JSON 文件
    with open(current_dir / "completed_orders.json", 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    print(f"✅ Created complete order data: {len(orders)} orders")
    
    # 过滤出已完成的订单并保存到 groundtruth_workspace
    completed_orders = [order for order in orders if order["status"] == "completed"]
    groundtruth_dir = current_dir.parent / "groundtruth_workspace"
    groundtruth_dir.mkdir(exist_ok=True)
    
    expected_orders_file = groundtruth_dir / "expected_orders.json"
    with open(expected_orders_file, 'w', encoding='utf-8') as f:
        json.dump(completed_orders, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved completed orders to groundtruth: {len(completed_orders)} orders")
    
    # 统计
    all_orders = orders
    completed_orders = [o for o in orders if o["status"] == "completed"]
    processing_orders = [o for o in orders if o["status"] == "processing"]
    onhold_orders = [o for o in orders if o["status"] == "on-hold"]
    
    # 详细统计各状态订单数
    status_summary = {}
    for order in orders:
        status = order["status"]
        status_summary[status] = status_summary.get(status, 0) + 1
    
    print(f"   - Total orders: {len(all_orders)}")
    print(f"   - Completed orders: {len(completed_orders)} ({len(completed_orders)/len(all_orders)*100:.0f}%)")
    print(f"   - Processing orders: {len(processing_orders)}")
    print(f"   - Onhold orders: {len(onhold_orders)}")
    
    print(f"\n📈 订单状态详情:")
    for status, count in sorted(status_summary.items()):
        print(f"   {status}: {count}")
    
    # 上传订单到 WooCommerce
    upload_success = False

    try:
        # 导入配置
        from token_key_session import all_token_key_session
        
        # 初始化 WooCommerce 订单管理器
        order_manager = WooCommerceOrderManager(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )
        
        # 删除现有订单
        order_manager.delete_existing_orders()
        
        # 上传新订单
        successful_count, failed_count = order_manager.upload_orders_to_woocommerce(orders)
        
        if failed_count == 0:
            upload_success = True
            print("✅ All orders successfully uploaded to WooCommerce")
        else:
            print(f"⚠️ Some orders failed to upload (success: {successful_count}, failed: {failed_count})")
            
    except Exception as e:
        print(f"❌ Error uploading orders to WooCommerce: {e}")
        print("💡 Will continue using local JSON file as data source")
        return False
    
    return True


def main():
    """主预处理函数"""
    
    parser = ArgumentParser(description="Preprocess script - Set up the initial environment for the WooCommerce customer survey task")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()
    
    print("=" * 60)
    print("WooCommerce customer survey task - Preprocess")
    print("=" * 60)
    
    try:
        # 第一步：清空邮箱（如果启用）
        
        print("\n" + "="*60)
        print("First Step: Clear mailbox")
        print("="*60)
        
        mailbox_result = clear_mailbox()
        
        if not mailbox_result.get('success'):
            print("Mailbox cleanup not fully successful, but continue with subsequent operations...")
            print(f"Mailbox cleanup details: {mailbox_result}")
        
        # 等待一下，确保邮箱操作完成
        print("Wait 2 seconds to ensure mailbox cleanup operation is complete...")
        time.sleep(2)
        
        # 第二步：清空Google Forms（如果启用）
        forms_result = None

        print("\n" + "="*60)
        print("Second Step: Clear Google Forms")
        print("="*60)
        form_name_pattern = "Customer Shopping Experience Feedback Survey"
        forms_result = clear_google_forms(form_name_pattern)
        
        if not forms_result.get('success'):
            print("Google Forms cleanup not fully successful, but continue with subsequent operations...")
            print(f"Google Forms cleanup details: {forms_result}")
        
        # 等待一下，确保Google Forms操作完成
        print("Wait 2 seconds to ensure Google Forms cleanup operation is complete...")
        time.sleep(2)
        
        
        # 第三步：设置任务数据文件
        print("\n" + "="*60)
        print("Third Step: Set task data")
        print("="*60)
        
        success1 = setup_task_data()
        
   
        
        
        if success1:
            print("\n🎉 Preprocessing completed! Task environment is ready")
            if forms_result and forms_result.get('success'):
                deleted_count = forms_result.get('deleted_count', 0)
                found_count = forms_result.get('found_count', 0)
                if form_name_pattern:
                    print(f"Cleared Google Forms matching '{form_name_pattern}' (found {found_count} deleted {deleted_count} )")
                else:
                    print(f"Cleared all Google Forms (found {found_count} deleted {deleted_count} )")
            return True
        else:
            print("\n Preprocessing partially completed, please check the error information")
            return False
        
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        return False


if __name__ == "__main__":
    main()