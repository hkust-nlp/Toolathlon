#!/usr/bin/env python3
"""
Script to generate English version groundtruth Excel file
Creates the complete ledger with historical data + last week's transactions
"""

import random
import datetime
from datetime import timedelta
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
import os

def generate_historical_data():
    """Generate the same historical data as the initial ledger"""
    
    # Product information (same as build_excel_ledger_en.py)
    products = {
        'iPhone 15': {'price': 7999, 'cost': 6500, 'category': 'Phone'},
        'iPhone 15 Pro': {'price': 9999, 'cost': 8000, 'category': 'Phone'},
        'iPhone 14': {'price': 6999, 'cost': 5500, 'category': 'Phone'},
        'MacBook Air': {'price': 8999, 'cost': 7200, 'category': 'Laptop'},
        'MacBook Pro': {'price': 12999, 'cost': 10500, 'category': 'Laptop'},
        'iPad': {'price': 4999, 'cost': 4000, 'category': 'Tablet'},
        'iPad Pro': {'price': 7999, 'cost': 6500, 'category': 'Tablet'},
        'AirPods Pro': {'price': 1899, 'cost': 1400, 'category': 'Accessories'},
        'AirPods': {'price': 1299, 'cost': 1000, 'category': 'Accessories'},
        'Apple Watch': {'price': 2999, 'cost': 2400, 'category': 'Smart Watch'},
        'iMac': {'price': 14999, 'cost': 12000, 'category': 'Desktop'},
        'Mac mini': {'price': 4999, 'cost': 4000, 'category': 'Desktop'},
        'Magic Keyboard': {'price': 999, 'cost': 700, 'category': 'Accessories'},
        'Magic Mouse': {'price': 699, 'cost': 500, 'category': 'Accessories'},
        'iPhone Charger': {'price': 299, 'cost': 200, 'category': 'Accessories'},
        'iPhone Case': {'price': 199, 'cost': 100, 'category': 'Accessories'},
        'MacBook Bag': {'price': 499, 'cost': 300, 'category': 'Accessories'},
        'iPad Keyboard': {'price': 1599, 'cost': 1200, 'category': 'Accessories'}
    }
    
    # Customer list (same as build_excel_ledger_en.py)
    customers = [
        'Zhang San', 'Li Si', 'Wang Wu', 'Zhao Liu', 'Liu Qi', 'Chen Ba', 'Yang Jiu', 'Huang Shi',
        'Zhou Yi', 'Wu Er', 'Zheng San', 'Sun Si', 'Zhu Wu', 'Hu Liu', 'Lin Qi', 'He Ba',
        'Gao Jiu', 'Liang Shi', 'Luo Shiyi', 'Song Shier', 'Xie Shisan', 'Tang Shisi', 'Han Shiwu', 'Feng Shiliu',
        'Yu Shiqi', 'Dong Shiba', 'Xiao Shijiu', 'Cheng Ershi', 'Cao Eryi', 'Yuan Erer', 'Deng Ersan', 'Xu Ersi',
        'Fu Erwu', 'Shen Erliu', 'Zeng Erqi', 'Peng Erba', 'Lu Erjiu', 'Su Sanshi', 'Lu Sanyi', 'Jiang Saner'
    ]
    
    # Suppliers
    suppliers = ['Supplier A', 'Supplier B', 'Supplier C', 'Supplier D', 'Supplier E']
    
    # Generate historical data (December 1, 2023 to January 6, 2024)
    ledger_data = []
    start_date = datetime.date(2023, 12, 1)
    current_date = datetime.date(2024, 1, 6)
    
    current = start_date
    transaction_count = 0
    
    # Set random seed for reproducible results (same as initial data)
    random.seed(42)
    
    while current <= current_date and transaction_count < 120:
        # Skip some dates (simulate rest days)
        if random.random() < 0.1:  # 10% chance to skip this day
            current += timedelta(days=1)
            continue
            
        # Generate 2-5 transactions per day
        daily_transactions = random.randint(2, 5)
        
        for _ in range(daily_transactions):
            if transaction_count >= 120:
                break
                
            transaction_type = random.choices(['Sales', 'Purchase'], weights=[0.7, 0.3])[0]
            product = random.choice(list(products.keys()))
            quantity = random.randint(1, 3) if transaction_type == 'Sales' else random.randint(5, 20)
            
            if transaction_type == 'Sales':
                unit_price = products[product]['price']
                customer = random.choice(customers)
                # Random discounts
                if random.random() < 0.2:  # 20% chance for discount
                    discount = random.uniform(0.05, 0.15)
                    unit_price = int(unit_price * (1 - discount))
                    note = f"Discount {discount*100:.1f}%"
                else:
                    note = ""
                partner = customer
            else:  # Purchase
                unit_price = products[product]['cost']
                supplier = random.choice(suppliers)
                note = ""
                partner = supplier
            
            total_amount = unit_price * quantity
            
            ledger_data.append({
                'date': current.strftime('%Y-%m-%d'),
                'type': transaction_type,
                'product': product,
                'quantity': quantity,
                'unit_price': unit_price,
                'total': total_amount,
                'partner': partner,
                'note': note
            })
            
            transaction_count += 1
        
        current += timedelta(days=1)
    
    return ledger_data

