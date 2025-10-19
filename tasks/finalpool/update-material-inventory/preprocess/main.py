from argparse import ArgumentParser
import os
import sys
import json
import shutil
import logging
from pathlib import Path
import asyncio

sys.path.append(os.path.dirname(__file__))

from utils.app_specific.googlesheet.drive_helper import (
    get_google_service, find_folder_by_name, create_folder, 
    clear_folder, copy_sheet_to_folder
)

GOOGLESHEET_URLS = [
    "https://docs.google.com/spreadsheets/d/1wDBqVX9duqdPR0P1t_ExSgSOtS-1M3NOpIFaJZQacNI/edit?usp=sharing",
]

FOLDER_NAME = "update-material-inventory"

# Add local paths for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
task_dir = os.path.dirname(current_dir)
sys.path.insert(0, task_dir)
sys.path.insert(0, current_dir)

async def setup_google_sheets( ):
    task_root_path = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.makedirs(os.path.join(task_root_path, "files"), exist_ok=True)
    folder_id_file = os.path.join(task_root_path, "files", "folder_id.txt")

    if os.path.exists(folder_id_file):
        os.remove(folder_id_file)

    drive_service, sheets_service = get_google_service()

    folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
    if not folder_id:
        folder_id = create_folder(drive_service, FOLDER_NAME)

    clear_folder(drive_service, folder_id)

    for sheet_url in GOOGLESHEET_URLS:
        copy_sheet_to_folder(drive_service, sheet_url, folder_id)

    with open(folder_id_file, "w") as f:
        f.write(folder_id)

    print(f"Folder ID saved: {folder_id}")

def setup_logging():
    """Setup logging"""
    logging.basicConfig(level=logging.INFO)
    return logging.getLogger(__name__)


