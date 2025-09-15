#!/usr/bin/env python3
"""
Main preprocess script for woocommerce-stock-alert task.
This script orchestrates the complete initialization process:
1. Synchronize WooCommerce products with configuration data
2. Copy existing Google Sheets to workspace folder
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

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder,
    clear_folder, copy_sheet_to_folder
)

# Target Google Sheet URL and folder configuration
GOOGLESHEET_URL = "https://docs.google.com/spreadsheets/d/1yvAav-H7bxzqYBSn7JjeGLqnXAJfAFfz/"
FOLDER_NAME = "woocommerce-stock-alert"


class WooCommerceProductSync:
    """Handle WooCommerce product synchronization"""

    def __init__(self, task_dir: Path):
        self.task_dir = task_dir
        self.preprocess = task_dir / "preprocess"
        self.products = {}  # Mock WooCommerce storage

    def load_woocommerce_products(self):
        """Load products from woocommerce_products.json"""
        products_file = self.preprocess / "woocommerce_products.json"

        if not products_file.exists():
            raise FileNotFoundError(f"Products file not found: {products_file}")

        with open(products_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            return data["products"]

    def get_product_by_sku(self, sku):
        """Get product by SKU (mock implementation)"""
        return self.products.get(sku)

    def create_product(self, product_data):
        """Create a new product (mock implementation)"""
        sku = product_data['sku']
        wc_product = {
            'id': product_data['id'],
            'name': product_data['name'],
            'sku': sku,
            'stock_quantity': product_data['stock_quantity'],
            'stock_threshold': product_data['stock_threshold'],
            'supplier': product_data['supplier'],
            'price': product_data['price'],
            'category': product_data['category']
        }
        self.products[sku] = wc_product
        return wc_product

    def update_product(self, sku, updates):
        """Update existing product (mock implementation)"""
        if sku in self.products:
            self.products[sku].update(updates)
            return self.products[sku]
        return None

    def sync_products(self):
        """Synchronize WooCommerce products with configuration"""
        print("Starting WooCommerce product synchronization...")

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
                    needs_update = (
                        existing_product['stock_quantity'] != target_product['stock_quantity'] or
                        existing_product['stock_threshold'] != target_product['stock_threshold']
                    )

                    if needs_update:
                        updates = {
                            'stock_quantity': target_product['stock_quantity'],
                            'stock_threshold': target_product['stock_threshold']
                        }
                        self.update_product(sku, updates)
                        print(f"  ✅ Updated product: {product_name}")
                        stats['updated'] += 1
                    else:
                        print(f"  ✅ Product up to date: {product_name}")
                        stats['existing_valid'] += 1
                else:
                    # Create new product
                    self.create_product(target_product)
                    print(f"  ✅ Created product: {product_name}")
                    stats['created'] += 1

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
        all_products = list(self.products.values())
        low_stock = [p for p in all_products if p['stock_quantity'] < p['stock_threshold']]

        if low_stock:
            print(f"\n⚠️ Low stock products detected ({len(low_stock)}):")
            for product in low_stock:
                print(f"  - {product['name']} (Stock: {product['stock_quantity']}, Threshold: {product['stock_threshold']})")

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
    print("1. Synchronize WooCommerce products with configuration data")
    print("2. Copy existing Google Sheets to workspace folder")
    print("="*60)

    # Get task directory
    task_dir = Path(__file__).parent.parent

    success_count = 0
    total_steps = 2

    # Step 1: Synchronize WooCommerce products
    print(f"\n{'='*60}")
    print("Step 1: Synchronize WooCommerce Products")
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

    # Step 2: Initialize Google Sheets
    print(f"\n{'='*60}")
    print("Step 2: Initialize Google Sheets")
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