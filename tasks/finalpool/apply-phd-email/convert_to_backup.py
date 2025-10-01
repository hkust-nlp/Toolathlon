#!/usr/bin/env python3
"""
Convert emails.jsonl to corrected_email_backup.json format.
"""
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any

def convert_jsonl_to_backup(jsonl_file: str, placeholder_file: str, output_file: str):
    """
    Convert emails in JSONL format to backup JSON format.

    Args:
        jsonl_file: Path to the input JSONL file.
        placeholder_file: Path to the placeholder values file.
        output_file: Path to the output backup JSON file.
    """
    # Load placeholder values
    placeholder_values = {}
    if placeholder_file and Path(placeholder_file).exists():
        with open(placeholder_file, 'r', encoding='utf-8') as f:
            placeholder_values = json.load(f)
    
    # Read JSONL file
    emails_data = []
    email_id = 1
    
    with open(jsonl_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                email_data = json.loads(line)
                
                # Replace placeholders in content
                content = email_data['content']
                for key, value in placeholder_values.items():
                    placeholder = f'<<<<||||{key}||||>>>>'
                    content = content.replace(placeholder, str(value))
                
                # Construct backup email format
                backup_email = {
                    "email_id": str(email_id),
                    "subject": email_data['subject'],
                    "from_addr": f"{email_data['sender_name']}@mcp.com",  # Simulated sender email
                    "to_addr": "mary.castillo@mcp.com",  # Receiver email
                    "cc_addr": None,
                    "bcc_addr": None,
                    "date": datetime.now().strftime("%a, %d %b %Y %H:%M:%S +0800"),
                    "message_id": f"<{email_id * 123456789}@mcp.com>",
                    "body_text": content,
                    "body_html": "",
                    "is_read": False,  # New emails are unread by default
                    "is_important": False,
                    "folder": "INBOX",  # Inbox folder
                    "attachments": []
                }
                
                emails_data.append(backup_email)
                email_id += 1
                
            except json.JSONDecodeError as e:
                print(f"Skipped invalid JSON line: {e}")
                continue
    
    # Construct final backup data
    backup_data = {
        "export_date": datetime.now().isoformat(),
        "total_emails": len(emails_data),
        "emails": emails_data
    }
    
    # Write to output file
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(backup_data, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Successfully converted {len(emails_data)} emails to {output_file}")
    return len(emails_data)

if __name__ == "__main__":
    # Set file paths
    current_dir = Path(__file__).parent
    jsonl_file = current_dir / "files" / "emails.jsonl"
    placeholder_file = current_dir / "files" / "placeholder_values.json"
    output_file = current_dir / "files" / "emails_backup.json"
    
    if not jsonl_file.exists():
        print(f"❌ JSONL file not found: {jsonl_file}")
        sys.exit(1)
    
    # Run conversion
    convert_jsonl_to_backup(str(jsonl_file), str(placeholder_file), str(output_file))