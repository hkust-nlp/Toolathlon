#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试邮件配置文件
验证配置文件是否正确加载和解析
"""

import json
from pathlib import Path

def test_config():
    """测试配置文件"""
    try:
        # 配置文件路径
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        print(f"📁 配置文件路径: {config_file}")
        print(f"📋 文件是否存在: {config_file.exists()}")
        
        if not config_file.exists():
            print("❌ 配置文件不存在！")
            return False
        
        # 加载配置文件
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✅ 配置文件加载成功！")
        print("\n📊 配置信息:")
        print(f"   SMTP服务器: {config['server_config']['smtp_server']}:{config['server_config']['smtp_port']}")
        print(f"   IMAP服务器: {config['server_config']['imap_server']}:{config['server_config']['imap_port']}")
        print(f"   发件人: {config['sender_account']['email']}")
        print(f"   收件人: {config['recipient']['email']}")
        print(f"   邮件主题: {config['email_content']['subject']}")
        print(f"   考试时间: {config['email_content']['exam_info']['exam_date']} {config['email_content']['exam_info']['exam_time']}")
        print(f"   考试地点: {config['email_content']['exam_info']['exam_location']}")
        
        # 检查邮件模板文件
        template_file = Path(__file__).parent.parent / 'files' / config['email_content']['template_file']
        print(f"\n📝 邮件模板文件: {template_file}")
        print(f"   模板文件是否存在: {template_file.exists()}")
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            print(f"   模板文件大小: {len(template_content)} 字符")
        
        print("\n🎯 配置验证完成！")
        return True
        
    except Exception as e:
        print(f"❌ 配置验证失败: {e}")
        return False

if __name__ == "__main__":
    test_config()

