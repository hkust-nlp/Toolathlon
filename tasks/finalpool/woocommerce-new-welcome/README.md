# New Customer Welcome Task

## 任务描述
检测过去7天在店铺完成第一笔订单的所有顾客，将其信息从WooCommerce同步到公司CRM数据库，并自动发送欢迎邮件。

## 任务目标
1. **识别新客户**：从WooCommerce订单数据中识别过去7天内的首次购买客户
2. **数据同步**：将新客户信息同步到CRM数据库
3. **发送欢迎邮件**：向每位新客户发送个性化欢迎邮件
4. **生成报告**：创建详细的同步报告

## 初始数据

### WooCommerce订单数据 (`woocommerce_orders.json`)
- 包含7个订单和5个客户的模拟数据
- 新客户（过去7天首次下单）：
  - Customer 101: John Smith (2025-08-28)
  - Customer 102: Emily Johnson (2025-08-29)
  - Customer 103: Michael Brown (2025-08-30)
  - Customer 104: Sarah Davis (2025-09-01)
- 老客户：
  - Customer 90: Robert Wilson (首单在2025-07-15)

### CRM数据库 (`crm_database.json`)
- 初始只包含一个老客户（Customer 90）
- Agent需要将4个新客户添加到此数据库

### 欢迎邮件模板 (`welcome_email_template.md`)
- 包含个性化占位符的邮件模板
- Agent需要使用此模板发送邮件

## 评估标准

### 1. 新客户检测 (Customer Detection)
- 正确识别4个新客户（ID: 101, 102, 103, 104）
- 不应包含老客户（ID: 90）

### 2. CRM同步 (CRM Sync)
- 将4个新客户添加到CRM数据库
- 包含完整的客户信息（姓名、邮箱、电话等）
- 避免重复添加

### 3. 邮件发送 (Email Sending)
- 向4个新客户发送欢迎邮件
- 使用提供的模板
- 记录发送状态

## 所需MCP服务器
- `woocommerce`: 获取订单和客户数据
- `filesystem`: 读写本地JSON文件
- `gmail`: 发送欢迎邮件

## 文件结构
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

## 运行评估
```bash
python evaluation/main.py \
  --agent_workspace <agent工作目录> \
  --groundtruth_workspace <初始数据目录> \
  --res_log <执行日志文件>
```

## 预期输出
Agent应该生成：
1. `new_customer_sync_report.json` - 包含同步结果的详细报告
2. 更新的 `crm_database.json` - 包含新客户信息
3. 邮件发送记录

请帮我完成以下新客户同步和欢迎邮件发送任务：

### 任务要求

1. **检测新客户**
   - 从WooCommerce获取过去7天内的所有订单数据
   - 识别在这7天内的新客户
   - 新客户定义：在过去7天内首次下单，且之前没有任何订单记录的客户

2. **同步到BigQuery数据库**
   - 将识别出的新客户信息同步到公司的顾客数据库（BigQuery `woocommerce_crm.customers`表）
   - 需要同步的信息包括：
     - 客户ID（WooCommerce ID）
     - 姓名（first_name, last_name）
     - 邮箱地址（email）
     - 电话号码（phone）
     - 首单信息（订单ID、金额、日期）
     - 客户类型标记为"new_customer"
   - 避免重复同步已存在的客户

3. **发送欢迎邮件**
   - 使用提供的邮件模板（`welcome_email_template.md`）向每位新客户发送个性化欢迎邮件

### BigQuery配置
- 项目ID: mcp-bench0606
- 数据集: woocommerce_crm  
- 表名: customers
- 使用Google Cloud服务账号密钥进行认证
