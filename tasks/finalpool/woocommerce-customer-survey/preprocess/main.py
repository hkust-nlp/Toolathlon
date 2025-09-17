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

# 导入 WooCommerce 客户端
from preprocess.woocommerce_client import WooCommerceClient

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
    """WooCommerce 订单管理器"""
    
    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        初始化 WooCommerce 订单管理器
        
        Args:
            site_url: WooCommerce网站URL
            consumer_key: WooCommerce API消费者密钥
            consumer_secret: WooCommerce API消费者密钥
        """
        self.wc_client = WooCommerceClient(site_url, consumer_key, consumer_secret)
        self.created_orders = []
    
    def delete_existing_orders(self):
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
    
    def upload_orders_to_woocommerce(self, orders_data):
        """将订单数据上传到 WooCommerce"""
        print("📤 开始上传订单到 WooCommerce...")
        
        successful_orders = 0
        failed_orders = 0
        
        for order in orders_data:
            # 计算订单总价
            item_total = float(order["product_price"]) * order["quantity"]
            
            # 构造 WooCommerce 订单数据格式
            order_data = {
                "status": order["status"],  # 使用原始订单的状态（completed/processing/shipped）
                "customer_id": 1,  # 默认客户ID
                "payment_method": "bacs",
                "payment_method_title": "Direct Bank Transfer",
                "total": str(item_total),
                "billing": {
                    "first_name": order["customer_name"].split()[0] if " " in order["customer_name"] else order["customer_name"],
                    "last_name": order["customer_name"].split()[-1] if " " in order["customer_name"] else "",
                    "email": order["customer_email"]
                },
                "line_items": [
                    {
                        "product_id": 1,  # 虚拟产品ID
                        "name": order["product_name"],
                        "quantity": order["quantity"],
                        "price": str(order["product_price"]),
                        "total": str(float(order["product_price"]) * order["quantity"]),
                        "subtotal": str(float(order["product_price"]) * order["quantity"])
                    }
                ],
                "meta_data": [
                    {"key": "test_order", "value": "true"},
                    {"key": "original_order_id", "value": str(order["order_id"])},
                    {"key": "original_date_created", "value": order["date_created"]},
                    {"key": "original_date_completed", "value": order["date_completed"] or ""},
                    {"key": "period", "value": order["period"]},
                    {"key": "customer_survey_target", "value": "true"}
                ]
            }

            # 调用 create_order 上传订单
            success, response = self.wc_client.create_order(order_data)

            if success:
                wc_order_id = response.get('id')
                successful_orders += 1
                print(f"✅ 订单 #{wc_order_id} 创建成功 - {order['customer_name']} ({order['status']}) - ${item_total:.2f}")
                
                self.created_orders.append({
                    'original_order_id': order['order_id'],
                    'wc_order_id': wc_order_id,
                    'customer_email': order['customer_email'],
                    'status': order['status'],
                    'period': order['period']
                })
            else:
                failed_orders += 1
                print(f"❌ 创建订单失败: {order['customer_name']} - {response}")
            
            # 添加延迟避免API限制
            time.sleep(0.8)
        
        # 统计订单状态分布
        status_counts = {}
        for order in self.created_orders:
            status = order['status']
            status_counts[status] = status_counts.get(status, 0) + 1
        
        print(f"\n📊 订单上传完成:")
        print(f"   ✅ 成功创建: {successful_orders} 个订单")
        print(f"   ❌ 创建失败: {failed_orders} 个订单")
        
        if status_counts:
            print(f"\n📈 WooCommerce 订单状态分布:")
            for status, count in sorted(status_counts.items()):
                print(f"   {status}: {count} 个")
        
        return successful_orders, failed_orders


def create_order_data():
    """
    创建20个最近的订单（混合送达状态）：70%已完成，30%处理中
    """
    print("📦 生成订单数据...")
    
    # 设置随机种子（基于当前时间，确保每次运行都不同）
    import time
    random.seed(int(time.time()))
    print("  🎲 使用随机种子生成订单数据")
    
    # 客户数据
    customers = [
        {"name": "Nancy Hill", "email": "nancy.hill@mcp.com"},
        {"name": "Cynthia Mendoza", "email": "cynthia.mendoza@mcp.com"},
        {"name": "Eric Jackson", "email": "ejackson@mcp.com"},
        {"name": "Amanda Evans", "email": "aevans@mcp.com"},
        {"name": "Kathleen Jones", "email": "kathleen.jones@mcp.com"},
        {"name": "Henry Howard", "email": "henry_howard51@mcp.com"},
        {"name": "Frances Miller", "email": "frances.miller@mcp.com"},
        {"name": "Jessica Patel", "email": "jessicap@mcp.com"},
        {"name": "Ryan Myers", "email": "rmyers81@mcp.com"},
        {"name": "Zachary Baker", "email": "zachary.baker53@mcp.com"},
        {"name": "Pamela Brooks", "email": "pbrooks@mcp.com"},
        {"name": "Eric Torres", "email": "etorres4@mcp.com"},
        {"name": "Tyler Perez", "email": "tyler_perez28@mcp.com"},
        {"name": "Janet Brown", "email": "brownj@mcp.com"},
        {"name": "Amanda Wilson", "email": "wilsona@mcp.com"},
        {"name": "Dorothy Adams", "email": "dorothya69@mcp.com"},
        {"name": "Aaron Clark", "email": "aaron.clark@mcp.com"},
        {"name": "Deborah Rodriguez", "email": "drodriguez@mcp.com"},
        {"name": "David Lopez", "email": "davidl35@mcp.com"},
        {"name": "Karen White", "email": "karen.white66@mcp.com"},
        {"name": "Alexander Williams", "email": "alexander_williams@mcp.com"},
    ]
    
    # 产品数据
    products = [
        {"name": "Wireless Bluetooth Earphones", "price": 299.00},
        {"name": "Smart Watch", "price": 899.00},
        {"name": "Portable Power Bank", "price": 129.00},
        {"name": "Wireless Charger", "price": 89.00},
        {"name": "Phone Stand", "price": 39.00},
        {"name": "Cable Set", "price": 49.00},
        {"name": "Bluetooth Speaker", "price": 199.00},
        {"name": "Car Charger", "price": 59.00},
        {"name": "Phone Case", "price": 29.00},
        {"name": "Screen Protector", "price": 19.00},
    ]
    
    orders = []
    now = datetime.now()
    
    # 创建7天内的10个订单（混合送达状态）
    print("  创建最近的20个订单（混合送达状态）...")
    for i in range(20):
        customer = customers[i]
        product = random.choice(products)
        
        # 随机订单日期（2-6天前）, 这里设一个2-6天的范围，减少7天和1天的edge case
        order_days_ago = random.randint(2, 6)
        order_date = now - timedelta(days=order_days_ago)
        
        # 混合送达状态：70%已送达，30%处理中/已发货
        if i < 14:  # 前14个已送达（70%）
            status = "completed"
            # 用了1-order_days_ago-1天完成订单
            time_to_complete = random.randint(1,order_days_ago-1)
            # 所以订单完成时间就是订单日期加上用了多少天完成订单
            date_completed = order_date + timedelta(time_to_complete)
        else:  # 后6个未送达（30%）
            status = random.choice(["processing", "on-hold"])
            date_completed = None
        
        order = {
            "order_id": 100 + i,
            "order_number": f"{100 + i}",
            "customer_email": customer["email"],
            "customer_name": customer["name"],
            "status": status,
            "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
            "date_completed": date_completed.strftime('%Y-%m-%dT%H:%M:%S') if date_completed else None,
            "product_name": product["name"],
            "product_price": product["price"],
            "quantity": random.randint(1, 3),
            "period": "recent_7_days"
        }
        orders.append(order)
    
    # 打乱订单顺序，增加随机性
    print("  🔀 打乱订单顺序...")
    random.shuffle(orders)
    
    # # 创建7天前的10个订单（都是已完成状态）
    # print("  创建7天前的订单（已完成状态）...")
    # for i in range(10):
    #     customer = customers[i + 10]
    #     product = random.choice(products)
        
    #     # 8-20天前的订单
    #     order_days_ago = random.randint(8, 20)
    #     order_date = now - timedelta(days=order_days_ago)
    #     date_completed = order_date + timedelta(days=random.randint(3, 7))
        
    #     order = {
    #         "order_id": 200 + i,
    #         "order_number": f"{200 + i}",
    #         "customer_email": customer["email"],
    #         "customer_name": customer["name"],
    #         "status": "completed",
    #         "date_created": order_date.strftime('%Y-%m-%dT%H:%M:%S'),
    #         "date_completed": date_completed.strftime('%Y-%m-%dT%H:%M:%S'),
    #         "product_name": product["name"],
    #         "product_price": product["price"],
    #         "quantity": random.randint(1, 3),
    #         "period": "before_7_days"
    #     }
    #     orders.append(order)
    
    return orders


def create_email_template():
    """创建邮件模板"""
    print("📧 创建邮件模板...")
    
    email_template = {
        "subject": "感谢您的购买！请分享您的购物体验 - {customer_name}",
        "body_template": """亲爱的 {customer_name}，

