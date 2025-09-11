#!/usr/bin/env python3
"""
将emails.jsonl转换为corrected_email_backup.json格式
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def convert_jsonl_to_backup(jsonl_file: str, placeholder_file: str, output_file: str):
    """
    将JSONL格式的邮件转换为备份JSON格式
    
    Args:
        jsonl_file: 输入的JSONL文件路径
        placeholder_file: 占位符文件路径
        output_file: 输出的备份JSON文件路径
    """
    # 加载占位符
    placeholder_values = {}
    if placeholder_file and Path(placeholder_file).exists():
        with open(placeholder_file, 'r', encoding='utf-8') as f:
            placeholder_values = json.load(f)
    
    # 读取JSONL文件
    emails_data = []
    email_id = 1
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                email_data = json.loads(line)
                
                # 处理占位符
                content = email_data['content']
                for key, value in placeholder_values.items():
                    placeholder = f'<<<<||||{key}||||>>>>'
                    content = content.replace(placeholder, str(value))
                
                # 构造备份格式的邮件
                backup_email = {
                    "email_id": str(email_id),
                    "subject": email_data['subject'],
                    "from_addr": f"{email_data['sender_name']}@mcp.com",  # 模拟邮箱地址
                    "to_addr": "mary.castillo@mcp.com",  # 接收者邮箱
                    "cc_addr": None,
                    "bcc_addr": None,
                    "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800"),
                    "message_id": f"<{email_id * 123456789}@mcp.com>",
                    "body_text": content,
                    "body_html": "",
                    "is_read": False,  # 新邮件默认未读
                    "is_important": False,
                    "folder": "INBOX",  # 收件箱
                    "attachments": []
                }
                
                emails_data.append(backup_email)
                email_id += 1
                
            except json.JSONDecodeError as e:
                print(f"跳过无效的JSON行: {e}")
                continue
    
    # 构造最终的备份格式
    backup_data = {
        "export_date": datetime.now().isoformat(),
        "total_emails": len(emails_data),
        "emails": emails_data
    }
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 成功转换 {len(emails_data)} 封邮件到 {output_file}")
    return len(emails_data)

if __name__ == "__main__":
    # 设置文件路径
    current_dir = Path(__file__).parent
    jsonl_file = current_dir / "files" / "emails.jsonl"
    placeholder_file = current_dir / "files" / "placeholder_values.json"
    output_file = current_dir / "files" / "emails_backup.json"
    
    if not jsonl_file.exists():
        print(f"❌ 找不到JSONL文件: {jsonl_file}")
        sys.exit(1)
    
    # 执行转换
    convert_jsonl_to_backup(str(jsonl_file), str(placeholder_file), str(output_file))