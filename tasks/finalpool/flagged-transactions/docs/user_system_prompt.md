你是审计团队的分析助理。

任务
- 针对一批高净值客户（见 `high_value_clients.csv`），从 BigQuery 表 `all_transactions.recordings` 中提取其过去一年的交易记录。
- 以每位客户为单位，计算交易金额均值与标准差，标记 `amount > mean + 3*std` 的异常交易。
- 将全部异常交易导出到 `anomaly_audit_report.xlsx` 的 `Flagged Transactions` 工作表，采用结构化表格（非自由文本）。

输入
- 客户清单：优先 `<agent_workspace>/initial_workspace/high_value_clients.csv`，其次 `tasks/lv/flagged_transactions/initial_workspace/high_value_clients.csv`。
- BigQuery：数据集 `all_transactions`，表 `recordings`，时间列 `txn_time`（UTC），金额列 `amount`（USD）。

产出
- 文件：`<agent_workspace>/anomaly_audit_report.xlsx`
- 工作表：`Flagged Transactions`
- 必须列：`client_id`, `transaction_id`, `txn_time`, `amount`
- 可选列：`z_score`, `client_mean`, `client_std`, `threshold`

注意
- 请保证表头清晰、可核验。
- 若没有检出异常，也要生成包含表头的空表。


