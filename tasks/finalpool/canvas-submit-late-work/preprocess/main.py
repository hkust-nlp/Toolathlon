#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Canvas exam environment preprocessing main script
Handles course setup and email sending functionality
"""

import asyncio
import sys
import imaplib
import email
import json
import os
import tarfile
from datetime import datetime
from pathlib import Path
from argparse import ArgumentParser
from typing import Dict
# add current directory to Python path to ensure correct module import
current_dir = Path(__file__).parent
sys.path.insert(0, str(current_dir))

# import local modules
from setup_courses_with_mcp import run_with_args  as setup_courses_main
# from send_exam_notification_smtp import main as send_email_main
from token_key_session import all_token_key_session

def clear_mailbox() -> Dict:
    """
    Clear mcpcanvasadmin2@mcp.com mailbox - delete all emails in Sent and Inbox folders
    
    Returns:
        Clear results dictionary
    """
    print("📧 Starting to clear mcpcanvasadmin2@mcp.com mailbox...")
    
    try:
        # mailbox configuration (according to the configuration in check_remote.py)
        imap_server = 'localhost'
        imap_port = 1143
        email_address = all_token_key_session.admin_email_address
        email_password = all_token_key_session.admin_email_password
        
        # connect to IMAP server
        mail = imaplib.IMAP4(imap_server, imap_port)
        
        # login
        mail.login(email_address, email_password)
        
        # list of folders to clear
        folders_to_clear = ['INBOX', 'Sent']
        clear_results = {}
        
        for folder in folders_to_clear:
            print(f"🗂️ Clearing folder: {folder}")
            
            try:
                # select folder
                status, _ = mail.select(folder)
                if status != "OK":
                    print(f"   ⚠️ Cannot select folder {folder}")
                    clear_results[folder] = {
                        "success": False,
                        "error": f"Cannot select folder {folder}",
                        "deleted_count": 0
                    }
                    continue
                
                # search all emails
                status, messages = mail.search(None, "ALL")
                if status != "OK":
                    print(f"   ⚠️ Cannot search emails in folder {folder}")
                    clear_results[folder] = {
                        "success": False,
                        "error": f"Cannot search emails in folder {folder}",
                        "deleted_count": 0
                    }
                    continue
                
                email_ids = messages[0].split()
                total_emails = len(email_ids)
                
                if total_emails == 0:
                    print(f"   📭 Folder {folder} is already empty")
                    clear_results[folder] = {
                        "success": True,
                        "deleted_count": 0,
                        "message": "Folder is already empty"
                    }
                    continue
                
                print(f"   📬 Found {total_emails} emails, starting to delete...")
                
                # mark all emails for deletion
                deleted_count = 0
                failed_count = 0
                
                for email_id in email_ids:
                    try:
                        # mark email for deletion
                        mail.store(email_id, '+FLAGS', '\\Deleted')
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ Failed to delete email {email_id.decode()}: {e}")
                        failed_count += 1
                
                # execute deletion
                mail.expunge()
                
                print(f"   ✅ Folder {folder}: deleted {deleted_count} emails, failed {failed_count} emails")
                
                clear_results[folder] = {
                    "success": failed_count == 0,
                    "deleted_count": deleted_count,
                    "failed_count": failed_count,
                    "total_found": total_emails
                }
                
            except Exception as e:
                print(f"   ❌ Error clearing folder {folder}: {e}")
                clear_results[folder] = {
                    "success": False,
                    "error": str(e),
                    "deleted_count": 0
                }
        
        # close connection
        mail.logout()
        
        # calculate total results
        total_deleted = sum(result.get('deleted_count', 0) for result in clear_results.values())
        all_success = all(result.get('success', False) for result in clear_results.values())
        
        final_result = {
            "success": all_success,
            "total_deleted": total_deleted,
            "folders": clear_results,
            "timestamp": datetime.now().isoformat()
        }
        
        print(f"📊 Email cleanup completed:")
        print(f"   Total deleted: {total_deleted} emails")
        
        if all_success:
            print("✅ Email cleanup successful!")
        else:
            print("⚠️ Email cleanup partially completed, some folders cleanup failed")
        
        return final_result
        
    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Error during email cleanup: {e}")
        return error_result


async def main(agent_workspace=None, launch_time=None):
    """Main function"""
    try:
        print("🚀 Starting to execute Canvas exam environment preprocessing...")
        
        # first step: clear mailbox
        print("\n" + "="*60)
        print("First step: clear mcpcanvasadmin2@mcp.com mailbox")
        print("="*60)
        
        mailbox_result = clear_mailbox()
        
        if not mailbox_result.get('success'):
            print("⚠️ Email cleanup not fully successful, but continuing with subsequent operations...")
            print(f"Email cleanup details: {mailbox_result}")
        
        # wait for a moment to ensure mailbox operations are completed
        print("⏳ Waiting for 2 seconds to ensure mailbox cleanup operations are completed...")
        await asyncio.sleep(2)
        
        # second step: execute course setup
        print("\n" + "="*60)
        print("Second step: execute course setup")
        print("="*60)
        
        await setup_courses_main(agent_workspace=agent_workspace)
        
        print("\n🎉 Canvas exam environment preprocessing completed!")
        
    except Exception as e:
        print(f"❌ Error during preprocessing: {e}")
        sys.exit(1)

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=True)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # run asynchronous main function
    asyncio.run(main(agent_workspace=args.agent_workspace, launch_time=args.launch_time))

    # ensure agent workspace exists
    os.makedirs(args.agent_workspace, exist_ok=True)
    
    # check if source file exists and is not empty
    initial_workspace_dir = os.path.join(os.path.dirname(__file__), '..', 'initial_workspace')
    src_tar_path = os.path.join(initial_workspace_dir, "files.tar.gz")
    dst_tar_path = os.path.join(args.agent_workspace, "files.tar.gz")
    
    if not os.path.exists(src_tar_path):
        print(f"⚠️ Source file does not exist: {src_tar_path}")
        print("Skipping decompression step")
    elif os.path.getsize(src_tar_path) == 0:
        print(f"⚠️ Source file is empty: {src_tar_path}")
        print("Skipping decompression step")
    else:
        # copy file to destination location
        try:
            import shutil
            shutil.copy2(src_tar_path, dst_tar_path)
            print(f"Copied file to: {dst_tar_path}")
        except Exception as e:
            print(f"Failed to copy file: {e}")
            sys.exit(1)
        
        # decompress
        try:
            with tarfile.open(dst_tar_path, 'r:gz') as tar:
                print(f"Decompressing to: {args.agent_workspace}")
                # compatible with old Python: fallback when filter parameter is not supported
                try:
                    tar.extractall(path=args.agent_workspace, filter='data')
                except TypeError:
                    # Python 3.7 and older versions do not support filter parameter
                    tar.extractall(path=args.agent_workspace)
                print("Decompression completed")
        except Exception as e:
            print(f"Decompression failed: {e}")
            sys.exit(1)
        
        # delete compressed file
        try:
            os.remove(dst_tar_path)
            print(f"Deleted original compressed file: {dst_tar_path}")
        except Exception as e:
            print(f"Failed to delete compressed file: {e}")

            