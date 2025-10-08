import zipfile
import xml.etree.ElementTree as ET

with zipfile.ZipFile('stock.xlsx', 'r') as zip_ref:
    # Get shared strings
    shared_xml = zip_ref.read('xl/sharedStrings.xml')
    shared_root = ET.fromstring(shared_xml)
    strings = []
    for si in shared_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}si'):
        t = si.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}t')
        if t is not None:
            strings.append(t.text)
    
    # Get worksheet data
    sheet_xml = zip_ref.read('xl/worksheets/sheet1.xml')
    sheet_root = ET.fromstring(sheet_xml)
    
    cells = {}
    for row in sheet_root.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}row'):
        for cell in row.findall('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}c'):
            ref = cell.get('r')
            val = cell.find('.//{http://schemas.openxmlformats.org/spreadsheetml/2006/main}v')
            typ = cell.get('t')
            
            if val is not None:
                value = val.text
                if typ == 's':
                    value = strings[int(value)]
                cells[ref] = value

print("Cell data:")
for ref in sorted(cells.keys()):
    print(f"{ref}: {cells[ref]}")
