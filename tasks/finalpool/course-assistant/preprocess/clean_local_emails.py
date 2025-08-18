#!/usr/bin/env python3
"""
本地邮箱清理模块
使用IMAP协议清理本地邮箱中的所有邮件
"""

import imaplib
import email
from typing import Dict, Tuple

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
    # 测试用例
    test_config = {
        "email": "virginia_diaz@mcp.com",
        "password": "virginia_85W",
        "imap_server": "localhost",
        "imap_port": 1143,
        "use_ssl": False
    }
    
    success, deleted = clean_local_emails(test_config)
    print(f"测试结果: 成功={success}, 删除={deleted}")