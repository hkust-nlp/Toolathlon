#!/usr/bin/env python3
"""
Local Email Cleanup Module
Uses IMAP protocol to clear all emails in local mailboxes.
"""

import imaplib
import email
import os
import json
from typing import Dict, Tuple, List, Union

def clean_local_emails(email_config: Dict[str, str]) -> Tuple[bool, int]:
    """
    Clean all emails from a local mailbox.
    
    Args:
        email_config: Config dict with keys: email, password, imap_server, imap_port, use_ssl, etc.
    
    Returns:
        Tuple[bool, int]: (success, number of emails deleted)
    """
    try:
        print("=" * 60)
        print(f"Cleaning mailbox: {email_config['email']}")
        print("=" * 60)
        
        # Connect to IMAP server
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
        
        # Login
        imap_connection.login(email_config['email'], email_config['password'])
        print(f"✅ Successfully connected to {email_config['email']}")
        
        # Select inbox
        imap_connection.select('INBOX')
        
        # Search for all emails
        status, message_numbers = imap_connection.search(None, 'ALL')
        
        if status != 'OK':
            print("❌ Failed to search for emails")
            imap_connection.logout()
            return False, 0
        
        message_list = message_numbers[0].split()
        total_messages = len(message_list)
        
        if total_messages == 0:
            print("📭 No emails to clean in this mailbox.")
            imap_connection.logout()
            return True, 0
        
        print(f"📧 Found {total_messages} emails. Starting cleanup...")
        
        deleted_count = 0
        
        # Mark all messages for deletion
        for i, num in enumerate(message_list, 1):
            try:
                imap_connection.store(num, '+FLAGS', '\\Deleted')
                deleted_count += 1
                
                # Print progress every 100 emails
                if i % 100 == 0:
                    print(f"  Processed: {i}/{total_messages} emails...")
                    
            except Exception as e:
                print(f"⚠️ Failed to delete email {num}: {e}")
                continue
        
        # Expunge deleted emails
        imap_connection.expunge()
        
        # Logout
        imap_connection.logout()
        
        print(f"✅ Mailbox cleanup completed!")
        print(f"   Total deleted: {deleted_count} emails")
        
        return True, deleted_count
        
    except Exception as e:
        print(f"❌ Error occurred while cleaning mailbox: {e}")
        return False, 0

def clean_multiple_accounts(email_configs: list) -> bool:
    """
    Clean multiple mailbox accounts.
    
    Args:
        email_configs: A list of mailbox config dicts.
    
    Returns:
        bool: True if all accounts cleaned successfully, False otherwise.
    """
    print("🧹 Starting cleanup of multiple mailbox accounts")
    print("=" * 80)
    
    all_success = True
    total_deleted = 0
    
    for i, config in enumerate(email_configs, 1):
        print(f"\n📧 Cleaning account {i}/{len(email_configs)}: {config['email']}")
        success, deleted = clean_local_emails(config)
        
        if not success:
            all_success = False
            print(f"❌ Account {config['email']} cleanup failed")
        else:
            total_deleted += deleted
            print(f"✅ Account {config['email']} cleaned, deleted {deleted} emails")
    
    print("\n" + "=" * 80)
    print("🏁 Cleanup Summary")
    print("=" * 80)
    print(f"Total deleted emails: {total_deleted}")
    
    if all_success:
        print("✅ All accounts cleaned successfully!")
    else:
        print("⚠️ Some accounts failed to clean, please check configurations.")
    
    return all_success

if __name__ == "__main__":
    # Read configs from: tasks/finalpool/course-assistant/emails_all_config.json
    try:
        current_dir = os.path.dirname(__file__)
        config_path = os.path.abspath(os.path.join(current_dir, '..', 'emails_all_config.json'))
        with open(config_path, 'r', encoding='utf-8') as f:
            raw_config: Union[Dict[str, str], List[Dict[str, str]]] = json.load(f)

        # Only support cleaning from a list
        if not isinstance(raw_config, list):
            print(f"Result: success=False, message=Config should be a JSON array (list), got {type(raw_config).__name__}, config file={config_path}")
        else:
            all_success = clean_multiple_accounts(raw_config)
            print(f"Result: success={all_success}, cleaned_accounts={len(raw_config)}, config_file={config_path}")
    except Exception as e:
        print(f"Result: success=False, message=Failed to read config: {e}")