import argparse
import asyncio
import os
import json
import sys
import tarfile
import tempfile
from typing import List, Dict, Any
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from utils.general.helper import read_json
from utils.app_specific.poste.ops import clear_folder
from rich import print

# Add project root to Python path  
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..', '..', '..'))
sys.path.insert(0, project_root)

# Local imports
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from generate_groundtruth_from_policy import (
    load_policy as load_policy_json,
    generate_claims_for_employee,
    inject_form_errors,
)

from generate_policy_pdf import (
    build_policy_story as build_policy_story_func,
    load_policy as load_policy_for_pdf
)

from create_snowflake_db import initialize_database as init_snowflake_contacts_db

from load_employees import load_employees_from_mapping_files
from generate_claims import generate_all_expense_claims


def load_expense_claims(groundtruth_dir: str) -> List[Dict[str, Any]]:
    """Load expense claims from JSON file"""
    expense_file = os.path.join(groundtruth_dir, "expense_claims.json")
    with open(expense_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def create_main_expense_pdf(filepath: str, claim: Dict[str, Any]) -> None:
    """Create the main expense PDF (without invoice details)"""
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    story.append(Paragraph("Travel Expense Reimbursement Form", title_style))
    story.append(Spacer(1, 20))
    
    # Basic information table
    basic_info = [
        ['Claim ID:', claim['claim_id'], 'Employee Name:', claim['employee_name']],
        ['Employee ID:', claim['employee_id'], 'Employee Level:', claim['employee_level']],
        ['Department:', claim['department'], 'Destination:', f"{claim['dest_city']}, {claim['dest_country']}"],
        ['Trip Start:', claim['trip_start'], 'Trip End:', claim['trip_end']],
        ['Nights:', str(claim['nights']), 'Total Amount:', f"CNY{claim['total_claimed']:.2f}"]
    ]
    
    basic_table = Table(basic_info, colWidths=[2*inch, 1.5*inch, 2*inch, 1.5*inch])
    basic_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),  # Left column background
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),  # Third column background
    ]))
    
    story.append(basic_table)
    story.append(Spacer(1, 20))
    
    # Expense details title
    story.append(Paragraph("Expense Details", styles['Heading2']))
    story.append(Spacer(1, 10))
    
    # Expense details table
    detail_header = ['No.', 'Date', 'City', 'Category', 'Amount(CNY)', 'Description']
    detail_data = [detail_header]
    
    for idx, item in enumerate(claim['line_items'], 1):
        detail_data.append([
            str(idx),
            item['date'],
            item['city'],
            item['category'],
            f"{item['amount']:.2f}",
            item['description'][:20] + "..." if len(item['description']) > 20 else item['description']
        ])
    
    detail_table = Table(detail_data, colWidths=[0.5*inch, 1*inch, 0.8*inch, 1*inch, 1*inch, 2.2*inch])
    detail_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),  # Table header background
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),  # Table header text color
    ]))
    
    story.append(detail_table)
    story.append(Spacer(1, 20))
    
    # Signature area
    signature_info = [
        ['Applicant Signature:', '', 'Application Date:', ''],
        ['Manager Signature:', '', 'Approval Date:', ''],
        ['Finance Audit Signature:', '', 'Audit Date:', '']
    ]
    
    signature_table = Table(signature_info, colWidths=[2*inch, 2*inch, 2*inch, 1.5*inch])
    signature_table.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('BACKGROUND', (2, 0), (2, -1), colors.lightgrey),
    ]))
    
    story.append(signature_table)
    
    # Build PDF
    doc.build(story)


