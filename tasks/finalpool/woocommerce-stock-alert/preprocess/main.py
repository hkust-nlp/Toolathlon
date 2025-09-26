#!/usr/bin/env python3
"""
Main preprocess script for woocommerce-stock-alert task.
This script orchestrates the complete initialization process:
1. Clear all email folders (INBOX, Drafts, Sent)
2. Synchronize WooCommerce products with configuration data
3. Copy existing Google Sheets to workspace folder
"""

import sys
import os
import asyncio
import json
from pathlib import Path
from argparse import ArgumentParser

# Add project root to Python path for proper module imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

# Add current task directory to path for token access
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder,
    clear_folder, copy_sheet_to_folder
)
from utils.app_specific.woocommerce.client import WooCommerceClient
from utils.app_specific.poste.local_email_manager import LocalEmailManager
from token_key_session import all_token_key_session

# Target Google Sheet URL and folder configuration
GOOGLESHEET_URL = "https://docs.google.com/spreadsheets/d/1cMNmXLps78jD-_5bYZlQRitx7mHXagInEHLWW2cBwEY/edit?usp=sharing"
FOLDER_NAME = "woocommerce-stock-alert"


def clear_all_email_folders():
    """
    Clear emails from INBOX, Drafts, Sent folders
    """
    # Get email configuration file path
    emails_config_file = all_token_key_session.emails_config_file
    print(f"Using email configuration file: {emails_config_file}")

    # Initialize email manager
    email_manager = LocalEmailManager(emails_config_file, verbose=True)

    # Folders to clear (will handle errors if folders don't exist during clearing)
    folders_to_clear = ['INBOX', 'Drafts', 'Sent']

    print(f"Will clear the following folders: {folders_to_clear}")

    for folder in folders_to_clear:
        try:
            print(f"Clearing {folder} folder...")
            email_manager.clear_all_emails(mailbox=folder)
            print(f"✅ {folder} folder cleared successfully")
        except Exception as e:
            print(f"⚠️ Error clearing {folder} folder: {e}")

    print("📧 All email folders clearing completed")


