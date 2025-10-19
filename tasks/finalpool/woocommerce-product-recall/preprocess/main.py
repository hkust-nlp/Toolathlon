#!/usr/bin/env python3
"""
Preprocessing Script - Initialize Product Recall Task Environment
"""

import os
import sys
import shutil
import json
import time
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime

# Add project path
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# Mail management imports
from token_key_session import all_token_key_session
from utils.app_specific.poste.local_email_manager import LocalEmailManager

from utils.app_specific.google_form.ops import clear_google_forms

# Google Drive imports
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
import random
random.seed(42)
def clear_all_email_folders():
    """
    Clear all emails in INBOX, Drafts, and Sent folders.
    """
    # Get the email config file path
    emails_config_file = all_token_key_session.emails_config_file
    print(f"Using email config file: {emails_config_file}")

    # Initialize the email manager
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # Folders to clear (try to clear these folders, errors are handled if non-existent)
    folders_to_clear = ['INBOX', 'Drafts', 'Sent']

    print(f"Will clear the following folders: {folders_to_clear}")

    for folder in folders_to_clear:
        try:
            print(f"Clearing folder {folder} ...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ Folder {folder} cleared")
        except Exception as e:
            print(f"⚠️ Error clearing folder {folder}: {e}")

    print("📧 All mailbox folders have been cleared")

def setup_recall_test_data():
    """Set up product recall test data"""
    print("🛒 Setting up product recall test data...")
    
    try:
        from .setup_recall_data import main as setup_recall_main
        from .verify_clean_state import verify_clean_state
        from token_key_session import all_token_key_session
        from .woocommerce_client import WooCommerceClient
        
        # Initialize WooCommerce client to verify
        wc_client = WooCommerceClient(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )
        
        # Verify clean state
        print("🔍 Verifying WooCommerce clean state...")
        verification = verify_clean_state(wc_client)
        
        if not verification["is_clean"]:
            print("⚠️ WooCommerce store is not completely clean. It is recommended to run the clean operation first.")
            print("Issues found:")
            for issue in verification["issues"]:
                print(f"  - {issue}")
        
        # Run recall data setup
        success = setup_recall_main()
        
        if success:
            print("✅ Product recall test data setup complete")
            
            # After setup, verify again
            print("\n🔍 Verifying setup results...")
            # final_verification = verify_clean_state(wc_client)
            
            # Check that the expected test data exists
            products = wc_client.get_all_products()
            orders = wc_client.get_all_orders()
            
            print(f"📊 Setup summary:")
            print(f"   - {len(products)} products created")
            print(f"   - {len(orders)} orders created")
            
            recalled_products = [
                p for p in products
                if any(meta.get('key') == 'recall_status' and meta.get('value') == 'need_recall'
                       for meta in p.get('meta_data', []))
            ]
            print(f"   - {len(recalled_products)} recalled products")
            
        else:
            print("⚠️ Product recall test data setup partially completed")
        return success
        
    except Exception as e:
        print(f"❌ Failed to set up product recall test data: {e}")
        print("ℹ️ Please make sure 'token_key_session.py' is correctly configured")
        return False

if __name__ == "__main__":
    
    parser = ArgumentParser(description="Preprocessing script - Initialize environment for product recall task")
    parser.add_argument("--agent_workspace", required=False, help="Agent workspace path")
    parser.add_argument("--setup_data", default=True, help="Also set up WooCommerce test data")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    parser.add_argument("--no-clear-mailbox", action="store_true", help="Do not clear mailbox")
    parser.add_argument("--no-clear-forms", action="store_true", help="Do not clear Google Forms")
    parser.add_argument("--form-name-pattern", type=str, help="Pattern of Google Forms to delete (if set, only deletes forms matching)")

    args = parser.parse_args()
    
    print("=" * 60)
    print("🎯 Product Recall Task - Preprocessing")
    print("=" * 60)

    clear_mailbox_enabled = not args.no_clear_mailbox
    clear_forms_enabled = not args.no_clear_forms
    form_name_pattern = args.form_name_pattern or "Product Recall Information Confirmation Form"
    
    if not clear_mailbox_enabled:
        print("🔧 Arg: Skip mailbox clearing operation")
    if not clear_forms_enabled:
        print("🔧 Arg: Skip Google Forms clearing operation")
    if form_name_pattern:
        print(f"🔧 Arg: Only delete Google Forms containing '{form_name_pattern}'")

    try:
        # Step 1: Clear mailbox
        if clear_mailbox_enabled:
            print("=" * 60)
            print("Step 1: Clearing mailbox folders")
            print("=" * 60)
            clear_all_email_folders()
            
            # Wait to ensure mailbox operation completes
            print("⏳ Waiting 2 seconds to ensure mailbox clearing is complete...")
            time.sleep(2)
        else:
            print("\n🔧 Mailbox clearing operation skipped")

        # Step 2: Clear Google Forms (if enabled)
        forms_result = None
        if clear_forms_enabled:
            print("\n" + "=" * 60)
            print("Step 2: Clearing Google Forms")
            print("=" * 60)
            
            forms_result = clear_google_forms(form_name_pattern)
            
            if not forms_result.get('success'):
                print("⚠️ Google Forms clearing was not fully successful, proceeding with subsequent operations...")
                print(f"Details: {forms_result}")
            
            # Wait to ensure Google Forms operation completes
            print("⏳ Waiting 2 seconds to ensure Google Forms clearing is complete...")
            time.sleep(2)
        else:
            print("\n🔧 Google Forms clearing operation skipped")
        
        # Step 3: Set up product recall test data
        success = True
        if args.setup_data:
            print("\n" + "=" * 60)
            print("Step 3: Setting up product recall test data")
            print("=" * 60)
            success = setup_recall_test_data()
    
        if success:
            print("\n🎉 Preprocessing complete! Agent workspace is now ready.")
            print("\n📝 Task data summary:")
            step_num = 1
            if clear_mailbox_enabled:
                print(f"{step_num}. ✅ Cleared mailbox (INBOX, Drafts, Sent folders)")
                step_num += 1
            if clear_forms_enabled:
                if forms_result and forms_result.get('success'):
                    deleted_count = forms_result.get('deleted_count', 0)
                    found_count = forms_result.get('found_count', 0)
                    print(f"{step_num}. ✅ Cleared Google Forms matching '{form_name_pattern}' (found {found_count}, deleted {deleted_count})")
                else:
                    print(f"{step_num}. ⚠️ Google Forms clearing partially complete")
                step_num += 1
            print(f"{step_num}. ✅ Product recall test data and environment set up")
            print("\n🎯 Task objectives:")
            print("- Detect recalled products and unlist them")
            print("- Create product recall information confirmation form (Google Forms)")
            print("- Send recall notification emails to affected customers")
            exit(0)
        else:
            print("\n⚠️ Preprocessing partially completed, please check error messages")
            exit(1)
    
    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        exit(1)