# New Customer Welcome Task

## Task Description
Detect all customers who placed their very first order in the past 7 days in the store, synchronize their information from WooCommerce to the company CRM database, and automatically send a welcome email.

## Task Objectives
1. **Identify New Customers**: Identify customers who made their first purchase in the past 7 days from WooCommerce order data.
2. **Data Synchronization**: Sync new customer information to the CRM database.
3. **Send Welcome Email**: Send a personalized welcome email to each new customer.
4. **Generate Report**: Create a detailed synchronization report.

## Initial Data

### WooCommerce Order Data (`woocommerce_orders.json`)
- Contains mock data for 7 orders and 5 customers.
- New customers (placed first order in the past 7 days):
  - Customer 101: John Smith (2025-08-28)
  - Customer 102: Emily Johnson (2025-08-29)
  - Customer 103: Michael Brown (2025-08-30)
  - Customer 104: Sarah Davis (2025-09-01)
- Existing customer (not new):
  - Customer 90: Robert Wilson (first order on 2025-07-15)

### CRM Database (`crm_database.json`)
- Initially contains only one existing customer (Customer 90)
- Agent needs to add the 4 new customers to this database

### Welcome Email Template (`welcome_email_template.md`)
- Email template with personalization placeholders
- The agent must use this template to send emails

## Evaluation Criteria

### 1. New Customer Detection
- Correctly identify 4 new customers (IDs: 101, 102, 103, 104)
- Do not include the existing customer (ID: 90)

### 2. CRM Synchronization
- Add 4 new customers to the CRM database
- Include complete customer information (name, email, phone, etc.)
- Prevent duplicate entries

### 3. Email Sending
- Send welcome emails to the 4 new customers
- Use the provided template
- Record the sending status

## Required MCP Servers
- `woocommerce`: For fetching order and customer data
- `filesystem`: For reading/writing local JSON files
- `gmail`: For sending welcome emails

## File Structure
```
new-customer-welcome/
├── docs/
│   ├── agent_system_prompt.md
│   ├── task.md
│   └── user_system_prompt.md
├── evaluation/
│   └── main.py
├── initial_workspace/
│   ├── woocommerce_orders.json
│   ├── crm_database.json
│   └── welcome_email_template.md
└── task_config.json
```

## How to Run Evaluation
```bash
python evaluation/main.py \
  --agent_workspace <agent_workspace> \
  --groundtruth_workspace <initial_data_directory> \
  --res_log <execution_log_file>
```

## Expected Output
The Agent should generate:
1. `new_customer_sync_report.json` - Detailed report of the synchronization results
2. Updated `crm_database.json` - Contains the new customer information
3. Email sending log/record

Please help me complete the following new customer synchronization and welcome email task:

### Task Requirements

1. **Detect New Customers**
   - Retrieve all order data from WooCommerce within the past 7 days
   - Identify new customers within these 7 days
   - New customer definition: Customer whose first-ever order was within the past 7 days and had no previous orders before that period

2. **Synchronize to BigQuery Database**
   - Sync identified new customer information to the company’s customer database (BigQuery table `woocommerce_crm.customers`)
   - Required fields to sync:
     - Customer ID (WooCommerce ID)
     - Name (first_name, last_name)
     - Email address
     - Phone number
     - First order info (order ID, amount, date)
     - Customer type marked as "new_customer"
   - Prevent duplicate entries for already existing customers

3. **Send Welcome Email**
   - Use the provided email template (`welcome_email_template.md`) and send a personalized welcome email to each new customer

### BigQuery Configuration
- Project ID: mcp-bench0606
- Dataset: woocommerce_crm  
- Table: customers
- Use a Google Cloud service account key for authentication
