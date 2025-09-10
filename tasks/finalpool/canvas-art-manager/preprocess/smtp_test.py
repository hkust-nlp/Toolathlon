#!/usr/bin/env python3
"""
SMTP连接测试脚本
用于诊断SMTP服务器连接和认证问题
"""

import smtplib
import ssl
import socket
from email.mime.text import MIMEText


def test_smtp_connection(server, port, timeout=10):
    """测试SMTP服务器连接"""
    print(f"测试连接到 {server}:{port}")
    try:
        # 测试TCP连接
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((server, port))
        sock.close()
        
        if result == 0:
            print(f"✓ TCP连接到 {server}:{port} 成功")
            return True
        else:
            print(f"✗ TCP连接到 {server}:{port} 失败")
            return False
    except Exception as e:
        print(f"✗ 连接测试失败: {e}")
        return False


def test_smtp_server(server, port, username, password, use_ssl=False):
    """测试SMTP服务器认证"""
    print(f"\n=== 测试SMTP服务器: {server}:{port} ===")
    
    try:
        if use_ssl:
            print("使用SSL连接...")
            context = ssl.create_default_context()
            smtp = smtplib.SMTP_SSL(server, port, context=context, timeout=10)
        else:
            print("使用普通连接...")
            smtp = smtplib.SMTP(server, port, timeout=10)
            print("启用STARTTLS...")
            smtp.starttls()
        
        print("✓ SMTP连接建立成功")
        
        # 启用调试模式
        smtp.set_debuglevel(1)
        
        print(f"尝试登录用户: {username}")
        smtp.login(username, password)
        print("✓ 登录成功")
        
        smtp.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ 认证失败: {e}")
        print("可能的原因:")
        print("1. 用户名或密码错误")
        print("2. 账户没有发送邮件权限")
        print("3. 服务器要求不同的认证方式")
        return False
    except smtplib.SMTPConnectError as e:
        print(f"✗ 连接失败: {e}")
        return False
    except smtplib.SMTPException as e:
        print(f"✗ SMTP错误: {e}")
        return False
    except Exception as e:
        print(f"✗ 意外错误: {e}")
        return False


def main():
    # 当前配置
    smtp_server = "localhost"
    smtp_port = 1587
    smtp_user = "coxw"
    smtp_pass = "WC0101#iKpTl"
    
    print("SMTP连接诊断工具")
    print("=" * 50)
    
    # 1. 测试基本连接
    if not test_smtp_connection(smtp_server, smtp_port):
        print("\n建议:")
        print("1. 检查SMTP服务器是否正在运行")
        print("2. 验证服务器地址和端口是否正确")
        print("3. 检查防火墙设置")
        return
    
    # 2. 测试标准SMTP端口
    print("\n测试标准SMTP端口...")
    standard_ports = [25, 587, 465]
    for port in standard_ports:
        if test_smtp_connection(smtp_server, port):
            print(f"发现可用端口: {port}")
    
    # 3. 测试当前配置
    print("\n测试当前配置...")
    success = test_smtp_server(smtp_server, smtp_port, smtp_user, smtp_pass, use_ssl=False)
    
    if not success:
        print("\n尝试SSL连接...")
        test_smtp_server(smtp_server, smtp_port, smtp_user, smtp_pass, use_ssl=True)
    
    # 4. 提供建议
    print("\n" + "=" * 50)
    print("诊断建议:")
    print("1. 如果认证失败，请检查用户名和密码")
    print("2. 尝试使用标准SMTP端口 (25, 587, 465)")
    print("3. 检查SMTP服务器配置")
    print("4. 确认账户有发送邮件权限")
    print("5. 检查是否需要特殊的认证方式")


if __name__ == "__main__":
    main()