class WooCommerceProductSync:
    """Handle WooCommerce product synchronization"""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        self.preprocess = task_dir / "preprocess"
        
        # Initialize real WooCommerce client
        self.wc_client = WooCommerceClient(
            site_url=all_token_key_session.woocommerce_site_url,
            consumer_key=all_token_key_session.woocommerce_api_key,
            consumer_secret=all_token_key_session.woocommerce_api_secret
        )

        # Execute complete reset
        result = self.wc_client.reset_to_empty_store(confirm=True)

        if result.get("success"):
            print("\n🎉 Store reset successful!")
            print("📋 Reset summary:")
            print(result.get("summary", ""))

            # Save reset report
            import json
            from datetime import datetime

            os.makedirs("./tmp", exist_ok=True)
            report_filename = f"./tmp/store_reset_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_filename, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"📄 Detailed report saved to: {report_filename}")

        else:
            print("\n❌ Store reset failed")
            print(f"Error message: {result.get('error', 'Unknown error')}")

    def load_woocommerce_products(self):
        """Load products from woocommerce_products.json"""
        products_file = self.preprocess / "woocommerce_products.json"

        if not products_file.exists():
            raise FileNotFoundError(f"Products file not found: {products_file}")

        with open(products_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data["products"]

    def get_product_by_sku(self, sku):
        """Get product by SKU from WooCommerce"""
        try:
            success, products = self.wc_client.list_products(sku=sku)
            if success and products:
                # Return the first product that exactly matches the SKU
                for product in products:
                    if product.get('sku') == sku:
                        return product
            return None
        except Exception as e:
            print(f"Error searching for product with SKU {sku}: {e}")
            return None

    def create_product(self, product_data):
        """Create a new product in WooCommerce"""
        try:
            wc_product_data = {
                'name': product_data['name'],
                'sku': product_data['sku'],
                'stock_quantity': product_data['stock_quantity'],
                'price': str(product_data['price']),
                'manage_stock': True,
                'stock_status': 'instock' if product_data['stock_quantity'] > 0 else 'outofstock',
                'meta_data': [
                    {'key': 'stock_threshold', 'value': str(product_data['stock_threshold'])},
                    {'key': 'supplier', 'value': product_data['supplier']},
                    {'key': 'category', 'value': product_data['category']}
                ]
            }
            
            success, result = self.wc_client.create_product(wc_product_data)
            if success:
                return result
            else:
                print(f"Failed to create product {product_data['name']}: {result}")
                return None
        except Exception as e:
            print(f"Error creating product {product_data['name']}: {e}")
            return None

    def update_product(self, product_id, updates):
        """Update existing product in WooCommerce"""
        try:
            update_data = {}
            
            if 'stock_quantity' in updates:
                update_data['stock_quantity'] = updates['stock_quantity']
                update_data['stock_status'] = 'instock' if updates['stock_quantity'] > 0 else 'outofstock'
            
            if 'stock_threshold' in updates:
                update_data['meta_data'] = [
                    {'key': 'stock_threshold', 'value': str(updates['stock_threshold'])}
                ]
            
            success, result = self.wc_client.update_product(str(product_id), update_data)
            if success:
                return result
            else:
                print(f"Failed to update product {product_id}: {result}")
                return None
        except Exception as e:
            print(f"Error updating product {product_id}: {e}")
            return None

    def sync_products(self):
        """Synchronize WooCommerce products with configuration"""
        print("Starting WooCommerce product synchronization...")
        print(f"Connecting to WooCommerce at: {all_token_key_session.woocommerce_site_url}")

        target_products = self.load_woocommerce_products()
        print(f"Loaded {len(target_products)} target products from configuration")

        stats = {
            'existing_valid': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }

        for target_product in target_products:
            sku = target_product['sku']
            product_name = target_product['name']

            try:
                existing_product = self.get_product_by_sku(sku)

                if existing_product:
                    # Check if updates needed
                    current_stock = existing_product.get('stock_quantity', 0)
                    current_threshold = None
                    
                    # Extract threshold from meta_data
                    for meta in existing_product.get('meta_data', []):
                        if meta.get('key') == 'stock_threshold':
                            try:
                                current_threshold = int(meta.get('value', 0))
                            except (ValueError, TypeError):
                                current_threshold = 0
                            break
                    
                    needs_update = (
                        current_stock != target_product['stock_quantity'] or
                        current_threshold != target_product['stock_threshold']
                    )

                    if needs_update:
                        updates = {
                            'stock_quantity': target_product['stock_quantity'],
                            'stock_threshold': target_product['stock_threshold']
                        }
                        result = self.update_product(existing_product['id'], updates)
                        if result:
                            print(f"  ✅ Updated product: {product_name}")
                            stats['updated'] += 1
                        else:
                            print(f"  ❌ Failed to update product: {product_name}")
                            stats['errors'] += 1
                    else:
                        print(f"  ✅ Product up to date: {product_name}")
                        stats['existing_valid'] += 1
                else:
                    # Create new product
                    result = self.create_product(target_product)
                    if result:
                        print(f"  ✅ Created product: {product_name}")
                        stats['created'] += 1
                    else:
                        print(f"  ❌ Failed to create product: {product_name}")
                        stats['errors'] += 1

            except Exception as e:
                print(f"  ❌ Error processing product {product_name}: {e}")
                stats['errors'] += 1

        # Show summary
        print(f"\nSynchronization Summary:")
        print(f"  Products already valid: {stats['existing_valid']}")
        print(f"  Products created: {stats['created']}")
        print(f"  Products updated: {stats['updated']}")
        print(f"  Errors: {stats['errors']}")

        # Show low stock products
        try:
            all_wc_products = self.wc_client.get_all_products()
            low_stock = []
            
            for product in all_wc_products:
                stock_qty = product.get('stock_quantity', 0)
                threshold = 0
                
                # Extract threshold from meta_data
                for meta in product.get('meta_data', []):
                    if meta.get('key') == 'stock_threshold':
                        try:
                            threshold = int(meta.get('value', 0))
                        except (ValueError, TypeError):
                            threshold = 0
                        break
                
                if stock_qty < threshold:
                    low_stock.append({
                        'name': product.get('name'),
                        'stock_quantity': stock_qty,
                        'stock_threshold': threshold
                    })

            if low_stock:
                print(f"\n⚠️ Low stock products detected ({len(low_stock)}):")
                for product in low_stock:
                    print(f"  - {product['name']} (Stock: {product['stock_quantity']}, Threshold: {product['stock_threshold']})")
        except Exception as e:
            print(f"Warning: Could not check low stock products: {e}")

        return stats['errors'] == 0


class GoogleSheetsInitializer:
    """Handle Google Sheets initialization"""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        self.files_dir = task_dir / "files"
        self.files_dir.mkdir(exist_ok=True)

    async def initialize_sheets(self):
        """Initialize Google Sheets"""
        print("Initializing Google Sheets for stock alert task...")
        print(f"Source sheet URL: {GOOGLESHEET_URL}")

        # Clean up existing files
        folder_id_file = self.files_dir / "folder_id.txt"
        sheet_id_file = self.files_dir / "sheet_id.txt"

        for file_path in [folder_id_file, sheet_id_file]:
            if file_path.exists():
                file_path.unlink()

        # Get Google services
        drive_service, sheets_service = get_google_service()

        # Create or find folder
        folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
        if not folder_id:
            folder_id = create_folder(drive_service, FOLDER_NAME)
            print(f"Created folder: {FOLDER_NAME}")
        else:
            print(f"Found existing folder: {FOLDER_NAME}")

        # Clear existing contents
        clear_folder(drive_service, folder_id)
        print("Cleared existing folder contents")

        # Copy the existing stock alert sheet
        copied_sheet_id = copy_sheet_to_folder(drive_service, GOOGLESHEET_URL, folder_id)
        print(f"Copied stock alert sheet to folder: {copied_sheet_id}")

        # Save folder and sheet IDs
        with open(folder_id_file, "w") as f:
            f.write(folder_id)
        print(f"Folder ID saved: {folder_id}")

        with open(sheet_id_file, "w") as f:
            f.write(copied_sheet_id)
        print(f"Sheet ID saved: {copied_sheet_id}")

        sheet_url = f"https://docs.google.com/spreadsheets/d/{copied_sheet_id}"
        print(f"Sheet URL: {sheet_url}")

        print("Google Sheets initialization completed successfully!")
        return True


async def main():
    """Main preprocess orchestration function"""
    parser = ArgumentParser(description="WooCommerce Stock Alert Task Preprocess")
    parser.add_argument("--agent_workspace", required=False, help="Agent workspace directory")
    parser.add_argument("--launch_time", required=False, help="Task launch time")
    args = parser.parse_args()

    print("="*60)
    print("WOOCOMMERCE STOCK ALERT TASK PREPROCESS")
    print("="*60)
    print("This script will:")
    print("1. Clear all email folders (INBOX, Drafts, Sent)")
    print("2. Synchronize WooCommerce products with configuration data")
    print("3. Copy existing Google Sheets to workspace folder")
    print("="*60)

    # Get task directory
    task_dir = Path(__file__).parent.parent

    success_count = 0
    total_steps = 3

    # Step 1: Clear email folders
    print(f"\n{'='*60}")
    print("Step 1: Clear Email Folders")
    print(f"{'='*60}")

    try:
        clear_all_email_folders()
        success_count += 1
        print("✅ Email folders cleared successfully")
    except Exception as e:
        print(f"❌ Email folder clearing failed: {e}")

    # Step 2: Synchronize WooCommerce products
    print(f"\n{'='*60}")
    print("Step 2: Synchronize WooCommerce Products")
    print(f"{'='*60}")

    try:
        wc_sync = WooCommerceProductSync(task_dir)
        if wc_sync.sync_products():
            success_count += 1
            print("✅ WooCommerce products synchronized successfully")
        else:
            print("❌ WooCommerce synchronization completed with errors")
    except Exception as e:
        print(f"❌ WooCommerce synchronization failed: {e}")

    # Step 3: Initialize Google Sheets
    print(f"\n{'='*60}")
    print("Step 3: Initialize Google Sheets")
    print(f"{'='*60}")

    try:
        sheets_init = GoogleSheetsInitializer(task_dir)
        if await sheets_init.initialize_sheets():
            success_count += 1
            print("✅ Google Sheets initialized successfully")
        else:
            print("❌ Google Sheets initialization failed")
    except Exception as e:
        print(f"❌ Google Sheets initialization failed: {e}")

    # Final summary
    print(f"\n{'='*60}")
    print("PREPROCESS SUMMARY")
    print(f"{'='*60}")
    print(f"Completed steps: {success_count}/{total_steps}")

    if success_count == total_steps:
        print("✅ All preprocessing steps completed successfully!")
        print("\nInitialized components:")
        print("  - Email folders (INBOX, Drafts, Sent) cleared")
        print("  - WooCommerce products synchronized with configuration")
        print("  - Google Sheets copied to workspace folder")

        return True
    else:
        print("❌ Some preprocessing steps failed!")
        print("Please check the error messages above and retry.")
        return False


if __name__ == "__main__":
    result = asyncio.run(main())
    sys.exit(0 if result else 1)