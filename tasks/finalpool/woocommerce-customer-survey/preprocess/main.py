#!/usr/bin/env python3
"""
WooCommerce Customer Survey Task - Preprocess Setup
Set up initial work environment: generate order data for recent and earlier periods, as well as email templates
"""
import os
import sys
import json
import shutil
import time
import imaplib
import email
from argparse import ArgumentParser
from pathlib import Path
from datetime import datetime, timedelta
import random
from typing import Dict

# Add project path
current_dir = Path(__file__).parent
task_dir = current_dir.parent
sys.path.insert(0, str(task_dir))

# Import WooCommerce common modules
import sys
from pathlib import Path
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))
from utils.app_specific.woocommerce import (
    setup_customer_survey_environment,
    OrderManager,
    create_customer_survey_orders
)

# Import Google Drive helper
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from utils.app_specific.google_form.ops import clear_google_forms

def clear_mailbox() -> Dict:
    """
    Clear the mailbox - delete all emails in the Sent and Inbox folders
    
    Returns:
        Dictionary of cleanup results
    """
    print("📧 Starting mailbox cleanup...")

    try:
        # Import configuration
        from token_key_session import all_token_key_session

        # Read mail config file
        try:
            with open(all_token_key_session.emails_config_file, 'r', encoding='utf-8') as f:
                email_config = json.load(f)
            email_address = email_config.get('email', 'admin@mcp.com')
            email_password = email_config.get('password', 'admin_password')
            imap_server = email_config.get('imap_server', 'localhost')
            imap_port = email_config.get('imap_port', 1143)
        except Exception as e:
            print(f"⚠️ Failed to read email config file, using default config: {e}")
            email_address = 'admin@mcp.com'
            email_password = 'admin_password'
            imap_server = 'localhost'
            imap_port = 1143

        # Connect to IMAP server
        mail = imaplib.IMAP4(imap_server, imap_port)

        # Login
        mail.login(email_address, email_password)

        # Folders to clear
        folders_to_clear = ['INBOX', 'Sent']
        clear_results = {}

        for folder in folders_to_clear:
            print(f"🗂️ Cleaning folder: {folder}")

            try:
                # Select folder
                status, _ = mail.select(folder)
                if status != "OK":
                    print(f"   ⚠️ Cannot select folder {folder}")
                    clear_results[folder] = {
                        "success": False,
                        "error": f"Cannot select folder {folder}",
                        "deleted_count": 0
                    }
                    continue

                # Search all emails
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
                        "message": "Folder already empty"
                    }
                    continue

                print(f"   📬 Found {total_emails} emails, deleting...")

                # Mark all emails for deletion
                deleted_count = 0
                failed_count = 0

                for email_id in email_ids:
                    try:
                        # Mark email as deleted
                        mail.store(email_id, '+FLAGS', '\\Deleted')
                        deleted_count += 1
                    except Exception as e:
                        print(f"   ❌ Failed to delete email {email_id.decode()}: {e}")
                        failed_count += 1

                # Expunge (delete) marked emails
                mail.expunge()

                print(f"   ✅ Folder {folder}: deleted {deleted_count} emails, failed {failed_count}")

                clear_results[folder] = {
                    "success": failed_count == 0,
                    "deleted_count": deleted_count,
                    "failed_count": failed_count,
                    "total_found": total_emails
                }

            except Exception as e:
                print(f"   ❌ Error cleaning folder {folder}: {e}")
                clear_results[folder] = {
                    "success": False,
                    "error": str(e),
                    "deleted_count": 0
                }

        # Close connection
        mail.logout()

        # Aggregate results
        total_deleted = sum(result.get('deleted_count', 0) for result in clear_results.values())
        all_success = all(result.get('success', False) for result in clear_results.values())

        final_result = {
            "success": all_success,
            "total_deleted": total_deleted,
            "folders": clear_results,
            "timestamp": datetime.now().isoformat()
        }

        print(f"📊 Mailbox cleanup completed:")
        print(f"   Total deleted: {total_deleted} emails")

        if all_success:
            print("✅ Mailbox cleanup successful!")
        else:
            print("⚠️ Mailbox cleanup partially successful, some folders failed")

        return final_result

    except Exception as e:
        error_result = {
            "success": False,
            "error": str(e),
            "timestamp": datetime.now().isoformat()
        }
        print(f"❌ Error during mailbox cleanup: {e}")
        return error_result