感谢您在我们商店购买 {product_name}！

您的订单 #{order_number} 已于 {completion_date} 成功完成。为了不断改善我们的服务质量，我们诚挚邀请您花几分钟时间分享您的购物体验。

请点击以下链接填写简短的反馈问卷：
{survey_link}

您的意见对我们非常重要，将帮助我们为您和其他客户提供更好的服务。

产品详情：
- 产品名称：{product_name}
- 订单金额：¥{product_price}
- 购买数量：{quantity}

如果您对产品或服务有任何问题，请随时联系我们的客服团队。

再次感谢您的支持！

此致
客户服务团队
在线商城""",
        "content_type": "text/plain",
        "from_name": "在线商城客服",
        "reply_to": "support@mcp.com"
    }
    
    return email_template


def copy_initial_files_to_workspace(agent_workspace: str):
    """
    将初始文件复制到agent工作空间
    
    Args:
        agent_workspace: Agent工作空间路径
    """
    print(f"🚀 设置初始工作环境到: {agent_workspace}")
    
    # 确保工作空间目录存在
    os.makedirs(agent_workspace, exist_ok=True)
    
    # 定义需要复制的文件
    files_dir = task_dir / "files"
    files_to_copy = [
        "email_config_template.json"
    ]
    
    copied_count = 0
    for filename in files_to_copy:
        source_path = files_dir / filename
        dest_path = Path(agent_workspace) / filename
        
        if source_path.exists():
            try:
                shutil.copy2(source_path, dest_path)
                print(f"✅ 复制文件: {filename}")
                copied_count += 1
            except Exception as e:
                print(f"❌ 复制文件失败 {filename}: {e}")
        else:
            print(f"⚠️  源文件不存在: {filename}")
    
    return copied_count >= 0  # 即使没有文件也算成功


def setup_task_data(upload_to_woocommerce=True):
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
    print(f"✅ 创建完整订单数据: {len(orders)} 个订单")
    
    # 过滤出已完成的订单并保存到 groundtruth_workspace
    completed_orders = [order for order in orders if order["status"] == "completed"]
    groundtruth_dir = current_dir.parent / "groundtruth_workspace"
    groundtruth_dir.mkdir(exist_ok=True)
    
    expected_orders_file = groundtruth_dir / "expected_orders.json"
    with open(expected_orders_file, 'w', encoding='utf-8') as f:
        json.dump(completed_orders, f, ensure_ascii=False, indent=2)
    print(f"✅ 保存已完成订单到 groundtruth: {len(completed_orders)} 个订单")
    
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
    
    print(f"   - 总订单数: {len(all_orders)} 个")
    print(f"   - 已完成订单: {len(completed_orders)} 个 ({len(completed_orders)/len(all_orders)*100:.0f}%)")
    print(f"   - 处理中订单: {len(processing_orders)} 个")
    print(f"   - 等待中订单: {len(onhold_orders)} 个")
    
    print(f"\n📈 订单状态详情:")
    for status, count in sorted(status_summary.items()):
        print(f"   {status}: {count} 个")
    
    # 上传订单到 WooCommerce
    upload_success = False
    if upload_to_woocommerce:
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
                print("✅ 所有订单已成功上传到 WooCommerce")
            else:
                print(f"⚠️ 部分订单上传失败 (成功: {successful_count}, 失败: {failed_count})")
                
        except Exception as e:
            print(f"❌ 上传订单到 WooCommerce 时出错: {e}")
            print("💡 将继续使用本地 JSON 文件作为数据源")
    
    # 创建邮件模板
    email_template = create_email_template()
    with open(current_dir / "email_template.json", 'w', encoding='utf-8') as f:
        json.dump(email_template, f, ensure_ascii=False, indent=2)
    print("✅ 创建邮件模板")
    
    return True


def main():
    """主预处理函数"""
    
    parser = ArgumentParser(description="预处理脚本 - 设置WooCommerce客户调研任务的初始环境")
    parser.add_argument("--agent_workspace", required=True, help="Agent工作空间路径")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--no-upload", action="store_true", help="不上传订单到 WooCommerce，仅创建本地文件")
    parser.add_argument("--no-clear-mailbox", action="store_true", help="不清空邮箱")
    parser.add_argument("--no-clear-forms", action="store_true", help="不清空Google Forms")
    parser.add_argument("--form-name-pattern", type=str, help="要删除的Google Forms名称模式（如果指定，只删除匹配的表单）")
    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 WooCommerce客户调研任务 - 预处理")
    print("=" * 60)
    
    upload_to_woocommerce = not args.no_upload
    clear_mailbox_enabled = not args.no_clear_mailbox
    clear_forms_enabled = not args.no_clear_forms
    form_name_pattern = args.form_name_pattern
    
    if not upload_to_woocommerce:
        print("🔧 参数: 仅创建本地文件，不上传到 WooCommerce")
    if not clear_mailbox_enabled:
        print("🔧 参数: 跳过邮箱清空操作")
    if not clear_forms_enabled:
        print("🔧 参数: 跳过Google Forms清空操作")
    if form_name_pattern:
        print(f"🔧 参数: 只删除包含 '{form_name_pattern}' 的Google Forms")
    
    try:
        # 第一步：清空邮箱（如果启用）
        if clear_mailbox_enabled:
            print("\n" + "="*60)
            print("第一步：清空邮箱")
            print("="*60)
            
            mailbox_result = clear_mailbox()
            
            if not mailbox_result.get('success'):
                print("⚠️ 邮箱清理未完全成功，但继续后续操作...")
                print(f"邮箱清理详情: {mailbox_result}")
            
            # 等待一下，确保邮箱操作完成
            print("⏳ 等待2秒，确保邮箱清理操作完成...")
            time.sleep(2)
        else:
            print("\n🔧 跳过邮箱清空操作")
        
        # 第二步：清空Google Forms（如果启用）
        forms_result = None
        if clear_forms_enabled:
            print("\n" + "="*60)
            print("第二步：清空Google Forms")
            print("="*60)
            form_name_pattern = "Customer Shopping Experience Feedback Survey"
            forms_result = clear_google_forms(form_name_pattern)
            
            if not forms_result.get('success'):
                print("⚠️ Google Forms清理未完全成功，但继续后续操作...")
                print(f"Google Forms清理详情: {forms_result}")
            
            # 等待一下，确保Google Forms操作完成
            print("⏳ 等待2秒，确保Google Forms清理操作完成...")
            time.sleep(2)
        else:
            print("\n🔧 跳过Google Forms清空操作")
        
        # 第三步：设置任务数据文件
        print("\n" + "="*60)
        print("第三步：设置任务数据")
        print("="*60)
        
        success1 = setup_task_data(upload_to_woocommerce=upload_to_woocommerce)
        
        # 第四步：复制初始文件到工作空间
        print("\n" + "="*60)
        print("第四步：复制文件到工作空间")
        print("="*60)
        
        success2 = copy_initial_files_to_workspace(args.agent_workspace)
        
        if success1 and success2:
            print("\n🎉 预处理完成！任务环境已准备就绪")
            print("\n📝 任务数据摘要：")
            step_num = 1
            if clear_mailbox_enabled:
                print(f"{step_num}. ✅ 清空了邮箱（INBOX 和 Sent 文件夹）")
                step_num += 1
            if clear_forms_enabled:
                if forms_result and forms_result.get('success'):
                    deleted_count = forms_result.get('deleted_count', 0)
                    found_count = forms_result.get('found_count', 0)
                    if form_name_pattern:
                        print(f"{step_num}. ✅ 清空了匹配 '{form_name_pattern}' 的Google Forms（找到 {found_count} 个，删除 {deleted_count} 个）")
                    else:
                        print(f"{step_num}. ✅ 清空了所有Google Forms（找到 {found_count} 个，删除 {deleted_count} 个）")
                else:
                    print(f"{step_num}. ⚠️ Google Forms清理部分完成")
                step_num += 1
            print(f"{step_num}. ✅ 创建了20个最近订单（70%已完成 + 30%处理中）")
            step_num += 1
            print(f"{step_num}. ✅ 订单包含混合送达状态（completed/processing/on-hold）")
            step_num += 1
            if upload_to_woocommerce:
                print(f"{step_num}. ✅ 订单已上传到 WooCommerce 并创建了本地备份")
            else:
                print(f"{step_num}. ✅ 订单已保存到本地 JSON 文件")
            step_num += 1
            print(f"{step_num}. ✅ 创建了邮件模板，支持动态参数填充")
            step_num += 1
            print(f"{step_num}. ✅ 配置文件已复制到工作空间")
            step_num += 1
            print(f"{step_num}. ✅ 已完成订单已保存到 groundtruth_workspace")
            print("\n🎯 任务目标：")
            print("- 查询已送达订单的客户")
            print("- 创建客户体验问卷（Google Forms）")
            print("- 向已送达订单的客户发送问卷邮件")
            return True
        else:
            print("\n⚠️  预处理部分完成，请检查错误信息")
            return False
        
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        return False


if __name__ == "__main__":
    main()