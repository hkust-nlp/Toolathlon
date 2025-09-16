#!/usr/bin/env python3
"""
预处理脚本 - 设置产品召回任务初始环境
"""

import os
import sys
import shutil
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime

# 添加项目路径
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# 添加邮件管理相关导入
from token_key_session import all_token_key_session
from utils.app_specific.poste.local_email_manager import LocalEmailManager

# 导入 Google Drive helper
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import random
random.seed(42)
def clear_all_email_folders():
    """
    清理INBOX、Draft、Sent三个文件夹的邮件
    """
    # 获取邮件配置文件路径
    emails_config_file = all_token_key_session.emails_config_file
    print(f"使用邮件配置文件: {emails_config_file}")

    # 初始化邮件管理器
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # 需要清理的文件夹（尝试清理这些文件夹，如果不存在会在清理时处理错误）
    folders_to_clear = ['INBOX', 'Drafts', 'Sent']

    print(f"将清理以下文件夹: {folders_to_clear}")

    for folder in folders_to_clear:
        try:
            print(f"清理 {folder} 文件夹...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ {folder} 文件夹清理完成")
        except Exception as e:
            print(f"⚠️ 清理 {folder} 文件夹时出错: {e}")

    print("📧 所有邮箱文件夹清理完成")


def clear_google_forms(form_name_pattern: str = None):
    """
    根据Google Form名称删除所有匹配的表单
    
    Args:
        form_name_pattern: 表单名称模式，如果为None则删除所有表单
    
    Returns:
        删除结果字典
    """
    print("📝 开始清理Google Forms...")
    
    try:
        # 导入配置
        from token_key_session import all_token_key_session
        
        # 读取Google凭据配置文件
        try:
            credentials_file = "configs/google_credentials.json"
            with open(credentials_file, 'r') as f:
                cred_data = json.load(f)
            
            creds = Credentials(
                token=cred_data['token'],
                refresh_token=cred_data['refresh_token'],
                token_uri=cred_data['token_uri'],
                client_id=cred_data['client_id'],
                client_secret=cred_data['client_secret'],
                scopes=cred_data['scopes']
            )
            
        except Exception as e:
            print(f"⚠️ 无法读取Google凭据配置文件: {e}")
            return {
                "success": False,
                "error": f"Google凭据配置错误: {e}",
                "timestamp": datetime.now().isoformat()
            }
        
        # 构建Google Drive服务
        drive_service = build('drive', 'v3', credentials=creds)
        
        # 构建查询字符串
        if form_name_pattern:
            query = f"name contains '{form_name_pattern}' and mimeType='application/vnd.google-apps.form'"
            print(f"🔍 查找包含 '{form_name_pattern}' 的Google Forms...")
        else:
            query = "mimeType='application/vnd.google-apps.form'"
            print("🔍 查找所有Google Forms...")
        
        # 查找所有匹配的Google Forms
        page_token = None
        all_forms = []
        
        while True:
            try:
                results = drive_service.files().list(
                    q=query,
                    fields="nextPageToken, files(id, name, createdTime)",
                    pageToken=page_token
                ).execute()
                
                forms = results.get('files', [])
                all_forms.extend(forms)
                
                page_token = results.get('nextPageToken')
                if not page_token:
                    break
                    
            except Exception as e:
                print(f"⚠️ 查询Google Forms时出错: {e}")
                break
        
        if not all_forms:
            print("📭 没有找到匹配的Google Forms")
            return {
                "success": True,
                "deleted_count": 0,
                "found_count": 0,
                "message": "没有找到匹配的表单",
                "timestamp": datetime.now().isoformat()
            }
        
        print(f"📋 找到 {len(all_forms)} 个匹配的Google Forms")
        
        # 删除找到的表单
        deleted_count = 0
        failed_count = 0
        deleted_forms = []
        
        for i, form in enumerate(all_forms, 1):
            form_id = form['id']
            form_name = form['name']
            created_time = form.get('createdTime', 'Unknown')
            
            try:
                # 删除表单
                drive_service.files().delete(fileId=form_id).execute()
                deleted_count += 1
                deleted_forms.append({
                    "id": form_id,
                    "name": form_name,
                    "created_time": created_time
                })
                print(f"   ✅ 删除表单 '{form_name}' (ID: {form_id}) [{i}/{len(all_forms)}]")
                
                # 添加短暂延迟避免API限制
                time.sleep(0.2)
                
            except Exception as e:
                failed_count += 1
                print(f"   ❌ 删除表单 '{form_name}' (ID: {form_id}) 失败: {e}")
        
        # 计算结果
        all_success = failed_count == 0
        
        final_result = {
            "success": all_success,
            "found_count": len(all_forms),
            "deleted_count": deleted_count,
            "failed_count": failed_count,
            "deleted_forms": deleted_forms,
            "search_pattern": form_name_pattern,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Google Forms清理完成:")
        print(f"   找到表单: {len(all_forms)} 个")
        print(f"   成功删除: {deleted_count} 个")
        print(f"   删除失败: {failed_count} 个")
        
        if all_success:
            print("✅ Google Forms清理成功！")
        else:
            print("⚠️ Google Forms清理部分完成，有部分表单删除失败")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Google Forms清理过程中出错: {e}")
        return error_result


def setup_recall_test_data():
    """设置产品召回测试数据"""
    print("🛒 设置产品召回测试数据...")
    
    try:
        from .setup_recall_data import main as setup_recall_main
        from .verify_clean_state import verify_clean_state
        from token_key_session import all_token_key_session
        from .woocommerce_client import WooCommerceClient
        
        # 初始化WooCommerce客户端进行验证
        wc_client = WooCommerceClient(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )
        
        # 验证清理状态
        print("🔍 验证WooCommerce清理状态...")
        verification = verify_clean_state(wc_client)
        
        if not verification["is_clean"]:
            print("⚠️ WooCommerce尚未完全清理，建议先运行清理操作")
            print("发现的问题:")
            for issue in verification["issues"]:
                print(f"  - {issue}")
        
        # 运行召回数据设置
        success = setup_recall_main()
        
        if success:
            print("✅ 产品召回测试数据设置完成")
            
            # 设置完成后再次验证
            print("\n🔍 验证设置结果...")
            # final_verification = verify_clean_state(wc_client)
            
            # 检查是否有预期的测试数据
            products = wc_client.get_all_products()
            orders = wc_client.get_all_orders()
            
            print(f"📊 设置完成摘要:")
            print(f"   - 创建了 {len(products)} 个商品")
            print(f"   - 创建了 {len(orders)} 个订单")
            
            recalled_products = [
                p for p in products
                if any(meta.get('key') == 'recall_status' and meta.get('value') == 'need_recall'
                       for meta in p.get('meta_data', []))
            ]
            print(f"   - 其中 {len(recalled_products)} 个是召回商品")
            
        else:
            print("⚠️ 产品召回测试数据设置部分完成")
        return success
        
    except Exception as e:
        print(f"❌ 产品召回测试数据设置失败: {e}")
        print("ℹ️ 请确保已正确配置 token_key_session.py 文件")
        return False

if __name__ == "__main__":
    
    parser = ArgumentParser(description="预处理脚本 - 设置产品召回任务的初始环境")
    parser.add_argument("--agent_workspace", required=False, help="Agent工作空间路径")
    parser.add_argument("--setup_data", default=True, help="同时设置WooCommerce测试数据")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--no-clear-mailbox", action="store_true", help="不清空邮箱")
    parser.add_argument("--no-clear-forms", action="store_true", help="不清空Google Forms")
    parser.add_argument("--form-name-pattern", type=str, help="要删除的Google Forms名称模式（如果指定，只删除匹配的表单）")

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 产品召回任务 - 预处理")
    print("=" * 60)

    clear_mailbox_enabled = not args.no_clear_mailbox
    clear_forms_enabled = not args.no_clear_forms
    form_name_pattern = args.form_name_pattern or "Product Recall Information Confirmation Form"
    
    if not clear_mailbox_enabled:
        print("🔧 参数: 跳过邮箱清空操作")
    if not clear_forms_enabled:
        print("🔧 参数: 跳过Google Forms清空操作")
    if form_name_pattern:
        print(f"🔧 参数: 只删除包含 '{form_name_pattern}' 的Google Forms")

    try:
        # 第一步：清理邮箱
        if clear_mailbox_enabled:
            print("=" * 60)
            print("第一步：清理邮箱文件夹")
            print("=" * 60)
            clear_all_email_folders()
            
            # 等待一下，确保邮箱操作完成
            print("⏳ 等待2秒，确保邮箱清理操作完成...")
            time.sleep(2)
        else:
            print("\n🔧 跳过邮箱清空操作")

        # 第二步：清空Google Forms（如果启用）
        forms_result = None
        if clear_forms_enabled:
            print("\n" + "=" * 60)
            print("第二步：清空Google Forms")
            print("=" * 60)
            
            forms_result = clear_google_forms(form_name_pattern)
            
            if not forms_result.get('success'):
                print("⚠️ Google Forms清理未完全成功，但继续后续操作...")
                print(f"Google Forms清理详情: {forms_result}")
            
            # 等待一下，确保Google Forms操作完成
            print("⏳ 等待2秒，确保Google Forms清理操作完成...")
            time.sleep(2)
        else:
            print("\n🔧 跳过Google Forms清空操作")
        
        # 第三步：设置产品召回测试数据
        success = True
        if args.setup_data:
            print("\n" + "=" * 60)
            print("第三步：设置产品召回测试数据")
            print("=" * 60)
            success = setup_recall_test_data()
    
        if success:
            print("\n🎉 预处理完成！agent工作空间已准备就绪")
            print("\n📝 任务数据摘要：")
            step_num = 1
            if clear_mailbox_enabled:
                print(f"{step_num}. ✅ 清空了邮箱（INBOX、Drafts 和 Sent 文件夹）")
                step_num += 1
            if clear_forms_enabled:
                if forms_result and forms_result.get('success'):
                    deleted_count = forms_result.get('deleted_count', 0)
                    found_count = forms_result.get('found_count', 0)
                    print(f"{step_num}. ✅ 清空了匹配 '{form_name_pattern}' 的Google Forms（找到 {found_count} 个，删除 {deleted_count} 个）")
                else:
                    print(f"{step_num}. ⚠️ Google Forms清理部分完成")
                step_num += 1
            print(f"{step_num}. ✅ 设置了产品召回测试数据和环境")
            print("\n🎯 任务目标：")
            print("- 检测召回产品并下架")
            print("- 创建产品召回信息确认表（Google Forms）")
            print("- 向受影响客户发送召回通知邮件")
            exit(0)
        else:
            print("\n⚠️ 预处理部分完成，请检查错误信息")
            exit(1)
    
    except Exception as e:
        print(f"❌ 预处理失败: {e}")
        exit(1)