import zipfile
import xml.etree.ElementTree as ET

# Extract Excel data manually
with zipfile.ZipFile('stock.xlsx', 'r') as zip_ref:
    # Read shared strings
    shared_strings_xml = zip_ref.read('xl/sharedStrings.xml')
    shared_strings_root = ET.fromstring(shared_strings_xml)
    
    # Extract shared strings
    shared_strings = []
    for si in shared_strings_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
        t = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
        if t is not None:
            shared_strings.append(t.text)
    
    print("Shared strings:", shared_strings)
    
    # Read worksheet data
    worksheet_xml = zip_ref.read('xl/worksheets/sheet1.xml')
    worksheet_root = ET.fromstring(worksheet_xml)
    
    # Extract cell data
    rows = []
    for row in worksheet_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        row_data = []
        for cell in row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            cell_value = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            cell_type = cell.get('t')
            
            if cell_value is not None:
                value = cell_value.text
                if cell_type == 's':  # shared string
                    value = shared_strings[int(value)]
                row_data.append(value)
            else:
                row_data.append('')
        
        if row_data:  # Only add non-empty rows
            rows.append(row_data)
    
    print("\nExtracted data:")
    for i, row in enumerate(rows):
        print(f"Row {i+1}: {row}")
    
    # Save as CSV
    with open('stock_data.csv', 'w') as f:
        for row in rows:
            f.write(','.join(str(cell) for cell in row) + '\n')
    
    print("\nSaved as stock_data.csv")
