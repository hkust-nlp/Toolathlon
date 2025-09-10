Perform anomaly detection on high-net-worth clients’ transactions: Extract the 2025 transactions of clients in `high_value_clients.csv` from BigQuery  `all_transactions.recordings` and mark the abnormal transactions with `amount > mean + 3*std` for each client, and fill them into  `anomaly_audit_report.xlsx`, the result should be sorted by the "transaction_id" (remove the sample data  
before adding results).

