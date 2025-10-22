import argparse
import os
import asyncio
import sys
import json
from rich import print
from utils.general.helper import read_json,print_color
from utils.app_specific.poste.ops import clear_folder

# Add project root to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
# Go up: preprocess -> payable-invoice-checker -> fan -> tasks -> toolathlon
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

from . import generate_test_invoices
from . import create_snowflake_db


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--agent_workspace", type=str, required=True)
    parser.add_argument("--launch_time", type=str, required=True)
    parser.add_argument("--num_invoices", type=int, default=15)
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF generation and only create database")

    args = parser.parse_args()

    agent_workspace = args.agent_workspace
    launch_time = args.launch_time

    print(f"agent_workspace: {agent_workspace}")
    print(f"launch_time: {launch_time}")
    
    # Set random seed for consistency
    generate_test_invoices.random.seed(42)
    
    if not args.skip_pdf:
        # Step 1: Generate test invoices PDFs
        print("\n" + "="*60)
        print("PREPROCESSING STEP 1: Generate Test Invoice PDFs")
        print("="*60)
        
        # Create files directory in the agent workspace
        files_dir = os.path.join(agent_workspace, "files")
        
        # Generate test invoices
        invoices = []
        supplier_types = list(generate_test_invoices.SUPPLIERS_CONFIG.keys())
        buyer_emails = list(generate_test_invoices.BUYERS_CONFIG.keys())
        template_styles = list(generate_test_invoices.TEMPLATE_STYLES.keys())
        
        if not os.path.exists(files_dir):
            os.makedirs(files_dir)
        
        # Generate invoices
        for i in range(1, args.num_invoices + 1):
            supplier_type = generate_test_invoices.random.choice(supplier_types)
            supplier_config = generate_test_invoices.SUPPLIERS_CONFIG[supplier_type]
            buyer_email = generate_test_invoices.random.choice(buyer_emails)
            
            # Generate items and payment status
            items = generate_test_invoices.generate_invoice_items(supplier_type)
            total_amount = sum(item['total'] for item in items)
            payment_status = generate_test_invoices.generate_random_payment_status(total_amount)
            
            # Generate random date
            month = generate_test_invoices.random.randint(1, 12)
            day = generate_test_invoices.random.randint(1, 28)
            date_str = f"2024-{month:02d}-{day:02d}"
            
            # Generate invoice ID formats
            invoice_formats = [
                f"INV-2024-{i:03d}",
                f"2024-{generate_test_invoices.random.randint(1000, 9999)}",
                f"MCP-{generate_test_invoices.random.randint(100000, 999999)}",
                f"PO{generate_test_invoices.random.randint(10000, 99999)}-24",
                f"BL-2024-{generate_test_invoices.random.randint(100, 999)}",
            ]
            invoice_id = generate_test_invoices.random.choice(invoice_formats)
            
            invoice = {
                "invoice_id": invoice_id,
                "date": date_str,
                "supplier": supplier_config["name"],
                "supplier_address": supplier_config["address"],
                "buyer_email": buyer_email,
                "total_amount": total_amount,
                "bank_account": supplier_config["bank_account"],
                "items": items,
                "payment_status": payment_status
            }
            
            # Generate PDF with rotating template styles
            template_style = template_styles[i % len(template_styles)]
            filename = os.path.join(files_dir, f"{invoice_id}.pdf")
            generate_test_invoices.create_invoice_pdf(filename, invoice, template_style)
            
            invoices.append(invoice)
            print(f"Generated: {filename} - {template_style} style")
        
        print(f"\n✅ Generated {len(invoices)} test invoice PDF files in {files_dir}")
        
        # Step 1.5: Generate groundtruth invoice.jsonl file
        print("\n" + "-"*40)
        print("STEP 1.5: Generate Groundtruth Invoice Data")
        print("-"*40)
        
        # Create groundtruth workspace directory in the correct location
        # Go up from preprocess/ to payable-invoice-checker/
        task_root = os.path.dirname(current_dir)
        groundtruth_dir = os.path.join(task_root, "groundtruth_workspace")
        if not os.path.exists(groundtruth_dir):
            os.makedirs(groundtruth_dir)
        
        # Write invoices to JSONL file
        groundtruth_file = os.path.join(groundtruth_dir, "invoice.jsonl")
        with open(groundtruth_file, 'w', encoding='utf-8') as f:
            for invoice in invoices:
                f.write(json.dumps(invoice, ensure_ascii=False) + '\n')
        
        print(f"✅ Generated groundtruth file: {groundtruth_file}")
        print(f"✅ Saved {len(invoices)} invoice records to groundtruth file")
        
        print("✅ Step 1 completed: Test invoice PDF generation and groundtruth file creation")
    else:
        print("\nℹ️ Skipping PDF generation (--skip-pdf flag)")
        print("⚠️ Groundtruth file generation also skipped (requires invoice generation)")
    
    # Step 2: Initialize Snowflake database with generated data
    print("\n" + "="*60)
    print("PREPROCESSING STEP 2: Initialize Snowflake Database")
    print("="*60)
    
    try:
        await create_snowflake_db.initialize_database()
        print("✅ Step 2 completed: Snowflake database initialization")
    except Exception as e:
        print(f"❌ Step 2 failed: Database initialization error - {e}")
        return
    
    # clear emails
    involved_emails_file = os.path.join(os.path.dirname(__file__), "..", "files", "involved_emails.json")
    involved_emails = read_json(involved_emails_file)
    for role in involved_emails:
        for email_address, config in involved_emails[role].items():
            full_config = {"email": email_address, **config}
            clear_folder("INBOX",full_config)
            clear_folder("Sent",full_config)
    
    print_color("Step 3: Emails cleared for all involved email accounts!","green")

    print("\n" + "="*60)
    print("🎉 PREPROCESSING COMPLETED SUCCESSFULLY!")
    print("="*60)
    print("✅ PDF invoices generated (if not skipped)")
    print("✅ Groundtruth invoice.jsonl file created (if not skipped)")
    print("✅ Snowflake database initialized with test data")
    print("✅ Ready for invoice processing workflow")


if __name__ == "__main__":
    asyncio.run(main())