#!/usr/bin/env python3
"""
本地邮箱清理模块
使用IMAP协议清理本地邮箱中的所有邮件
"""

import imaplib
import email
import os
import json
from typing import Dict, Tuple, List, Union

def clean_local_emails(email_config: Dict[str, str]) -> Tuple[bool, int]:
    """
    清理本地邮箱中的所有邮件
    
    Args:
        email_config: 邮箱配置信息，包含email, password, imap_server, imap_port, use_ssl等
    
    Returns:
        Tuple[bool, int]: (是否成功, 删除的邮件数量)
    """
    try:
        print("=" * 60)
        print(f"本地邮箱清理: {email_config['email']}")
        print("=" * 60)
        
        # 连接IMAP服务器
        if email_config.get('use_ssl', False):
            imap_connection = imaplib.IMAP4_SSL(
                email_config['imap_server'], 
                email_config['imap_port']
            )
        else:
            imap_connection = imaplib.IMAP4(
                email_config['imap_server'], 
                email_config['imap_port']
            )
        
        # 登录
        imap_connection.login(email_config['email'], email_config['password'])
        print(f"✅ 成功连接到 {email_config['email']}")
        
        # 选择收件箱
        imap_connection.select('INBOX')
        
        # 搜索所有邮件
        status, message_numbers = imap_connection.search(None, 'ALL')
        
        if status != 'OK':
            print("❌ 邮件搜索失败")
            imap_connection.logout()
            return False, 0
        
        message_list = message_numbers[0].split()
        total_messages = len(message_list)
        
        if total_messages == 0:
            print("📭 邮箱中没有邮件需要清理")
            imap_connection.logout()
            return True, 0
        
        print(f"📧 找到 {total_messages} 封邮件，开始清理...")
        
        deleted_count = 0
        
        # 标记所有邮件为删除
        for i, num in enumerate(message_list, 1):
            try:
                # 标记邮件为删除
                imap_connection.store(num, '+FLAGS', '\\Deleted')
                deleted_count += 1
                
                # 每处理100封邮件显示进度
                if i % 100 == 0:
                    print(f"  已处理: {i}/{total_messages} 封邮件...")
                    
            except Exception as e:
                print(f"⚠️ 删除邮件 {num} 失败: {e}")
                continue
        
        # 执行清空操作
        imap_connection.expunge()
        
        # 关闭连接
        imap_connection.logout()
        
        print(f"✅ 邮箱清理完成！")
        print(f"   成功删除: {deleted_count} 封邮件")
        
        return True, deleted_count
        
    except Exception as e:
        print(f"❌ 清理邮箱时发生错误: {e}")
        return False, 0

def clean_multiple_accounts(email_configs: list) -> bool:
    """
    清理多个邮箱账户
    
    Args:
        email_configs: 邮箱配置列表
    
    Returns:
        bool: 是否全部成功
    """
    print("🧹 开始清理多个邮箱账户")
    print("=" * 80)
    
    all_success = True
    total_deleted = 0
    
    for i, config in enumerate(email_configs, 1):
        print(f"\n📧 清理账户 {i}/{len(email_configs)}: {config['email']}")
        success, deleted = clean_local_emails(config)
        
        if not success:
            all_success = False
            print(f"❌ 账户 {config['email']} 清理失败")
        else:
            total_deleted += deleted
            print(f"✅ 账户 {config['email']} 清理成功，删除 {deleted} 封邮件")
    
    print("\n" + "=" * 80)
    print("🏁 邮箱清理总结")
    print("=" * 80)
    print(f"总计删除邮件: {total_deleted} 封")
    
    if all_success:
        print("✅ 所有账户清理成功！")
    else:
        print("⚠️ 部分账户清理失败，请检查配置")
    
    return all_success

if __name__ == "__main__":
    # 从相对路径读取配置: tasks/finalpool/course-assistant/emails_config.json
    try:
        current_dir = os.path.dirname(__file__)
        config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_all_config.json'))
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config: Union[Dict[str, str], List[Dict[str, str]]] = json.load(f)

        # 仅支持从列表批量清理
        if not isinstance(raw_config, list):
            print(f"运行结果: 成功=False, 消息=配置应为JSON数组(list)，实际为{type(raw_config).__name__}, 配置文件={config_path}")
        else:
            all_success = clean_multiple_accounts(raw_config)
            # 统一输出
            print(f"运行结果: 成功={all_success}, 清理账户数={len(raw_config)}, 配置文件={config_path}")
    except Exception as e:
        # 使用统一输出
        print(f"运行结果: 成功=False, 消息=读取配置失败: {e}")