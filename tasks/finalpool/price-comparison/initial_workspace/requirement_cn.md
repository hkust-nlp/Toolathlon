**BigQuery 存储要求：**
- 数据集：`bigquery_pricing_analysis`
- 表：`analysis`
- 完整路径：`bigquery_pricing_analysis.analysis`

**BigQuery 表结构（必填列）：**
- `产品名称`（字符串）- 使用我们内部 CSV 文件中的准确产品名称
- `我们的价格`（浮点型）- 我们的产品定价
- `竞争对手价格`（浮点型）- FutureGadget 的同类产品定价
- `差价`（浮点型）- 计算公式为 (我们的价格 - 竞争对手价格)

**数据处理要求：**
- 使用我们内部 CSV 文件中的 **产品名称** 字段作为标准产品标识符
- 根据产品功能/类别将竞争对手的产品与我们的产品进行匹配
- 计算差价，并将这 4 列精确存储在最终的 BigQuery 表中