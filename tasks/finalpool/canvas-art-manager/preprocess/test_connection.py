#!/usr/bin/env python3
"""
简单的SMTP连接测试 - 确保使用非SSL模式
"""

import smtplib
import socket


def test_plain_connection():
    """测试纯文本SMTP连接"""
    smtp_server = "localhost"
    smtp_port = 1587
    
    print("=== 测试纯文本SMTP连接 ===")
    print(f"服务器: {smtp_server}")
    print(f"端口: {smtp_port}")
    print("连接模式: 非SSL (纯文本)")
    
    try:
        # 1. 测试TCP连接
        print("\n1. 测试TCP连接...")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        result = sock.connect_ex((smtp_server, smtp_port))
        sock.close()
        
        if result != 0:
            print(f"✗ TCP连接失败 (错误代码: {result})")
            return False
        
        print("✓ TCP连接成功")
        
        # 2. 测试SMTP连接
        print("\n2. 测试SMTP连接...")
        server = smtplib.SMTP(smtp_server, smtp_port)
        
        # 检查连接状态
        print(f"✓ SMTP连接建立成功")
        print(f"  连接类型: {type(server).__name__}")
        
        # 获取服务器欢迎信息
        try:
            response = server.ehlo()
            print(f"  服务器响应: {response}")
        except:
            print("  无法获取服务器响应")
        
        server.quit()
        print("✓ 连接测试完成")
        return True
        
    except smtplib.SMTPConnectError as e:
        print(f"✗ SMTP连接失败: {e}")
        return False
    except Exception as e:
        print(f"✗ 意外错误: {e}")
        return False


def test_authentication():
    """测试认证（不实际发送邮件）"""
    smtp_server = "localhost"
    smtp_port = 1587
    smtp_user = "coxw"
    smtp_pass = "WC0101#iKpTl"
    
    print("\n=== 测试认证 ===")
    
    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        print("✓ SMTP连接建立")
        
        # 尝试登录
        print(f"尝试登录用户: {smtp_user}")
        server.login(smtp_user, smtp_pass)
        print("✓ 登录成功")
        
        server.quit()
        return True
        
    except smtplib.SMTPAuthenticationError as e:
        print(f"✗ 认证失败: {e}")
        print("可能的原因:")
        print("  - 用户名或密码错误")
        print("  - 账户没有发送权限")
        print("  - 服务器要求不同的认证方式")
        return False
    except Exception as e:
        print(f"✗ 认证测试失败: {e}")
        return False


if __name__ == "__main__":
    print("SMTP非SSL连接测试")
    print("=" * 50)
    
    # 测试连接
    if test_plain_connection():
        # 如果连接成功，测试认证
        test_authentication()
    else:
        print("\n建议:")
        print("1. 检查SMTP服务器是否在端口1587上运行")
        print("2. 确认服务器支持非SSL连接")
        print("3. 检查防火墙设置")

