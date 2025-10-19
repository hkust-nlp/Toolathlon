#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test the email configuration file
Verify if the config file can be loaded and parsed correctly
"""

import json
from pathlib import Path

def test_config():
    """Test email configuration file"""
    try:
        # Path to config file
        config_file = Path(__file__).parent.parent / 'files' / 'email_config.json'
        
        print(f"📁 Config file path: {config_file}")
        print(f"📋 File exists: {config_file.exists()}")
        
        if not config_file.exists():
            print("❌ Config file does not exist!")
            return False
        
        # Load the config file
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✅ Config file loaded successfully!")
        print("\n📊 Config content:")
        print(f"   SMTP server: {config['server_config']['smtp_server']}:{config['server_config']['smtp_port']}")
        print(f"   IMAP server: {config['server_config']['imap_server']}:{config['server_config']['imap_port']}")
        print(f"   Sender: {config['sender_account']['email']}")
        print(f"   Recipient: {config['recipient']['email']}")
        print(f"   Email subject: {config['email_content']['subject']}")
        print(f"   Exam time: {config['email_content']['exam_info']['exam_date']} {config['email_content']['exam_info']['exam_time']}")
        print(f"   Exam location: {config['email_content']['exam_info']['exam_location']}")
        
        # Check email template file
        template_file = Path(__file__).parent.parent / 'files' / config['email_content']['template_file']
        print(f"\n📝 Email template file: {template_file}")
        print(f"   Template file exists: {template_file.exists()}")
        
        if template_file.exists():
            with open(template_file, 'r', encoding='utf-8') as f:
                template_content = f.read()
            print(f"   Template file size: {len(template_content)} characters")
        
        print("\n🎯 Config verification completed!")
        return True
        
    except Exception as e:
        print(f"❌ Config verification failed: {e}")
        return False

if __name__ == "__main__":
    test_config()

