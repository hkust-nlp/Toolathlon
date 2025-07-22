# Digital Products Store Ledger Task

## Task Description
Simulate a scenario where a digital products store owner needs to complete the store's ledger based on last week's business records.

## Input Data
1. **Account_Book.xlsx** - Excel ledger containing 120 historical transaction records (December 1, 2023 to January 6, 2024)
2. **memory.json** - Knowledge graph format data of last week's transaction records, including:
   - Product information (iPhone 15 Pro, MacBook Air, AirPods Pro)
   - Customer information (Wang Wu, Zhao Liu, Liu Qi)
   - Supplier information (Supplier A, Supplier B)
   - 5 sales and purchase transaction records (January 7-10, 2024)

## Task Objectives
The Agent needs to:
1. Read and understand the knowledge graph data in memory.json
2. Extract specific transaction information from it (date, type, product, quantity, price, customer/supplier)
3. Correctly add these transaction records to Account_Book.xlsx
4. Ensure the ledger format is correct and data is complete, with a final total of 125 records

## Evaluation Criteria
1. **Local Check**: Verify that the ledger Excel file is correctly updated with all 5 last week's transaction records
2. **Log Check**: Confirm that the Agent mentioned key transaction information during processing
3. **Remote Check**: (Not yet implemented)

## Data Scale
- **Initial Ledger**: 121 rows (including header), 120 historical transaction records
- **Complete Ledger**: 126 rows (including header), 125 transaction records
- **Knowledge Graph**: 13 entities, 15 relationships

## Tools Used
- **Memory Tool**: Read and parse knowledge graph data
- **Excel Tool**: Operate and update Excel ledger files

## Data Construction
Use the `build_excel_ledger.py` script to build all data files:
- Generate complex historical transaction data (18 products, 40+ customers, 5 suppliers)
- Create formatted Excel ledger files
- Generate corresponding knowledge graph JSON data 