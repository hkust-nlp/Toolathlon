import sys
import os

# Check if pandas is available
try:
    import pandas as pd
    print("pandas available")
    
    try:
        # Try reading Excel
        df = pd.read_excel('stock.xlsx')
        print("Successfully read Excel file:")
        print(df.to_string())
        print("\nColumns:", list(df.columns))
        
        # Save as CSV
        df.to_csv('stock_data.csv', index=False)
        print("Saved as stock_data.csv")
        
    except Exception as e:
        print(f"Error reading Excel: {e}")
        
except ImportError:
    print("pandas not available")
    
    # Try manual Excel reading (very basic)
    try:
        import zipfile
        import xml.etree.ElementTree as ET
        
        print("Attempting manual Excel parsing...")
        # Excel files are ZIP archives
        with zipfile.ZipFile('stock.xlsx', 'r') as zip_ref:
            # List contents
            print("Excel file contents:", zip_ref.namelist())
            
    except Exception as e:
        print(f"Manual parsing failed: {e}")
