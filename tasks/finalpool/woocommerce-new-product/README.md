## 核心任务流程

### 1. 新品商品筛选
- **筛选条件**: status为draft/pending状态的商品，且计划在未来30天内发布（基于scheduled_date/launch_date字段）
- **数据源**: 使用WooCommerce MCP服务器获取商品数据

### 2. 折扣商品筛选  
- **筛选条件**: 有sale_price字段设置的商品（sale_price < regular_price）
- **数据源**: 使用WooCommerce MCP服务器获取折扣商品信息

### 3. 客户分类和邮件发送
- **新品预约邮件**: 发送给订阅了自动预约提醒上新服务的顾客（subscription_preferences包含"new_product_alerts"）
- **折扣提醒邮件**: 发送给所有顾客
- **邮件服务**: 使用emails MCP服务器发送邮件