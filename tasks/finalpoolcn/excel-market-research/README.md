# Excel市场研究数据转换任务

## 任务描述
模拟市场研究分析师需要根据公司内部分类标准转换外部市场数据，计算特定门类增长率的场景。

## 输入数据
1. **Market_Data.xlsx** - 包含两个工作表的市场数据文件：
   - **Methodology工作表**：原始市场分类到公司内部分类的映射关系和权重
   - **RawData工作表**：2014-2032年各行业领域的原始市场数据

## 任务目标
Agent需要：
1. 读取并理解Market_Data.xlsx中的分类映射关系
2. 识别Appliance门类对应的组件：Electric(50%)、Construction(30%)、Furniture(20%)
3. 根据权重计算Appliance门类2015-2024年的年度增长率
4. 生成growth_rate.xlsx文件，包含计算结果

## 关键计算逻辑
- **Electric增长率** = (当年Electric值 - 前年Electric值) / 前年Electric值 × 100%
- **Construction增长率** = (当年Construction值 - 前年Construction值) / 前年Construction值 × 100%  
- **Furniture增长率** = (当年Furniture值 - 前年Furniture值) / 前年Furniture值 × 100%
- **Appliance增长率** = Electric增长率×50% + Construction增长率×30% + Furniture增长率×20%

## 评估标准
1. **本地检查**：验证growth_rate.xlsx文件是否存在并包含合理的增长率数据
2. **日志检查**：确认Agent处理过程中提及关键信息：
   - Appliance门类
   - Electric、Construction、Furniture组件
   - 50%、30%、20%权重分配
   - 增长率相关词汇
   - 2015-2024年份范围
3. **远程检查**：（暂未实现）

## 数据结构
- **原始数据**：19年市场数据（2014-2032），多个行业领域
- **计算范围**：2015-2024年增长率（10个数据点）
- **组件列位置**：Electric(G列)、Construction(K列)、Furniture(J列)

## 使用的工具
- **Excel工具**：读取Market_Data.xlsx，创建growth_rate.xlsx文件

## 输出文件格式
生成的growth_rate.xlsx应包含：
- 年份标识（2015-2024）
- 对应的Appliance门类增长率计算结果
- 清晰的数据结构和合理的数值范围
