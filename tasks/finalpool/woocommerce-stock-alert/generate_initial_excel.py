#!/usr/bin/env python3
"""
Generate comprehensive initial Excel file for woocommerce-stock-alert task.
This script creates a more realistic stock alert spreadsheet with multiple low-stock items.
"""

import json
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

def load_woocommerce_products():
    """Load WooCommerce products data from the initial workspace."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    products_file = os.path.join(script_dir, '..', 'initial_workspace', 'woocommerce_products.json')

    with open(products_file, 'r', encoding='utf-8') as f:
        data = json.load(f)

    return data['products']

def calculate_suggested_quantity(current_stock, threshold):
    """Calculate suggested purchase quantity based on stock level."""
    # Simple logic: order enough to reach 2x threshold, with minimum order of 10
    shortage = threshold - current_stock
    suggested = max(shortage + threshold, 10)

    # Round to reasonable order quantities
    if suggested <= 20:
        return ((suggested - 1) // 5 + 1) * 5  # Round to nearest 5
    elif suggested <= 100:
        return ((suggested - 1) // 10 + 1) * 10  # Round to nearest 10
    else:
        return ((suggested - 1) // 50 + 1) * 50  # Round to nearest 50

def generate_alert_time(base_time, index):
    """Generate alert times spread over recent days."""
    return base_time - timedelta(days=index % 7, hours=index % 12, minutes=index * 15 % 60)

def create_comprehensive_stock_data():
    """Create comprehensive stock alert data from WooCommerce products."""
    products = load_woocommerce_products()

    # Find products that are below their safety threshold
    low_stock_products = [
        product for product in products
        if product['stock_quantity'] < product['stock_threshold']
    ]

    base_time = datetime.now()
    stock_alert_records = []

    for i, product in enumerate(low_stock_products):
        supplier = product['supplier']
        alert_time = generate_alert_time(base_time, i)
        suggested_qty = calculate_suggested_quantity(
            product['stock_quantity'],
            product['stock_threshold']
        )

        record = {
            'Product ID': str(product['id']),
            'Product Name': product['name'],
            'SKU': product['sku'],
            'Current Stock': str(product['stock_quantity']),
            'Safety Threshold': str(product['stock_threshold']),
            'Supplier Name': supplier['name'],
            'Supplier ID': supplier['supplier_id'],
            'Supplier Contact': supplier['contact'],
            'Alert Time': alert_time.strftime('%Y-%m-%d %H:%M:%S'),
            'Suggested Order Quantity': str(suggested_qty)
        }
        stock_alert_records.append(record)

    return stock_alert_records

def update_google_sheets_json(records):
    """Update the Google Sheets JSON file with comprehensive data."""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    sheets_file = os.path.join(script_dir, '..', 'initial_workspace', 'google_sheets_data.json')

    # Load existing structure
    with open(sheets_file, 'r', encoding='utf-8') as f:
        sheets_data = json.load(f)

    # Update with comprehensive records
    sheets_data['records'] = records

    # Write back to file
    with open(sheets_file, 'w', encoding='utf-8') as f:
        json.dump(sheets_data, f, ensure_ascii=False, indent=2)

    print(f"Updated {sheets_file} with {len(records)} stock alert records")

def create_excel_file(records):
    """Create an Excel file for reference (optional)."""
    if not records:
        print("No low-stock products found to create Excel file")
        return

    script_dir = os.path.dirname(os.path.abspath(__file__))
    excel_file = os.path.join(script_dir, 'stock_alerts_initial.xlsx')

    # Convert to DataFrame
    df = pd.DataFrame(records)

    # Create Excel file with formatting
    with pd.ExcelWriter(excel_file, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='stock_sheet', index=False)

        # Get workbook and worksheet for formatting
        workbook = writer.book
        worksheet = writer.sheets['stock_sheet']

        # Auto-adjust column widths
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter

            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass

            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width

    print(f"Created Excel file: {excel_file}")
    return excel_file

def main():
    """Main function to generate comprehensive stock alert data."""
    print("Generating comprehensive stock alert data...")

    # Create comprehensive stock alert records
    records = create_comprehensive_stock_data()

    if not records:
        print("No products found below safety threshold.")
        return

    print(f"Found {len(records)} products below safety threshold:")
    for record in records:
        print(f"  - {record['Product Name']} (Stock: {record['Current Stock']}, Threshold: {record['Safety Threshold']})")

    # Update Google Sheets JSON file
    update_google_sheets_json(records)

    # Optionally create Excel file for reference
    try:
        create_excel_file(records)
    except ImportError:
        print("pandas/openpyxl not available, skipping Excel file creation")
    except Exception as e:
        print(f"Could not create Excel file: {e}")

    print("\nStock alert initialization data generated successfully!")
    print("Updated files:")
    print("  - initial_workspace/google_sheets_data.json")
    print("  - preprocess/stock_alerts_initial.xlsx (if pandas available)")

if __name__ == "__main__":
    main()