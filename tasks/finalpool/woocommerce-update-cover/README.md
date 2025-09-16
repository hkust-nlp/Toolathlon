# Update Photo Task

## 任务概述

这是一个基于上周销量数据自动更新 WooCommerce 商品主图的任务。任务目标是检测 MCP Server 能否分析销量数据，找出每个可变商品销量最高的规格，并将该规格的图片设置为商品主图。

## 任务描述

根据上周销量数据更新 WooCommerce 商品主图，将销量最高的规格图片设为商品主图。

### 具体步骤

1. **确定时间范围**
   - 获取上周（周一至周日）的完整日期范围
   - 使用系统当前时间计算上周的起始和结束日期

2. **销量数据分析**
   - 遍历所有"可变商品"（Variable Products）
   - 获取每个商品下各个规格（Variation）在上周的销量数据
   - 找出每个商品销量最高的规格

3. **图片更新操作**
   - 获取销量最高规格的"变量图片"（Variation Image）
   - 将该图片设置为父商品的"主图"（Featured Image）
   - 如果销量最高的规格没有独立图片，跳过该商品

4. **结果输出**
   - 统计更新成功的商品数量
   - 提供操作摘要报告

## 技术要求

- 使用 WooCommerce MCP 服务器
- 正确处理日期范围计算
- 妥善处理异常情况（如无销量数据、无图片等）
- 提供清晰的进度反馈

## 预期结果

完成后应输出包含以下信息的报告：
- 处理的商品总数
- 成功更新的商品数量  
- 跳过的商品数量及原因
- 操作完成时间

## 文件结构

```
update-photo-task/
├── README.md                    # 本文件
├── task_config.json            # 任务配置
├── docs/
│   ├── task.md                 # 任务详细说明
│   └── user_system_prompt.md   # 用户系统提示
├── evaluation/
│   ├── main.py                 # 主评估脚本
│   └── check_content.py        # 内容检查脚本
├── preprocess/
│   ├── setup_test_products.py  # 测试产品设置
│   └── woocommerce_client.py   # WooCommerce 客户端
├── initial_workspace/          # 初始工作空间
└── groundtruth_workspace/      # 标准答案工作空间
```