def calculate_max_producible_quantities() -> dict:
    """
    Calculate maximum producible quantities for each product based on material inventory

    Returns:
        dict: Maximum producible quantities for each product
    """
    # Material inventory (from sheets_setup.py)
    material_inventory = {
        'WOOD_OAK': 250.0,
        'SCREW_M6': 600,
        'SCREW_M8': 450,
        'GLUE_WOOD': 15.0,
        'FINISH_VARNISH': 25.0,
        'WOOD_PINE': 100.0,
        'METAL_LEG': 100,
        'FINISH_PAINT': 10.0
    }
    
    # BOM definition
    bom = {
        'CHAIR_001': {
            'WOOD_OAK': 2.5,
            'SCREW_M6': 8,
            'GLUE_WOOD': 0.1,
            'FINISH_VARNISH': 0.2
        },
        'TABLE_001': {
            'WOOD_OAK': 5.0,
            'SCREW_M8': 12,
            'GLUE_WOOD': 0.3,
            'FINISH_VARNISH': 0.5
        },
        'DESK_001': {
            'WOOD_PINE': 3.0,
            'METAL_LEG': 4,
            'SCREW_M6': 16,
            'FINISH_PAINT': 0.3
        }
    }
    
    max_quantities = {}
    
    for product_sku, materials in bom.items():
        possible_quantities = []
        
        for material_id, unit_requirement in materials.items():
            if material_id not in material_inventory:
                possible_quantities.append(0)
                continue
            
            available_stock = material_inventory[material_id]
            possible_qty = int(available_stock // unit_requirement)
            possible_quantities.append(possible_qty)
        
        # Take minimum value as maximum producible quantity
        max_quantities[product_sku] = min(possible_quantities) if possible_quantities else 0
    
    return max_quantities

def setup_woocommerce_products(wc_client) -> dict:
    """Setup test products in WooCommerce
    
    Args:
        wc_client: WooCommerce client instance
        
    Returns:
        dict: Mapping of SKU to WooCommerce product ID
    """
    logger = setup_logging()
    product_mapping = {}
    
    # First, delete existing products to ensure clean state
    logger.info("🧹 Deleting existing products...")
    existing_products = wc_client.get_all_products()
    for product in existing_products:
        try:
            product_id = product.get('id')
            product_name = product.get('name', 'Unknown')
            success, result = wc_client.delete_product(str(product_id), force=True)
            if success:
                logger.info(f"🗑️ Deleted existing product: {product_name} (ID: {product_id})")
            else:
                logger.warning(f"⚠️ Failed to delete product {product_name} (ID: {product_id}): {result}")
        except Exception as e:
            logger.error(f"❌ Error deleting product {product.get('name', 'Unknown')}: {e}")
    
    logger.info(f"🧹 Cleaned up {len(existing_products)} existing products")
    
    # Calculate max producible quantities based on material inventory
    max_quantities = calculate_max_producible_quantities()
    logger.info(f"📊 Calculated max producible quantities: {max_quantities}")
    
    # Define test products with calculated stock quantities
    test_products = [
        {
            "sku": "CHAIR_001",
            "name": "Classic Wooden Chair",
            "description": "Comfortable, classic wooden chair, perfect for dining rooms and offices",
            "regular_price": "299.00",
            "manage_stock": True,
            "stock_quantity": max_quantities.get("CHAIR_001", 0),
            "categories": [{"name": "Furniture"}, {"name": "Chairs"}]
        },
        {
            "sku": "TABLE_001", 
            "name": "Oak Dining Table",
            "description": "Beautiful oak dining table, seating 4-6",
            "regular_price": "899.00",
            "manage_stock": True,
            "stock_quantity": max_quantities.get("TABLE_001", 0),
            "categories": [{"name": "Furniture"}, {"name": "Tables"}]
        },
        {
            "sku": "DESK_001",
            "name": "Office Desk",
            "description": "Modern, minimalist office desk, perfect for home and office use",
            "regular_price": "699.00", 
            "manage_stock": True,
            "stock_quantity": max_quantities.get("DESK_001", 0),
            "categories": [{"name": "Furniture"}, {"name": "Office furniture"}]
        }
    ]
    
    for product_data in test_products:
        try:
            success, result = wc_client.create_product(product_data)
            if success:
                product_id = result.get("id")
                sku = product_data["sku"]
                product_mapping[sku] = product_id
                logger.info(f"✅ Created product {sku} with ID {product_id}")
            else:
                logger.error(f"❌ Failed to create product {product_data['sku']}: {result}")
        except Exception as e:
            logger.error(f"❌ Error creating product {product_data['sku']}: {e}")
    
    return product_mapping

def setup_test_environment() -> bool:
    """Setup test environment with WooCommerce products and Google Sheets"""
    logger = setup_logging()
    
    try:
        logger.info("🛒 Setting up test environment...")
        
        # Import setup modules
        from woocommerce_client import WooCommerceClient
        # from sheets_setup import GoogleSheetsClient
        from token_key_session import all_token_key_session
        from order_simulator import OrderSimulator
        
        # Setup WooCommerce client
        wc_client = WooCommerceClient(
            all_token_key_session.woocommerce_site_url,
            all_token_key_session.woocommerce_api_key, 
            all_token_key_session.woocommerce_api_secret
        )
        
        if not wc_client.test_connection():
            logger.warning("⚠️ WooCommerce connection failed, skipping product setup")
            return True  # Continue anyway

        # Clear existing orders before setting up new environment
        logger.info("🧹 Clearing existing orders...")
        success, deleted_count = wc_client.clear_all_orders()
        if success:
            logger.info(f"✅ Successfully cleared {deleted_count} existing orders")
        else:
            logger.warning("⚠️ Failed to clear existing orders, continuing anyway")

        # Create products in WooCommerce
        logger.info("🛍️ Creating products in WooCommerce...")
        product_mapping = setup_woocommerce_products(wc_client)

        # Create orders using OrderSimulator
        logger.info("📦 Creating orders...")
        order_simulator = OrderSimulator(wc_client)
        test_orders = order_simulator.simulate_order_batch(count=3, interval=2)
        
        # Save test orders to current directory for reference
        workspace_orders_file = os.path.join(current_dir, "test_orders.json")
        order_simulator.save_orders_to_file(test_orders, workspace_orders_file)
        
        # Calculate expected results based on generated orders
        from calculate_expected_results import calculate_expected_results
        calculate_expected_results()
        
        # Setup Google Sheets using drive helper approach
        try:
            from utils.app_specific.googlesheet.drive_helper import (
                get_google_service, find_folder_by_name, create_folder, 
                clear_folder, copy_sheet_to_folder
            )
            
            GOOGLESHEET_URLS = [
                "https://docs.google.com/spreadsheets/d/1S9BFFHU262CjU87DnGFfP_LMChhAT4lx7uNvwY-7HoI",
            ]
            FOLDER_NAME = "update-material-inventory"
            
            drive_service, sheets_service = get_google_service()
            
            folder_id = find_folder_by_name(drive_service, FOLDER_NAME)
            if not folder_id:
                folder_id = create_folder(drive_service, FOLDER_NAME)
                logger.info(f"📁 Created Google Sheets folder: {FOLDER_NAME}")
            
            clear_folder(drive_service, folder_id)
            logger.info(f"🧹 Cleared Google Sheets folder: {folder_id}")
            
            for sheet_url in GOOGLESHEET_URLS:
                copy_sheet_to_folder(drive_service, sheet_url, folder_id)
                logger.info(f"📋 Copied sheet to folder: {sheet_url}")
                
            logger.info("✅ Google Sheets setup completed using drive helper")
            
            # Use folder_id as spreadsheet_id reference for config
            spreadsheet_id = folder_id
            
        except Exception as e:
            logger.warning(f"⚠️ Google Sheets setup failed: {e}")
            spreadsheet_id = None
        
        # Create complete config with spreadsheet ID and product mapping
        config_path = os.path.join(task_dir, "initial_workspace", "config.json")
        
        # Create new config dictionary
        config = {
            "bom_sheet_name": "BOM",
            "inventory_sheet_name": "Material_Inventory",
            "product_mapping": {}
        }
        
        # Add spreadsheet ID if available
        if spreadsheet_id:
            config["spreadsheet_id"] = spreadsheet_id
            logger.info(f"💾 Saved spreadsheet ID to config: {spreadsheet_id}")
        
        # Add product mapping with WooCommerce IDs
        for sku, wc_id in product_mapping.items():
            config["product_mapping"][sku] = {
                "woocommerce_id": str(wc_id)
            }
        
        # Ensure initial_workspace directory exists
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        with open(config_path, 'w') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        logger.info(f"💾 Config file created: {config_path}")
        
        logger.info("✅ Test environment setup completed")
        return True
        
    except Exception as e:
        logger.error(f"Test environment setup failed: {e}")
        logger.info("⚠️ Continuing with basic setup...")
        return True  # Don't fail completely if test setup fails

if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")

    # default to use setup_test
    args = parser.parse_args()
    
    logger = setup_logging()
    
    print("🎯 Material Inventory Management - Preprocessing")
    print("=" * 60)
    
    success = True
    
    if not setup_test_environment():
        logger.warning("Test environment setup had issues, but continuing...")
        success = False

    if success:
        print("\\n🎉 Preprocessing completed successfully!")
        sys.exit(0)
    else:
        print("\\n❌ Preprocessing failed")
        sys.exit(1)