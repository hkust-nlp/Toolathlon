from argparse import ArgumentParser
import os
import csv
from utils.general.helper import read_json

def check_csv_filename_and_date(csv_path, groundtruth_data):
    """Check if CSV contains correct filename and date columns with exact matches"""
    if not os.path.exists(csv_path):
        raise ValueError("CSV file not found")
    
    try:
        with open(csv_path, 'r') as f:
            reader = csv.DictReader(f)
            csv_data = list(reader)
    except Exception as e:
        raise ValueError(f"Error reading CSV: {e}")
    
    gt_invoices = groundtruth_data["calculation_details"]["invoice_conversions"]
    
    # Create lookup dict from groundtruth
    gt_lookup = {inv["filename"]: inv["date"] for inv in gt_invoices}
    
    # Check each CSV row
    csv_lookup = {}
    for row in csv_data:
        filename = row.get("filename", row.get("file", "")).strip()
        date = row.get("date", "").strip()
        if filename:
            csv_lookup[filename] = date
    
    # Check for missing filenames
    missing_files = set(gt_lookup.keys()) - set(csv_lookup.keys())
    if missing_files:
        raise ValueError(f"Missing filenames in CSV: {missing_files}")
    
    # Check for extra filenames
    extra_files = set(csv_lookup.keys()) - set(gt_lookup.keys())
    if extra_files:
        raise ValueError(f"Extra filenames in CSV: {extra_files}")
    
    # Check dates for each filename
    date_mismatches = []
    for filename, expected_date in gt_lookup.items():
        actual_date = csv_lookup[filename]
        if actual_date != expected_date and expected_date != "":
            date_mismatches.append(f"{filename}: expected '{expected_date}', got '{actual_date}'")
    
    if date_mismatches:
        raise ValueError(f"Date mismatches: {'; '.join(date_mismatches)}")
    
    return True, f"All {len(gt_lookup)} filenames and dates match correctly"

def check_total_amount(agent_total, groundtruth_data):
    """Check total amount with strict tolerance"""
    gt_total = groundtruth_data["total"]
    tolerance = 2
    diff = abs(agent_total - gt_total)
    
    if diff > tolerance:
        raise ValueError(f"Total amount mismatch: Agent: {agent_total:.2f}, GT: {gt_total:.2f}, Diff: {diff:.2f} exceeds tolerance {tolerance}")
    
    return True, f"Total amount correct: Agent: {agent_total:.2f}, GT: {gt_total:.2f}"

if __name__=="__main__":
    parser = ArgumentParser()
    parser.add_argument("--agent_workspace", required=False)
    parser.add_argument("--groundtruth_workspace", required=False)
    parser.add_argument("--res_log_file", required=False)
    parser.add_argument("--launch_time", required=False, help="Launch time")
    args = parser.parse_args()

    # Load agent and groundtruth data
    agent_json_file = os.path.join(args.agent_workspace, "total_invoice.json")
    agent_csv_file = os.path.join(args.agent_workspace, "invoice_summary.csv")
    groundtruth_file = os.path.join(args.groundtruth_workspace, "total_invoice.json")
    
    try:
        agent_data = read_json(agent_json_file)
        groundtruth_data = read_json(groundtruth_file)
    except Exception as e:
        raise ValueError(f"Error loading required files: {e}")
    
    print(f"=== Invoice Organization Task Evaluation ===")
    
    try:
        # 1. Check CSV filename and date columns
        csv_success, csv_msg = check_csv_filename_and_date(agent_csv_file, groundtruth_data)
        print(f"CSV Check: PASS - {csv_msg}")
        
        # 2. Check total amount calculation
        total_success, total_msg = check_total_amount(agent_data["total"], groundtruth_data)
        print(f"Total Check: PASS - {total_msg}")
        
        print("All checks passed!")
        exit(0)
        
    except ValueError as e:
        print(f"FAULT: {e}")
        exit(1)