def get_last_week_transactions():
    """Get the last week's transaction data matching memory.json"""
    
    return [
        {
            'date': '2024-01-07',
            'type': 'Purchase',
            'product': 'iPhone 15 Pro',
            'quantity': 5,
            'unit_price': 8000,
            'total': 40000,
            'partner': 'Supplier A',
            'note': ''
        },
        {
            'date': '2024-01-08',
            'type': 'Purchase',
            'product': 'MacBook Air',
            'quantity': 3,
            'unit_price': 7200,
            'total': 21600,
            'partner': 'Supplier B',
            'note': ''
        },
        {
            'date': '2024-01-08',
            'type': 'Sales',
            'product': 'iPhone 15 Pro',
            'quantity': 2,
            'unit_price': 9999,
            'total': 19998,
            'partner': 'Wang Wu',
            'note': 'VIP Customer'
        },
        {
            'date': '2024-01-09',
            'type': 'Sales',
            'product': 'MacBook Air',
            'quantity': 1,
            'unit_price': 8999,
            'total': 8999,
            'partner': 'Zhao Liu',
            'note': 'New Customer'
        },
        {
            'date': '2024-01-10',
            'type': 'Sales',
            'product': 'AirPods Pro',
            'quantity': 3,
            'unit_price': 1899,
            'total': 5697,
            'partner': 'Liu Qi',
            'note': 'Returning Customer'
        }
    ]

def create_groundtruth_excel():
    """Create the complete groundtruth Excel file"""
    
    # Generate historical data
    historical_data = generate_historical_data()
    print(f"Generated {len(historical_data)} historical transaction records")
    
    # Get last week's data
    last_week_data = get_last_week_transactions()
    print(f"Added {len(last_week_data)} last week's transaction records")
    
    # Merge all data
    complete_data = historical_data + last_week_data
    print(f"Complete ledger contains {len(complete_data)} transaction records")
    
    # Create Excel workbook
    wb = Workbook()
    ws = wb.active
    ws.title = "Complete Ledger"
    
    # Set headers in English
    headers = ['Date', 'Type', 'Product', 'Quantity', 'Unit Price', 'Total', 'Customer/Supplier', 'Notes']
    for col, header in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=header)
        cell.font = Font(bold=True)
        cell.fill = PatternFill(start_color="E1E1E1", end_color="E1E1E1", fill_type="solid")
        cell.alignment = Alignment(horizontal="center")
    
    # Write data
    for row_idx, record in enumerate(complete_data, 2):
        ws.cell(row=row_idx, column=1, value=record['date'])
        ws.cell(row=row_idx, column=2, value=record['type'])
        ws.cell(row=row_idx, column=3, value=record['product'])
        ws.cell(row=row_idx, column=4, value=record['quantity'])
        ws.cell(row=row_idx, column=5, value=record['unit_price'])
        ws.cell(row=row_idx, column=6, value=record['total'])
        ws.cell(row=row_idx, column=7, value=record['partner'])
        ws.cell(row=row_idx, column=8, value=record['note'])
        
        # Highlight last week's new data (January 7-10)
        if record['date'] >= '2024-01-07':
            for col in range(1, 9):
                cell = ws.cell(row=row_idx, column=col)
                cell.fill = PatternFill(start_color="FFFFCC", end_color="FFFFCC", fill_type="solid")
    
    # Adjust column widths
    column_widths = [12, 10, 15, 8, 10, 12, 15, 12]
    for col, width in enumerate(column_widths, 1):
        ws.column_dimensions[chr(64 + col)].width = width
    
    # Ensure directory exists
    os.makedirs("groundtruth_workspace_en", exist_ok=True)
    
    # Save file
    file_path = "groundtruth_workspace_en/Account_Book_Complete.xlsx"
    wb.save(file_path)
    print(f"Complete groundtruth ledger saved: {file_path}")
    
    return complete_data

def main():
    """Main function"""
    print("Generating English version groundtruth Excel file...")
    
    try:
        complete_data = create_groundtruth_excel()
        print(f"\nGroundtruth generation completed successfully!")
        print(f"- Historical records: 120")
        print(f"- Last week's records: 5") 
        print(f"- Total records: {len(complete_data)}")
        print(f"- File saved: groundtruth_workspace_en/Account_Book_Complete.xlsx")
        
    except Exception as e:
        print(f"Error generating groundtruth: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main()) 