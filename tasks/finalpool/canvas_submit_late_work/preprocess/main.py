#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas考试环境预处理主脚本
执行课程设置和邮件发送功能
"""

import asyncio
import sys
import imaplib
import email
import json
from datetime import datetime
from pathlib import Path
from argparse import ArgumentParser
from typing import Dict
# 添加当前目录到Python路径，确保能正确导入模块
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# 导入本地模块
from setup_courses_with_mcp import run_with_args  as setup_courses_main
# from send_exam_notification_smtp import main as send_email_main
from token_key_session import all_token_key_session

def clear_mailbox() -> Dict:
    """
    清空mcpcanvasadmin2@mcp.com邮箱 - 删除 Sent 和 Inbox 文件夹中的所有邮件
    
    Returns:
        清理结果字典
    """
    print("📧 开始清空mcpcanvasadmin2@mcp.com邮箱...")
    
    try:
        # 邮箱配置（根据check_remote.py中的配置）
        imap_server = 'localhost'
        imap_port = 1143
        email_address = all_token_key_session.admin_email_address
        email_password = all_token_key_session.admin_email_password
        
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


async def main(agent_workspace=None, launch_time=None):
    """主函数"""
    try:
        print("🚀 开始执行Canvas考试环境预处理...")
        
        # 第一步：清空邮箱
        print("\n" + "="*60)
        print("第一步：清空mcpcanvasadmin2@mcp.com邮箱")
        print("="*60)
        
        mailbox_result = clear_mailbox()
        
        if not mailbox_result.get('success'):
            print("⚠️ 邮箱清理未完全成功，但继续后续操作...")
            print(f"邮箱清理详情: {mailbox_result}")
        
        # 等待一下，确保邮箱操作完成
        print("⏳ 等待2秒，确保邮箱清理操作完成...")
        await asyncio.sleep(2)
        
        # 第二步：执行课程设置
        print("\n" + "="*60)
        print("第二步：执行课程设置")
        print("="*60)
        
        await setup_courses_main(agent_workspace=agent_workspace)
        
        print("\n🎉 Canvas考试环境预处理完成！")
        
    except Exception as e:
        print(f"❌ 预处理过程中发生错误: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # 运行异步主函数
    asyncio.run(main(agent_workspace=args.agent_workspace, launch_time=args.launch_time))