class WooCommerceOrderManager:
    """WooCommerce Order Manager - using universal client & tools"""

    def __init__(self, site_url: str, consumer_key: str, consumer_secret: str):
        """
        Initialize WooCommerce Order Manager

        Args:
            site_url: WooCommerce site URL
            consumer_key: WooCommerce API consumer key
            consumer_secret: WooCommerce API consumer secret
        """
        self.order_manager = OrderManager(site_url, consumer_key, consumer_secret)
        self.created_orders = []

    def delete_existing_orders(self):
        """Delete all existing orders to ensure a clean environment"""
        print("🗑️ Deleting existing orders...")

        try:
            # Use the bulk delete function of the generic order manager
            result = self.order_manager.clear_all_orders(confirm=True)

            if result['success']:
                deleted_count = result.get('deleted_count', 0)
                print(f"✅ Successfully deleted {deleted_count} existing orders")
            else:
                error_msg = result.get('error', 'Unknown error')
                print(f"❌ Failed to delete orders: {error_msg}")

        except Exception as e:
            print(f"❌ Error deleting orders: {e}")

    def upload_orders_to_woocommerce(self, orders_data):
        """Upload order data to WooCommerce"""
        print("📤 Starting to upload orders to WooCommerce...")

        # Use the generic order manager's upload functionality
        upload_result = self.order_manager.upload_orders(
            orders_data,
            virtual_product_id=1,
            batch_delay=0.8
        )

        # Maintain compatibility with the original interface
        self.created_orders = upload_result.get('created_orders', [])

        successful_orders = upload_result.get('successful_orders', 0)
        failed_orders = upload_result.get('failed_orders', 0)

        return successful_orders, failed_orders


def create_order_data():
    """
    Create 20 recent orders (mixed delivery status): 70% completed, 30% processing.
    Uses universal order generator function.
    """
    print("📦 Generating order data...")

    # Use generic order generator
    all_orders, completed_orders = create_customer_survey_orders()

    print(f"Created {len(all_orders)} orders")
    print(f"   - Completed orders: {len(completed_orders)}")
    print(f"   - Other status orders: {len(all_orders) - len(completed_orders)}")

    return all_orders

