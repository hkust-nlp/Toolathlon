# 低销量商品筛选和促销任务

## 项目概述

这是一个电商店铺的低销量商品自动处理系统，用于识别、分类和促销库存积压商品。系统通过分析商品的库存天数和销售数据，自动筛选出符合条件的商品，并执行相应的促销活动。

## 任务目标

识别并处理店铺中的低销量商品：
- 筛选在库天数超过90天且过去30天内销量小于10件的商品
- 将这些商品移动到"Clearance"分类
- 生成促销博客文章并发布
- 向订阅客户发送促销邮件

## 目录结构

```
filter-low-selling-products/
├── README.md                          # 项目说明文档
├── task_config.json                   # 任务配置文件
├── run_setup.py                       # 快速设置脚本
├── token_key_session.py               # 认证和会话管理
├── email_config.json                  # 邮件服务配置
│
├── docs/                              # 文档目录
│   ├── task.md                        # 任务详细说明
│   ├── agent_system_prompt.md         # AI Agent系统提示
│   └── user_system_prompt.md          # 用户系统提示
│
├── initial_workspace/                 # 初始工作区文件
│   ├── store_products.json            # 店铺商品初始数据
│   ├── subscriber.json                # 订阅客户信息
│   └── blog_template.md               # 博客文章模板
│
├── preprocess/                        # 数据预处理模块
│   ├── main.py                        # 主预处理脚本
│   ├── setup_test_products.py         # 测试商品数据设置
│   └── woocommerce_client.py          # WooCommerce API客户端
│
└── evaluation/                        # 评估模块
    ├── main.py                        # 主评估脚本
    └── check_remote.py                # 远程服务验证
```

## 核心功能

### 1. 商品筛选
- **筛选标准**：在库天数 > 90天 AND 过去30天销量 < 10件
- **数据来源**：通过WooCommerce API获取实时商品信息
- **筛选逻辑**：基于商品上架时间和销售历史数据

### 2. 分类管理
- 创建"Clearance" Product Categories
- 批量移动筛选出的商品到新分类
- 设置促销价格（建议折扣）

<!-- ### 3. 内容生成
- 基于模板生成促销博客文章
- 包含筛选商品的详细信息
- 自动填充价格和促销信息 -->

### 4. 邮件营销
- 向订阅客户发送促销邮件
- 包含商品信息和促销活动详情
- 支持批量发送和状态跟踪


## 使用方法


1. **快速设置**
```bash
python run_setup.py --agent_workspace /path/to/workspace
```

2. **手动预处理**
```bash
python preprocess/main.py --agent_workspace /path/to/workspace
```

3. **设置WooCommerce测试数据**
```bash
python preprocess/main.py --agent_workspace /path/to/workspace --setup_wc
```

### 执行任务
- 启动MCP客户端，连接所需服务器
- 参照 `docs/agent_system_prompt.md` 执行任务流程
- 系统将自动完成商品筛选、分类和促销流程

### 结果验证
```bash
python evaluation/main.py --agent_workspace /path/to/workspace
```

## 输入文件

### 初始工作区 (`initial_workspace/`)
- `store_products.json`: 包含商品ID、名称、价格、上架时间等基础信息
- `subscriber.json`: 订阅客户的邮件地址和个人信息
- `blog_template.md`: 促销博客文章的标准模板

## 输出文件

任务执行完成后生成：
- `promotion_blog_post.md`: 基于模板生成的促销博客文章
- `promotion_summary_report.md`: 详细的任务执行报告
- 邮件发送状态日志


## 评估标准

系统通过 `evaluation/` 模块进行自动化验证：
- 验证远程WooCommerce服务的 Product Categories变更
- 检查生成文件的完整性和格式
- 确认邮件发送状态和收件人覆盖

## 扩展功能

- 支持自定义筛选参数（库存天数阈值、销量阈值）
- 多种促销策略（折扣率、买一送一等）
- 邮件模板个性化和A/B测试
- 多渠道营销集成（社交媒体、短信等）

## 注意事项

**没有实现blog功能，因为看woocommerce mcp 的function list没有相关的接口。**