def create_invoice_pdf(filepath: str, item: Dict[str, Any], item_idx: int) -> None:
    """Create a separate invoice PDF"""
    doc = SimpleDocTemplate(filepath, pagesize=A4)
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        alignment=1  # Center
    )
    
    invoice_title = f"Invoice #{item_idx} - {item['category']} ({item['date']})"
    story.append(Paragraph(invoice_title, title_style))
    story.append(Spacer(1, 20))
    
    if item['receipts']:
        # If there is a receipt, generate the invoice details table
        receipt = item['receipts'][0]  # Take the first receipt
        
        invoice_data = [
            ['Invoice Number:', receipt.get('invoice_number', 'N/A'), 'Date:', receipt.get('date', 'N/A')],
            ['Vendor:', receipt.get('vendor', 'N/A'), 'Amount:', f"CNY{receipt.get('amount', 0):.2f}"],
            ['City:', receipt.get('city', 'N/A'), 'Country:', receipt.get('country', 'N/A')],
            ['Category:', receipt.get('category', 'N/A'), 'Tax Amount:', f"CNY{receipt.get('tax_amount', 0):.2f}"],
            ['Description:', receipt.get('description', 'N/A'), '', '']
        ]
        
        invoice_table = Table(invoice_data, colWidths=[2*inch, 2*inch, 2*inch, 1.5*inch])
        invoice_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightblue),  # Left column background
            ('BACKGROUND', (2, 0), (2, -1), colors.lightblue),  # Third column background
            ('SPAN', (-2, -1), (-1, -1)),  # Merge the last two cells of the description row
        ]))
        
        story.append(invoice_table)
    else:
        # If there is no receipt
        story.append(Paragraph("No receipt available for this item.", styles['Normal']))
    
    # Build PDF
    doc.build(story)


def create_expense_package(package_path: str, claim: Dict[str, Any]) -> None:
    """Create the expense package tar.gz file"""
    # Create a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        # Generate the main expense PDF
        main_pdf_path = os.path.join(temp_dir, f"expense_claim_{claim['claim_id']}_main.pdf")
        create_main_expense_pdf(main_pdf_path, claim)
        
        # Generate the invoice PDFs
        for idx, item in enumerate(claim['line_items'], 1):
            invoice_filename = f"expense_claim_{claim['claim_id']}_invoice_{idx:02d}.pdf"
            invoice_pdf_path = os.path.join(temp_dir, invoice_filename)
            create_invoice_pdf(invoice_pdf_path, item, idx)
        
        # Create the tar.gz file
        with tarfile.open(package_path, 'w:gz') as tar:
            # Add all PDF files to the compressed package
            for filename in os.listdir(temp_dir):
                if filename.endswith('.pdf'):
                    file_path = os.path.join(temp_dir, filename)
                    tar.add(file_path, arcname=filename)