def setup_task_data():
    """
    Set up required task data files
    
    Args:
        upload_to_woocommerce: Whether to upload orders to WooCommerce (default True)
    """
    print("📝 Setting up task data files...")

    # Generate order data
    orders = create_order_data()

    # Save complete order data to local JSON file
    with open(current_dir / "completed_orders.json", 'w', encoding='utf-8') as f:
        json.dump(orders, f, ensure_ascii=False, indent=2)
    print(f"✅ Created complete order data: {len(orders)} orders")

    # Filter completed orders and save to groundtruth_workspace
    completed_orders = [order for order in orders if order["status"] == "completed"]
    groundtruth_dir = current_dir.parent / "groundtruth_workspace"
    groundtruth_dir.mkdir(exist_ok=True)

    expected_orders_file = groundtruth_dir / "expected_orders.json"
    with open(expected_orders_file, 'w', encoding='utf-8') as f:
        json.dump(completed_orders, f, ensure_ascii=False, indent=2)
    print(f"✅ Saved completed orders to groundtruth: {len(completed_orders)} orders")

    # Aggregate status counts
    all_orders = orders
    completed_orders = [o for o in orders if o["status"] == "completed"]
    processing_orders = [o for o in orders if o["status"] == "processing"]
    onhold_orders = [o for o in orders if o["status"] == "on-hold"]

    # Detailed statistics for each status
    status_summary = {}
    for order in orders:
        status = order["status"]
        status_summary[status] = status_summary.get(status, 0) + 1

    print(f"   - Total orders: {len(all_orders)}")
    print(f"   - Completed orders: {len(completed_orders)} ({len(completed_orders)/len(all_orders)*100:.0f}%)")
    print(f"   - Processing orders: {len(processing_orders)}")
    print(f"   - Onhold orders: {len(onhold_orders)}")

    print(f"\n📈 Order status detail:")
    for status, count in sorted(status_summary.items()):
        print(f"   {status}: {count}")

    # Upload orders to WooCommerce
    upload_success = False

    try:
        # Import configuration
        from token_key_session import all_token_key_session

        # Initialize WooCommerce order manager
        order_manager = WooCommerceOrderManager(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key,
            all_token_key_session.woocommerce_api_secret
        )

        # Delete existing orders
        order_manager.delete_existing_orders()

        # Upload new orders
        successful_count, failed_count = order_manager.upload_orders_to_woocommerce(orders)

        if failed_count == 0:
            upload_success = True
            print("✅ All orders successfully uploaded to WooCommerce")
        else:
            print(f"⚠️ Some orders failed to upload (success: {successful_count}, failed: {failed_count})")

    except Exception as e:
        print(f"❌ Error uploading orders to WooCommerce: {e}")
        print("💡 Will continue using local JSON file as data source")
        return False

    return True


def main():
    """Main preprocessing function"""

    parser = ArgumentParser(description="Preprocess script - Set up the initial environment for the WooCommerce customer survey task")
    parser.add_argument("--agent_workspace", required=False, help="Agent workspace path")
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    print("=" * 60)
    print("WooCommerce customer survey task - Preprocess")
    print("=" * 60)

    try:
        # Step 1: Clear mailbox (if enabled)

        print("\n" + "="*60)
        print("First Step: Clear mailbox")
        print("="*60)

        mailbox_result = clear_mailbox()

        if not mailbox_result.get('success'):
            print("Mailbox cleanup not fully successful, but continue with subsequent operations...")
            print(f"Mailbox cleanup details: {mailbox_result}")

        # Wait a bit to ensure mailbox operation is complete
        print("Wait 2 seconds to ensure mailbox cleanup operation is complete...")
        time.sleep(2)

        # Step 2: Clear Google Forms (if enabled)
        forms_result = None

        print("\n" + "="*60)
        print("Second Step: Clear Google Forms")
        print("="*60)
        form_name_pattern = "Customer Shopping Experience Feedback Survey"
        forms_result = clear_google_forms(form_name_pattern)

        if not forms_result.get('success'):
            print("Google Forms cleanup not fully successful, but continue with subsequent operations...")
            print(f"Google Forms cleanup details: {forms_result}")

        # Wait a bit to ensure Google Forms operation is complete
        print("Wait 2 seconds to ensure Google Forms cleanup operation is complete...")
        time.sleep(2)

        # Step 3: Set up task data
        print("\n" + "="*60)
        print("Third Step: Set task data")
        print("="*60)

        success1 = setup_task_data()

        if success1:
            print("\n🎉 Preprocessing completed! Task environment is ready")
            if forms_result and forms_result.get('success'):
                deleted_count = forms_result.get('deleted_count', 0)
                found_count = forms_result.get('found_count', 0)
                if form_name_pattern:
                    print(f"Cleared Google Forms matching '{form_name_pattern}' (found {found_count} deleted {deleted_count} )")
                else:
                    print(f"Cleared all Google Forms (found {found_count} deleted {deleted_count} )")
            return True
        else:
            print("\n Preprocessing partially completed, please check the error information")
            return False

    except Exception as e:
        print(f"❌ Preprocessing failed: {e}")
        return False


if __name__ == "__main__":
    main()