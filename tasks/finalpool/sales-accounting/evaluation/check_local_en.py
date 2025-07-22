import os
from utils.general.helper import read_json

def check_local(agent_workspace: str, groundtruth_workspace: str):
    # Check agent generated ledger file
    agent_book_file = os.path.join(agent_workspace, "Account_Book.xlsx")
    groundtruth_book_file = os.path.join(groundtruth_workspace, "Account_Book_Complete.xlsx")
    
    if not os.path.exists(agent_book_file):
        return False, "Account_Book.xlsx file does not exist"
    
    if not os.path.exists(groundtruth_book_file):
        return False, "Reference ledger file does not exist"
    
    try:
        # Use openpyxl to check Excel content
        from openpyxl import load_workbook
        
        # Load agent ledger
        wb_agent = load_workbook(agent_book_file)
        ws_agent = wb_agent.active
        agent_rows = ws_agent.max_row
        
        # Load reference ledger
        wb_ref = load_workbook(groundtruth_book_file)
        ws_ref = wb_ref.active
        ref_rows = ws_ref.max_row
        
        # Check if last week's data was added (should have 126 rows including header)
        if agent_rows < ref_rows:
            return False, f"Insufficient ledger records, current {agent_rows} rows, should have {ref_rows} rows"
        
        # Check if last week's key transactions are included
        key_transactions = [
            ('2024-01-07', 'iPhone 15 Pro', 40000),
            ('2024-01-08', 'MacBook Air', 21600),
            ('2024-01-08', 'iPhone 15 Pro', 19998),
            ('2024-01-09', 'MacBook Air', 8999),
            ('2024-01-10', 'AirPods Pro', 5697)
        ]
        
        found_transactions = []
        for row in ws_agent.iter_rows(min_row=2, values_only=True):
            if row[0] and str(row[0]) >= '2024-01-07':
                found_transactions.append((str(row[0]), row[2], row[5]))
        
        missing_transactions = []
        for expected in key_transactions:
            if expected not in found_transactions:
                missing_transactions.append(expected)
        
        if missing_transactions:
            return False, f"Missing key transaction records: {missing_transactions}"
            
        return True, None
        
    except ImportError:
        # If openpyxl is not available, fall back to file size check
        agent_size = os.path.getsize(agent_book_file)
        ref_size = os.path.getsize(groundtruth_book_file)
        
        if agent_size < ref_size * 0.9:  # Allow 10% difference
            return False, f"Updated ledger file is too small, may not have added data correctly. Current {agent_size} bytes, reference {ref_size} bytes"
            
        return True, None
        
    except Exception as e:
        return False, f"Error checking ledger file: {str(e)}" 