async def main():
    parser = argparse.ArgumentParser(description="One-click preprocess: generate groundtruth from policy, create policy PDF, and render claim PDFs (form-correct, policy-challenging)")
    parser.add_argument("--agent_workspace", type=str, required=True)
    parser.add_argument("--launch_time", type=str, required=True)
    
    args = parser.parse_args()
    
    agent_workspace = args.agent_workspace
    launch_time = args.launch_time
    
    print(f"agent_workspace: {agent_workspace}")
    print(f"launch_time: {launch_time}")
    # Fixed seed for reproducibility (no options)
    fixed_seed = 7
    print(f"seed: {fixed_seed}")
    
    # Step 0: clear the emails
    print("\n" + "="*60)
    print("PREPROCESSING STEP 0: Clear Emails")
    print("="*60)
    
    involved_emails_file = os.path.join(os.path.dirname(__file__), "..", "files", "involved_emails.json")
    involved_emails = read_json(involved_emails_file)
    for role in involved_emails:
        for email_address, config in involved_emails[role].items():
            full_config = {"email": email_address, **config}
            clear_folder("INBOX",full_config)
            clear_folder("Sent",full_config)
    print("✅ Step 0 completed: Emails cleared")

    # Step 1: Generate groundtruth from policy
    print("\n" + "="*60)
    print("PREPROCESSING STEP 1: Generate Groundtruth from Policy")
    print("="*60)
    
    # Get groundtruth directory
    current_dir = os.path.dirname(os.path.abspath(__file__))
    task_root = os.path.dirname(current_dir)
    groundtruth_dir = os.path.join(task_root, "groundtruth_workspace")
    
    # Load policy JSON
    policy_path = os.path.join(groundtruth_dir, "policy_standards_en.json")
    policy = load_policy_json(policy_path)

    # Load employees from mapping files
    employees_with_errors, employees_no_errors = load_employees_from_mapping_files(groundtruth_dir)
    
    # Generate all expense claims
    generated_claims = generate_all_expense_claims(
        employees_with_errors,
        employees_no_errors,
        policy,
        fixed_seed,
        generate_claims_for_employee,
        inject_form_errors
    )

    # Save groundtruth (overwrite)
    os.makedirs(groundtruth_dir, exist_ok=True)
    gt_file = os.path.join(groundtruth_dir, "expense_claims.json")
    with open(gt_file, 'w', encoding='utf-8') as f:
        json.dump(generated_claims, f, ensure_ascii=False, indent=2)

    claims = generated_claims
    modified_claims = claims  # no form-error injection
    print(f"✅ Generated and saved {len(claims)} expense claims from policy")
    
    # Step 2: Generate PDFs (Policy + Claims)
    print("\n" + "="*60)
    print("PREPROCESSING STEP 2: Generate PDFs (Policy + Claims)")
    print("="*60)
    
    # Create files directory in agent workspace
    files_dir = os.path.join(agent_workspace, "files")
    if not os.path.exists(files_dir):
        os.makedirs(files_dir)
    
    # 2a. Policy PDF
    policy_for_pdf = load_policy_for_pdf(policy_path)
    policy_pdf_path = os.path.join(files_dir, "policy_en.pdf")
    policy_doc = SimpleDocTemplate(policy_pdf_path, pagesize=A4)
    story = build_policy_story_func(policy_for_pdf)
    policy_doc.build(story)
    print(f"Generated: {os.path.abspath(policy_pdf_path)}")

    # 2b. Generate expense packages for each claim
    claim_with_error_count = 0
    for claim in modified_claims:
        filename = os.path.join(files_dir, f"expense_claim_{claim['claim_id']}.tar.gz")
        create_expense_package(filename, claim)

        has_errors = claim.get('_form_errors') or claim.get('_policy_violations')
        if has_errors:
            claim_with_error_count += 1
            form_error_types = sorted({e['type'] for e in claim.get('_form_errors', [])})
            policy_violation_types = sorted({v['type'] for v in claim.get('_policy_violations', [])})
            status = ""
            if form_error_types:
                status += f" [Form: {', '.join(form_error_types)}]"
            if policy_violation_types:
                status += f" [Policy: {', '.join(policy_violation_types)}]"
        fullpath = os.path.abspath(filename)
        print(f"Generated: {fullpath}{status}")
        
        # Print error details
        if claim.get('_form_errors'):
            for err in claim['_form_errors']:
                et = err.get('type', 'unknown')
                detail = err.get('details', '')
                print(f"  - Form error: {et}: {detail}")
        if claim.get('_policy_violations'):
            for viol in claim['_policy_violations']:
                vt = viol.get('type', 'unknown')
                print(f"  - Policy violation: {vt}")
    
    print(f"\n✅ Generated {len(modified_claims)} expense packages (tar.gz)")
    print(f"✅ Claims with form-injected errors: {claim_with_error_count} (expected 0)")

    # Step 3: Initialize Snowflake Enterprise Contacts DB
    print("\n" + "="*60)
    print("PREPROCESSING STEP 3: Initialize Snowflake Enterprise Contacts DB")
    print("="*60)
    await init_snowflake_contacts_db()
    print("✅ Enterprise contacts table ensured and seeded in Snowflake")

    print("\n" + "="*60)
    print("🎉 PREPROCESSING COMPLETED SUCCESSFULLY!")
    print("="*60)
    print(f"✅ Processed {len(claims)} expense claims")
    print(f"✅ Generated {len(modified_claims)} expense packages (tar.gz)")
    total_form_errors = sum(len(c.get('_form_errors', [])) for c in modified_claims)
    total_policy_violations = sum(len(c.get('_policy_violations', [])) for c in modified_claims)
    print(f"✅ Introduced {total_form_errors} form errors and {total_policy_violations} policy violations")
    print("✅ Ready for policy compliance workflow")


if __name__ == "__main__":
    asyncio.run(main())
